import React, { useEffect, useState } from 'react';
import { X, Server, Key, Cpu, Thermometer, RefreshCw, Terminal, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import useAppStore from '../../store/appStore';

export default function SettingsModal() {
  const { 
    settings, 
    updateSettings, 
    saveSettings,
    setSettingsModalOpen, 
    fetchLocalModels, 
    fetchPythonInterpreters 
  } = useAppStore();

  const [isRefreshingModels, setIsRefreshingModels] = useState(false);
  const [isRefreshingInterpreters, setIsRefreshingInterpreters] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);

  // Initial settings to compare for "isDirty"
  const [initialSettings] = useState({ ...settings });

  useEffect(() => {
    // Initial fetch
    fetchPythonInterpreters();
    if (settings.llmProvider === 'local' || settings.llmProvider === 'ollama') {
      fetchLocalModels(settings.llmProvider);
    }

    // Handle browser back/refresh when dirty
    const handleBeforeUnload = (e) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty]);

  const handleUpdateSetting = (updates) => {
    updateSettings(updates);
    setIsDirty(true);
  };

  const handleClose = () => {
    if (isDirty) {
      if (window.confirm('You have unsaved changes. Are you sure you want to leave?')) {
        setSettingsModalOpen(false);
      }
    } else {
      setSettingsModalOpen(false);
    }
  };

  const handleRefreshModels = async () => {
    setIsRefreshingModels(true);
    await fetchLocalModels(settings.llmProvider);
    setIsRefreshingModels(false);
  };

  const handleRefreshInterpreters = async () => {
    setIsRefreshingInterpreters(true);
    await fetchPythonInterpreters();
    setIsRefreshingInterpreters(false);
  };

  const handleApply = async () => {
    setIsSaving(true);
    const success = await saveSettings();
    setIsSaving(false);
    if (success) {
      setIsDirty(false);
      toast.success('Settings saved successfully');
      setSettingsModalOpen(false);
    } else {
      toast.error('Failed to save settings');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
      onClick={() => setSettingsModalOpen(false)}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0, y: 20 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.95, opacity: 0, y: 20 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg rounded-2xl border overflow-hidden flex flex-col"
        style={{
          background: 'var(--surface-card)',
          borderColor: 'var(--border)',
          boxShadow: '0 24px 80px -12px rgba(0,0,0,0.6)',
          maxHeight: '90vh'
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b" style={{ borderColor: 'var(--border)' }}>
          <div>
            <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>System Settings</h2>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Configure your AI engine and execution environment</p>
          </div>
          <button onClick={handleClose} className="btn-ghost p-2 rounded-full">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Unsaved Warning Banner */}
        <AnimatePresence>
          {isDirty && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="bg-amber-500/10 border-b border-amber-500/20 px-6 py-2 flex items-center justify-between"
            >
              <div className="flex items-center gap-2 text-amber-500 text-xs font-medium">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                You have unsaved changes
              </div>
              <button 
                onClick={handleApply}
                className="text-[10px] font-bold uppercase tracking-wider text-amber-500 hover:underline"
              >
                Save Now
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Body */}
        <div className="px-6 py-6 space-y-8 overflow-y-auto custom-scrollbar flex-1">
          {/* LLM PROVIDER SECTION */}
          <section className="space-y-4">
            <h3 className="text-[10px] uppercase tracking-[0.2em] font-bold opacity-50 mb-4">LLM Configuration</h3>
            
            <div className="grid grid-cols-2 gap-4">
              {/* Provider Selector */}
              <div className="space-y-2">
                <label className="text-xs font-semibold flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
                  <Server className="w-3.5 h-3.5" /> Provider
                </label>
                <select
                  value={settings.llmProvider}
                  onChange={(e) => {
                    handleUpdateSetting({ llmProvider: e.target.value });
                    if (e.target.value === 'local' || e.target.value === 'ollama') {
                      fetchLocalModels(e.target.value);
                    }
                  }}
                  className="input w-full"
                >
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="google">Google Gemini</option>
                  <option value="local">LM Studio</option>
                  <option value="ollama">Ollama</option>
                </select>
              </div>

              {/* Model Selector / Search */}
              <div className="space-y-2">
                <label className="text-xs font-semibold flex items-center justify-between" style={{ color: 'var(--text-muted)' }}>
                  <span className="flex items-center gap-2"><Cpu className="w-3.5 h-3.5" /> Model</span>
                  {(settings.llmProvider === 'local' || settings.llmProvider === 'ollama') && (
                    <button 
                      onClick={handleRefreshModels}
                      className={`p-1 hover:bg-white/5 rounded transition-colors ${isRefreshingModels ? 'animate-spin' : ''}`}
                      title="Refresh models"
                    >
                      <RefreshCw className="w-3 h-3" />
                    </button>
                  )}
                </label>
                
                {settings.availableLocalModels?.length > 0 && (settings.llmProvider === 'local' || settings.llmProvider === 'ollama') ? (
                  <select
                    className="input w-full"
                    value={settings.modelName}
                    onChange={(e) => handleUpdateSetting({ modelName: e.target.value })}
                  >
                    <option value="">Select a model...</option>
                    {settings.availableLocalModels.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    className="input w-full"
                    value={settings.modelName}
                    onChange={(e) => handleUpdateSetting({ modelName: e.target.value })}
                    placeholder={settings.llmProvider === 'openai' ? 'gpt-4o' : 'Enter model id...'}
                  />
                )}
              </div>
            </div>

            {/* API Key (Show only if not local/ollama) */}
            {!['local', 'ollama'].includes(settings.llmProvider) && (
              <div className="space-y-2">
                <label className="text-xs font-semibold flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
                  <Key className="w-3.5 h-3.5" /> API Key
                </label>
                <div className="relative">
                  <input
                    className="input w-full pr-10"
                    type="password"
                    value={settings.llmApiKey}
                    onChange={(e) => handleUpdateSetting({ llmApiKey: e.target.value })}
                    placeholder="sk-..."
                  />
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    <div className={`w-2 h-2 rounded-full ${settings.llmApiKey ? 'bg-green-500' : 'bg-red-500 opacity-30'}`} />
                  </div>
                </div>
              </div>
            )}
            
            {/* Base URL (Show for local/ollama if needed, or if custom openai) */}
            {(settings.llmProvider === 'local' || settings.llmProvider === 'ollama') && (
              <div className="space-y-2">
                <label className="text-xs font-semibold flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
                  <Server className="w-3.5 h-3.5" /> Endpoint URL
                </label>
                <input
                  className="input w-full opacity-70"
                  value={settings.llmProvider === 'ollama' ? settings.ollamaBaseUrl : settings.lmStudioBaseUrl}
                  readOnly
                />
                <p className="text-[10px] opacity-40">Managed via environment variables</p>
              </div>
            )}
          </section>

          <div className="h-px w-full" style={{ background: 'var(--border)', opacity: 0.5 }} />

          {/* RUNTIME SECTION */}
          <section className="space-y-4">
            <h3 className="text-[10px] uppercase tracking-[0.2em] font-bold opacity-50 mb-4">Runtime & Execution</h3>
            
            <div className="space-y-4">
              {/* Python Interpreter Selection */}
              <div className="space-y-2">
                <label className="text-xs font-semibold flex items-center justify-between" style={{ color: 'var(--text-muted)' }}>
                  <span className="flex items-center gap-2"><Terminal className="w-3.5 h-3.5" /> Python Interpreter</span>
                  <button 
                    onClick={handleRefreshInterpreters}
                    className={`p-1 hover:bg-white/5 rounded transition-colors ${isRefreshingInterpreters ? 'animate-spin' : ''}`}
                    title="Scan for Python installations"
                  >
                    <RefreshCw className="w-3 h-3" />
                  </button>
                </label>
                
                {settings.availableInterpreters?.length > 0 ? (
                  <select
                    className="input w-full text-ellipsis overflow-hidden"
                    value={settings.pythonInterpreter}
                    onChange={(e) => handleUpdateSetting({ pythonInterpreter: e.target.value })}
                    title={settings.pythonInterpreter}
                  >
                    <option value="" title="System Default (python)">System Default (python)</option>
                    {settings.availableInterpreters.map(interpreter => {
                      const displayPath = interpreter.path.length > 45 ? '...' + interpreter.path.slice(-42) : interpreter.path;
                      return (
                        <option key={interpreter.path} value={interpreter.path} title={interpreter.path}>
                          {interpreter.version} — {displayPath} {interpreter.is_default ? '(Current)' : ''}
                        </option>
                      );
                    })}
                  </select>
                ) : (
                  <input
                    className="input w-full font-mono text-[11px]"
                    value={settings.pythonInterpreter}
                    onChange={(e) => handleUpdateSetting({ pythonInterpreter: e.target.value })}
                    placeholder="C:\Python311\python.exe or /usr/bin/python3"
                  />
                )}
                <p className="text-[10px] opacity-40">The environment used to execute generated code</p>
              </div>

              {/* Temperature */}
              <div className="space-y-3">
                <label className="text-xs font-semibold flex items-center justify-between" style={{ color: 'var(--text-muted)' }}>
                  <span className="flex items-center gap-2"><Thermometer className="w-3.5 h-3.5" /> Creativity (Temperature)</span>
                  <span className="font-mono text-accent">{settings.temperature}</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="1.5"
                  step="0.05"
                  value={settings.temperature}
                  onChange={(e) => updateSettings({ temperature: parseFloat(e.target.value) })}
                  className="w-full accent-[var(--accent)]"
                />
                <div className="flex justify-between text-[9px] uppercase tracking-tighter opacity-30">
                  <span>Precise</span>
                  <span>Creative</span>
                </div>
              </div>
            </div>
          </section>

          <div className="h-px w-full" style={{ background: 'var(--border)', opacity: 0.5 }} />

          {/* FAILOVER SECTION */}
          <section className="space-y-4">
            <h3 className="text-[10px] uppercase tracking-[0.2em] font-bold opacity-50 mb-4">Reliability & Failover</h3>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              Configuration for self-healing and fallback if the primary provider fails.
            </p>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-semibold flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
                  <Server className="w-3.5 h-3.5" /> Fallback Provider
                </label>
                <select
                  value={settings.fallbackLlmProvider}
                  onChange={(e) => handleUpdateSetting({ fallbackLlmProvider: e.target.value })}
                  className="input w-full"
                >
                  <option value="openai">OpenAI (Recommended)</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="google">Google Gemini</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
                  <Cpu className="w-3.5 h-3.5" /> Fallback Model
                </label>
                <input
                  className="input w-full"
                  value={settings.fallbackModelName}
                  onChange={(e) => handleUpdateSetting({ fallbackModelName: e.target.value })}
                  placeholder="e.g. gpt-4o-mini"
                />
              </div>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-5 border-t bg-black/20" style={{ borderColor: 'var(--border)' }}>
          <button 
            onClick={() => setSettingsModalOpen(false)} 
            className="px-5 py-2 rounded-lg text-sm font-semibold transition-all hover:bg-white/5 active:scale-95"
            style={{ color: 'var(--text-primary)' }}
          >
            Close
          </button>
          <button 
            onClick={handleApply}
            disabled={isSaving}
            className="px-6 py-2 rounded-lg text-sm font-bold bg-accent text-black transition-all hover:brightness-110 active:scale-95 shadow-[0_0_20px_-5px_var(--accent)] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
            {isSaving ? 'Saving...' : 'Apply Settings'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
