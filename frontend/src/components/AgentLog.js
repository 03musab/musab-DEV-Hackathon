import React, { useState, useEffect, useRef } from 'react';
import { CheckCircle, AlertCircle, Info, Zap, ChevronsRight, ChevronsLeft, Cpu } from 'lucide-react';
import TypingAnimation from './TypingAnimation';

const AgentLog = ({ log = [], isLoading = false, isCollapsed, onToggle }) => {
    const [displayedLog, setDisplayedLog] = useState(() => {
        const saved = sessionStorage.getItem('agentLogDisplayed');
        return saved ? JSON.parse(saved) : [];
    });
    const logEndRef = useRef(null);
    const [isAnimating, setIsAnimating] = useState(false);

    useEffect(() => {
        if (logEndRef.current) {
            logEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
        sessionStorage.setItem('agentLogDisplayed', JSON.stringify(displayedLog));
    }, [displayedLog, isAnimating]);

    const handleTypingComplete = () => {
        // Check if there are more logs to display
        if (displayedLog.length < log.length) {
            // Add the next log item to the displayedLog
            setDisplayedLog(currentLogs => [...currentLogs, log[currentLogs.length]]);
        } else {
            setIsAnimating(false);
        }
    };

    useEffect(() => {
        if (log.length === 0) {
            setDisplayedLog([]);
            return;
        }
        // If the live log has more items than the displayed one, start the animation.
        if (log.length > displayedLog.length) {
            setIsAnimating(true);
            // If displayedLog is empty, start with the first item.
            // Otherwise, the typing complete handler will add the next one.
            if (displayedLog.length === 0) {
            setDisplayedLog([log[0]]);
            }
        }
    }, [log, displayedLog.length]);

    const categorizeLog = (logText) => {
        const patterns = [
            { 
                regex: /^[✅✓]/, 
                type: 'success',
                icon: <CheckCircle size={12} />,
                className: 'log-item-success'
            },
            { 
                regex: /^[❌✗]/, 
                type: 'error',
                icon: <AlertCircle size={12} />,
                className: 'log-item-error'
            },
            { 
                regex: /^[📝📄]/, 
                type: 'info',
                icon: <Info size={12} />,
                className: 'log-item-info'
            },
            { 
                regex: /^[🤔❓⚠️]/, 
                type: 'warning',
                icon: <AlertCircle size={12} />,
                className: 'log-item-warning'
            },
            { 
                regex: /^[🎯🔍🛠️⚙️💾💿🧠💡]/, 
                type: 'process',
                icon: <Zap size={12} />,
                className: 'log-item-process'
            }
        ];

        for (const pattern of patterns) {
            if (pattern.regex.test(logText)) {
                return { 
                    text: logText, 
                    icon: pattern.icon,
                    className: pattern.className
                };
            }
        }
        
        return { 
            text: logText,
            icon: <div className="log-item-default-icon" />,
            className: 'log-item'
        };
    };

    return (
        <div className={`agent-log-container ${isCollapsed ? 'collapsed' : ''}`}>
            {!isCollapsed ? (
                <div className="agent-log-header">
                    <div className="agent-log-header-title">
                        <Cpu size={14} />
                        <h4>System Logs</h4>
                    </div>
                    {isLoading && (
                        <div className="agent-log-active-indicator">
                            <div></div>
                            <span>Active</span>
                        </div>
                    )}
                    <button className="agent-log-toggle" onClick={onToggle} aria-label="Collapse logs">
                        <ChevronsRight size={18} className="toggle-icon" />
                    </button>
                </div>
            ) : (
                <button className="agent-log-toggle" onClick={onToggle} aria-label="Expand logs">
                    <ChevronsLeft size={18} className="toggle-icon" />
                </button>
            )}
            <div className="agent-log-wrapper">
                {/* Log Content */}
                <div className="log-content-area">
                    {log.length === 0 ? (
                        <div className="log-empty-state">
                            <div className="log-empty-icon-wrapper">
                                <Info size={24} />
                            </div>
                            <p>No logs available</p>
                            <p>Waiting for system activity...</p>
                        </div>
                    ) : (
                        <div className="log-items-container">
                            {displayedLog.map((logItem, index) => {
                                const categorized = categorizeLog(logItem);
                                return (
                                    <div 
                                        key={index}
                                        className={`log-item ${categorized.className}`}
                                    >
                                        <div className="log-item-icon">
                                            {categorized.icon}
                                        </div>
                                        <div className="log-item-text">
                                            {/* Only animate the last item in the list */}
                                            {isAnimating && index === displayedLog.length - 1 ? (
                                                <TypingAnimation
                                                    text={categorized.text}
                                                    onComplete={handleTypingComplete}
                                                />
                                            ) : (
                                                <p>{categorized.text}</p>
                                            )}
                                        </div>
                                        <span className="log-item-index">
                                            #{String(index + 1).padStart(3, '0')}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                    <div ref={logEndRef} />
                </div>
            </div>
        </div>
    );
};

export default AgentLog;