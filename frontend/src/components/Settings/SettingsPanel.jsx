// frontend/src/components/Settings/SettingsPanel.jsx
import { useState, useEffect } from 'react';
import { Save, RotateCcw, Eye, EyeOff, CheckCircle2, Settings as SettingsIcon } from 'lucide-react';
import useAppStore from '../../store/appStore';
import { getSettings, updateSettings as updateSettingsAPI } from '../../utils/api';
import { toast } from 'sonner';

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI', models: ['gpt-4o', 'gpt-4o-mini'] },
  { value: 'anthropic', label: 'Anthropic', models: ['claude-sonnet-4-20250514', 'claude-haiku-4-20250514'] },
  { value: 'google', label: 'Google', models: ['gemini-2.0-flash', 'gemini-2.5-pro-preview-06-05'] },
  { value: 'ollama', label: 'Ollama', models: ['llama3.1', 'codellama'] },
];

export default function SettingsPanel() {
  const { settings, updateSettings } = useAppStore();
  const [local, setLocal] = useState({ ...settings });
  const [showKeys, setShowKeys] = useState({});
  const [saving, setSaving] = useState(false);
  const [keys, setKeys] = useState({ openai_api_key: '', anthropic_api_key: '', google_api_key: '', e2b_api_key: '' });

  useEffect(() => {
    getSettings().then(r => {
      const d = r.data;
      setLocal({ llmProvider: d.llm_provider, modelName: d.model_name, executionEnv: d.execution_env, temperature: d.temperature, maxTokens: d.max_tokens, availableProviders: d.available_providers });
    }).catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateSettingsAPI({ llm_provider: local.llmProvider, model_name: local.modelName, execution_env: local.executionEnv, temperature: local.temperature, max_tokens: local.maxTokens, ...Object.fromEntries(Object.entries(keys).filter(([,v]) => v)) });
      updateSettings(local);
      toast.success('Settings saved!');
    } catch (e) { toast.error('Save failed'); }
    finally { setSaving(false); }
  };

  const cur = PROVIDERS.find(p => p.value === local.llmProvider) || PROVIDERS[0];

  return (
    <div className="h-full overflow-y-auto no-scrollbar">
      <div className="panel-header"><div className="flex items-center gap-2"><SettingsIcon className="w-4 h-4 text-brand-400" /><span className="text-sm font-semibold text-gray-300">Settings</span></div></div>
      <div className="p-4 space-y-5">
        <div><label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">LLM Provider</label>
          <select value={local.llmProvider} onChange={e => { const p = PROVIDERS.find(x => x.value === e.target.value); setLocal({...local, llmProvider: e.target.value, modelName: p?.models[0] || ''}); }} className="input">
            {PROVIDERS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
          </select></div>

        <div><label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">Model</label>
          <select value={local.modelName} onChange={e => setLocal({...local, modelName: e.target.value})} className="input">
            {cur.models.map(m => <option key={m} value={m}>{m}</option>)}
          </select></div>

        <div><label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">Execution</label>
          <div className="flex gap-2">
            {['local','e2b'].map(env => (
              <button key={env} onClick={() => setLocal({...local, executionEnv: env})}
                className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all ${local.executionEnv === env ? 'bg-brand-600/20 text-brand-400 border border-brand-500/30' : 'bg-surface-800 text-gray-400 border border-surface-700'}`}>
                {env === 'local' ? '💻 Local' : '☁️ E2B'}
              </button>
            ))}
          </div></div>

        <div><label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">Temperature: <span className="text-brand-400">{local.temperature}</span></label>
          <input type="range" min="0" max="1" step="0.05" value={local.temperature} onChange={e => setLocal({...local, temperature: parseFloat(e.target.value)})} className="w-full h-1.5 bg-surface-700 rounded-full appearance-none cursor-pointer accent-brand-500" />
          <div className="flex justify-between text-[10px] text-gray-600 mt-1"><span>Precise</span><span>Creative</span></div></div>

        <div><label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">Max Tokens: <span className="text-brand-400">{local.maxTokens}</span></label>
          <input type="range" min="256" max="8192" step="256" value={local.maxTokens} onChange={e => setLocal({...local, maxTokens: parseInt(e.target.value)})} className="w-full h-1.5 bg-surface-700 rounded-full appearance-none cursor-pointer accent-brand-500" /></div>

        <div className="border-t border-surface-700 pt-4">
          <label className="block text-xs font-medium text-gray-400 mb-3 uppercase tracking-wider">API Keys</label>
          {[{k:'openai_api_key',l:'OpenAI',p:'sk-...'},{k:'anthropic_api_key',l:'Anthropic',p:'sk-ant-...'},{k:'google_api_key',l:'Google',p:'AI...'},{k:'e2b_api_key',l:'E2B',p:'e2b_...'}].map(({k,l,p}) => (
            <div key={k} className="mb-3"><label className="block text-xs text-gray-500 mb-1">{l}</label>
              <div className="relative"><input type={showKeys[k]?'text':'password'} value={keys[k]} onChange={e => setKeys({...keys,[k]:e.target.value})} placeholder={p} className="input pr-10 text-sm font-mono" />
                <button onClick={() => setShowKeys({...showKeys,[k]:!showKeys[k]})} className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-500 hover:text-gray-300">
                  {showKeys[k] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button></div></div>
          ))}
        </div>

        <div className="flex gap-2 border-t border-surface-700 pt-4">
          <button onClick={handleSave} disabled={saving} className="btn-primary flex-1 flex items-center justify-center gap-2"><Save className="w-4 h-4" />{saving?'Saving...':'Save'}</button>
          <button onClick={() => { setLocal({llmProvider:'openai',modelName:'gpt-4o',executionEnv:'local',temperature:0.1,maxTokens:4096,availableProviders:settings.availableProviders}); setKeys({openai_api_key:'',anthropic_api_key:'',google_api_key:'',e2b_api_key:''}); }} className="btn-secondary flex items-center gap-2"><RotateCcw className="w-4 h-4" />Reset</button>
        </div>

        {local.availableProviders?.length > 0 && (
          <div className="border-t border-surface-700 pt-4"><label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">Active</label>
            <div className="flex flex-wrap gap-2">{local.availableProviders.map(p => <span key={p} className="badge-success flex items-center gap-1"><CheckCircle2 className="w-3 h-3" />{p}</span>)}</div></div>
        )}
      </div>
    </div>
  );
}
