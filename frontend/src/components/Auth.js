import React, { useState, useEffect } from 'react';
import * as api from '../services/api';
import { useToast } from './ToastContext';
import './Auth.css';

const Auth = () => {
    // Note: Auth must be rendered inside ToastProvider to use useToast
    const [loading, setLoading] = useState(false);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [displayName, setDisplayName] = useState('');
    const [username, setUsername] = useState(''); // Add state for username
    const [isSignUp, setIsSignUp] = useState(false);
    const [authSuccess, setAuthSuccess] = useState(false); // New state for success
    const { addToast } = useToast();

    const handleAuth = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            if (isSignUp) {
                // Sign up the user
                const { error: signUpError } = await api.signUpUser(email, password, displayName, username);
                if (signUpError) throw signUpError;

                addToast('Check your email for the confirmation link!', 'success');
                setLoading(false); // Stop loading after showing the confirmation message
            } else {
                // Sign in the user
                const { error: signInError } = await api.signInUser(email, password);
                if (signInError) throw signInError;

                // Profile validation is now handled by the onAuthStateChange listener in App.js
                // which calls getProfile and will sign the user out if the profile is missing.

                // On successful sign-in with a valid profile, show a success message.
                setAuthSuccess(true);
                // The onAuthStateChange listener in App.js will handle the redirect.
                // We keep `loading` as true here to show the success overlay.
                // The Auth component will be unmounted automatically when the session is set in App.js,
                // which will remove the loader.
            }
        } catch (error) {
            addToast(error.error_description || error.message, 'error');
            setLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-card">
                {loading && (
                    <div className="auth-loader-overlay">
                        {authSuccess ? (
                            <div className="auth-loader-content">
                                <p>Success! Redirecting...</p>
                            </div>
                        ) : (
                            <div className="auth-loader-content">
                                <div className="spinner-big"></div>
                                <p>Processing...</p>
                            </div>
                        )}
                    </div>
                )}
                <h1 className="auth-title">{isSignUp ? 'Create Account' : 'Welcome Back'}</h1>
                <p className="auth-subtitle">
                    {isSignUp ? 'Join the platform to collaborate with AI agents.' : 'Sign in to continue to your dashboard.'}
                </p>
                <form onSubmit={handleAuth} className="auth-form">
                    {isSignUp && (
                        <div className="input-group">
                            <label htmlFor="displayName">Display Name</label>
                            <input
                                id="displayName"
                                type="text"
                                placeholder="Your Name"
                                value={displayName}
                                onChange={(e) => setDisplayName(e.target.value)}
                                required
                            />
                        </div>
                    )}
                    {isSignUp && (
                        <div className="input-group">
                            <label htmlFor="username">Username</label>
                            <input
                                id="username"
                                type="text"
                                placeholder="e.g., john_doe (lowercase, no spaces)"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                required
                            />
                        </div>
                    )}
                    <div className="input-group">
                        <label htmlFor="email">Email</label>
                        <input
                            id="email"
                            type="email"
                            placeholder="your@email.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>
                    <div className="input-group">
                        <label htmlFor="password">Password</label>
                        <input
                            id="password"
                            type="password"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>
                    <button type="submit" className="auth-button" disabled={loading}>
                        {isSignUp ? 'Sign Up' : 'Sign In'}
                    </button>
                </form>
                <div className="auth-toggle">
                    {isSignUp ? 'Already have an account?' : "Don't have an account?"}
                    <button onClick={() => setIsSignUp(!isSignUp)}>
                        {isSignUp ? 'Sign In' : 'Sign Up'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Auth;