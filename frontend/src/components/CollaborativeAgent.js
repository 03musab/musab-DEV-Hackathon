import React, { useState, useEffect, useRef } from 'react';
import Silk from './Silk';
import * as api from '../services/api';
import { supabase } from './supabaseClient'; // Assuming this is your Supabase client
import { useToast } from './ToastContext';
import './CollaborativeAgent.css';
import CollaborativeSessionPanel from './CollaborativeSessionPanel';
import TeamChatPanel from './TeamChatPanel'; // This will be the right-side team chat
import AgentChatPanel from './AgentChatPanel';

const CollaborativeAgent = ({ recipient }) => {
    // --- STATE MANAGEMENT ---

    const [prompt, setPrompt] = React.useState('');
    const [cooldown, setCooldown] = React.useState(0);
    const [isSubmitting, setIsSubmitting] = React.useState(false);
    const [proposal, setProposal] = React.useState(null);
    const [chatMessages, setChatMessages] = React.useState([]);
    const [agentMessages, setAgentMessages] = useState([]); // New state for AI chat
    const [chatInput, setChatInput] = useState('');
    const [currentUser, setCurrentUser] = useState(null);
    const [conversation, setConversation] = useState(null);
    const [loading, setLoading] = useState(true);
    const chatMessagesRef = useRef(null);
    const [isTyping, setIsTyping] = useState(false);
    const typingTimeoutRef = useRef(null);
    const { addToast } = useToast();
    const [theme, setTheme] = useState(() => {
        // Read theme from localStorage to apply correct background color
        return localStorage.getItem('theme') || 'dark';
    });

    // --- EFFECTS ---

    // Scroll to bottom of chat
    useEffect(() => {
        if (chatMessagesRef.current) {
            chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
        }
    }, [chatMessages]);

    // Cooldown Timer Effect
    React.useEffect(() => {
        if (cooldown > 0) {
            const timer = setTimeout(() => setCooldown(cooldown - 1), 1000);
            return () => clearTimeout(timer);
        }
    }, [cooldown]);

    // Listen for theme changes from other components
    useEffect(() => {
        const handleStorageChange = (e) => {
            if (e.key === 'theme') {
                setTheme(e.newValue || 'dark');
            }
        };
        window.addEventListener('storage', handleStorageChange);
        return () => window.removeEventListener('storage', handleStorageChange);
    }, []);

    // --- Initial Setup and Sanity Checks ---
    useEffect(() => {
        console.log('[Debug] CollaborativeAgent mounted.');

        // 1. Check for localStorage availability
        try {
            localStorage.setItem('__test', '1');
            localStorage.removeItem('__test');
            console.log('[Debug] localStorage access: OK');
        } catch (e) {
            console.error('[Debug] localStorage is not available.', e);
            addToast('Browser storage is disabled, which may affect session persistence.', 'error');
        }

        // 2. Log Supabase client config
        console.log('[Debug] Supabase client auth config:', {
            persistSession: supabase.auth.flowManager?.options?.persistSession,
            autoRefreshToken: supabase.auth.flowManager?.options?.autoRefreshToken,
        });
    }, [addToast]);
    // --- Data Fetching and Realtime Subscription ---
    useEffect(() => {
        const setupConversation = async () => {
            if (!recipient?.id) {
                setLoading(false);
                addToast('No recipient selected for the chat.', 'error');
                return;
            }

            try {
                setLoading(true);
                // 1. Get current user
                const { data: { user } } = await supabase.auth.getUser();
                if (!user) throw new Error("User not authenticated.");
                console.log('[Debug] Auth status: OK, User ID:', user.id);
                setCurrentUser(user);

                // 2. Get or create conversation
                const conv = await api.getOrCreateConversation(recipient.id);
                console.log('[Debug] Session/Conversation ID:', conv.id);
                setConversation(conv);

                // 3. Try to load state from localStorage first
                const cacheKey = `collaborativeSession_${conv.id}`;
                const cachedState = localStorage.getItem(cacheKey);

                if (cachedState) {
                    console.log(`[Debug] Restoring state from localStorage for session ${conv.id}.`);
                    const parsedState = JSON.parse(cachedState);
                    setChatMessages(parsedState.chatMessages || []);
                    setProposal(parsedState.proposal || null);
                    setAgentMessages(parsedState.agentMessages || []);
                    setPrompt(parsedState.prompt || '');
                    setChatInput(parsedState.chatInput || '');
                } else {
                    // 4. If no cache, fetch from network
                    console.log(`[Debug] No cache found. Fetching initial state for session ${conv.id}.`);
                    const initialMessages = await api.getMessages(conv.id);
                    setChatMessages(initialMessages);

                    const latestProposal = await api.getLatestProposal(conv.id);
                    if (latestProposal) setProposal(latestProposal);
                }

            } catch (error) {
                addToast(error.message || 'Failed to start chat session.', 'error');
                console.error("Error setting up conversation:", error);
            } finally {
                setLoading(false);
                // Clear cache for other conversations to avoid stale data
                Object.keys(localStorage).forEach(key => {
                    if (key.startsWith('collaborativeSession_') && !key.endsWith(recipient.id)) localStorage.removeItem(key);
                });
            }
        };

        setupConversation();
    }, [recipient, addToast]);

    // Separate effect for realtime subscription, depends on `conversation`
    useEffect(() => {
        if (!conversation?.id) return;

        // Persist state to localStorage on change
        const cacheKey = `collaborativeSession_${conversation.id}`;
        const stateToCache = {
            chatMessages,
            proposal,
            agentMessages,
            prompt,
            chatInput,
        };
        console.log(`[Debug] Caching state to localStorage for session ${conversation.id}.`);
        localStorage.setItem(cacheKey, JSON.stringify(stateToCache));

    }, [chatMessages, proposal, agentMessages, prompt, chatInput, conversation?.id]);

    useEffect(() => {
        if (!conversation?.id) return;

        const channel = supabase.channel(`session-${conversation.id}`, {
            config: {
                broadcast: {
                    self: false
                }, // Don't receive our own broadcasts
            },
        });

        const handleMessageUpdate = (payload) => {
            console.log('[Debug] Realtime: Received message update:', payload);
            switch (payload.eventType) {
                case 'INSERT':
                    // Add new message if it's not from the current user (already handled optimistically)
                    if (payload.new.sender_id !== currentUser?.id) {
                        setChatMessages(current => [...current, payload.new]);
                    }
                    break;
                case 'UPDATE':
                    // Update a message in the list
                    setChatMessages(current => current.map(m => m.id === payload.new.id ? payload.new : m));
                    break;
                case 'DELETE':
                    // Remove a message from the list
                    setChatMessages(current => current.filter(m => m.id !== payload.old.id));
                    break;
                default:
                    break;
            }
        };

        const handleProposalUpdate = (payload) => {
            console.log('[Debug] Realtime: Received proposal update:', payload);
            // If a new proposal is created, set it as the current one.
            if (payload.eventType === 'INSERT') {
                setProposal(payload.new);
                setIsSubmitting(false); // Unlock UI for both users
                setCooldown(5); // Set cooldown after agent responds
            }
            // If the existing proposal is updated (e.g., by the agent or another user)
            else if (payload.eventType === 'UPDATE' && payload.new.id === proposal?.id) {
                setProposal(payload.new);
                // When the task is approved, show a processing indicator in the agent chat
                if (payload.new.status === 'approved' && payload.old.status !== 'approved') {
                    // --- MOCK DEMO LOGIC ---
                    // If it's a mock proposal, handle it on the frontend
                    if (payload.new.metadata?.isMock) {
                        const processingMessage = { id: `processing-${payload.new.id}`, type: 'system', content: `Processing task: "${payload.new.title}"...` };
                        setAgentMessages(prev => [...prev.filter(m => m.type !== 'system'), processingMessage]);
                        
                        // Simulate processing time and then show the mock response
                        setTimeout(() => {
                            const mockResponseMessage = { id: `analysis-${payload.new.id}`, type: 'agent', content: payload.new.metadata.mockResponse };
                            setAgentMessages(prev => [...prev.filter(m => !m.id.startsWith('processing-')), mockResponseMessage]);
                        }, 1500);
                        return; // Stop here for mock proposals
                    }
                    // --- END MOCK DEMO LOGIC ---
                    const processingMessage = { id: `processing-${payload.new.id}`, type: 'system', content: `Processing task: "${payload.new.title}"...` };
                    // Remove any previous rejection messages and add the new processing one
                    setAgentMessages(prev => [...prev.filter(m => m.type !== 'system'), processingMessage]);
                }
                // If the agent has finished processing, add its analysis to the chat
                if (payload.new.status === 'processed' && payload.old.status !== 'processed') {
                    const analysisMessage = { id: `analysis-${payload.new.id}`, type: 'agent', content: payload.new.agent_analysis || "Agent finished but provided no response." };
                    // Replace the "Processing..." message with the final analysis
                    setAgentMessages(prev => [...prev.filter(m => !m.id.startsWith('processing-')), analysisMessage]);
                }
                // If the task was interrupted by the user
                if (payload.new.status === 'interrupted' && payload.old.status !== 'interrupted') {
                    const interruptedMessage = { id: `interrupted-${payload.new.id}`, type: 'system', content: `Processing stopped by user.` };
                    // Replace the "Processing..." message with the "Stopped" message
                    setAgentMessages(prev => [...prev.filter(m => !m.id.startsWith('processing-')), interruptedMessage]);
                }
                // If the task was rejected and processed by the Cerebras model
                if (payload.new.status === 'rejected_processed' && payload.old.status !== 'rejected_processed') {
                    const rejectionResponseMessage = { id: `rejection-response-${payload.new.id}`, type: 'agent', content: payload.new.agent_analysis };
                    setAgentMessages(prev => [...prev, rejectionResponseMessage]);
                }
            }
        };

        const handleTypingEvent = (payload) => {
            console.log('[Debug] Realtime: Received broadcast event:', payload);
            setIsTyping(payload.isTyping);
            if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
            typingTimeoutRef.current = setTimeout(() => setIsTyping(false), 3000); // Typing indicator disappears after 3s
        };

        channel
            .on('postgres_changes', { event: '*', schema: 'public', table: 'messages', filter: `conversation_id=eq.${conversation.id}` }, handleMessageUpdate)
            .on('postgres_changes', { event: '*', schema: 'public', table: 'proposals', filter: `conversation_id=eq.${conversation.id}` }, handleProposalUpdate)
            .on('broadcast', { event: 'typing' }, handleTypingEvent)
            .subscribe((status) => {
                console.log(`[Debug] Realtime channel 'session-${conversation.id}' status:`, status);
                if (status === 'SUBSCRIBED') {
                    console.log(`[Debug] Successfully connected to Realtime for session ${conversation.id}.`);
                } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
                    addToast(`Realtime connection issue: ${status}. Some features may not work.`, 'error');
                }
            });
        // Cleanup subscription on component unmount
        return () => {
            supabase.removeChannel(channel);
        };
    }, [conversation?.id, currentUser?.id, proposal?.id, addToast]); // proposal?.id is needed to avoid stale closures in handleProposalUpdate

    const handleChatSubmit = async (e) => {
        e.preventDefault();
        if (!chatInput.trim() || !conversation) return;
    
        const content = chatInput;
        setChatInput('');
    
        // Optimistic UI update: Add the message to the state immediately.
        // Supabase doesn't broadcast back to the sender by default.
        const optimisticMessage = {
            id: `temp-${Date.now()}`, // Temporary unique ID
            conversation_id: conversation.id,
            sender_id: currentUser.id,
            content: content,
            created_at: new Date().toISOString(),
        };
    
        setChatMessages(currentMessages => [...currentMessages, optimisticMessage]);
    
        try {
            console.log('[Debug] Sending chat message:', { conversationId: conversation.id, content });
            await api.sendMessage(conversation.id, content);
            // The message is sent. The realtime subscription will handle updates for the other user.
        } catch (error) {
            addToast('Failed to send message. Please try again.', 'error');
            // If sending fails, remove the optimistic message.
            setChatMessages(currentMessages => currentMessages.filter(msg => msg.id !== optimisticMessage.id));
        }
    };

    const handleChatInputChange = (e) => {
        setChatInput(e.target.value);
        if (conversation) {
            const channel = supabase.channel(`session-${conversation.id}`);
            // Broadcast that this user is typing
            channel.send({
                type: 'broadcast',
                event: 'typing',
                payload: { isTyping: e.target.value.length > 0 },
            });
        }
    };

    const handlePromptSubmit = async (e) => {
        e.preventDefault();
        if (!prompt.trim() || !conversation || isSubmitting || cooldown > 0) return;

        setIsSubmitting(true);

        // Optimistically add user's message to the agent chat
        const userMessage = {
            id: `user-prompt-${Date.now()}`,
            type: 'user',
            content: prompt,
            sender_name: currentUser?.user_metadata?.display_name || 'You',
        };
        setAgentMessages(prev => [...prev, userMessage]);

        // If there's no active proposal, create one. This is the "task submission".
        // If there IS an active proposal, this is a follow-up question.
        try {
            // Only allow creating a new proposal if there isn't one or the current one is fully processed/rejected.
            if (!proposal || ['processed', 'rejected_processed'].includes(proposal.status)) {
                console.log('[Debug] Submitting new task proposal:', { conversationId: conversation.id, prompt });
                await api.createProposal(conversation.id, prompt);
            }
            setPrompt(''); // Clear input after submission
        } catch (error) {
            addToast(error.message || 'Failed to submit prompt to agent.', 'error');
            // Revert optimistic update on error
            setAgentMessages(prev => prev.filter(m => m.id !== userMessage.id));
        } finally {
            // isSubmitting will be set to false by the realtime 'INSERT' handler for proposals
        }
    };

    // --- HANDLERS ---


    const handleApproval = async (decision) => {
        if (!proposal || !currentUser) return;
    
        const newApprovals = {
            ...proposal.approvals,
            [currentUser.id]: decision
        };
    
        // Optimistically update the UI
        setProposal(p => ({ ...p, approvals: newApprovals }));
    
        // Update the database, which will trigger a realtime broadcast
        try {
            console.log('[Debug] Submitting approval:', { proposalId: proposal.id, decision });
            await api.updateProposalApprovals(proposal.id, newApprovals);
    
            // --- New Logic: Check if all users have approved ---
            const sessionUsers = [currentUser, recipient].filter(Boolean);
            const totalUsers = sessionUsers.length;
            const approvals = Object.values(newApprovals).filter(d => d === 'approved').length;
            const rejections = Object.values(newApprovals).filter(d => d === 'rejected').length;
    
            // Case 1: All users approved
            if (approvals === totalUsers) {
                console.log('[Debug] All users approved. Setting status to "approved".');
                await api.updateProposalStatus(proposal.id, 'approved');
            }
            // Case 2: All users rejected
            else if (rejections === totalUsers) {
                console.log('[Debug] All users rejected. Setting status to "rejected" for Cerebras model processing.');
                await api.updateProposalStatus(proposal.id, 'rejected');
            }
            // Case 3: At least one user has rejected, but not all
            else if (rejections > 0) {
                console.log('[Debug] Partial rejection detected. Displaying system message.');
                const rejectionMessage = {
                    id: `system-rejection-${proposal.id}`,
                    type: 'system',
                    content: 'Task rejected because one user has declined approval.',
                };
                // Add message only if it doesn't already exist to prevent duplicates
                setAgentMessages(prev => {
                    if (prev.find(m => m.id === rejectionMessage.id)) {
                        return prev;
                    }
                    return [...prev, rejectionMessage];
                });
            }
            // --- End of New Logic ---
    
        } catch (error) {
            addToast(error.message || 'Failed to sync approval. Please try again.', 'error');
            // Revert optimistic update on error
            setProposal(p => ({ ...p, approvals: proposal.approvals }));
        }
    };

    const getApprovalStatus = (userId) => {
        if (!proposal) return null;
        return proposal.approvals[userId];
    };

    const handleClearAgentChat = () => {
        setAgentMessages([]);
        addToast('Agent chat has been cleared.', 'info');
    };

    const handleClearSession = () => {
        setProposal(null);
        setAgentMessages([]);
        setPrompt('');
        addToast('Collaborative session has been reset.', 'info');
    };

    const handleMockPromptClick = async (mockPrompt, mockResponse) => {
        if (!conversation || isSubmitting || cooldown > 0) return;

        // This function now behaves like handlePromptSubmit, but for mock data.
        setIsSubmitting(true);

        const userMessage = {
            id: `user-prompt-${Date.now()}`,
            type: 'user',
            content: mockPrompt,
            sender_name: currentUser?.user_metadata?.display_name || 'You',
        };
        setAgentMessages(prev => [...prev, userMessage]);

        try {
            // Create a real proposal but tag it with mock data in its metadata
            await api.createProposal(conversation.id, mockPrompt, { isMock: true, mockResponse: mockResponse });
        } catch (error) {
            addToast(error.message || 'Failed to create mock proposal.', 'error');
            setAgentMessages(prev => prev.filter(m => m.id !== userMessage.id));
        }
    };

    const handleInterruptAgent = async () => {
        if (!proposal || proposal.status !== 'approved') return;
        try {
            await api.interruptProposal(proposal.id);
            addToast('Agent processing has been stopped.', 'info');
        } catch (error) {
            addToast(error.message || 'Failed to stop the agent.', 'error');
        }
    };

    // --- RENDER LOGIC ---
    if (loading) {
        return (
            <div className="collaborative-agent-page">
                <div className="loading-overlay">Loading Collaborative Session...</div>
            </div>
        );
    }
    return (
        <div className="collaborative-agent-page">
            <div className="collaborative-agent-background">
                <Silk
                    speed={5}
                    scale={1}
                    color={theme === 'dark' ? '#4A4458' : '#E5E7EB'}
                    noiseIntensity={1.5}
                    rotation={0}
                />
            </div>
            <div className="collaborative-agent-content">
                <div className="collaborative-workspace-grid">
                    {/* Left Panel: Collaborative Session & Approvals */}
                    <CollaborativeSessionPanel
                        currentUser={currentUser}
                        recipient={recipient}
                        proposal={proposal}
                        handleApproval={handleApproval}
                        getApprovalStatus={getApprovalStatus}
                        onClearSession={handleClearSession}
                    />

                    {/* Middle Panel: Agent Chat */}
                    <AgentChatPanel
                        prompt={prompt}
                        setPrompt={setPrompt}
                        handlePromptSubmit={handlePromptSubmit}
                        isSubmitting={isSubmitting}
                        cooldown={cooldown}
                        proposal={proposal}
                        agentMessages={agentMessages}
                        onClearChat={handleClearAgentChat}
                        onInterrupt={handleInterruptAgent}
                        onMockPromptClick={handleMockPromptClick}
                    />

                    {/* Right Panel: Team Chat */}
                    <TeamChatPanel
                        chatMessages={chatMessages}
                        currentUser={currentUser}
                        recipient={recipient}
                        isTyping={isTyping}
                        handleChatSubmit={handleChatSubmit}
                        chatInput={chatInput}
                        handleChatInputChange={handleChatInputChange}
                        chatMessagesRef={chatMessagesRef}
                    />
                </div>
            </div>
        </div>
    );
};

export default CollaborativeAgent;