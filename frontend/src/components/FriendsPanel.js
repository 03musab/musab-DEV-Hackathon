import React, { useState, useMemo, useEffect } from 'react';
import { Search, Trash2, User, MessageSquare, ChevronLeft, ChevronRight } from 'lucide-react';

const ITEMS_PER_PAGE = 5;

const FriendItem = ({ friend, onRemove, onViewProfile, onStartChat }) => {
    // Mock online status for demonstration. useMemo is not needed here and can cause stale closures if not used carefully.
    const isOnline = Math.random() > 0.5;

    return (
        <div className="friend-item">
            <div className="friend-info">
                <div className={`friend-status ${isOnline ? 'online' : 'offline'}`} title={isOnline ? 'Online' : 'Offline'}></div>
                <div className="user-avatar-sm">{friend.avatar}</div>
                <span className="friend-name">{friend.name}</span>
            </div>
            <div className="friend-actions">
                <button onClick={() => onStartChat(friend)} title="Start Chat">
                    <MessageSquare size={14} /> Chat
                </button>
                <button onClick={() => onViewProfile(friend.id)} title="View Profile">
                    <User size={14} /> Profile
                </button>
                <button onClick={() => onRemove(friend.id)} title="Remove Friend">
                    <Trash2 size={14} /> Remove
                </button>
            </div>
        </div>
    );
};

const FriendsPanel = ({ friends, onRemove, onViewProfile, onStartChat }) => {
    const [searchTerm, setSearchTerm] = useState(() => sessionStorage.getItem('friendsSearchTerm') || '');
    const [currentPage, setCurrentPage] = useState(() => parseInt(sessionStorage.getItem('friendsCurrentPage'), 10) || 1);

    // Persist search term to sessionStorage
    useEffect(() => {
        sessionStorage.setItem('friendsSearchTerm', searchTerm);
    }, [searchTerm]);

    // Persist current page to sessionStorage
    useEffect(() => {
        sessionStorage.setItem('friendsCurrentPage', currentPage);
    }, [currentPage]);

    const filteredFriends = useMemo(() => {
        return friends.filter(friend =>
            friend.name.toLowerCase().includes(searchTerm.toLowerCase())
        );
    }, [friends, searchTerm]);

    const totalPages = Math.ceil(filteredFriends.length / ITEMS_PER_PAGE);
    const paginatedFriends = useMemo(() => {
        const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
        return filteredFriends.slice(startIndex, startIndex + ITEMS_PER_PAGE);
    }, [filteredFriends, currentPage]);

    const handleNextPage = () => {
        setCurrentPage(prev => Math.min(prev + 1, totalPages));
    };

    const handlePrevPage = () => {
        setCurrentPage(prev => Math.max(prev - 1, 1));
    };

    return (
        <div className="friends-list-container">
            <div className="friends-panel-header">
                <h3>Your Friends ({friends.length})</h3>
                <div className="friends-search-bar">
                    <Search size={16} className="search-icon" />
                    <input
                        type="text"
                        placeholder="Search friends..."
                        value={searchTerm}
                        onChange={(e) => {
                            setSearchTerm(e.target.value);
                            setCurrentPage(1); // Reset to first page on search
                        }}
                    />
                </div>
            </div>

            <div className="friends-list">
                {paginatedFriends.length > 0 ? (
                    paginatedFriends.map(friend => (
                        <FriendItem
                            key={friend.id}
                            friend={friend}
                            onRemove={onRemove}
                            onViewProfile={onViewProfile}
                            onStartChat={onStartChat}
                        />
                    ))
                ) : (
                    <p style={{ padding: '0 16px', color: 'var(--text-secondary)' }}>
                        {searchTerm ? 'No friends found.' : "You haven't added any friends yet."}
                    </p>
                )}
            </div>

            {totalPages > 1 && (
                <div className="pagination">
                    <button onClick={handlePrevPage} disabled={currentPage === 1}>
                        <ChevronLeft size={16} />
                    </button>
                    <span>
                        Page {currentPage} of {totalPages}
                    </span>
                    <button onClick={handleNextPage} disabled={currentPage === totalPages}>
                        <ChevronRight size={16} />
                    </button>
                </div>
            )}
        </div>
    );
};

export default FriendsPanel;