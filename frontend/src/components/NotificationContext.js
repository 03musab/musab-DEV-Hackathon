import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';
import { supabase } from '../components/supabaseClient';

const NotificationContext = createContext(null);

export const useNotifications = () => {
    const context = useContext(NotificationContext);
    if (!context) {
        throw new Error('useNotifications must be used within a NotificationProvider');
    }
    return context;
};

export const NotificationProvider = ({ children, session }) => {
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshCallback, setRefreshCallback] = useState(() => () => {});

    const handleNewNotification = useCallback((payload) => {
        setNotifications(prev => [payload.new, ...prev]);
    }, []);

    const handleUpdateNotification = useCallback((payload) => {
        setNotifications(prev => prev.map(n => n.id === payload.new.id ? payload.new : n));
    }, []);

    useEffect(() => {
        if (!session?.user?.id) {
            setLoading(false);
            setNotifications([]);
            return;
        }

        const fetchNotifications = async () => {
            setLoading(true);
            const { data, error } = await supabase
                .from('notifications')
                .select('*')
                .eq('user_id', session.user.id)
                .order('created_at', { ascending: false });

            if (error) {
                console.error('Error fetching notifications:', error);
            } else {
                setNotifications(data || []);
            }
            setLoading(false);
        };

        fetchNotifications();

        const userId = session.user.id;
        const channel = supabase.channel(`user-notifications:${userId}`)
            .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'notifications', filter: `user_id=eq.${userId}` }, handleNewNotification)
            .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'notifications', filter: `user_id=eq.${userId}` }, handleUpdateNotification)
            .subscribe();

        return () => {
            supabase.removeChannel(channel);
        };
    }, [session, handleNewNotification, handleUpdateNotification]);

    const markAllAsRead = useCallback(async () => {
        const unreadIds = notifications.filter(n => !n.read).map(n => n.id);
        if (unreadIds.length > 0) {
            await supabase.from('notifications').update({ read: true }).in('id', unreadIds);
            // The UI will update automatically via the realtime subscription
        }
    }, [notifications]);

    const unreadCount = notifications.filter(n => !n.read).length;

    const value = {
        notifications,
        loading,
        unreadCount,
        markAllAsRead,
        refresh: refreshCallback, // This function will be executed
        setRefreshCallback,
    };

    return (
        <NotificationContext.Provider value={value}>
            {children}
        </NotificationContext.Provider>
    );
};