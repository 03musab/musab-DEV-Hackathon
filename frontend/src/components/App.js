import React, { useState, useEffect, useCallback } from 'react';
import { supabase } from './supabaseClient';
import Auth from './Auth';
import Dashboard from './Dashboard.js';
import { ToastProvider, useToast } from './ToastContext';
import { NotificationProvider } from './NotificationContext.js';

function AppContent() {
    const [session, setSession] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isValidated, setIsValidated] = useState(false); // New state to track validation
    const { addToast } = useToast();
    
    const validateAndSetSession = useCallback(async (session) => {
        if (session?.user) {
            setIsValidated(false); // Reset validation status on session change
            // If there's a session, verify a profile exists.
            const { data: profile, error } = await supabase
                .from('profiles')
                .select('id')
                .eq('id', session.user.id)
                .single();

            if (profile && !error) {
                // Profile exists, session is valid.
                setSession(session);
                setIsValidated(true); // Mark as validated
            } else {
                // Profile missing or query error, session is invalid. Sign out.
                addToast('Your user profile could not be found. Please sign in again.', 'error');
                // signOut() will trigger onAuthStateChange, which will then set session to null.
                // This prevents a race condition where we set session to null, but onAuthStateChange sets it back briefly.
                supabase.auth.signOut();
                setSession(null);
                setIsValidated(true); // Validation is complete, even if it failed
            }
        } else {
            // No session.
            setSession(null);
            setIsValidated(true); // No session to validate, so we are "validated"
        }
        setLoading(false);
    }, [addToast]);

    useEffect(() => {
        // Initial check on component mount
        supabase.auth.getSession().then(({ data: { session: initialSession } }) => {
            validateAndSetSession(initialSession);
        });

        // Listen for changes in auth state (login, logout)
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            // Re-validate on every auth change to catch edge cases.
            // A login will be validated, and a logout will correctly result in a null session.
            // No need to setLoading(true) here as it's for the initial load.
            validateAndSetSession(session);
        });

        return () => subscription.unsubscribe();
    }, [validateAndSetSession]);

    if (loading) {
        return <div>Loading...</div>; // Or a spinner component
    }

    return (
        !session || !isValidated ? ( // Gate rendering on both session and validation status
            <Auth />
        ) : (
            <NotificationProvider session={session}>
                <Dashboard key={session.user.id} session={session} />
            </NotificationProvider>
        )
    );
}

function App() {
    return (
        <ToastProvider>
            <AppContent />
        </ToastProvider>
    );
}

export default App;