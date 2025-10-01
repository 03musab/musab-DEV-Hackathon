import React, { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [status, setStatus] = useState('Welcome! Ask me anything or upload a file.');
  const [viewMode, setViewMode] = useState('agent'); // 'agent' or 'control'
  const [selectedFile, setSelectedFile] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setStatus('Agent is thinking...');
    setIsTyping(true);

    try {
      const response = await fetch('http://localhost:5000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: input
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const agentMessage = { sender: 'agent', text: data.answer, log: data.log };
      setMessages(prev => [...prev, agentMessage]);
      setStatus('Ready for your next question.');

    } catch (error) {
      console.error("Failed to send message:", error);
      const errorMessage = { sender: 'agent', text: 'Sorry, something went wrong.' };
      setMessages(prev => [...prev, errorMessage]);
      setStatus('Error occurred. Please try again.');
    } finally {
      setIsTyping(false);
    }
  };

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
  };

  const handleFileUpload = async () => {
    if (!selectedFile) {
      setStatus('Please select a file first.');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    setStatus(`Uploading ${selectedFile.name}...`);

    try {
      const response = await fetch('http://localhost:5000/api/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'File upload failed');
      }

      setStatus(data.status || 'File uploaded successfully!');
      setSelectedFile(null); // Clear the file input

    } catch (error) {
      console.error("Failed to upload file:", error);
      setStatus(`Upload failed: ${error.message}`);
    }
  };

  // Static data for the new dashboard UI
  const agents = [
    { name: 'Document Processor' },
    { name: 'Research Assistant' },
    { name: 'Content Analyzer' },
    { name: 'Data Scientist' },
  ];

  return (
    <div className={`dashboard-container ${!isSidebarOpen ? 'sidebar-closed' : ''}`}>
      <header className="top-nav">
        <div className="nav-title">Multi-Agent Dashboard</div>
        <div className="nav-toggle">
          <span>AI Agent</span>
          <label className="switch">
            <input type="checkbox" checked={viewMode === 'control'} onChange={() => setViewMode(prev => prev === 'agent' ? 'control' : 'agent')} />
            <span className="slider round"></span>
          </label>
          <span>Agent Control</span>
        </div>
      </header>

      <main className="main-content">
        <div className="status-panels">
          <div className="panel">
            <h3>Active Agents</h3>
            <p>4 <span>currently active</span></p>
          </div>
          <div className="panel">
            <h3>Tasks Running</h3>
            <p>6 <span>in progress</span></p>
          </div>
          <div className="panel">
            <h3>System Status</h3>
            <p className="status-online">Online</p>
          </div>
        </div>

        {viewMode === 'agent' && (
          <div className="agent-workspace">
            <div className="quick-actions">
              <div className="action-card upload-section">
                <h2>Upload Documents</h2>
                <p>Add files to the knowledge base</p>
                <input type="file" id="file-upload" onChange={handleFileChange} style={{display: 'none'}}/>
                <label htmlFor="file-upload" className="button">Choose File</label>
                {selectedFile && <span>{selectedFile.name}</span>}
                <button onClick={handleFileUpload} disabled={!selectedFile}>Upload & Ingest</button>
              </div>
              <div className="action-card chat-section">
                <h2>Start Conversation</h2>
                <p>Chat with an agent</p>
                <div className="chat-window">
                  <div className="messages">
                    {messages.length === 0 && <div className="message-placeholder">Ready for Agent Tasks. Upload documents and chat directly to an agent to assign tasks.</div>}
                    {messages.map((msg, index) => (
                      <div key={index} className={`message ${msg.sender}`}>
                        <p>{msg.text}</p>
                        {msg.sender === 'agent' && msg.log && (
                          <details className="log-details">
                            <summary>View Thought Process</summary>
                            <ul>
                              {msg.log.map((step, i) => <li key={i}>{step}</li>)}
                            </ul>
                          </details>
                        )}
                      </div>
                    ))}
                    {isTyping && (
                      <div className="message agent">
                        <div className="typing-indicator">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                  <div className="input-area">
                    <input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                      placeholder="Ask the agent..."
                    />
                    <button onClick={handleSendMessage}>Send</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        {viewMode === 'control' && <div className="agent-workspace"><p className="message-placeholder">Agent Control Panel is active. Configure agents from the right sidebar.</p></div>}
      </main>

      <aside className="sidebar">
        <button className="toggle-sidebar-btn" onClick={() => setIsSidebarOpen(!isSidebarOpen)}>
          {isSidebarOpen ? '→' : '←'}
        </button>
        <div className="agent-control-panel">
          <div className="sidebar-header">
            <h2>Agent Control</h2>
          </div>
          <ul>
            {agents.map(agent => (
              <li key={agent.name}>
                <span>{agent.name}</span>
                <button className="configure-btn">Configure</button>
              </li>
            ))}
          </ul>
          <div className="sidebar-actions">
            <button>Add New Agent</button>
            <button>Settings</button>
          </div>
        </div>
      </aside>
    </div>
  );
}

export default App;