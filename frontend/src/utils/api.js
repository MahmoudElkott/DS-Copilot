// frontend/src/utils/api.js
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000';

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

  return api.post('/files/upload', formData, {
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

export const resumePipeline = (config) => api.post('/pipeline/resume', config);

export const getPipelineStatus = (sessionId) =>
  api.get(`/pipeline/status/${sessionId}`);

export const recoverPipeline = (sessionId) =>
  api.post(`/pipeline/recover/${sessionId}`);

export const runNotebook = (sessionId, stepKey = 'training', timeout = 600000) =>
  api.post(
    `/pipeline/${sessionId}/notebook/run`,
    { step_key: stepKey, timeout },
    { timeout }
  );

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

export const fetchLocalModels = ({ provider, baseUrl, apiKey } = {}) => {
  const params = new URLSearchParams();
  if (provider) {
    params.append('provider', provider);
  }
  if (baseUrl) {
    params.append('base_url', baseUrl);
  }
  if (apiKey) {
    params.append('api_key', apiKey);
  }

  const query = params.toString();
  return api.get(`/llm/local-models${query ? `?${query}` : ''}`);
};

// System
export const getPythonInterpreters = () => api.get('/system/python-interpreters');

// Stats
export const getStats = () => api.get('/stats');

// Notebook Execution
export const executeNotebookCell = (code, timeout = 30) =>
  api.post('/notebook/execute', { code, timeout }, { timeout: (timeout + 5) * 1000 });


// ═══════════════════════════════════════════════════════════
// WebSocket
// ═══════════════════════════════════════════════════════════

export const createWebSocket = (sessionId) => {
  return new WebSocket(`${WS_BASE}/ws/${sessionId}`);
};

export { API_BASE, WS_BASE };
export default api;
