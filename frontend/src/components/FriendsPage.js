import React, { useState, useEffect, useCallback, useRef } from 'react';
import { UserCheck, UserX, Trash2, Users, UserPlus } from 'lucide-react';
import FriendsPanel from './FriendsPanel'; // Import the new component
import FriendRequestModal from './FriendRequestModal'; // Import the new modal
import Silk from './Silk'; // Import the Silk background component
import { useToast } from './ToastContext'; // Import the useToast hook
import { supabase } from './supabaseClient'; // Import Supabase client
import * as api from '../services/api';

const FriendItem = ({ friend, type, onAccept, onReject, onRemove }) => (
    <div className="friend-item">
        <div className="friend-info">
            <div className="user-avatar-sm">{friend.avatar}</div>
            <span className="friend-name">{friend.name}</span>
        </div>
        <div className="friend-actions">
            {type === 'request' && (
                <>
                    <button onClick={() => onAccept(friend.requestId, friend.id)} title="Accept Request">
                        <UserCheck size={14} /> Accept
                    </button>
                    <button onClick={() => onReject(friend.requestId, friend.id)} title="Reject Request">
                        <UserX size={14} /> Reject
                    </button>
                </>
            )}
            {type === 'friend' && (
                <button onClick={() => onRemove(friend.id)} title="Remove Friend">
                    <Trash2 size={14} /> Remove
                </button>
            )}
        </div>
    </div>
);

const FriendsPage = ({ setChatRecipient, setCurrentPage }) => {
    const [friends, setFriends] = useState([]);
    const [requests, setRequests] = useState([]);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const { addToast } = useToast();
    
    // Cache for friends data to prevent re-fetching on every mount
    const friendsCache = useRef({ data: null, timestamp: 0 });
    const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

    const fetchData = useCallback(async () => {
        setIsLoading(true);
        try {
            const [friendsData, requestsData] = await Promise.all([
                api.getFriends(),
                api.getFriendRequests(),
            ]);
            friendsCache.current = { data: { friendsData, requestsData }, timestamp: Date.now() };
            setFriends(friendsData);
            setRequests(requestsData);

        } catch (error) {
            addToast(error.message || 'Failed to fetch friends data.', 'error');
        } finally {
            setIsLoading(false);
        }
    }, [addToast]);

    useEffect(() => {
        const now = Date.now();
        const isCacheValid = friendsCache.current.data && (now - friendsCache.current.timestamp < CACHE_DURATION);

        if (isCacheValid) {
            setFriends(friendsCache.current.data.friendsData);
            setRequests(friendsCache.current.data.requestsData);
            setIsLoading(false);
        } else {
            fetchData();
        }
    }, [fetchData]);

    const handleSendRequest = async (userId) => {
        try {
            await api.sendFriendRequest(userId);
            addToast('Friend request sent!', 'success');
            setIsModalOpen(false);
        } catch (error) {
            addToast(error.message || 'Could not send friend request.', 'error');
        }
    };

    const handleAccept = async (requestId, requesterId) => {
        const { data: { session } } = await supabase.auth.getSession();
        const currentUser = session?.user;
        if (!currentUser) {
            addToast('You must be logged in to perform this action.', 'error');
            return;
        }
        try {
            await api.acceptFriendRequest(requestId, requesterId, currentUser);
            addToast('Friend request accepted!', 'success');
            fetchData(); // Re-fetch data to update lists
        } catch (error) {
            addToast(error.message || 'Could not accept friend request.', 'error');
        }
    };

    const handleReject = async (requestId) => {
        try {
            await api.rejectFriendRequest(requestId);
            addToast('Friend request rejected.', 'info');
            fetchData(); // Re-fetch data to update lists
        } catch (error) {
            addToast(error.message || 'Could not reject friend request.', 'error');
        }
    };

    const handleRemove = async (friendId) => {
        if (window.confirm('Are you sure you want to remove this friend?')) {
            try {
                await api.removeFriend(friendId);
                addToast('Friend removed.', 'info');
                fetchData(); // Re-fetch data to update lists
            } catch (error) {
                addToast(error.message || 'Could not remove friend.', 'error');
            }
        }
    };

    const handleViewProfile = (friendId) => {
        // In a real app, this would navigate to a user profile page
        alert(`Viewing profile for: ${friendId}`);
    };

    const handleStartChat = (friend) => {
        if (!setChatRecipient || !setCurrentPage) return;
        setChatRecipient(friend);
        setCurrentPage('collaborative-agent');
    };

    return (
        <div className="page-with-silk-background">
            <div className="collaborative-agent-background">
                <Silk
                    speed={5}
                    scale={1}
                    color="#4A4458"
                    noiseIntensity={1.5}
                    rotation={0}
                />
            </div>
            <div className="collaborative-agent-content">
                <div className="friends-page">
                    <div className="friends-header">
                        <h2><Users size={28} style={{ verticalAlign: 'bottom', marginRight: '12px' }} />Manage Friends</h2>
                        <button className="button-primary" onClick={() => setIsModalOpen(true)}>
                            <UserPlus size={16} /> Add Friend
                        </button>
                    </div>

                    <FriendRequestModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onSendRequest={handleSendRequest} onSearchUsers={api.searchUsers} />

                    {requests.length > 0 && (
                        <div className="friends-list-container">
                            <h3>Friend Requests</h3>
                            <div className="friends-list">
                                {requests.map(req => (
                                    <FriendItem
                                        key={req.id}
                                        friend={req}
                                        type="request"
                                        onAccept={handleAccept}
                                        onReject={handleReject}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {isLoading ? (
                        <p style={{ padding: '0 16px', color: 'var(--text-secondary)' }}>Loading friends...</p>
                    ) : (
                        <FriendsPanel
                            friends={friends}
                            onRemove={handleRemove}
                            onViewProfile={handleViewProfile}
                            onStartChat={handleStartChat}
                        />
                    )}
                </div>
            </div>
        </div>
    );
};

export default FriendsPage;