import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy } from 'lucide-react';

const Chat = ({ setAgentLog, setIsLogLoading, log, isLoading: isLogLoading }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const chatWindowRef = useRef(null);

    useEffect(() => {
        // Scroll to the bottom of the chat window when new messages are added
        if (chatWindowRef.current) {
            chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMessage = { text: input, sender: 'user' };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);
        setIsLogLoading(true);
        setAgentLog([]); // Clear previous log

        try {
            const response = await fetch('http://localhost:5000/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    message: input,
                    history: messages.map(m => [m.sender === 'user' ? m.text : '', m.sender === 'agent' ? m.text : '']).slice(-5)
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const agentMessage = { text: data.answer, sender: 'agent' };
            setMessages(prev => [...prev, agentMessage]);
            setAgentLog(data.log || []);

        } catch (error) {
            console.error("Failed to send message:", error);
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