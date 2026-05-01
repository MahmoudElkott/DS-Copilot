import { motion } from 'framer-motion';

/**
 * StandardCard — The atomic container for the entire DS-Copilot UI.
 * Inherits all colors from the active CSS-variable theme.
 *
 * @param {string}  title       - Card header title
 * @param {string}  subtitle    - Optional secondary text
 * @param {React.ReactNode} icon - Optional icon element (top-left)
 * @param {React.ReactNode} actions - Optional header-right actions
 * @param {boolean} interactive - Enable hover states
 * @param {boolean} compact     - Reduce padding
 * @param {string}  className   - Extra classes
 * @param {React.ReactNode} children - Card body
 */
export default function StandardCard({
  title,
  subtitle,
  icon,
  actions,
  interactive = false,
  compact = false,
  className = '',
  children,
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className={`
        rounded-xl border
        ${interactive
          ? 'card-hover cursor-pointer'
          : 'card'
        }
        ${compact ? 'p-4' : 'p-6'}
        ${className}
      `}
    >
      {/* Header row */}
      {(title || icon || actions) && (
        <div className={`flex items-start justify-between ${children ? (compact ? 'mb-3' : 'mb-5') : ''}`}>
          <div className="flex items-center gap-3 min-w-0">
            {icon && (
              <div
                className="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center"
                style={{ background: 'var(--accent-muted)', color: 'var(--accent)' }}
              >
                {icon}
              </div>
            )}
            <div className="min-w-0">
              {title && (
                <h3 className="text-sm font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--text-muted)' }}>
                  {subtitle}
                </p>
              )}
            </div>
          </div>

          {actions && (
            <div className="flex items-center gap-2 flex-shrink-0 ml-3">
              {actions}
            </div>
          )}
        </div>
      )}

      {/* Body */}
      {children}
    </motion.div>
  );
}
