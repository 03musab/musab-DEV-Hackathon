import React from 'react';
import { Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

const TeamChatPanel = ({
    chatMessages,
    currentUser,
    recipient,
    isTyping,
    handleChatSubmit,
    chatInput,
    handleChatInputChange,
    chatMessagesRef,
}) => {
    return (
        <div className="team-chat-panel">
            <h4>Team Chat</h4>
            <div className="chat-messages" ref={chatMessagesRef}>
                {chatMessages.map((msg, i) => (
                    <div key={msg.id || i} className={`chat-message ${msg.sender_id === currentUser.id ? 'current-user' : ''}`}>
                        <div className="user-avatar-sm" title={msg.sender_id === currentUser?.id ? currentUser?.user_metadata?.display_name : recipient?.name}>
                            {msg.sender_id === currentUser?.id ? currentUser?.user_metadata?.display_name?.substring(0, 1) : recipient?.avatar?.substring(0, 1)}
                        </div>
                        <div className="chat-message-content">
                            <ReactMarkdown
                                children={msg.content || ''}
                                components={{
                                    code({node, inline, className, children, ...props}) {
                                        const match = /language-(\w+)/.exec(className || '');
                                        const codeString = String(children).replace(/\n$/, '');

                                        if (inline || !match) {
                                            return <code className={className} {...props}>{children}</code>;
                                        }

                                        return (
                                            <div className="code-block-wrapper small">
                                                <SyntaxHighlighter style={atomDark} language={match[1]} PreTag="div" {...props}>
                                                    {codeString}
                                                </SyntaxHighlighter>
                                            </div>
                                        );
                                    }
                                }}
                            />
                        </div>
                    </div>
                ))}
                {isTyping && <div className="typing-indicator"><span></span><span></span><span></span></div>}
            </div>
            <form onSubmit={handleChatSubmit} className="chat-input-form">
                <input type="text" value={chatInput} onChange={handleChatInputChange} placeholder="Type to chat..." />
                <button type="submit"><Send size={16} /></button>
            </form>
        </div>
    );
};

export default TeamChatPanel;