import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const THEMES = [
  { id: 'emerald',  label: 'Emerald',  icon: '🌿', description: 'Professional data science' },
  { id: 'oled',     label: 'OLED',     icon: '🖤', description: 'Pure black high contrast' },
  { id: 'snow',     label: 'Snow',     icon: '❄️', description: 'Clean light mode' },
  { id: 'cyber',    label: 'Cyber',    icon: '⚡', description: 'Neon cyberpunk' },
  { id: 'terminal', label: 'Terminal', icon: '▓', description: 'Retro amber console' },
];

const STORAGE_KEY = 'ds-copilot-theme';

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(STORAGE_KEY) || 'emerald';
    }
    return 'emerald';
  });

  const setTheme = useCallback((newTheme) => {
    setThemeState(newTheme);
    localStorage.setItem(STORAGE_KEY, newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  }, []);

  // Apply theme on mount and changes
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const cycleTheme = useCallback(() => {
    const currentIndex = THEMES.findIndex(t => t.id === theme);
    const nextIndex = (currentIndex + 1) % THEMES.length;
    setTheme(THEMES[nextIndex].id);
  }, [theme, setTheme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, cycleTheme, themes: THEMES }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

export { THEMES };
export default ThemeContext;
