import { motion } from 'framer-motion';
import {
  Upload,
  BarChart3,
  Brain,
  Rocket,
  Activity,
  Clock,
  CheckCircle2,
  ArrowRight,
  Database,
  Cpu,
  TrendingUp,
} from 'lucide-react';
import StandardCard from '../../components/shared/StandardCard';
import useAppStore from '../../store/appStore';

const stagger = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
};

const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] } },
};

const QUICK_ACTIONS = [
  { label: 'Import CSV', icon: Upload, path: '/preparation', color: 'var(--status-success)' },
  { label: 'Run EDA', icon: BarChart3, path: '/eda', color: 'var(--status-info)' },
  { label: 'Train Model', icon: Brain, path: '/training', color: 'var(--status-warning)' },
  { label: 'Deploy', icon: Rocket, path: '/deployment', color: 'var(--status-error)' },
];

export default function ProjectHub() {
  const { pipelineSteps, pipelineStatus, stats, uploadedFile } = useAppStore();

  const completedSteps = pipelineSteps.filter(s => s.status === 'completed').length;
  const runningStep = pipelineSteps.find(s => s.status === 'running');

  return (
    <div className="h-full overflow-y-auto no-scrollbar">
      <div className="max-w-6xl mx-auto px-8 py-10 space-y-8">
        {/* Welcome Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <h1 className="text-3xl font-bold tracking-tight mb-2" style={{ color: 'var(--text-primary)' }}>
            Project Hub
          </h1>
          <p className="text-base" style={{ color: 'var(--text-secondary)' }}>
            Your autonomous ML workspace. Everything starts here.
          </p>
        </motion.div>

        {/* Metrics Row */}
        <motion.div
          variants={stagger}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        >
          <motion.div variants={item}>
            <StandardCard compact>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
                    Pipeline
                  </p>
                  <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                    {completedSteps}/{pipelineSteps.length}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'var(--accent-muted)' }}>
                  <Activity className="w-5 h-5" style={{ color: 'var(--accent)' }} />
                </div>
              </div>
            </StandardCard>
          </motion.div>

          <motion.div variants={item}>
            <StandardCard compact>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
                    Status
                  </p>
                  <p className="text-lg font-bold capitalize" style={{ color: pipelineStatus === 'running' ? 'var(--status-warning)' : 'var(--text-primary)' }}>
                    {pipelineStatus || 'Idle'}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'var(--accent-muted)' }}>
                  {pipelineStatus === 'running'
                    ? <Clock className="w-5 h-5 animate-spin" style={{ color: 'var(--status-warning)' }} />
                    : <CheckCircle2 className="w-5 h-5" style={{ color: 'var(--status-success)' }} />
                  }
                </div>
              </div>
            </StandardCard>
          </motion.div>

          <motion.div variants={item}>
            <StandardCard compact>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
                    Dataset
                  </p>
                  <p className="text-lg font-bold truncate max-w-[140px]" style={{ color: 'var(--text-primary)' }} title={uploadedFile ? uploadedFile.name : 'None'}>
                    {uploadedFile ? uploadedFile.name : 'None'}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'var(--accent-muted)' }}>
                  <Database className="w-5 h-5" style={{ color: 'var(--accent)' }} />
                </div>
              </div>
            </StandardCard>
          </motion.div>

          <motion.div variants={item}>
            <StandardCard compact>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
                    Agent Calls
                  </p>
                  <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                    {stats.totalCalls}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'var(--accent-muted)' }}>
                  <Cpu className="w-5 h-5" style={{ color: 'var(--accent)' }} />
                </div>
              </div>
            </StandardCard>
          </motion.div>
        </motion.div>

        {/* Quick Actions */}
        <motion.div variants={stagger} initial="hidden" animate="show">
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>Quick Actions</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {QUICK_ACTIONS.map((action) => {
              const Icon = action.icon;
              return (
                <motion.a
                  key={action.label}
                  variants={item}
                  href={action.path}
                  className="card-hover p-5 flex flex-col items-center gap-3 text-center group"
                >
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110 duration-200"
                    style={{ background: `${action.color}15`, color: action.color }}
                  >
                    <Icon className="w-6 h-6" />
                  </div>
                  <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{action.label}</span>
                </motion.a>
              );
            })}
          </div>
        </motion.div>

        {/* Pipeline Progress */}
        <StandardCard title="Mission Lifecycle" icon={<TrendingUp className="w-4 h-4" />}>
          <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            {pipelineSteps.map((step, i) => (
              <div key={step.key} className="flex flex-col items-center gap-2">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center text-xs font-bold transition-all duration-300"
                  style={{
                    background:
                      step.status === 'completed' ? 'var(--status-success)' :
                      step.status === 'running'   ? 'var(--status-warning)' :
                      step.status === 'error'     ? 'var(--status-error)' :
                      'var(--surface-raised)',
                    color:
                      step.status !== 'pending' ? 'var(--bg-primary)' : 'var(--text-muted)',
                  }}
                >
                  {i + 1}
                </div>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-center" style={{
                  color: step.status === 'running' ? 'var(--status-warning)' :
                         step.status === 'completed' ? 'var(--status-success)' : 'var(--text-muted)'
                }}>
                  {step.name}
                </span>
              </div>
            ))}
          </div>
        </StandardCard>
      </div>
    </div>
  );
}
