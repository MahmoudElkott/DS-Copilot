import { NavLink, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  Terminal,
  Wand2,
  FlaskConical,
  Wrench,
  Brain,
  Target,
  FileText,
  Rocket,
} from 'lucide-react';
import useAppStore from '../../store/appStore';

const NAV_SECTIONS = [
  {
    label: 'Overview',
    items: [
      { path: '/',                   label: 'Project Hub',         icon: LayoutDashboard },
      { path: '/notebook',           label: 'Notebook',            icon: Terminal },
    ],
  },
  {
    label: 'Data Pipeline',
    items: [
      { path: '/preparation',       label: 'Data Preparation',    icon: Wand2 },
      { path: '/eda',                label: 'EDA Exploration',     icon: FlaskConical },
      { path: '/features',           label: 'Feature Engineering', icon: Wrench },
    ],
  },
  {
    label: 'Modeling',
    items: [
      { path: '/training',           label: 'Model Training',      icon: Brain },
      { path: '/evaluation',         label: 'Model Evaluation',    icon: Target },
      { path: '/reporting',          label: 'Reporting',           icon: FileText },
      { path: '/deployment',         label: 'Deployment',          icon: Rocket },
    ],
  },

];

export default function Sidebar() {
  const location = useLocation();
  const { pipelineSteps } = useAppStore();

  return (
    <nav
      className="flex-shrink-0 flex flex-col h-full border-r overflow-hidden"
      style={{
        width: 'var(--sidebar-width)',
        background: 'var(--bg-tertiary)',
        borderColor: 'var(--border)',
      }}
    >
      {/* Navigation */}
      <div className="flex-1 overflow-y-auto py-4 px-3 no-scrollbar space-y-6">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            <p
              className="text-[10px] font-bold uppercase tracking-[0.15em] px-3 mb-2"
              style={{ color: 'var(--text-muted)' }}
            >
              {section.label}
            </p>

            <div className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;

                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group relative"
                    style={{
                      background: isActive ? 'var(--accent-muted)' : 'transparent',
                      color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                    }}
                  >
                    {/* Active indicator bar */}
                    {isActive && (
                      <motion.div
                        layoutId="sidebar-indicator"
                        className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full"
                        style={{ background: 'var(--accent)' }}
                        transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                      />
                    )}

                    <Icon className="w-4 h-4 flex-shrink-0" style={{ opacity: isActive ? 1 : 0.6 }} />
                    <span className="text-[13px] font-medium truncate">{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* ── Pipeline Progress Footer ────────────────────────── */}
      <div className="flex-shrink-0 px-3 py-3 border-t" style={{ borderColor: 'var(--border)' }}>
        {/* Header row */}
        <div className="flex items-center justify-between px-2 mb-2.5">
          <span
            className="text-[10px] font-bold uppercase tracking-[0.15em]"
            style={{ color: 'var(--text-muted)' }}
          >
            Pipeline
          </span>
          <span
            className="text-[10px] font-mono font-bold"
            style={{
              color: pipelineSteps.every(s => s.status === 'completed')
                ? 'var(--status-success)'
                : pipelineSteps.some(s => s.status === 'running')
                  ? 'var(--accent)'
                  : 'var(--text-muted)',
            }}
          >
            {pipelineSteps.filter(s => s.status === 'completed').length}/{pipelineSteps.length}
          </span>
        </div>

        {/* 8-segment progress bar */}
        <div className="flex gap-[3px] px-2 mb-1.5">
          {pipelineSteps.map((step) => {
            const segmentClass =
              step.status === 'completed' ? 'pipeline-segment-completed' :
              step.status === 'running'   ? 'pipeline-segment-active' :
              (step.status === 'error' || step.status === 'failed') ? 'pipeline-segment-failed' :
              'pipeline-segment-pending';

            return (
              <div
                key={step.key}
                className={`pipeline-segment ${segmentClass} flex-1 h-[5px] rounded-full`}
                title={`${step.name}: ${step.status}`}
              />
            );
          })}
        </div>

        {/* Step labels */}
        <div className="flex gap-[3px] px-2">
          {pipelineSteps.map((step) => (
            <span
              key={step.key}
              className="flex-1 text-center text-[7px] font-bold uppercase tracking-wider truncate"
              style={{
                color: step.status === 'completed' ? 'var(--status-success)' :
                       step.status === 'running'   ? 'var(--accent)' :
                       'var(--text-muted)',
                opacity: step.status === 'pending' ? 0.4 : 1,
              }}
            >
              {step.name}
            </span>
          ))}
        </div>
      </div>
    </nav>
  );
}
