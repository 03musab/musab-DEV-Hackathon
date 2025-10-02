import React, { useReducer, useRef, useState } from 'react';
import { Upload, File, X, ChevronDown } from 'lucide-react';
import { uploadFile } from '../services/api';
import './FileUpload.css';

const initialState = {
    selectedFile: null,
    isDragging: false,
    uploadProgress: 0,
    status: 'idle', // 'idle', 'dragging', 'file-selected', 'uploading', 'success', 'error'
};

function fileUploadReducer(state, action) {
    switch (action.type) {
        case 'DRAG_ENTER':
            return { ...state, isDragging: true, status: 'dragging' };
        case 'DRAG_LEAVE':
            return { ...state, isDragging: false, status: state.selectedFile ? 'file-selected' : 'idle' };
        case 'SELECT_FILE':
            return { ...state, selectedFile: action.payload, isDragging: false, status: 'file-selected', uploadProgress: 0 };
        case 'UPLOAD_START':
            return { ...state, status: 'uploading', uploadProgress: 0 };
        case 'SET_PROGRESS':
            return { ...state, uploadProgress: action.payload };
        case 'UPLOAD_COMPLETE':
            return { ...state, status: 'success', uploadProgress: 100 };
        case 'UPLOAD_ERROR':
            return { ...state, status: 'error', uploadProgress: 0 };
        case 'RESET':
            return { ...initialState };
        default:
            throw new Error(`Unhandled action type: ${action.type}`);
    }
}

const FileUpload = ({ onUploadSuccess, onUploadError, setIsUploading }) => {
    const [isOpen, setIsOpen] = useState(true);
    const [state, dispatch] = useReducer(fileUploadReducer, initialState);
    const { selectedFile, isDragging, uploadProgress, status } = state;
    const fileInputRef = useRef(null);

    const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file) {
            dispatch({ type: 'SELECT_FILE', payload: file });
        }
    };

    const handleDragOver = (event) => {
        event.preventDefault();
        dispatch({ type: 'DRAG_ENTER' });
    };

    const handleDragLeave = (event) => {
        event.preventDefault();
        dispatch({ type: 'DRAG_LEAVE' });
    };

    const handleDrop = (event) => {
        event.preventDefault();
        const file = event.dataTransfer.files[0];
        if (file) {
            dispatch({ type: 'SELECT_FILE', payload: file });
        }
    };

    const handleRemoveFile = () => {
        dispatch({ type: 'RESET' });
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const handleUpload = async () => {
        if (!selectedFile) {
            onUploadError('Please select a file first.');
            return;
        }

        setIsUploading(true);
        dispatch({ type: 'UPLOAD_START' });

        try {
            // Simulate progress (replace with actual progress tracking if API supports it)
            const progressInterval = setInterval(() => {
                dispatch({ type: 'SET_PROGRESS', payload: state.uploadProgress + 10 });
                if (state.uploadProgress >= 90) {
                        clearInterval(progressInterval);
                    }
            }, 200);

            const result = await uploadFile(selectedFile);
            
            clearInterval(progressInterval);
            dispatch({ type: 'UPLOAD_COMPLETE' });
            
            setTimeout(() => {
                onUploadSuccess(result.status || 'File processed successfully!');
                dispatch({ type: 'RESET' });
            }, 500);
        } catch (error) {
            dispatch({ type: 'UPLOAD_ERROR' });
            onUploadError(error.message || 'Failed to upload file');
        } finally {
            setIsUploading(false);
        }
    };

    const formatFileSize = (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    };

    const getFileExtension = (filename) => {
        return filename.slice((filename.lastIndexOf(".") - 1 >>> 0) + 2).toUpperCase();
    };

    return (
        <div className="file-upload-container">
            <div className="file-upload-header" onClick={() => setIsOpen(!isOpen)}>
                <h2 className="file-upload-title">Upload Knowledge</h2>
                <ChevronDown className={`file-upload-toggle-icon ${!isOpen ? 'closed' : ''}`} size={20} />
            </div>
            <div className={`file-upload-content ${!isOpen ? 'closed' : ''}`}>
                <div
                    className={`file-upload-dropzone ${status === 'dragging' ? 'dragging' : ''} ${selectedFile ? 'has-file' : ''}`}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => !selectedFile && fileInputRef.current?.click()}
                >
                    <input
                        ref={fileInputRef}
                        type="file"
                        onChange={handleFileChange}
                        className="file-upload-input"
                        accept=".pdf,.doc,.docx,.txt,.csv,.xlsx,.xls"
                    />

                    {!selectedFile ? (
                        <div className="file-upload-prompt">
                            <Upload size={18} className="upload-icon" />
                            <h4>Drop your file here</h4>
                            <p>or click to browse</p>
                            <span className="file-upload-hint">
                                Supported: PDF, DOC, TXT, CSV...
                            </span>
                        </div>
                    ) : (
                        <div className="file-upload-preview">
                            <div className="file-preview-icon">
                                <File size={20} />
                                <span className="file-extension">{getFileExtension(selectedFile.name)}</span>
                            </div>
                            <div className="file-preview-info">
                                <h4>{selectedFile.name}</h4>
                                <p>{formatFileSize(selectedFile.size)}</p>
                            </div>
                            <button
                                className="file-remove-btn"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    handleRemoveFile();
                                }}
                                title="Remove file"
                            >
                                <X size={16} />
                            </button>
                        </div>
                    )}

                    {status === 'uploading' && uploadProgress < 100 && (
                        <div className="file-upload-progress">
                            <div className="progress-bar">
                                <div 
                                    className="progress-fill" 
                                    style={{ width: `${uploadProgress}%` }}
                                />
                            </div>
                            <span className="progress-text">{uploadProgress}%</span>
                        </div>
                    )}
                </div>

                <button
                    className="file-upload-btn"
                    onClick={handleUpload}
                    disabled={!selectedFile || status === 'uploading'}
                >
                    <Upload size={16} />
                    {status === 'uploading' ? 'Uploading...' : 'Upload & Process'}
                </button>
            </div>
        </div>
    );
};

export default FileUpload;