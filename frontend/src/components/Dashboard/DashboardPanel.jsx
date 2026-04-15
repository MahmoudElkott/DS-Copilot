// frontend/src/components/Dashboard/DashboardPanel.jsx
import { Activity, Zap, CheckCircle2, XCircle, Timer, Brain } from 'lucide-react';
import useAppStore from '../../store/appStore';
import MetricsCard from './MetricsCard';
import AgentPipeline from './AgentPipeline';

export default function DashboardPanel() {
  const { pipelineSteps, pipelineStatus, stats, harness_reports } = useAppStore();

  const completedSteps = pipelineSteps.filter((s) => s.status === 'completed').length;
  const failedSteps = pipelineSteps.filter((s) => s.status === 'failed').length;
  const totalSteps = pipelineSteps.length;
  const progress = Math.round((completedSteps / totalSteps) * 100);

  return (
    <div className="h-full overflow-y-auto p-6 no-scrollbar">
      {/* Pipeline Visualization */}
      <div className="mb-8">
        <AgentPipeline />
      </div>

      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-300">Pipeline Progress</span>
          <span className="text-sm font-bold text-brand-400">{progress}%</span>
        </div>
        <div className="w-full h-2 bg-surface-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-brand-600 to-purple-500 rounded-full transition-all duration-1000 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        <MetricsCard
          title="Steps Complete"
          value={completedSteps}
          suffix={`/ ${totalSteps}`}
          icon={CheckCircle2}
          color="emerald"
          delay={0}
        />
        <MetricsCard
          title="Failures"
          value={failedSteps}
          icon={XCircle}
          color={failedSteps > 0 ? 'red' : 'emerald'}
          delay={100}
        />
        <MetricsCard
          title="API Calls"
          value={stats?.totalCalls || 0}
          icon={Zap}
          color="amber"
          delay={200}
        />
        <MetricsCard
          title="Budget Left"
          value={stats?.budgetRemaining || 100}
          icon={Brain}
          color="purple"
          delay={300}
        />
        <MetricsCard
          title="Status"
          value={pipelineStatus || 'Idle'}
          icon={Activity}
          color={
            pipelineStatus === 'completed' ? 'emerald' :
            pipelineStatus === 'running' ? 'amber' :
            pipelineStatus === 'failed' ? 'red' : 'brand'
          }
          delay={400}
        />
        <MetricsCard
          title="Active Sessions"
          value={stats?.activeSessions || 0}
          icon={Timer}
          color="cyan"
          delay={500}
        />
      </div>

      {/* Empty state */}
      {!pipelineStatus && (
        <div className="text-center py-12">
          <div className="w-16 h-16 rounded-2xl bg-surface-800 flex items-center justify-center mx-auto mb-4">
            <Activity className="w-8 h-8 text-gray-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-400 mb-2">No Pipeline Running</h3>
          <p className="text-sm text-gray-500 max-w-sm mx-auto">
            Upload a dataset and start a pipeline to see real-time progress, metrics, and agent activity here.
          </p>
        </div>
      )}
    </div>
  );
}
