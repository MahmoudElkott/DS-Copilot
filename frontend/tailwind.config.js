/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Outfit', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Outfit', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        // All mapped to CSS variables for theme switching
        th: {
          bg:         'var(--bg-primary)',
          'bg-sub':   'var(--bg-secondary)',
          'bg-deep':  'var(--bg-tertiary)',
          surface:    'var(--surface-card)',
          raised:     'var(--surface-raised)',
          overlay:    'var(--surface-overlay)',
          accent:     'var(--accent)',
          'accent-h': 'var(--accent-hover)',
          'accent-m': 'var(--accent-muted)',
          border:     'var(--border)',
          'border-h': 'var(--border-hover)',
          text:       'var(--text-primary)',
          'text-sub': 'var(--text-secondary)',
          'text-dim': 'var(--text-muted)',
          success:    'var(--status-success)',
          warning:    'var(--status-warning)',
          error:      'var(--status-error)',
          info:       'var(--status-info)',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-up': 'slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-down': 'slideDown 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'fade-in': 'fadeIn 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
      },
      keyframes: {
        slideUp: {
          '0%': { transform: 'translateY(12px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-12px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
