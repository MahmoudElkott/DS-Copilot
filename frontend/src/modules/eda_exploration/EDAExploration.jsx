import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FlaskConical, TrendingUp, ScatterChart, Loader2, BarChart3, PieChart } from 'lucide-react';
import StandardCard from '../../components/shared/StandardCard';
import useAppStore from '../../store/appStore';

/**
 * Simple bar chart using CSS — no charting library needed.
 */
function MiniBarChart({ data, label }) {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data.map(d => Math.abs(d.value)));

  return (
    <div className="space-y-1.5">
      {label && (
        <p className="text-[10px] uppercase tracking-wider font-bold mb-3" style={{ color: 'var(--text-muted)' }}>
          {label}
        </p>
      )}
      {data.map((item, i) => (
        <div key={i} className="flex items-center gap-3">
          <span
            className="text-xs font-mono w-24 truncate text-right"
            style={{ color: 'var(--text-secondary)' }}
          >
            {item.name}
          </span>
          <div className="flex-1 h-5 rounded-full overflow-hidden" style={{ background: 'var(--surface-raised)' }}>
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(Math.abs(item.value) / max) * 100}%` }}
              transition={{ duration: 0.6, delay: i * 0.05 }}
              className="h-full rounded-full"
              style={{
                background: item.value >= 0
                  ? 'linear-gradient(90deg, var(--accent), var(--status-success))'
                  : 'linear-gradient(90deg, var(--status-error), var(--status-warning))',
              }}
            />
          </div>
          <span
            className="text-xs font-mono w-16 text-right"
            style={{ color: 'var(--text-muted)' }}
          >
            {typeof item.value === 'number' ? item.value.toFixed(2) : item.value}
          </span>
        </div>
      ))}
    </div>
  );
}

/**
 * Attempts to parse correlation-like or distribution-like data from text.
 */
function parseDistributions(text) {
  if (!text) return [];

  const lines = text.trim().split('\n').filter(Boolean);
  const result = [];

  for (const line of lines) {
    const parts = line.split(/\s{2,}/).map(s => s.trim());
    if (parts.length >= 2) {
      const name = parts[0];
      const value = parseFloat(parts[parts.length - 1]);
      if (!isNaN(value)) {
        result.push({ name, value });
      }
    }
  }

  return result;
}

export default function EDAExploration() {
  const { visualizationPayload, uploadedFile, agentWorking, agentStage } = useAppStore();
  const [distributions, setDistributions] = useState([]);

  const edaOutput = visualizationPayload?.eda_output;
  const profilingOutput = visualizationPayload?.profiling_output;
  const edaImages = visualizationPayload?.eda_images || {};
  const hasImages = Object.keys(edaImages).length > 0;
  const hasData = edaOutput || profilingOutput || hasImages;
  const isWorkingOnEDA = agentWorking && (agentStage === 'eda' || agentStage === 'data_preparation');

  // Try to extract numeric distributions from any available output
  useEffect(() => {
    const source = edaOutput || profilingOutput;
    if (!source) return;

    const parsed = parseDistributions(source);
    if (parsed.length > 0) {
      setDistributions(parsed.slice(0, 20)); // limit to 20 items
    }
  }, [edaOutput, profilingOutput]);

  return (
    <div className="h-full overflow-y-auto no-scrollbar">
      <div className="max-w-5xl mx-auto px-8 py-10 space-y-8">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold tracking-tight mb-2" style={{ color: 'var(--text-primary)' }}>
            EDA Exploration
          </h1>
          <p className="text-base" style={{ color: 'var(--text-secondary)' }}>
            Statistical analysis, distributions, and correlation mapping.
          </p>
        </motion.div>

        {/* Working indicator */}
        <AnimatePresence>
          {isWorkingOnEDA && (
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
                  Running exploratory analysis...
                </p>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  The agent is generating EDA insights. Charts and stats will appear here.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {hasData ? (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Distribution bars */}
            {distributions.length > 0 && (
              <StandardCard title="Feature Distributions" icon={<TrendingUp className="w-4 h-4" />}>
                <MiniBarChart data={distributions} label="Numeric Features" />
              </StandardCard>
            )}

            {/* EDA Visualizations */}
            {hasImages && (
              <StandardCard title="EDA Visualizations" icon={<PieChart className="w-4 h-4" />}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.entries(edaImages).map(([filename, val]) => {
                    const { getArtifactUrl } = useAppStore.getState();
                    const src = val?.__lazy ? getArtifactUrl(val.filename) : val;
                    
                    return (
                      <div key={filename} className="flex flex-col items-center p-2 rounded-lg" style={{ background: 'var(--surface-raised)' }}>
                        <img src={src} alt={filename} className="w-full h-auto rounded" loading="lazy" />
                        <p className="text-xs mt-2 font-mono" style={{ color: 'var(--text-muted)' }}>{filename}</p>
                      </div>
                    );
                  })}
                </div>
              </StandardCard>
            )}

            {/* Raw EDA output */}
            {edaOutput && (
              <StandardCard title="EDA Analysis Output" icon={<ScatterChart className="w-4 h-4" />}>
                <pre
                  className="text-xs font-mono whitespace-pre-wrap overflow-x-auto p-4 rounded-lg max-h-[500px] overflow-y-auto"
                  style={{ background: 'rgba(0,0,0,0.2)', color: 'var(--text-secondary)' }}
                >
                  {edaOutput}
                </pre>
              </StandardCard>
            )}

            {/* Show profiling data as fallback for EDA */}
            {!edaOutput && profilingOutput && (
              <StandardCard title="Profiling Data (EDA Preview)" icon={<BarChart3 className="w-4 h-4" />}>
                <pre
                  className="text-xs font-mono whitespace-pre-wrap overflow-x-auto p-4 rounded-lg max-h-[400px] overflow-y-auto"
                  style={{ background: 'rgba(0,0,0,0.2)', color: 'var(--text-secondary)' }}
                >
                  {profilingOutput}
                </pre>
              </StandardCard>
            )}

            {/* Timestamp */}
            {(visualizationPayload?.eda_timestamp || visualizationPayload?.profiling_timestamp) && (
              <p className="text-xs text-right" style={{ color: 'var(--text-muted)' }}>
                Last updated:{' '}
                {new Date(
                  visualizationPayload.eda_timestamp || visualizationPayload.profiling_timestamp
                ).toLocaleString()}
              </p>
            )}
          </motion.div>
        ) : (
          <StandardCard title="Exploration Workspace" icon={<FlaskConical className="w-4 h-4" />}>
            <div className="py-16 text-center" style={{ color: 'var(--text-muted)' }}>
              <FlaskConical className="w-12 h-12 mx-auto mb-4 opacity-30" />
              <p className="text-sm font-medium mb-1">No EDA data yet</p>
              <p className="text-xs opacity-70">
                Run the pipeline and execute code cells in the Notebook. EDA results will appear here automatically.
              </p>
            </div>
          </StandardCard>
        )}
      </div>
    </div>
  );
}
