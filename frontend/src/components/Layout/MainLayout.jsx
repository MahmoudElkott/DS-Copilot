// frontend/src/components/Layout/MainLayout.jsx
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquare, LayoutDashboard, Code2, Settings, FolderTree,
  PanelRightClose, PanelRightOpen, Sparkles, Wifi, WifiOff, ChevronDown,
} from 'lucide-react';
import useAppStore from '../../store/appStore';

export default function MainLayout({ children }) {
  const {
    activeTab, setActiveTab,
    rightPanelOpen, setRightPanelOpen,
    rightPanelTab, setRightPanelTab,
    isConnected,
    pipelineStatus,
  } = useAppStore();

  const navItems = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  ];

  const rightTabs = [
    { id: 'code', label: 'Code', icon: Code2 },
    { id: 'files', label: 'Files', icon: FolderTree },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="h-screen flex flex-col bg-surface-900 overflow-hidden">
      {/* ── Top Bar ──────────────────────────────── */}
      <header className="h-14 flex items-center justify-between px-4 border-b border-surface-700 bg-surface-850/80 backdrop-blur-xl z-50">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center shadow-lg shadow-brand-500/30">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-lg font-bold gradient-text">DS-Copilot</h1>
          </div>

          {/* Tab Navigation */}
          <nav className="flex items-center ml-6 gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? 'bg-brand-600/20 text-brand-400 border border-brand-500/30'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {/* Pipeline Status Badge */}
          {pipelineStatus && (
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className={`badge ${
                pipelineStatus === 'running' ? 'badge-warning' :
                pipelineStatus === 'completed' ? 'badge-success' : 'badge-error'
              }`}
            >
              {pipelineStatus === 'running' && (
                <span className="w-2 h-2 bg-amber-400 rounded-full mr-1.5 animate-pulse" />
              )}
              {pipelineStatus}
            </motion.div>
          )}

          {/* Connection Status */}
          <div className={`flex items-center gap-1.5 text-xs ${isConnected ? 'text-emerald-400' : 'text-gray-500'}`}>
            {isConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
            {isConnected ? 'Live' : 'Offline'}
          </div>

          {/* Right Panel Toggle */}
          <button
            onClick={() => setRightPanelOpen(!rightPanelOpen)}
            className="btn-ghost p-1.5"
          >
            {rightPanelOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
          </button>
        </div>
      </header>

      {/* ── Main Content ─────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Center Panel */}
        <main className="flex-1 min-w-0 overflow-hidden">
          {children}
        </main>

        {/* Right Panel */}
        <AnimatePresence>
          {rightPanelOpen && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 420, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: 'easeInOut' }}
              className="border-l border-surface-700 bg-surface-850 overflow-hidden flex flex-col"
            >
              {/* Right Panel Tabs */}
              <div className="flex border-b border-surface-700 px-2 pt-2">
                {rightTabs.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = rightPanelTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setRightPanelTab(tab.id)}
                      className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-t-lg transition-all duration-200 ${
                        isActive
                          ? 'bg-surface-900 text-brand-400 border-t border-x border-brand-500/30'
                          : 'text-gray-500 hover:text-gray-300'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              {/* Right Panel Content (rendered by App.jsx) */}
              <div className="flex-1 overflow-hidden" id="right-panel-content" />
            </motion.aside>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
