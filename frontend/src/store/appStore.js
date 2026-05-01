import { create } from 'zustand';
import { normalizeStepKey } from '../utils/pipeline';

const PIPELINE_STEPS = [
  { key: 'data_prep',    name: 'Prep',      stage: 'data_preparation',   status: 'pending' },
  { key: 'eda',          name: 'EDA',       stage: 'eda',                status: 'pending' },
  { key: 'features',     name: 'Features',  stage: 'feature_engineering', status: 'pending' },
  { key: 'training',     name: 'Train',     stage: 'model_training',     status: 'pending' },
  { key: 'evaluation',   name: 'Evaluate',  stage: 'model_evaluation',   status: 'pending' },
  { key: 'reporting',    name: 'Report',    stage: 'reporting',          status: 'pending' },
  { key: 'deployment',   name: 'Deploy',    stage: 'deployment',         status: 'pending' },
];

const DEFAULT_SETTINGS = {
  llmProvider: 'openai',
  modelName: 'gpt-4o',
  llmBaseUrl: '',
  llmApiKey: '',
  e2bApiKey: '',
  executionEnv: 'local',
  pythonInterpreter: '',
  temperature: 0.1,
  maxTokens: 4096,
  fallbackLlmProvider: 'openai',
  fallbackModelName: 'gpt-4o',
  availableProviders: [],
  availableLocalModels: [],
  availableInterpreters: [],
  ollamaBaseUrl: 'http://localhost:11434',
  lmStudioBaseUrl: 'http://localhost:1234/v1',
  openaiApiKeyLoaded: false,
  anthropicApiKeyLoaded: false,
  geminiApiKeyLoaded: false,
  e2bApiKeyLoaded: false,
};

const SESSION_STORAGE_KEY = 'ds-copilot:session-id';

function loadStoredSessionId() {
  try {
    return localStorage.getItem(SESSION_STORAGE_KEY);
  } catch (err) {
    return null;
  }
}

function persistSessionId(sessionId) {
  try {
    if (sessionId) {
      localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
    } else {
      localStorage.removeItem(SESSION_STORAGE_KEY);
    }
  } catch (err) {
    // Storage is best-effort.
  }
}

/**
 * @typedef {Object} PipelineArtifacts
 * @property {Object} data_prep
 * @property {string=} data_prep.profiling_output
 * @property {string=} data_prep.profiling_timestamp
 * @property {Object} eda
 * @property {string=} eda.eda_output
 * @property {string=} eda.eda_timestamp
 * @property {Object} features
 * @property {Object} training
 * @property {Object} evaluation
 * @property {Object=} evaluation.evaluation_metrics
 * @property {string=} evaluation.evaluation_output
 * @property {string=} evaluation.evaluation_timestamp
 * @property {Object} reporting
 * @property {Object} deployment
 */

/** @type {PipelineArtifacts} */
const DEFAULT_ARTIFACTS = {
  data_prep: {},
  eda: {},
  features: {},
  training: {},
  evaluation: {},
  reporting: {},
  deployment: {},
};

function nextId(prefix = 'id') {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

const useAppStore = create((set) => ({
  // Sessions
  sessions: [],
  currentSessionId: null,
  setSessions: (sessions) => set({ sessions }),
  setCurrentSession: (sessionId) => {
    persistSessionId(sessionId);
    set({ currentSessionId: sessionId });
  },

  // Messages
  messages: [],
  addMessage: (message) => set((state) => ({
    messages: [
      ...state.messages,
      {
        ...message,
        id: message.id || nextId('msg'),
        timestamp: message.timestamp || new Date().toISOString(),
      },
    ],
  })),
  setMessages: (messages) => set({ messages }),
  clearMessages: () => set({ messages: [] }),

  // Pipeline
  pipelineStatus: null,
  pipelineSteps: PIPELINE_STEPS,
  artifacts: DEFAULT_ARTIFACTS,
  setPipelineStatus: (status) => set({ pipelineStatus: status }),
  setArtifact: (stageKey, data) => set((state) => {
    if (!stageKey || !data) return state;
    
    // Performance Optimization: Strip huge base64 strings from state
    // and store as metadata for lazy loading
    const sanitized = {};
    Object.keys(data).forEach(key => {
      const val = data[key];
      if (typeof val === 'string' && val.length > 10000) {
        // Store metadata instead of the full payload
        sanitized[key] = { 
          __lazy: true, 
          filename: key.includes('.') ? key : `${stageKey}_${key}.png`,
          type: key.includes('output') ? 'text' : 'image',
          size: val.length 
        };
      } else {
        sanitized[key] = val;
      }
    });

    return {
      artifacts: {
        ...state.artifacts,
        [stageKey]: {
          ...(state.artifacts?.[stageKey] || {}),
          ...sanitized,
        },
      },
    };
  }),
  getArtifactUrl: (filename) => {
    const state = useAppStore.getState();
    if (!state.currentSessionId || !filename) return null;
    const baseUrl = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';
    return `${baseUrl}/files/${state.currentSessionId}/artifact/${filename}`;
  },
  setArtifacts: (artifactMap) => set((state) => ({
    artifacts: {
      ...state.artifacts,
      ...(artifactMap || {}),
    },
  })),
  updateStep: (stepKey, updates) => set((state) => ({
    pipelineSteps: state.pipelineSteps.map((step) =>
      step.key === stepKey ? { ...step, ...updates } : step
    ),
  })),
  resetPipeline: () => set((state) => ({
    pipelineStatus: null,
    pipelineSteps: state.pipelineSteps.map((step) => ({ ...step, status: 'pending', error: null })),
    codeStreams: {},
    notebookStreams: {},
    activeCodeStep: 'training',
    terminalLogs: [],
    visualizationPayload: {},
    artifacts: DEFAULT_ARTIFACTS,
  })),
  rehydratePipelineState: async (sessionId) => {
    if (!sessionId) return null;
    try {
      const { getPipelineStatus } = await import('../utils/api');
      const response = await getPipelineStatus(sessionId);
      const status = response.data;

      // Also trigger backend state recovery to WebSocket
      const { recoverPipeline } = await import('../utils/api');
      try {
        await recoverPipeline(sessionId);
      } catch (e) {
        console.warn('Failed to recover pipeline state via WebSocket:', e);
      }

      (status.steps || []).forEach((step) => {
        const stepKey = normalizeStepKey(step.key || step.name);
        if (!stepKey) return;
        set((state) => ({
          pipelineSteps: state.pipelineSteps.map((item) =>
            item.key === stepKey
              ? { ...item, status: step.status, error: step.error || null }
              : item
          ),
        }));
      });

      set({ pipelineStatus: status.status });
      return status;
    } catch (err) {
      return null;
    }
  },
  resumePipeline: async () => {
    const { currentSessionId, pipelineSteps } = useAppStore.getState();
    if (!currentSessionId) return;

    try {
      const { resumePipeline: apiResume } = await import('../utils/api');
      set({ pipelineStatus: 'running' });
      
      // Mark the first pending step as running
      const nextStep = pipelineSteps.find(s => s.status === 'pending' || s.status === 'failed');
      if (nextStep) {
        useAppStore.getState().updateStep(nextStep.key, { status: 'running' });
      }

      await apiResume({ session_id: currentSessionId });
      toast.success('Pipeline resumed from last step');
    } catch (err) {
      console.error('Failed to resume pipeline:', err);
      toast.error('Failed to resume pipeline');
      set({ pipelineStatus: 'failed' });
    }
  },

  // ── Notebook Cells (Agent-generated) ──
  notebookCells: [],
  addNotebookCell: (cell) => set((state) => ({
    notebookCells: [
      ...state.notebookCells,
      {
        id: cell.id || crypto.randomUUID(),
        cell_type: cell.cell_type || 'code',
        source: Array.isArray(cell.source) ? cell.source : (cell.source || '').split('\n'),
        metadata: { language: cell.language || 'python', stage: cell.stage || '' },
        outputs: [],
        execution_count: 0,
      },
    ],
  })),
  setNotebookCells: (cells) => set({ notebookCells: cells }),
  clearNotebookCells: () => set({ notebookCells: [] }),

  // ── Agent Working State ──
  agentWorking: false,
  agentStage: null,
  setAgentWorking: (working, stage = null) => set({
    agentWorking: working,
    agentStage: stage,
  }),

  // Notebook + code streams
  codeStreams: {},
  notebookStreams: {},
  activeCodeStep: 'training',
  setCodeStream: (stepKey, code) => set((state) => ({
    codeStreams: { ...state.codeStreams, [stepKey]: code },
  })),
  appendCodeStream: (stepKey, chunk) => set((state) => ({
    codeStreams: {
      ...state.codeStreams,
      [stepKey]: (state.codeStreams[stepKey] || '') + chunk,
    },
  })),
  setNotebookStream: (stepKey, notebook) => set((state) => ({
    notebookStreams: {
      ...state.notebookStreams,
      [stepKey]: notebook,
    },
  })),
  setActiveCodeStep: (stepKey) => set({ activeCodeStep: stepKey }),

  // Terminal logs
  terminalLogs: [],
  appendTerminalLog: (entry) => set((state) => {
    const activeStep = state.pipelineSteps.find(s => s.status === 'running')?.key || state.activeCodeStep;
    return {
      terminalLogs: [
        ...state.terminalLogs,
        {
          id: entry.id || nextId('term'),
          timestamp: entry.timestamp || new Date().toISOString(),
          stream: entry.stream || 'stdout',
          content: entry.content || '',
          stepKey: entry.stepKey || activeStep,
        },
      ],
    };
  }),
  clearTerminalLogs: () => set({ terminalLogs: [] }),

  // Visualization payload (weights, metrics, EDA snippets)
  visualizationPayload: {},
  setVisualizationPayload: (payload) => set((state) => ({
    visualizationPayload: {
      ...state.visualizationPayload,
      ...(payload || {}),
    },
  })),

  // Files (kept for backward compatibility)
  fileTree: {},
  setFileTree: (tree) => set({ fileTree: tree }),

  // Settings
  settings: DEFAULT_SETTINGS,
  updateSettings: (updates) => set((state) => ({
    settings: { ...state.settings, ...updates },
  })),

  saveSettings: async () => {
    const { settings } = useAppStore.getState();
    try {
      const { updateSettings: apiUpdate } = await import('../utils/api');

      // Resolve the correct base URL based on the active provider
      let resolvedBaseUrl = null;
      if (settings.llmProvider === 'local') {
        resolvedBaseUrl = settings.lmStudioBaseUrl || 'http://localhost:1234/v1';
      } else if (settings.llmProvider === 'ollama') {
        // Ollama uses its own field, not openai_api_base
        resolvedBaseUrl = null;
      } else if (settings.llmBaseUrl) {
        resolvedBaseUrl = settings.llmBaseUrl;
      }

      // Map to backend snake_case schema
      const payload = {
        llm_provider: settings.llmProvider,
        model_name: settings.modelName,
        execution_env: settings.executionEnv,
        python_interpreter: settings.pythonInterpreter || null,
        temperature: settings.temperature,
        max_tokens: settings.maxTokens,
        openai_api_key: settings.llmApiKey || null,
        openai_api_base: resolvedBaseUrl,
        ollama_base_url: settings.ollamaBaseUrl,
        e2b_api_key: settings.e2bApiKey || null,
        fallback_llm_provider: settings.fallbackLlmProvider,
        fallback_model_name: settings.fallbackModelName,
      };
      const response = await apiUpdate(payload);
      // Update local state with response
      useAppStore.getState().updateSettings({
        availableProviders: response.data.available_providers,
        openaiApiKeyLoaded: response.data.openai_api_key_loaded,
        anthropicApiKeyLoaded: response.data.anthropic_api_key_loaded,
        geminiApiKeyLoaded: response.data.gemini_api_key_loaded,
        e2bApiKeyLoaded: response.data.e2b_api_key_loaded,
      });
      return true;
    } catch (err) {
      console.error('Failed to save settings:', err);
      return false;
    }
  },

  // UI
  activeTab: 'chat',
  rightPanelOpen: true,
  rightPanelTab: 'code', // code | terminal | visualization | todo
  isSettingsModalOpen: false,
  isConnected: false,
  isLoading: false,
  uploadedFile: null,

  setActiveTab: (tab) => set({ activeTab: tab }),
  setRightPanelOpen: (open) => set({ rightPanelOpen: open }),
  setRightPanelTab: (tab) => set({ rightPanelTab: tab }),
  setSettingsModalOpen: (open) => set({ isSettingsModalOpen: open }),
  setConnected: (connected) => set({ isConnected: connected }),
  setLoading: (loading) => set({ isLoading: loading }),
  setUploadedFile: (file) => set({ uploadedFile: file }),

  // Stats
  stats: {
    totalCalls: 0,
    budgetRemaining: 100,
    activeSessions: 0,
  },
  setStats: (stats) => set({ stats }),

  // Discovery Actions
  fetchLocalModels: async (provider) => {
    try {
      const { fetchLocalModels } = await import('../utils/api');
      const response = await fetchLocalModels({ provider });
      set((state) => ({
        settings: { ...state.settings, availableLocalModels: response.data.models }
      }));
      return response.data.models;
    } catch (err) {
      console.error('Failed to fetch local models:', err);
      return [];
    }
  },
  fetchPythonInterpreters: async () => {
    try {
      const { getPythonInterpreters } = await import('../utils/api');
      const response = await getPythonInterpreters();
      set((state) => ({
        settings: { ...state.settings, availableInterpreters: response.data.interpreters }
      }));
      return response.data.interpreters;
    } catch (err) {
      console.error('Failed to fetch python interpreters:', err);
      return [];
    }
  },

  // ── Session + Settings Initialization ──
  initializeSession: async () => {
    try {
      const { createSession, getSettings: apiGetSettings } = await import('../utils/api');

      // 1. Load persisted backend settings into local state
      try {
        const settingsRes = await apiGetSettings();
        const d = settingsRes.data;
        set((state) => ({
          settings: {
            ...state.settings,
            llmProvider: d.llm_provider || state.settings.llmProvider,
            modelName: d.model_name || state.settings.modelName,
            executionEnv: d.execution_env || state.settings.executionEnv,
            pythonInterpreter: d.python_interpreter || '',
            temperature: d.temperature ?? state.settings.temperature,
            maxTokens: d.max_tokens ?? state.settings.maxTokens,
            fallbackLlmProvider: d.fallback_llm_provider || 'openai',
            fallbackModelName: d.fallback_model_name || 'gpt-4o',
            availableProviders: d.available_providers || [],
            openaiApiKeyLoaded: d.openai_api_key_loaded,
            anthropicApiKeyLoaded: d.anthropic_api_key_loaded,
            geminiApiKeyLoaded: d.gemini_api_key_loaded,
            e2bApiKeyLoaded: d.e2b_api_key_loaded,
          },
        }));
      } catch (e) {
        console.warn('Could not load settings from backend:', e);
      }

      // 2. Restore existing session (if any) and rehydrate pipeline state
      const storedSessionId = loadStoredSessionId();
      if (storedSessionId) {
        set({ currentSessionId: storedSessionId });
        const rehydrated = await useAppStore.getState().rehydratePipelineState(storedSessionId);
        if (rehydrated) {
          return;
        }
        persistSessionId(null);
        set({ currentSessionId: null });
      }

      // 3. Create a default session so WebSocket connects immediately
      const { currentSessionId } = useAppStore.getState();
      if (!currentSessionId) {
        const res = await createSession('ds-workspace');
        useAppStore.getState().setCurrentSession(res.data.session_id);
        console.log('[Init] Auto-created session:', res.data.session_id);
      }
    } catch (err) {
      console.error('Failed to initialize session:', err);
    }
  },
}));

export default useAppStore;
