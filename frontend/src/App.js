import React, { useState } from 'react';
import Chat from './components/Chat';
import FileUpload from './components/FileUpload';
import AgentLog from './components/AgentLog';
import './App.css';

function App() {
    const [uploadStatus, setUploadStatus] = useState('');
    const [isUploading, setIsUploading] = useState(false);
    const [chatKey, setChatKey] = useState(Date.now()); // Used to reset chat
    const [agentLog, setAgentLog] = useState([]);
    const [isLogLoading, setIsLogLoading] = useState(false);

    const handleUploadSuccess = (status) => {
        setUploadStatus(status);
        setIsUploading(false);
        // Optional: Clear the status message after a few seconds
        setTimeout(() => setUploadStatus(''), 5000);
    };

    const handleUploadError = (error) => {
        setUploadStatus(`Upload failed: ${error}`);
        setIsUploading(false);
    };

    const handleNewChat = () => {
        setChatKey(Date.now()); // Change key to force re-mount of Chat component
        setUploadStatus('');
        setAgentLog([]);
    };

    return (
        <div className="App">
            <main className="App-main">
                {/* Left Sidebar */}
                <div className="sidebar">
                    <button onClick={handleNewChat} className="new-chat-button">
                        + New Chat
                    </button>
                    <div className="upload-section">
                        <div className="file-upload">
                            <FileUpload
                                onUploadSuccess={handleUploadSuccess}
                                onUploadError={handleUploadError}
                                setIsUploading={setIsUploading}
                            />
                            {isUploading && <p className="status-message">Uploading...</p>}
                            {uploadStatus && <p className="status-message">{uploadStatus}</p>}
                        </div>
                    </div>
                </div>
                <div className="chat-container">
                    <Chat 
                        key={chatKey} 
                        setAgentLog={setAgentLog}
                        setIsLogLoading={setIsLogLoading}
                    />
                </div>
                <AgentLog 
                    log={agentLog} 
                    isLoading={isLogLoading} 
                />
            </main>
        </div>
    );
}

export default App;