import { useEffect } from 'react';
import { Sparkles, Wifi, WifiOff, Settings2 } from 'lucide-react';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from 'react-resizable-panels';
import useAppStore from '../../store/appStore';
import useWebSocket from '../../hooks/useWebSocket';
import Sidebar from './Sidebar';
import ChatPane from './ChatPane';
import NotebookPane from './NotebookPane';
import ThemeSwitcher from '../shared/ThemeSwitcher';
import SettingsModal from '../settings/SettingsModal';

export default function MainLayout() {
  const { 
    isConnected, 
    pipelineStatus, 
    setSettingsModalOpen, 
    isSettingsModalOpen,
    currentSessionId,
    addMessage,
    initializeSession,
    fetchLocalModels,
    settings,
  } = useAppStore();
  

  // ── Auto-initialize session + load settings on mount ──
  useEffect(() => {
    initializeSession().then(() => {
      const { settings: s } = useAppStore.getState();
      if (s.llmProvider === 'local' || s.llmProvider === 'ollama') {
        fetchLocalModels(s.llmProvider);
      }
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Initialize WebSocket connection
  const { sendMessage } = useWebSocket(currentSessionId);

  // Global event listener for sending messages from other components
  useEffect(() => {
    const handleGlobalSend = (e) => {
      const { message, type = 'chat' } = e.detail;
      if (currentSessionId) {
        sendMessage(type, message);
      } else {
        addMessage({
          role: 'system',
          content: '⚠️ No active session. Upload a file to begin.',
        });
      }
    };

    window.addEventListener('ds-copilot:send', handleGlobalSend);
    return () => window.removeEventListener('ds-copilot:send', handleGlobalSend);
  }, [currentSessionId, sendMessage, addMessage]);

  return (
    <div className="h-screen flex flex-col overflow-hidden" style={{ background: 'var(--bg-primary)' }}>
      {/* ── HEADER ────────────────────────────────────── */}
      <header
        className="flex-shrink-0 flex items-center justify-between px-5 z-50 border-b"
        style={{
          height: 'var(--header-height)',
          background: 'var(--bg-tertiary)',
          borderColor: 'var(--border)',
        }}
      >
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: 'var(--accent)', color: 'var(--bg-primary)' }}
          >
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
              DS-Copilot
            </h1>
            <p className="text-[9px] uppercase tracking-[0.25em] font-semibold -mt-0.5" style={{ color: 'var(--text-muted)' }}>
              Autonomous Intelligence
            </p>
          </div>
        </div>

        {/* Status + Actions */}
        <div className="flex items-center gap-3">
          {pipelineStatus && (
            <span className={`badge ${
              pipelineStatus === 'running' ? 'badge-warning' :
              pipelineStatus === 'completed' ? 'badge-success' : 'badge-error'
            }`}>
              {pipelineStatus === 'running' && (
                <span className="w-1.5 h-1.5 rounded-full mr-1.5 animate-pulse" style={{ background: 'var(--status-warning)' }} />
              )}
              {pipelineStatus}
            </span>
          )}

          <div className="w-px h-4" style={{ background: 'var(--border)' }} />

          <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider" style={{ color: isConnected ? 'var(--status-success)' : 'var(--text-muted)' }}>
            {isConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
            {isConnected ? 'Live' : 'Offline'}
          </div>

          <div className="w-px h-4" style={{ background: 'var(--border)' }} />

          <ThemeSwitcher />

          <button
            onClick={() => setSettingsModalOpen(true)}
            className="btn-ghost p-2"
            title="Settings"
          >
            <Settings2 className="w-4 h-4" />
          </button>

        </div>
      </header>

      {/* ── BODY: Sidebar + Panels ───────────────────── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Column A: Sidebar (fixed) */}
        <Sidebar />

        {/* Column B + C: Resizable panels */}
        <div className="flex-1 min-w-0">
          <PanelGroup direction="horizontal">
            {/* Column B: Chat Pane */}
            <Panel defaultSize={35} minSize={20}>
              <ChatPane />
            </Panel>
            <PanelResizeHandle
              className="w-[3px] transition-colors duration-150"
              style={{ background: 'var(--border)' }}
            />

            {/* Column C: Notebook Pane (Routes) */}
            <Panel defaultSize={65}>
              <NotebookPane />
            </Panel>
          </PanelGroup>
        </div>
      </div>

      {/* Settings Modal */}
      {isSettingsModalOpen && <SettingsModal />}
    </div>
  );
}
