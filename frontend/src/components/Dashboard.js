import React, { useState, useEffect } from 'react';
import * as api from '../services/api.js';
import { LogOut, PanelLeft, MessageSquarePlus, Users, ArrowLeft } from 'lucide-react';
import SplitText from "./SplitText"; // Import the new component
import ThemeToggle from './ThemeToggle';
import Chat from './Chat';
import FileUpload from './FileUpload';
import AgentLog from './AgentLog';
import CollaborativeAgent from './CollaborativeAgent'; // Import the new component
import FriendsPage from './FriendsPage'; // Import the Friends page component
import NotificationDropdown from './NotificationDropdown'; // Import the new component
import { useToast } from './ToastContext';
import '../App.css'; // Assuming Dashboard can use App's styles

// Layout Component to wrap pages and provide consistent header/structure
const DashboardLayout = ({ children, session, profile, loadingProfile, handleSignOut, currentPage, onBack, className }) => {
    const isDashboard = currentPage === 'dashboard';

    return (
        <div className={`App ${className || ''}`}>
            <header className="App-header">
                <div className="navbar-brand">
                    {isDashboard ? (
                        <h3>AI Agent Dashboard</h3>
                    ) : (
                        <button onClick={onBack} className="back-button-header">
                            <ArrowLeft size={18} />
                            <h3>Back to Dashboard</h3>
                        </button>
                    )}
                </div>
                <div className="user-info">
                    <span>Welcome, {loadingProfile ? '...' : profile?.display_name || session.user.email}!</span>
                    <NotificationDropdown />
                    <ThemeToggle />
                    <button onClick={handleSignOut} className="sign-out-button">
                        <LogOut size={16} /> Sign Out
                    </button>
                </div>
            </header>
            {children}
        </div>
    );
};


const Dashboard = ({ session }) => {
    const [loadingProfile, setLoadingProfile] = useState(true);
    const [profile, setProfile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
        const [chatKey, setChatKey] = useState(() => {
        const savedChatKey = sessionStorage.getItem('chatKey');
        return savedChatKey ? JSON.parse(savedChatKey) : Date.now();
    });
    const [agentLog, setAgentLog] = useState([]);
    const [isLogLoading, setIsLogLoading] = useState(false);
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
        return sessionStorage.getItem('isSidebarCollapsed') === 'true';
    });
    const [isAgentLogCollapsed, setIsAgentLogCollapsed] = useState(() => {
        return sessionStorage.getItem('isAgentLogCollapsed') === 'true';
    });

    const { addToast } = useToast();
    // Use sessionStorage to ensure the animation only plays once per session.
    const [showWelcome, setShowWelcome] = useState(() => {
        // If the flag is not set, show the animation.
        return !sessionStorage.getItem('welcomeAnimationPlayed');
    });
    const [isFadingOut, setIsFadingOut] = useState(false);

    // State to control the main dashboard fade-in animation.
    const [shouldFadeIn, setShouldFadeIn] = useState(() => {
        // If the flag is not set, we should play the animation.
        return !sessionStorage.getItem('dashboardHasFadedIn');
    });

    // Use sessionStorage to persist the current page across reloads/tab switches
    const [currentPage, setCurrentPage] = useState(() => {
        return localStorage.getItem('currentPage') || 'dashboard';
    });

    // Temp state to hold the user we want to chat with
    const [chatRecipient, setChatRecipient] = useState(() => {
        const savedRecipient = sessionStorage.getItem('chatRecipient');
        return savedRecipient ? JSON.parse(savedRecipient) : null;
    });

    // Lift the messages state to the Dashboard
    const [messages, setMessages] = useState(() => {
        const savedMessages = sessionStorage.getItem('chatMessages');
        return savedMessages ? JSON.parse(savedMessages) : [];
    });
    // Effect to save the chat recipient to sessionStorage whenever it changes
    useEffect(() => {
        if (chatRecipient) sessionStorage.setItem('chatRecipient', JSON.stringify(chatRecipient));
    }, [chatRecipient]);
    
    useEffect(() => {
        const fetchProfile = async () => {
            try {
                setLoadingProfile(true);
                const data = await api.getProfile(session.user.id);
                if (data) setProfile(data);
            } catch (error) {
                addToast(error.message, 'error');
            } finally {
                setLoadingProfile(false);
            }
        };
        fetchProfile();
    }, [session, addToast]);

    // Effect to save the current page to sessionStorage whenever it changes
    useEffect(() => {
        localStorage.setItem('currentPage', currentPage);
    }, [currentPage]);

    // Effect to save messages to sessionStorage
    useEffect(() => {
        sessionStorage.setItem('chatMessages', JSON.stringify(messages));
    }, [messages]);

    // Effect to save sidebar collapsed state
    useEffect(() => {
        sessionStorage.setItem('isSidebarCollapsed', isSidebarCollapsed);
    }, [isSidebarCollapsed]);

    // Effect to save agent log collapsed state
    useEffect(() => {
        sessionStorage.setItem('isAgentLogCollapsed', isAgentLogCollapsed);
    }, [isAgentLogCollapsed]);

    useEffect(() => {
        sessionStorage.setItem('chatKey', JSON.stringify(chatKey));
    }, [chatKey]);

    // Effect to set the fade-in flag after the welcome animation is done.
    // This is more reliable than setting it in the render body.
    useEffect(() => {
        if (shouldFadeIn && !showWelcome) {
            sessionStorage.setItem('dashboardHasFadedIn', 'true');
        }
    }, [shouldFadeIn, showWelcome]);

    const handleUploadSuccess = (status) => {
        addToast(status, 'success');
        setIsUploading(false);
    };

    const handleUploadError = (error) => {
        addToast(error, 'error');
        setIsUploading(false);
    };

    const handleNewChat = () => {
        setChatKey(Date.now());
        setAgentLog([]);
        setMessages([]); // Clear messages
        sessionStorage.removeItem('chatMessages');
        sessionStorage.removeItem('chatRecipient');
        setCurrentPage('dashboard');
    };

    const handleSignOut = async () => {
        if (window.confirm('Are you sure you want to sign out?')) {
            localStorage.removeItem('chatRecipient');
            await api.signOutUser();
        }
    };

    const toggleSidebar = () => {
        setIsSidebarCollapsed(!isSidebarCollapsed);
    };

    const toggleAgentLog = () => {
        setIsAgentLogCollapsed(!isAgentLogCollapsed);
    };

    const handleFriendsClick = () => {
        setCurrentPage('friends');
    };

    const handleWelcomeAnimationComplete = () => {
        // Wait a moment before fading out
        setTimeout(() => {
            setIsFadingOut(true);
            // Wait for fade out animation to finish before removing the component
            setTimeout(() => {
                setShowWelcome(false);
                sessionStorage.setItem('welcomeAnimationPlayed', 'true');
            }, 500);
        }, 800);
    };


    const renderPage = () => {
        switch (currentPage) {
            case 'collaborative-agent':
                return <CollaborativeAgent recipient={chatRecipient} />;
            case 'friends':
                return <FriendsPage 
                    setChatRecipient={setChatRecipient}
                    setCurrentPage={setCurrentPage}
                />;
            default:
                return (
                    <main className={`App-main ${isAgentLogCollapsed ? 'log-collapsed' : ''}`}>
                        <div className={`sidebar ${isSidebarCollapsed ? 'collapsed' : ''}`}>
                            <div className="sidebar-header">
                                <button onClick={toggleSidebar} className="sidebar-toggle">
                                    <PanelLeft className="toggle-icon" size={20} />
                                    <span className="toggle-text">Collapse</span>
                                </button>
                            </div>
                            <div className="sidebar-content">
                                <div className="sidebar-actions">
                                    <button onClick={handleNewChat} className="new-chat-button" title="New Chat">
                                        <MessageSquarePlus size={20} />
                                        <span className="sidebar-item-text">New Chat</span>
                                    </button>
                                    <button onClick={handleFriendsClick} className="new-chat-button" title="Friends">
                                        <Users size={20} />
                                        <span className="sidebar-item-text">Friends 👥</span>
                                    </button>
                                </div>
                                <FileUpload onUploadSuccess={handleUploadSuccess} onUploadError={handleUploadError} setIsUploading={setIsUploading} isSidebarCollapsed={isSidebarCollapsed} isUploading={isUploading} />
                            </div>
                        </div>
                        <div className="chat-container" style={{ flex: 1 }}>
                            <Chat 
                                key={chatKey} 
                                setAgentLog={setAgentLog} 
                                setIsLogLoading={setIsLogLoading}
                                messages={messages}
                                setMessages={setMessages}
                            />
                        </div>
                        <AgentLog
                            log={agentLog}
                            isLoading={isLogLoading}
                            isCollapsed={isAgentLogCollapsed}
                            onToggle={toggleAgentLog}
                        />
                    </main>
                );
        }
    };

    // While fetching the profile, show a blank screen or a loader to prevent flicker.
    if (loadingProfile) {
        return <div style={{ backgroundColor: 'black', height: '100vh' }} />;
    }

    // Only show the welcome animation if we have the profile data to display the name.
    if (showWelcome && profile) {
        return (
            <div
                className={`welcome-container ${isFadingOut ? 'fade-out' : ''}`}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '100vh',
                    backgroundColor: 'black'
                }}>
                <SplitText
                    tag="h1"
                    text={`Welcome, ${profile?.display_name || session.user.email}!`}
                    className="welcome-text"
                    delay={50}
                    duration={0.5}
                    ease="power2.out"
                    splitType="chars"
                    from={{ opacity: 0, y: 20 }}
                    to={{ opacity: 1, y: 0 }}
                    onLetterAnimationComplete={handleWelcomeAnimationComplete}
                />
            </div>
        );
    }

    return (
        // The className now depends on the `shouldFadeIn` state and whether the welcome animation is active.
        <DashboardLayout session={session} profile={profile} loadingProfile={loadingProfile} handleSignOut={handleSignOut} currentPage={currentPage} onBack={() => setCurrentPage('dashboard')} className={shouldFadeIn && !showWelcome ? "dashboard-fade-in" : ""}>
            {renderPage()}
        </DashboardLayout>
    );
};

export default Dashboard;