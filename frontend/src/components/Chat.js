import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy } from 'lucide-react';
import { postChatMessage } from '../services/api'; // Import the API function

const Chat = ({ messages, setMessages, setAgentLog, setIsLogLoading }) => {
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const chatWindowRef = useRef(null);

    useEffect(() => {
        // Scroll to the bottom of the chat window when new messages are added
        if (chatWindowRef.current) {
            chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
        }
    }, [messages]);

    const createChatHistory = (msgs) => {
        const history = [];
        // Iterate through messages to form user/agent pairs
        for (let i = 0; i < msgs.length; i += 2) {
            const userMsg = msgs[i];
            const agentMsg = msgs[i + 1];

            if (userMsg?.sender === 'user' && agentMsg?.sender === 'agent') {
                history.push([userMsg.text, agentMsg.text]);
            }
        }
        // Return the last 5 turns
        return history.slice(-5);
    };

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMessage = { text: input, sender: 'user' };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);
        setIsLogLoading(true);
        setAgentLog([]); // Clear previous log

        try {
            // Use the centralized API function
            const history = createChatHistory(messages);
            const data = await postChatMessage(input, history);
            
            const agentMessage = { 
                text: data.answer || "I'm sorry, I encountered an issue and couldn't process your request. Please try again.", 
                sender: 'agent' 
            };
            setMessages(prev => [...prev, agentMessage]);
            setAgentLog(data.log || []);

        } catch (error) {
            // Enhanced error logging
            console.error("Failed to send message. Full error:", error);
            const errorMessage = { text: `Error: Could not connect to the agent. ${error.message}`, sender: 'agent' };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
            setIsLogLoading(false);
        }
    };

    return (
        <div className="chat-view">
            {/* New Chat Header */}
            <div className="chat-header">
                <h3>Conversation</h3>
            </div>

            {/* Main Chat Window */}
            <div className="chat-window" ref={chatWindowRef}>
                {messages.map((msg, index) => (
                    <div key={index} className={`message ${msg.sender}`}>
                        <ReactMarkdown
                                children={msg.text}
                                components={{
                                    code({node, inline, className, children, ...props}) {
                                        const match = /language-(\w+)/.exec(className || '');
                                        const codeString = String(children).replace(/\n$/, '');

                                        const handleCopy = (e) => {
                                            navigator.clipboard.writeText(codeString);
                                            const button = e.currentTarget;
                                            const originalText = button.innerHTML;
                                            button.innerHTML = 'Copied!';
                                            setTimeout(() => {
                                                button.innerHTML = originalText;
                                            }, 2000);
                                        };

                                        if (inline || !match) {
                                            return <code className={className} {...props}>{children}</code>;
                                        }

                                        return (
                                            <div className="code-block-wrapper">
                                                <button className="copy-code-button" onClick={handleCopy}><Copy size={14} /> <span>Copy</span></button>
                                                <SyntaxHighlighter style={atomDark} language={match[1]} PreTag="div" {...props}>
                                                    {codeString}
                                                </SyntaxHighlighter>
                                            </div>
                                        );
                                    }
                                }}
                            />
                    </div>
                ))}
                {isLoading && <div className="message agent"><div className="loading-dots"><span></span><span></span><span></span></div></div>}
            </div>

            {/* Chat Input Area */}
            <div className="chat-input">
                <input type="text" value={input} onChange={(e) => setInput(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && handleSend()} placeholder="Ask the agent..." disabled={isLoading} />
                <button onClick={handleSend} disabled={isLoading}>Send</button>
            </div>
        </div>
    );
};

export default Chat;