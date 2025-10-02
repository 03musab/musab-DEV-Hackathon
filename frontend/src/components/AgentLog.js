import React, { useState, useEffect, useRef } from 'react';
import { CheckCircle, AlertCircle, Info, Zap } from 'lucide-react';
import TypingAnimation from './TypingAnimation';

const AgentLog = ({ log = [], isLoading = false }) => {
    const [displayedLog, setDisplayedLog] = useState([]);
    const logEndRef = useRef(null);

    useEffect(() => {
        if (logEndRef.current) {
            logEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [displayedLog]);

    const handleTypingComplete = () => {
        // Check if there are more logs to display
        if (displayedLog.length < log.length) {
            // Add the next log item to the displayedLog
            setDisplayedLog(currentLogs => [...currentLogs, log[currentLogs.length]]);
        }
    };

    useEffect(() => {
        if (log.length === 0) {
            setDisplayedLog([]);
            return;
        }
        // Start the animation sequence if it hasn't started
        if (log.length > 0 && displayedLog.length === 0) {
            setDisplayedLog([log[0]]);
        }
    }, [log, displayedLog]);

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
        <div className="agent-log-container">
            <div className="agent-log-wrapper">
                {/* Header */}
                <div className="agent-log-header">
                    <div className="agent-log-header-title">
                        <h4>System Logs</h4>
                        <div className="agent-log-header-meta">
                            <span>{log.length}</span>
                            {isLoading && (
                                <div className="agent-log-active-indicator">
                                    <div />
                                    <span>Active</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

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
                                            {index === displayedLog.length - 1 ? (
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