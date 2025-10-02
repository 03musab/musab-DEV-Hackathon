const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

/**
 * A helper function to handle fetch requests and JSON parsing.
 * @param {string} url - The URL to fetch.
 * @param {object} options - The options for the fetch request.
 * @returns {Promise<any>} - The JSON response.
 */
const fetchJson = async (url, options = {}) => {
    const response = await fetch(url, options);
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Network response was not ok' }));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }
    return response.json();
};

/**
 * Sends a chat message to the backend.
 * @param {string} message - The user's message.
 * @param {Array<Array<string>>} history - The conversation history.
 * @returns {Promise<object>} - The agent's response and log.
 */
export const postChatMessage = (message, history) => {
    return fetchJson(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message, history }),
    });
};

/**
 * Uploads a file to the backend for ingestion.
 * @param {File} file - The file to upload.
 * @returns {Promise<object>} - The status of the upload.
 */
export const uploadFile = (file) => {
    const formData = new FormData();
    formData.append('file', file);

    return fetchJson(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
    });
};

