import React, { useState, useEffect, useRef } from 'react';
import { Bell, UserPlus, UserCheck, UserX, Trash2, Check, X } from 'lucide-react';
import { useNotifications } from './NotificationContext.js';
import { supabase } from './supabaseClient';
import * as api from '../services/api';

const notificationDetails = {
    request_received: { icon: <UserPlus size={20} />, color: 'var(--accent-color)' },
    request_accepted: { icon: <UserCheck size={20} />, color: '#34D399' },
    request_rejected: { icon: <UserX size={20} />, color: '#F4B400' },
    friend_removed: { icon: <Trash2 size={20} />, color: '#ef4444' },
};

const NotificationItem = ({ notification, onAction }) => {
    const details = notificationDetails[notification.type];

    const handleAccept = async (e) => {
        e.stopPropagation();
        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user || !notification.data?.friendship_id) return;
            await api.acceptFriendRequest(notification.data.friendship_id, notification.data.sender_id, user);
            await supabase.from('notifications').update({ read: true }).eq('id', notification.id);
            if (onAction) onAction();
        } catch (error) {
            // Optionally show a toast notification here
        }
    };

    const handleReject = async (e) => {
        e.stopPropagation();
        try {
            if (!notification.data?.friendship_id) return;
            await api.rejectFriendRequest(notification.data.friendship_id);
            await supabase.from('notifications').delete().eq('id', notification.id);
            if (onAction) onAction();
        } catch (error) {
            // Optionally show a toast notification here
        }
    };

    const getMessage = () => {
        switch (notification.type) {
            case 'request_received':
                return <><strong>{notification.data?.sender_name || 'Someone'}</strong> sent you a friend request.</>
            case 'request_accepted':
                return <><strong>{notification.data?.sender_name || 'Someone'}</strong> accepted your friend request.</>
            case 'request_rejected':
                return <>Your friend request to <strong>{notification.data?.sender_name || 'Someone'}</strong> was rejected.</>
            case 'friend_removed':
                return <>You are no longer friends with <strong>{notification.data?.sender_name || 'Someone'}</strong>.</>
            default:
                return 'New notification';
        }
    };

    return (
        <div className={`notification-item ${notification.read ? '' : 'unread'}`}>
            <div className="notification-icon" style={{ color: details?.color }}>
                {details?.icon}
            </div>
            <div className="notification-content">
                <p className="notification-message">{getMessage()}</p>
                {notification.type === 'request_received' && !notification.read && (
                    <div className="notification-actions">
                        <button className="notification-action-btn accept" onClick={handleAccept}>
                            <Check size={14} /> Accept
                        </button>
                        <button className="notification-action-btn reject" onClick={handleReject}>
                            <X size={14} /> Reject
                        </button>
                    </div>
                )}
                <span className="notification-time">{new Date(notification.created_at).toLocaleString()}</span>
            </div>
        </div>
    );
};

const NotificationDropdown = () => {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef(null);

    // Consume the global notification state
    const { notifications, loading, unreadCount, markAllAsRead, refresh } = useNotifications();

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleToggle = async () => {
        setIsOpen(!isOpen);
        // When opening the dropdown and there are unread non-actionable notifications
        if (!isOpen && unreadCount > 0) {
            // We now only mark non-actionable notifications as read on open.
            // Friend requests will be marked as read upon action.
            markAllAsRead();
        }
    };

    return (
        <div className="notification-dropdown" ref={dropdownRef}>
            <button onClick={handleToggle} className="notification-bell-btn">
                <Bell size={20} />
                {unreadCount > 0 && <span className="notification-badge">{unreadCount}</span>}
            </button>

            {isOpen && (
                <div className="notification-panel">
                    <div className="notification-panel-header">
                        <h3>Notifications</h3>
                        {/* The "Mark all as read" action is now triggered on open */}
                    </div>
                    <div className="notification-list">
                        {loading ? (
                            <div className="notification-empty-state"><p>Loading...</p></div>
                        ) : notifications.length > 0 ? (
                            notifications.map(n => <NotificationItem key={n.id} notification={n} onAction={refresh} />)
                        ) : (
                            <div className="notification-empty-state">
                                <p>You're all caught up!</p>
                            </div>
                        )}
                    </div>
                    <div className="notification-panel-footer">
                        <a href="#">View all notifications</a>
                    </div>
                </div>
            )}
        </div>
    );
};

export default NotificationDropdown;