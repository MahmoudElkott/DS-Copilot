// frontend/src/App.jsx
import { createPortal } from 'react-dom';
import { Toaster } from 'sonner';
import useAppStore from './store/appStore';
import MainLayout from './components/Layout/MainLayout';
import ChatPanel from './components/Chat/ChatPanel';
import DashboardPanel from './components/Dashboard/DashboardPanel';
import CodeStream from './components/CodeViewer/CodeStream';
import SettingsPanel from './components/Settings/SettingsPanel';
import FileTree from './components/FileExplorer/FileTree';
import { useEffect, useState } from 'react';

function RightPanelContent() {
  const { rightPanelTab } = useAppStore();

  switch (rightPanelTab) {
    case 'code': return <CodeStream />;
    case 'files': return <FileTree />;
    case 'settings': return <SettingsPanel />;
    default: return <CodeStream />;
  }
}

function RightPanelPortal() {
  const [container, setContainer] = useState(null);

  useEffect(() => {
    const el = document.getElementById('right-panel-content');
    if (el) setContainer(el);

    const observer = new MutationObserver(() => {
      const el = document.getElementById('right-panel-content');
      setContainer(el || null);
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  if (!container) return null;
  return createPortal(<RightPanelContent />, container);
}

export default function App() {
  const { activeTab } = useAppStore();

  return (
    <div className="dark">
      <Toaster
        theme="dark"
        position="top-right"
        toastOptions={{
          style: {
            background: '#0f172a',
            border: '1px solid rgba(255,255,255,0.1)',
            color: '#e2e8f0',
          },
        }}
      />

      <MainLayout>
        {activeTab === 'chat' ? <ChatPanel /> : <DashboardPanel />}
      </MainLayout>

      <RightPanelPortal />
    </div>
  );
}
