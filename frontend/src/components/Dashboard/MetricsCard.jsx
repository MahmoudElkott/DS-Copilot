// frontend/src/components/Dashboard/MetricsCard.jsx
import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

export default function MetricsCard({ title, value, icon: Icon, color = 'brand', suffix = '', delay = 0 }) {
  const [displayValue, setDisplayValue] = useState(0);

  const colorMap = {
    brand: { bg: 'bg-brand-500/10', border: 'border-brand-500/20', text: 'text-brand-400', icon: 'text-brand-400' },
    emerald: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', text: 'text-emerald-400', icon: 'text-emerald-400' },
    amber: { bg: 'bg-amber-500/10', border: 'border-amber-500/20', text: 'text-amber-400', icon: 'text-amber-400' },
    red: { bg: 'bg-red-500/10', border: 'border-red-500/20', text: 'text-red-400', icon: 'text-red-400' },
    purple: { bg: 'bg-purple-500/10', border: 'border-purple-500/20', text: 'text-purple-400', icon: 'text-purple-400' },
    cyan: { bg: 'bg-cyan-500/10', border: 'border-cyan-500/20', text: 'text-cyan-400', icon: 'text-cyan-400' },
  };

  const c = colorMap[color] || colorMap.brand;

  // Count-up animation
  useEffect(() => {
    const numValue = typeof value === 'number' ? value : parseFloat(value) || 0;
    if (numValue === 0) {
      setDisplayValue(0);
      return;
    }

    const duration = 1000;
    const steps = 30;
    const increment = numValue / steps;
    let current = 0;
    let step = 0;

    const timer = setTimeout(() => {
      const interval = setInterval(() => {
        step++;
        current = Math.min(numValue, increment * step);
        setDisplayValue(Math.round(current * 10) / 10);

        if (step >= steps) {
          setDisplayValue(numValue);
          clearInterval(interval);
        }
      }, duration / steps);

      return () => clearInterval(interval);
    }, delay);

    return () => clearTimeout(timer);
  }, [value, delay]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: delay / 1000, duration: 0.3 }}
      className={`glass-card-hover p-4 ${c.bg} border ${c.border}`}
    >
      <div className="flex items-start justify-between mb-3">
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">{title}</span>
        {Icon && (
          <div className={`w-8 h-8 rounded-lg ${c.bg} flex items-center justify-center`}>
            <Icon className={`w-4 h-4 ${c.icon}`} />
          </div>
        )}
      </div>
      <div className={`text-2xl font-bold ${c.text}`}>
        {typeof value === 'number' ? displayValue : value}
        {suffix && <span className="text-sm font-normal text-gray-500 ml-1">{suffix}</span>}
      </div>
    </motion.div>
  );
}
