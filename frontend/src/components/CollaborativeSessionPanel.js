import React from 'react';
import { Users, Check, X, RotateCcw } from 'lucide-react';

const CollaborativeSessionPanel = ({
    currentUser,
    recipient,
    proposal,
    handleApproval,
    getApprovalStatus,
    onClearSession,
}) => {
    if (!currentUser) return null; // Don't render until user is loaded

    const sessionUsers = [currentUser, recipient].filter(Boolean);

    return (
        <div className="agent-panel">
            <div className="agent-panel-header">
                <Users size={20} />
                <h3>Collaborative Session</h3>
                <button onClick={onClearSession} className="clear-session-btn" title="Clear Session & Agent Memory">
                    <RotateCcw size={14} />
                </button>
                <div className="session-users">
                    {sessionUsers.map(u => (
                        <div key={u.id} className="user-avatar-sm" title={u.user_metadata?.display_name || u.email}>
                            {u.user_metadata?.display_name?.substring(0, 1) || '?'}
                        </div>
                    ))}
                </div>
            </div>

            {proposal && (
                <div className="proposal-card">
                    <h4>{proposal.title}</h4>
                    <p className="proposal-content-text">{proposal.content}</p>
                    <div className="approval-section">
                        <small className="approval-note">Requires {sessionUsers.length}-person approval to apply changes.</small>

                        <div className="approval-progress-bar">
                            <div
                                className="progress-fill"
                                style={{ width: `${(Object.values(proposal.approvals).filter(d => d === 'approved').length / sessionUsers.length) * 100}%` }}
                            ></div>
                        </div>

                        {/* Show controls only if the proposal is pending */}
                        {proposal.status === 'pending' && (
                            <div className="approval-controls">
                                <button onClick={() => handleApproval('approved')} className="approve-btn"><Check size={16} /> Approve</button>
                                <button onClick={() => handleApproval('rejected')} className="reject-btn"><X size={16} /> Reject</button>
                            </div>
                        )}

                        {/* Show a processing state when approved */}
                        {proposal.status === 'approved' && (
                            <div className="processing-indicator">Processing...</div>
                        )}

                        <div className="approval-status">
                            {sessionUsers.map(user => (
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
        </div>
    );
};

export default CollaborativeSessionPanel;