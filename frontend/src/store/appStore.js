// frontend/src/store/appStore.js
import { create } from 'zustand';

const useAppStore = create((set, get) => ({
  // ── Sessions ────────────────────────────────────────
  sessions: [],
  currentSessionId: null,
  
  setSessions: (sessions) => set({ sessions }),
  setCurrentSession: (sessionId) => set({ currentSessionId: sessionId }),
  
  // ── Messages ────────────────────────────────────────
  messages: [],
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, {
      ...message,
      id: message.id || Date.now().toString(),
      timestamp: message.timestamp || new Date().toISOString(),
    }],
  })),
  
  setMessages: (messages) => set({ messages }),
  clearMessages: () => set({ messages: [] }),
  
  // ── Pipeline ────────────────────────────────────────
  pipelineStatus: null,
  pipelineSteps: [
    { key: 'data_ingest', name: 'Ingest', agent: 'DataIngestAgent', status: 'pending' },
    { key: 'data_cleaning', name: 'Clean', agent: 'DataCleaningAgent', status: 'pending' },
    { key: 'eda', name: 'EDA', agent: 'EDAAgent', status: 'pending' },
    { key: 'model_selection', name: 'Select', agent: 'ModelSelectionAgent', status: 'pending' },
    { key: 'code_writing', name: 'Code', agent: 'CodeWriterAgent', status: 'pending' },
    { key: 'testing', name: 'Test', agent: 'TestingAgent', status: 'pending' },
    { key: 'optimization', name: 'Optimize', agent: 'OptimizationAgent', status: 'pending' },
    { key: 'documentation', name: 'Document', agent: 'DocumentationAgent', status: 'pending' },
  ],
  
  setPipelineStatus: (status) => set({ pipelineStatus: status }),
  
  updateStep: (stepKey, updates) => set((state) => ({
    pipelineSteps: state.pipelineSteps.map((step) =>
      step.key === stepKey ? { ...step, ...updates } : step
    ),
  })),
  
  resetPipeline: () => set((state) => ({
    pipelineSteps: state.pipelineSteps.map((step) => ({ ...step, status: 'pending' })),
    pipelineStatus: null,
  })),
  
  // ── Code Stream ─────────────────────────────────────
  codeStreams: {},  // step_key -> code string
  activeCodeStep: null,
  
  setCodeStream: (stepKey, code) => set((state) => ({
    codeStreams: { ...state.codeStreams, [stepKey]: code },
  })),
  
  appendCodeStream: (stepKey, chunk) => set((state) => ({
    codeStreams: {
      ...state.codeStreams,
      [stepKey]: (state.codeStreams[stepKey] || '') + chunk,
    },
  })),
  
  setActiveCodeStep: (stepKey) => set({ activeCodeStep: stepKey }),
  
  // ── Files ───────────────────────────────────────────
  fileTree: {},
  
  setFileTree: (tree) => set({ fileTree: tree }),
  
  // ── Settings ────────────────────────────────────────
  settings: {
    llmProvider: 'openai',
    modelName: 'gpt-4o',
    executionEnv: 'local',
    temperature: 0.1,
    maxTokens: 4096,
    availableProviders: [],
  },
  
  updateSettings: (updates) => set((state) => ({
    settings: { ...state.settings, ...updates },
  })),
  
  // ── UI State ────────────────────────────────────────
  activeTab: 'chat',  // 'chat' | 'dashboard'
  rightPanelOpen: true,
  rightPanelTab: 'code',  // 'code' | 'settings' | 'files'
  isConnected: false,
  isLoading: false,
  uploadedFile: null,
  
  setActiveTab: (tab) => set({ activeTab: tab }),
  setRightPanelOpen: (open) => set({ rightPanelOpen: open }),
  setRightPanelTab: (tab) => set({ rightPanelTab: tab }),
  setConnected: (connected) => set({ isConnected: connected }),
  setLoading: (loading) => set({ isLoading: loading }),
  setUploadedFile: (file) => set({ uploadedFile: file }),
  
  // ── Stats ───────────────────────────────────────────
  stats: {
    totalCalls: 0,
    budgetRemaining: 100,
    activeSessions: 0,
  },
  
  setStats: (stats) => set({ stats }),
}));

export default useAppStore;
