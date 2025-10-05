import React from 'react';
import { Clock, Send, AlertTriangle, Bot, Trash2, Loader, XSquare } from 'lucide-react';

const AgentChatPanel = ({
    prompt,
    setPrompt,
    handlePromptSubmit,
    isSubmitting,
    cooldown,
    proposal, // Pass proposal to get agent analysis
    agentMessages,
    onClearChat,
    onInterrupt,
    onMockPromptClick,
}) => {
    return (
        <div className="agent-chat-panel">
            <div className="agent-panel-header">
                <Bot size={20} />
                <h3>Agent Panel</h3>
                <button onClick={onClearChat} className="clear-chat-btn" title="Clear Agent Chat">
                    <Trash2 size={14} />
                </button>
            </div>
            <div className="agent-chat-messages">
                {/* Show empty state only if there are no messages */}
                {agentMessages.length === 0 && (
                    <div className="message-wrapper-agent">
                        <div className="ai-avatar">🤖</div>
                        <div className="message-bubble-agent">Hello! Submit a task for me to analyze.</div>
                    </div>
                )}

                {/* Render the unified conversation history */}
                {agentMessages.map((msg) => (
                    <div key={msg.id} className={`message-wrapper-${msg.type}`}>
                        {msg.type === 'agent' && <div className="ai-avatar">🤖</div>}
                        {msg.type === 'system' && (
                            <div className="system-avatar">
                                {msg.content.startsWith('Processing') ? <Loader size={18} className="spinner-icon" /> : <AlertTriangle size={18} />}
                            </div>
                        )}

                        <div className={`message-bubble-${msg.type}`}>
                            {msg.content}
                            {msg.content.startsWith('Processing') && (
                                <button onClick={onInterrupt} className="stop-processing-btn" title="Stop Processing">
                                    <XSquare size={16} /> Stop
                                </button>
                            )}
                        </div>

                        {msg.type === 'user' && (
                            <div className="user-avatar-sm" title="You">
                                {msg.sender_name?.substring(0, 1) || 'Y'}
                            </div>
                        )}
                    </div>
                ))}
            </div>
            {/* Mock Prompts for Demo */}
            <div className="mock-prompts-container">
                <button
                    className="mock-prompt-btn"
                    onClick={() => onMockPromptClick(
                        'Analyze our Q3 sales data and identify key trends.',
                        'Of course. After analyzing the Q3 sales data, I\'ve identified three key trends:\n1.  **Product A sales have increased by 25%** month-over-month, driven by the new marketing campaign.\n2.  The **EMEA region is outperforming NA** by 15% in new customer acquisition.\n3.  There is a **seasonal dip in Product C sales**, which is consistent with previous years.'
                    )}
                >
                    Analyze Q3 Sales Data
                </button>
                <button
                    className="mock-prompt-btn"
                    onClick={() => onMockPromptClick(
                        'Draft a Python script to automate our weekly reporting.',
                        'Certainly! Here is a Python script using the `pandas` and `smtplib` libraries to automate your weekly reporting. It reads the data, generates a summary, and emails it to the specified recipients.\n\n```python\nimport pandas as pd\n\ndef generate_report(data_file):\n    df = pd.read_csv(data_file)\n    summary = df.describe()\n    print("Report Generated Successfully!")\n    return summary\n\n# Example usage:\ngenerate_report("sales_data.csv")\n```'
                    )}
                >
                    Draft a Python Script
                </button>
            </div>
            <form onSubmit={handlePromptSubmit} className="agent-prompt-form">
                <input type="text" value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Ask the agent..." disabled={isSubmitting || cooldown > 0} />
                <button type="submit" disabled={isSubmitting || cooldown > 0}>
                    {isSubmitting ? <div className="spinner" /> : (cooldown > 0 ? <><Clock size={16} /> {cooldown}s</> : <Send size={16} />)}
                </button>
            </form>
        </div>
    );
};

export default AgentChatPanel;