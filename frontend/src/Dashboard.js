import React, { useState, useEffect } from 'react';
import { supabase } from './supabaseClient';
import { useToasts } from './ToastContext';
import {
    FileUp,
    Plus,
    LogOut,
    Sun,
    Moon,
    Bot,
    User,
    Send,
    ChevronsLeft,
} from 'lucide-react';
import AgentLog from './components/AgentLog';

const Dashboard = ({ session }) => {
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    const [isLogCollapsed, setIsLogCollapsed] = useState(false); // State for the log sidebar
    const [theme, setTheme] = useState('dark');

    useEffect(() => {
        document.body.setAttribute('data-theme', theme);
    }, [theme]);

    const toggleTheme = () => {
        setTheme(prevTheme => (prevTheme === 'light' ? 'dark' : 'light'));
    };

    const handleSignOut = async () => {
        await supabase.auth.signOut();
    };

    // Dummy data for demonstration
    const agentLogs = [
        'Planner starting analysis for user query.',
        'Searching web for "React best practices 2024"...',
        'Web search complete. Found 3 relevant articles.',
        'Synthesizing information to generate response.',
    ];
    const isAgentRunning = true;

    return (
        <div className="App">
            <header className="App-header">
                <div className="navbar-brand">
                    <h3>AI Agent Platform</h3>
                </div>
                <div className="user-info">
                    <div className="theme-toggle" onClick={toggleTheme}>
                        <button className={`theme-toggle-button ${theme === 'dark' ? 'active' : ''}`}><Moon size={16} /></button>
                        <button className={`theme-toggle-button ${theme === 'light' ? 'active' : ''}`}><Sun size={16} /></button>
                        <div className="theme-toggle-indicator"></div>
                    </div>
                    <span>{session.user.email}</span>
                    <button onClick={handleSignOut} className="sign-out-button">
                        <LogOut size={16} />
                        Sign Out
                    </button>
                </div>
            </header>
            <main className={`App-main ${isLogCollapsed ? 'log-collapsed' : ''}`}>
                <aside className={`sidebar ${isSidebarCollapsed ? 'collapsed' : ''}`}>
                    <div className="sidebar-header">
                        <button className="sidebar-toggle" onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}>
                            <ChevronsLeft size={20} className="toggle-icon" />
                            <span className="toggle-text">Collapse Menu</span>
                        </button>
                    </div>
                    <div className="sidebar-content">
                        <button className="new-chat-button">
                            <Plus size={20} />
                            <span className="sidebar-item-text">New Chat</span>
                        </button>
                        <div className="upload-section">
                            <h2>Knowledge Base</h2>
                            <p>Upload documents for the agent to use as context.</p>
                            <button className="file-upload-btn">
                                <FileUp size={16} />
                                <span className="sidebar-item-text">Upload Files</span>
                            </button>
                        </div>
                    </div>
                </aside>

                <div className="chat-container">
                    <div className="chat-view">
                        <div className="chat-window">
                            {/* Chat messages would go here */}
                            <div className="message agent">
                                <div className="message-avatar"><Bot size={20} /></div>
                                <div className="message-content">Hello! How can I assist you today?</div>
                            </div>
                            <div className="message user">
                                <div className="message-avatar"><User size={20} /></div>
                                <div className="message-content">Tell me about React best practices.</div>
                            </div>
                        </div>
                        <div className="chat-input">
                            <input placeholder="Send a message..." />
                            <button><Send size={18} /></button>
                        </div>
                    </div>
                </div>

                <AgentLog
                    log={agentLogs}
                    isLoading={isAgentRunning}
                    isCollapsed={isLogCollapsed}
                    onToggle={() => setIsLogCollapsed(!isLogCollapsed)}
                />
            </main>
        </div>
    );
};

export default Dashboard;