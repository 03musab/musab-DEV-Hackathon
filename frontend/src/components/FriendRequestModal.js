import React, { useState, useEffect, useCallback } from 'react';
import { X, Send, UserPlus, Search, Loader } from 'lucide-react';

// A generic, reusable Modal component
const Modal = ({ isOpen, onClose, children }) => {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-panel" onClick={e => e.stopPropagation()}>
                <button onClick={onClose} className="modal-close-btn">
                    <X size={20} />
                </button>
                {children}
            </div>
        </div>
    );
};

// Debounce hook to prevent excessive API calls while typing
const useDebounce = (value, delay) => {
    const [debouncedValue, setDebouncedValue] = useState(value);
    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedValue(value);
        }, delay);
        return () => {
            clearTimeout(handler);
        };
    }, [value, delay]);
    return debouncedValue;
};


// The specific modal for sending friend requests
const FriendRequestModal = ({ isOpen, onClose, onSendRequest, onSearchUsers }) => {
    const [mode, setMode] = useState('search'); // 'search' or 'id'

    // State for search mode
    const [searchTerm, setSearchTerm] = useState('');
    const [results, setResults] = useState([]);
    const [selectedUser, setSelectedUser] = useState(null);
    const [isSearching, setIsSearching] = useState(false);
    const [userId, setUserId] = useState(''); // State for ID mode
    const [error, setError] = useState('');

    const debouncedSearchTerm = useDebounce(searchTerm, 300);

    // Reset state when modal opens/closes
    useEffect(() => {
        if (!isOpen) {
            setMode('search');
            setSearchTerm('');
            setResults([]);
            setSelectedUser(null);
            setError('');
            setUserId('');
            setIsSearching(false);
        }
    }, [isOpen]);

    // Effect to search for users when debounced search term changes
    useEffect(() => {
        const searchUsers = async () => {
            if (debouncedSearchTerm.trim().length < 2) {
                setResults([]);
                return;
            }
            setIsSearching(true);
            setError('');
            try {
                const data = await onSearchUsers(debouncedSearchTerm);
                setResults(data);
            } catch (err) {
                setError('Failed to search for users.');
            } finally {
                setIsSearching(false);
            }
        };

        searchUsers();
    }, [debouncedSearchTerm, onSearchUsers]);

    const handleSelectUser = (user) => {
        setSelectedUser(user);
        setSearchTerm(user.display_name);
        setResults([]);
    };

    const handleSendRequest = (e) => {
        e.preventDefault();
        setError('');
        if (mode === 'search') {
            // The button's disabled state already ensures selectedUser exists.
            onSendRequest(selectedUser.id); 
        } else { // mode === 'id'
            if (!userId.trim()) {
                setError('User ID cannot be empty.');
                return;
            }
            onSendRequest(userId.trim());
        }
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose}>
            <div className="modal-header">
                <UserPlus size={24} />
                <h3>Find & Add Friend</h3>
            </div>
            <div className="modal-tabs">
                <button className={`modal-tab-btn ${mode === 'search' ? 'active' : ''}`} onClick={() => setMode('search')}>
                    Search by Name
                </button>
                <button className={`modal-tab-btn ${mode === 'id' ? 'active' : ''}`} onClick={() => setMode('id')}>
                    Add by ID
                </button>
            </div>
            <div className="modal-content">
                {mode === 'search' ? (
                    <>
                        <p>Search for a user by their display name.</p>
                        <div className="input-group">
                            <label htmlFor="friend-search-input">Search by Name</label>
                            <div className="search-input-wrapper">
                                <Search size={16} className="search-icon-modal" />
                                <input
                                    id="friend-search-input"
                                    type="text"
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    placeholder="e.g., Jane Doe"
                                    className={error ? 'input-error' : ''}
                                    autoComplete="off"
                                />
                                {isSearching && <Loader size={16} className="search-spinner" />}
                            </div>
                            {results.length > 0 && (
                                <ul className="search-results-list">
                                    {results.map(user => (
                                        <li key={user.id} onClick={() => handleSelectUser(user)}>
                                            {user.display_name}
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    </>
                ) : (
                    <>
                        <p>Enter the exact User ID of the person you want to add.</p>
                        <div className="input-group">
                            <label htmlFor="friend-id-input">User ID</label>
                            <input
                                id="friend-id-input"
                                type="text"
                                value={userId}
                                onChange={(e) => setUserId(e.target.value)}
                                placeholder="e.g., 123e4567-e89b-12d3-a456-426614174000"
                                className={error ? 'input-error' : ''}
                            />
                        </div>
                    </>
                )}
                {error && <span className="validation-error">{error}</span>}
            </div>
            <div className="modal-actions">
                <button className="button-secondary" onClick={onClose}>Cancel</button>
                <button className="button-primary" onClick={handleSendRequest} disabled={(mode === 'search' && !selectedUser) || (mode === 'id' && !userId.trim())}>
                    <Send size={16} /> Send Request
                </button>
            </div>
        </Modal>
    );
};

export default FriendRequestModal;