// frontend/src/utils/api.js
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

// ═══════════════════════════════════════════════════════════
// Axios Instance
// ═══════════════════════════════════════════════════════════

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Error interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Unknown error';
    console.error('[API Error]', message);
    return Promise.reject(error);
  }
);

// ═══════════════════════════════════════════════════════════
// REST API Functions
// ═══════════════════════════════════════════════════════════

// Health
export const checkHealth = () => api.get('/health');

// Sessions
export const createSession = (projectName = 'ds-project') =>
  api.post('/sessions', { project_name: projectName });

export const listSessions = () => api.get('/sessions');

export const getSession = (sessionId) => api.get(`/sessions/${sessionId}`);

// File Upload
export const uploadFile = (file, sessionId, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);
  if (sessionId) {
    formData.append('session_id', sessionId);
  }

  return api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  });
};

// Pipeline
export const startPipeline = (config) => api.post('/pipeline/start', config);

export const getPipelineStatus = (sessionId) =>
  api.get(`/pipeline/status/${sessionId}`);

// Chat
export const sendChatMessage = (content, sessionId) =>
  api.post('/chat', { content, session_id: sessionId });

export const getChatHistory = (sessionId, limit = 50) =>
  api.get(`/chat/${sessionId}?limit=${limit}`);

// Files
export const getFileTree = (sessionId) => api.get(`/files/${sessionId}`);

export const downloadFile = (sessionId, filepath) =>
  api.get(`/files/${sessionId}/download/${filepath}`, {
    responseType: 'blob',
  });

// Settings
export const getSettings = () => api.get('/settings');

export const updateSettings = (settings) => api.put('/settings', settings);

// Stats
export const getStats = () => api.get('/stats');


// ═══════════════════════════════════════════════════════════
// WebSocket
// ═══════════════════════════════════════════════════════════

export const createWebSocket = (sessionId) => {
  return new WebSocket(`${WS_BASE}/ws/${sessionId}`);
};

export { API_BASE, WS_BASE };
export default api;
