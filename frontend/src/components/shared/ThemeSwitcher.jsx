import { motion, AnimatePresence } from 'framer-motion';
import { Palette, Check, X } from 'lucide-react';
import { useState } from 'react';
import { useTheme } from '../../context/ThemeContext';

export default function ThemeSwitcher() {
  const { theme, setTheme, themes } = useTheme();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="btn-ghost"
        title="Switch theme"
      >
        <Palette className="w-4 h-4" />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />

            {/* Dropdown */}
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 top-full mt-2 z-50 w-56 rounded-xl border p-1.5"
              style={{
                background: 'var(--surface-card)',
                borderColor: 'var(--border)',
                boxShadow: '0 12px 40px -8px rgba(0,0,0,0.5)',
              }}
            >
              <div className="px-3 py-2 mb-1">
                <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                  Theme
                </p>
              </div>

              {themes.map((t) => (
                <button
                  key={t.id}
                  onClick={() => { setTheme(t.id); setIsOpen(false); }}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left group"
                  style={{
                    background: theme === t.id ? 'var(--accent-muted)' : 'transparent',
                    color: theme === t.id ? 'var(--accent)' : 'var(--text-secondary)',
                  }}
                >
                  <span className="text-base w-5 text-center">{t.icon}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{t.label}</p>
                    <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{t.description}</p>
                  </div>
                  {theme === t.id && <Check className="w-3.5 h-3.5 flex-shrink-0" />}
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
