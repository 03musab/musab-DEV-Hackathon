import React, { useState, useEffect, useCallback } from 'react';
import { supabase } from './components/supabaseClient';
import * as api from './services/api';
import Auth from './components/Auth';
import Dashboard from './components/Dashboard.js';
import { ToastProvider, useToast } from './components/ToastContext';
import { NotificationProvider } from './components/NotificationContext.js';
import './App.css';

function AppContent() {
    const [session, setSession] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isValidated, setIsValidated] = useState(false); // New state to track validation
    const { addToast } = useToast();
    
    useEffect(() => {
        // By defining the validation function inside useEffect, we avoid useCallback dependencies
        // and ensure it always has the correct `addToast` reference.
        const validateAndSetSession = async (sessionToValidate) => {
            if (sessionToValidate?.user) {
                try {
                    await api.getProfile(sessionToValidate.user.id);
                    setSession(sessionToValidate);
                    setIsValidated(true);
                } catch (e) {
                    addToast(e.message, 'error');
                    api.signOutUser(); // This will trigger onAuthStateChange to nullify the session.
                }
            } else {
                // No session.
                setSession(null);
                setIsValidated(true); // No session to validate, so we are "validated" in a sense.
            }
            setLoading(false);
        };
        
        // onAuthStateChange fires immediately with the current session, so we don't need a separate getSession() call.
        // This single listener handles initial load, login, logout, and token refresh events.
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, newSession) => {
            // The listener provides the most up-to-date session state.
            // We simply pass it to our validation function.
            validateAndSetSession(newSession);
        });

        return () => subscription.unsubscribe();
    }, [addToast]); // useEffect now only depends on the stable `addToast` function.

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