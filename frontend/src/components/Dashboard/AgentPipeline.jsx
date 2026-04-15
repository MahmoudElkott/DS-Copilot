// frontend/src/components/Dashboard/AgentPipeline.jsx
import { motion } from 'framer-motion';
import { CheckCircle2, Circle, Loader2, XCircle, ChevronRight } from 'lucide-react';
import useAppStore from '../../store/appStore';

const STEP_ICONS = {
  data_ingest: '📥',
  data_cleaning: '🧹',
  eda: '📊',
  model_selection: '🤖',
  code_writing: '✍️',
  testing: '🧪',
  optimization: '⚡',
  documentation: '📝',
};

const STATUS_CONFIG = {
  pending: {
    icon: Circle,
    color: 'text-gray-500',
    bg: 'bg-surface-700',
    glow: '',
  },
  running: {
    icon: Loader2,
    color: 'text-amber-400',
    bg: 'bg-amber-500/20',
    glow: 'glow-brand animate-pulse-slow',
  },
  completed: {
    icon: CheckCircle2,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/20',
    glow: 'glow-success',
  },
  failed: {
    icon: XCircle,
    color: 'text-red-400',
    bg: 'bg-red-500/20',
    glow: 'glow-error',
  },
};

export default function AgentPipeline() {
  const { pipelineSteps, setActiveCodeStep } = useAppStore();

  return (
    <div className="w-full">
      <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-brand-500" />
        Agent Pipeline
      </h3>

      <div className="flex items-center gap-1 overflow-x-auto no-scrollbar pb-2">
        {pipelineSteps.map((step, index) => {
          const config = STATUS_CONFIG[step.status] || STATUS_CONFIG.pending;
          const StatusIcon = config.icon;
          const isLast = index === pipelineSteps.length - 1;

          return (
            <div key={step.key} className="flex items-center flex-shrink-0">
              <motion.button
                onClick={() => setActiveCodeStep(step.key)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={`flex flex-col items-center gap-1.5 px-3 py-2.5 rounded-xl transition-all duration-300 ${config.bg} border ${
                  step.status === 'running' ? 'border-amber-500/30' :
                  step.status === 'completed' ? 'border-emerald-500/20' :
                  step.status === 'failed' ? 'border-red-500/20' :
                  'border-surface-700'
                } hover:bg-white/5 min-w-[72px]`}
              >
                {/* Step Icon */}
                <div className={`relative ${config.glow} rounded-full`}>
                  <span className="text-lg">{STEP_ICONS[step.key]}</span>
                  <div className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full flex items-center justify-center ${config.bg}`}>
                    <StatusIcon className={`w-2.5 h-2.5 ${config.color} ${step.status === 'running' ? 'animate-spin' : ''}`} />
                  </div>
                </div>

                {/* Step Name */}
                <span className={`text-[10px] font-medium ${config.color}`}>
                  {step.name}
                </span>
              </motion.button>

              {/* Arrow */}
              {!isLast && (
                <ChevronRight className={`w-3.5 h-3.5 mx-0.5 flex-shrink-0 ${
                  step.status === 'completed' ? 'text-emerald-500/50' : 'text-surface-700'
                }`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
