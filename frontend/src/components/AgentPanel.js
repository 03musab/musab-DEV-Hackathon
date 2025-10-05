import React from 'react';
import { Users, Check, X, Clock, Send, Copy } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

const AgentPanel = ({
    currentUser,
    recipient,
    proposal,
    handleApproval,
    getApprovalStatus,
    handlePromptSubmit,
    prompt,
    setPrompt,
    isSubmitting,
    cooldown,
}) => {
    return (
        <div className="agent-panel">
            <div className="agent-panel-header">
                <Users size={20} />
                <h3>Collaborative Session</h3>
                <div className="session-users">
                    {[currentUser, recipient].filter(Boolean).map(u => (
                        <div key={u.id} className="user-avatar-sm" title={u.user_metadata?.display_name || u.email}>
                            {u.user_metadata?.display_name?.substring(0, 1) || '?'}
                        </div>
                    ))}
                </div>
            </div>

            {proposal && (
                <div className="proposal-card">
                    <h4>{proposal.title}</h4>
                    <div className="proposal-content">
                        <ReactMarkdown
                            children={proposal.content || ''}
                            components={{
                                code({node, inline, className, children, ...props}) {
                                    const match = /language-(\w+)/.exec(className || '');
                                    const codeString = String(children).replace(/\n$/, '');

                                    const handleCopy = (e) => {
                                        navigator.clipboard.writeText(codeString);
                                        const button = e.currentTarget;
                                        const originalText = button.querySelector('span').innerText;
                                        button.querySelector('span').innerText = 'Copied!';
                                        setTimeout(() => {
                                            button.querySelector('span').innerText = originalText;
                                        }, 2000);
                                    };

                                    if (inline || !match) {
                                        return <code className={className} {...props}>{children}</code>;
                                    }

                                    return (
                                        <div className="code-block-wrapper">
                                            <button className="copy-code-button" onClick={handleCopy}><Copy size={14} /> <span>Copy</span></button>
                                            <SyntaxHighlighter style={atomDark} language={match[1]} PreTag="div" {...props}>{codeString}</SyntaxHighlighter>
                                        </div>
                                    );
                                }
                            }}
                        />
                    </div>
                    <div className="approval-section">
                        <small className="approval-note">Requires 2-person approval to apply changes.</small>
                        <div className="approval-controls">
                            <button onClick={() => handleApproval('approved')} className="approve-btn"><Check size={16} /> Approve</button>
                            <button onClick={() => handleApproval('rejected')} className="reject-btn"><X size={16} /> Reject</button>
                        </div>
                        <div className="approval-status">
                            {[currentUser, recipient].filter(Boolean).map(user => (
                                <div key={user.id} className={`user-status ${getApprovalStatus(user.id)}`}>
                                    <div className="user-avatar-sm">{user.user_metadata?.display_name?.substring(0, 1) || '?'}</div>
                                    <span>{user.user_metadata?.display_name}</span>
                                    <span className="status-indicator">{getApprovalStatus(user.id) || 'Pending...'}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            <form onSubmit={handlePromptSubmit} className="agent-prompt-form">
                <input type="text" value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Send a message to the agent..." disabled={isSubmitting || cooldown > 0} />
                <button type="submit" disabled={isSubmitting || cooldown > 0}>
                    {isSubmitting ? <div className="spinner" /> : (cooldown > 0 ? <><Clock size={16} /> {cooldown}s</> : <Send size={16} />)}
                </button>
            </form>
        </div>
    );
};

export default AgentPanel;