import { supabase } from '../components/supabaseClient';
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

/**
 * A helper function to handle fetch requests and JSON parsing.
 * @param {string} url - The URL to fetch.
 * @param {object} options - The options for the fetch request.
 * @returns {Promise<any>} - The JSON response.
 */
const fetchJson = async (url, options = {}) => {
    const response = await fetch(url, options);
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Network response was not ok' }));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }
    return response.json();
};

/**
 * Sends a chat message to the backend.
 * @param {string} message - The user's message.
 * @param {Array<Array<string>>} history - The conversation history.
 * @returns {Promise<object>} - The agent's response and log.
 */
export const postChatMessage = (message, history) => {
    return fetchJson(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message, history }),
    });
};

/**
 * Uploads a file to the backend for ingestion.
 * @param {File} file - The file to upload.
 * @returns {Promise<object>} - The status of the upload.
 */
export const uploadFile = (file) => {
    const formData = new FormData();
    formData.append('file', file);

    return fetchJson(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
    });
};

/**
 * =================================================================
 * Auth & Profile API (Supabase)
 * =================================================================
 */

export const signUpUser = (email, password, displayName, username) => {
    return supabase.auth.signUp({
        email,
        password,
        options: {
            data: {
                display_name: displayName,
                username: username.toLowerCase().trim()
            },
        },
    });
};

export const signInUser = (email, password) => {
    return supabase.auth.signInWithPassword({ email, password });
};

export const signOutUser = () => {
    return supabase.auth.signOut();
};

export const getProfile = async (userId) => {
    const { data, error, status } = await supabase
        .from('profiles')
        .select(`id, display_name`)
        .eq('id', userId)
        .single();

    if (error) {
        if (status === 406) { // PGRST116: "exact one row was not found"
            throw new Error('Your user profile could not be found. Please sign in again.');
        }
        throw error;
    }
    return data;
};

export const searchUsers = async (searchTerm) => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user || !searchTerm) return [];

    const { data, error } = await supabase
        .from('profiles')
        .select('id, display_name')
        .ilike('display_name', `%${searchTerm}%`)
        .neq('id', user.id)
        .limit(10);

    if (error) throw error;

    return data.map(profile => ({ ...profile, avatar: profile.display_name?.substring(0, 2).toUpperCase() || '??' }));
};


/**
 * =================================================================
 * Friends API (Supabase)
 * =================================================================
 */

export const getFriends = async () => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return [];

    const { data, error } = await supabase
        .from('friends')
        .select('user_id_1(id, display_name), user_id_2(id, display_name)')
        .or(`user_id_1.eq.${user.id},user_id_2.eq.${user.id}`)
        .eq('status', 'accepted');

    if (error) throw error;

    return data.map(friendship => {
        const friendProfile = friendship.user_id_1.id === user.id ? friendship.user_id_2 : friendship.user_id_1;
        return {
            id: friendProfile.id,
            name: friendProfile.display_name,
            avatar: friendProfile.display_name?.substring(0, 2).toUpperCase() || '??'
        };
    });
};

export const getFriendRequests = async () => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return [];

    const { data, error } = await supabase
        .from('friends')
        .select('id, requested_by(id, display_name)')
        .or(`user_id_1.eq.${user.id},user_id_2.eq.${user.id}`)
        .eq('status', 'pending')
        .neq('requested_by', user.id);

    if (error) throw error;

    return data.map(req => ({
        id: req.requested_by.id,
        requestId: req.id,
        name: req.requested_by.display_name,
        avatar: req.requested_by.display_name?.substring(0, 2).toUpperCase() || '??'
    }));
};

export const sendFriendRequest = async (recipientId) => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) throw new Error("User not authenticated");

    const [user_id_1, user_id_2] = [user.id, recipientId].sort();

    const { data: friendship, error: insertError } = await supabase.from('friends').insert({
        user_id_1,
        user_id_2,
        requested_by: user.id,
        status: 'pending'
    }).select('id').single();

    if (insertError || !friendship) {
        throw new Error("Could not create friend request.");
    }

    await createNotification(recipientId, 'request_received', {
        friendship_id: friendship.id,
        sender_id: user.id,
        sender_name: user.user_metadata?.display_name || user.email
    });

    return { status: 'success' };
};

export const acceptFriendRequest = async (requestId, requesterId, currentUser) => {
    const { error } = await supabase
        .from('friends')
        .update({ status: 'accepted', updated_at: new Date().toISOString() })
        .eq('id', requestId);
    if (error) throw error;

    // Create a notification for the user who sent the request
    await createNotification(
        requesterId,
        'request_accepted',
        {
            sender_id: currentUser.id,
            sender_name: currentUser.user_metadata?.display_name || currentUser.email
        }
    );
    return { status: 'success' };
};

export const rejectFriendRequest = (requestId) => {
    return supabase.from('friends').delete().eq('id', requestId);
};

export const removeFriend = async (friendId) => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) throw new Error("User not authenticated");

    const { error: deleteError } = await supabase
        .from('friends')
        .delete()
        .or(
            `and(user_id_1.eq.${user.id},user_id_2.eq.${friendId}),` +
            `and(user_id_1.eq.${friendId},user_id_2.eq.${user.id})`
        )
        .eq('status', 'accepted');

    if (deleteError) throw deleteError;

    // Create a notification for the user who was removed
    await createNotification(friendId, 'friend_removed', {
        sender_id: user.id,
        sender_name: user.user_metadata?.display_name || user.email
    });

    return { status: 'success' };
};

/**
 * =================================================================
 * Notifications API (Supabase)
 * =================================================================
 */

export const createNotification = (userId, type, data) => {
    return supabase.from('notifications').insert({ user_id: userId, type, data });
};

/**
 * =================================================================
 * Conversation/Chat API (Supabase)
 * =================================================================
 */

/**
 * Gets an existing conversation between two users or creates a new one.
 * @param {string} recipientId - The ID of the other user in the conversation.
 * @returns {Promise<object>} The conversation object.
 */
export const getOrCreateConversation = async (recipientId) => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) throw new Error("User not authenticated.");

    // Sort IDs to ensure consistency in the database (user_id_1 < user_id_2)
    const [user_id_1, user_id_2] = [user.id, recipientId].sort();

    // Check if a conversation already exists
    const { data: existingConv, error: existingError } = await supabase
        .from('conversations')
        .select('*')
        .eq('user_id_1', user_id_1)
        .eq('user_id_2', user_id_2)
        .single();

    if (existingError && existingError.code !== 'PGRST116') { // PGRST116 = no rows found
        throw existingError;
    }

    if (existingConv) {
        return existingConv;
    }

    // If not, create a new one
    const { data: newConv, error: insertError } = await supabase
        .from('conversations')
        .insert({ user_id_1, user_id_2 })
        .select()
        .single();

    if (insertError) throw insertError;

    return newConv;
};

/**
 * Fetches all messages for a given conversation.
 * @param {string} conversationId - The ID of the conversation.
 * @returns {Promise<Array<object>>} An array of message objects.
 */
export const getMessages = async (conversationId) => {
    const { data, error } = await supabase
        .from('messages')
        .select('*')
        .eq('conversation_id', conversationId)
        .order('created_at', { ascending: true });

    if (error) throw error;
    return data;
};

export const sendMessage = async (conversationId, content) => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) throw new Error("User not authenticated.");

    const { error } = await supabase.from('messages').insert({
        conversation_id: conversationId,
        sender_id: user.id,
        content: content,
    });

    if (error) throw error;
    return { status: 'success' };
};

/**
 * Creates a new proposal for an agent to act on within a conversation.
 * This is the entry point for a collaborative agent prompt.
 * @param {string} conversationId - The ID of the conversation.
 * @param {string} prompt - The user's prompt for the agent.
 * @returns {Promise<object>} The newly created proposal object.
 */
export const createProposal = async (conversationId, prompt, metadata = {}) => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) throw new Error("User not authenticated.");

    const { data: newProposal, error } = await supabase
        .from('proposals')
        .insert({
            conversation_id: conversationId,
            requested_by: user.id,
            title: `Agent Task: "${prompt.substring(0, 40)}..."`,
            content: prompt, // The agent will process this content
            status: 'pending', // The agent will pick up 'pending' proposals
            approvals: {}, // Approvals start empty
            metadata: metadata, // Store mock data here
        })
        .select()
        .single();

    if (error) throw error;
    return newProposal;
};
/**
 * =================================================================
 * Proposals API (Supabase)
 * =================================================================
 */

/**
 * Fetches the latest proposal for a given conversation.
 * @param {string} conversationId - The ID of the conversation.
 * @returns {Promise<object|null>} The latest proposal object or null.
 */
export const getLatestProposal = async (conversationId) => {
    const { data, error } = await supabase
        .from('proposals')
        .select('*')
        .eq('conversation_id', conversationId)
        .order('created_at', { ascending: false })
        .limit(1)
        .single();

    if (error && error.code !== 'PGRST116') throw error; // Ignore "no rows found"
    return data;
};

/**
 * Updates the approval status of a proposal.
 * @param {string} proposalId - The ID of the proposal to update.
 * @param {object} newApprovals - The updated approvals object.
 * @returns {Promise<object>} The result of the update operation.
 */
export const updateProposalApprovals = async (proposalId, newApprovals) => {
    const { error } = await supabase
        .from('proposals')
        .update({ approvals: newApprovals, updated_at: new Date().toISOString() })
        .eq('id', proposalId);

    if (error) throw error;
    return { status: 'success' };
};

/**
 * Updates the status of a proposal.
 * @param {string} proposalId - The ID of the proposal to update.
 * @param {string} status - The new status (e.g., 'approved', 'running').
 * @returns {Promise<object>} The result of the update operation.
 */
export const updateProposalStatus = async (proposalId, status) => {
    const { error } = await supabase
        .from('proposals')
        .update({ status: status, updated_at: new Date().toISOString() })
        .eq('id', proposalId);

    if (error) throw error;
    return { status: 'success' };
};

/**
 * Sends a signal to interrupt an in-progress agent task.
 * @param {string} proposalId - The ID of the proposal to interrupt.
 * @returns {Promise<object>} The result of the interrupt request.
 */
export const interruptProposal = (proposalId) => {
    return fetchJson(`${API_BASE_URL}/proposal/${proposalId}/interrupt`, {
        method: 'POST',
    });
};
