import { motion, AnimatePresence } from 'framer-motion';
import { Target, TrendingUp, BarChart3, CheckCircle2, Loader2, AlertTriangle } from 'lucide-react';
import StandardCard from '../../components/shared/StandardCard';
import useAppStore from '../../store/appStore';

/**
 * Animated metric gauge — shows a metric name and value with a visual bar.
 */
function MetricGauge({ name, value, maxValue = 1.0 }) {
  // Normalize to 0-100% scale
  const isPercentScale = value <= 1.0 && maxValue <= 1.0;
  const percent = isPercentScale ? (value * 100) : Math.min((value / maxValue) * 100, 100);
  const displayValue = isPercentScale ? (value * 100).toFixed(1) + '%' : value.toFixed(4);

  // Color based on the value (higher = better for accuracy/f1, lower = better for error metrics)
  const isErrorMetric = ['mse', 'rmse', 'mae'].includes(name.toLowerCase());
  const quality = isErrorMetric
    ? (value < 0.5 ? 'good' : value < 1.0 ? 'ok' : 'poor')
    : (percent >= 80 ? 'good' : percent >= 60 ? 'ok' : 'poor');

  const colorMap = {
    good: 'var(--status-success)',
    ok: 'var(--status-warning)',
    poor: 'var(--status-error)',
  };

  const labelMap = {
    accuracy: 'Accuracy',
    precision: 'Precision',
    recall: 'Recall',
    f1_score: 'F1 Score',
    roc_auc: 'ROC AUC',
    r2_score: 'R\u00B2 Score',
    mse: 'MSE',
    rmse: 'RMSE',
    mae: 'MAE',
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="rounded-xl border p-4"
      style={{ background: 'var(--surface-card)', borderColor: 'var(--border)' }}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
          {labelMap[name] || name}
        </span>
        <span
          className="text-lg font-bold font-mono"
          style={{ color: colorMap[quality] }}
        >
          {displayValue}
        </span>
      </div>

      {/* Visual gauge bar */}
      {isPercentScale && (
        <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--surface-raised)' }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${percent}%` }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="h-full rounded-full"
            style={{ background: colorMap[quality] }}
          />
        </div>
      )}
    </motion.div>
  );
}

/**
 * Summary card showing overall model quality.
 */
function OverallScore({ metrics }) {
  // Use accuracy or f1_score as the "headline" metric
  const primary = metrics.accuracy ?? metrics.f1_score ?? metrics.roc_auc ?? null;
  if (primary === null) return null;

  const percent = (primary * 100).toFixed(1);
  const quality = primary >= 0.9 ? 'Excellent' : primary >= 0.8 ? 'Good' : primary >= 0.7 ? 'Fair' : 'Needs Work';
  const qualityColor = primary >= 0.9 ? 'var(--status-success)' : primary >= 0.8 ? 'var(--accent)' : primary >= 0.7 ? 'var(--status-warning)' : 'var(--status-error)';

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="rounded-2xl border p-6 text-center"
      style={{
        background: 'var(--surface-card)',
        borderColor: qualityColor,
        boxShadow: `0 0 20px ${qualityColor}22`,
      }}
    >
      <p className="text-[10px] uppercase tracking-wider font-bold mb-2" style={{ color: 'var(--text-muted)' }}>
        Model Score
      </p>
      <p className="text-5xl font-black font-mono mb-1" style={{ color: qualityColor }}>
        {percent}%
      </p>
      <p className="text-sm font-semibold" style={{ color: qualityColor }}>
        {quality}
      </p>
    </motion.div>
  );
}

export default function ModelEvaluation() {
  const { visualizationPayload, agentWorking, agentStage } = useAppStore();

  const evalMetrics = visualizationPayload?.evaluation_metrics;
  const evalOutput = visualizationPayload?.evaluation_output;
  const hasMetrics = evalMetrics && Object.keys(evalMetrics).length > 0;
  const isWorkingOnEval = agentWorking && agentStage === 'model_evaluation';

  // Split metrics into classification vs regression
  const classificationKeys = ['accuracy', 'precision', 'recall', 'f1_score', 'roc_auc'];
  const regressionKeys = ['r2_score', 'mse', 'rmse', 'mae'];

  const classificationMetrics = hasMetrics
    ? Object.entries(evalMetrics).filter(([k]) => classificationKeys.includes(k))
    : [];
  const regressionMetrics = hasMetrics
    ? Object.entries(evalMetrics).filter(([k]) => regressionKeys.includes(k))
    : [];

  return (
    <div className="h-full overflow-y-auto no-scrollbar">
      <div className="max-w-5xl mx-auto px-8 py-10 space-y-8">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold tracking-tight mb-2" style={{ color: 'var(--text-primary)' }}>
            Model Evaluation
          </h1>
          <p className="text-base" style={{ color: 'var(--text-secondary)' }}>
            Metrics, confusion matrices, and performance analysis.
          </p>
        </motion.div>

        {/* Working indicator */}
        <AnimatePresence>
          {isWorkingOnEval && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="flex items-center gap-3 px-5 py-4 rounded-xl"
              style={{ background: 'var(--accent-muted)', border: '1px solid var(--accent)' }}
            >
              <Loader2 className="w-5 h-5 animate-spin" style={{ color: 'var(--accent)' }} />
              <div>
                <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Evaluating model performance...
                </p>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  The agent is computing metrics. Results will appear here in real-time.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {hasMetrics ? (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-8"
          >
            {/* Overall Score Hero */}
            <OverallScore metrics={evalMetrics} />

            {/* Classification Metrics */}
            {classificationMetrics.length > 0 && (
              <div>
                <h2 className="text-sm font-bold uppercase tracking-wider mb-4 flex items-center gap-2"
                    style={{ color: 'var(--text-muted)' }}>
                  <CheckCircle2 className="w-4 h-4" style={{ color: 'var(--accent)' }} />
                  Classification Metrics
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {classificationMetrics.map(([name, value]) => (
                    <MetricGauge key={name} name={name} value={value} />
                  ))}
                </div>
              </div>
            )}

            {/* Regression Metrics */}
            {regressionMetrics.length > 0 && (
              <div>
                <h2 className="text-sm font-bold uppercase tracking-wider mb-4 flex items-center gap-2"
                    style={{ color: 'var(--text-muted)' }}>
                  <TrendingUp className="w-4 h-4" style={{ color: 'var(--accent)' }} />
                  Regression Metrics
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {regressionMetrics.map(([name, value]) => (
                    <MetricGauge key={name} name={name} value={value} maxValue={100} />
                  ))}
                </div>
              </div>
            )}

            {/* Raw output */}
            {evalOutput && (
              <StandardCard title="Evaluation Details" icon={<BarChart3 className="w-4 h-4" />}>
                <pre
                  className="text-xs font-mono whitespace-pre-wrap overflow-x-auto p-4 rounded-lg max-h-[400px] overflow-y-auto"
                  style={{ background: 'rgba(0,0,0,0.2)', color: 'var(--text-secondary)' }}
                >
                  {evalOutput}
                </pre>
              </StandardCard>
            )}

            {/* Timestamp */}
            {visualizationPayload?.evaluation_timestamp && (
              <p className="text-xs text-right" style={{ color: 'var(--text-muted)' }}>
                Evaluated: {new Date(visualizationPayload.evaluation_timestamp).toLocaleString()}
              </p>
            )}
          </motion.div>
        ) : (
          <StandardCard title="Evaluation Results" icon={<Target className="w-4 h-4" />}>
            <div className="py-16 text-center" style={{ color: 'var(--text-muted)' }}>
              <Target className="w-12 h-12 mx-auto mb-4 opacity-30" />
              <p className="text-sm font-medium mb-1">No evaluation data yet</p>
              <p className="text-xs opacity-70">
                Train a model in the pipeline, then run evaluation code.
                Metrics like accuracy, precision, and recall will appear here automatically.
              </p>
            </div>
          </StandardCard>
        )}
      </div>
    </div>
  );
}
