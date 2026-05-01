import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload,
  FileSpreadsheet,
  Wand2,
  CheckCircle2,
  AlertTriangle,
  X,
  ArrowRight,
  Table2,
  Rows3,
  Columns3,
  Loader2,
  BarChart3,
  Sparkles,
} from 'lucide-react';
import StandardCard from '../../components/shared/StandardCard';
import useAppStore from '../../store/appStore';
import useAgent from '../../hooks/useAgent';

/**
 * Phase indicator — shows which sub-phase of Data Preparation is active.
 */
function PhaseStep({ label, status, index }) {
  const isActive = status === 'active';
  const isDone = status === 'done';

  return (
    <div className="flex items-center gap-2">
      <div
        className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all duration-300"
        style={{
          background: isDone ? 'var(--status-success)' : isActive ? 'var(--accent)' : 'var(--surface-raised)',
          color: isDone || isActive ? 'var(--bg-primary)' : 'var(--text-muted)',
          boxShadow: isActive ? '0 0 8px var(--accent)' : 'none',
        }}
      >
        {isDone ? '✓' : index + 1}
      </div>
      <span
        className="text-xs font-semibold"
        style={{
          color: isDone ? 'var(--status-success)' : isActive ? 'var(--accent)' : 'var(--text-muted)',
        }}
      >
        {label}
      </span>
    </div>
  );
}

export default function DataPreparation() {
  const {
    uploadedFile,
    addMessage,
    isConnected,
    currentSessionId,
    settings,
    setAgentWorking,
    agentWorking,
    agentStage,
    visualizationPayload,
    pipelineSteps,
  } = useAppStore();
  const { handleUpload } = useAgent();
  const navigate = useNavigate();
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isPipelineStarting, setIsPipelineStarting] = useState(false);

  // Determine sub-phase status
  const prepStep = pipelineSteps.find(s => s.key === 'data_prep');
  const isPrepping = agentWorking && ['data_preparation', 'profiling', 'cleaning', 'ingestion'].includes(agentStage);
  const isPrepDone = prepStep?.status === 'completed';
  const hasProfiling = !!visualizationPayload?.profiling_output;

  const onDrop = useCallback(async (accepted, rejected) => {
    setError(null);

    if (rejected.length > 0) {
      setError('Unsupported file format. Please use CSV, Excel, JSON, or Parquet.');
      return;
    }

    const file = accepted[0];
    if (!file) return;

    setIsUploading(true);
    try {
      await handleUpload(file);

      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target.result;
        const lines = text.split('\n').filter(Boolean);
        const headers = lines[0]?.split(',').map(h => h.trim().replace(/"/g, ''));
        const rows = lines.slice(1, 6).map(line =>
          line.split(',').map(c => c.trim().replace(/"/g, ''))
        );
        setPreview({ headers, rows, totalRows: lines.length - 1 });
      };
      reader.readAsText(file);
    } catch (err) {
      setError('Failed to upload/read file.');
    } finally {
      setIsUploading(false);
    }
  }, [handleUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/json': ['.json'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
    maxFiles: 1,
    maxSize: 100 * 1024 * 1024,
  });

  const handleStartPipeline = async () => {
    if (!uploadedFile || !isConnected) return;

    setIsPipelineStarting(true);

    try {
      const commandPayload = JSON.stringify({
        command: 'START_PIPELINE',
        file: uploadedFile.name,
        task: 'Data Preparation',
      });

      window.dispatchEvent(new CustomEvent('ds-copilot:send', {
        detail: {
          message: commandPayload,
          type: 'command',
        },
      }));

      addMessage({
        role: 'system',
        content: `🚀 Pipeline started for **${uploadedFile.name}**. Running Data Preparation...`,
      });

      setAgentWorking(true, 'data_preparation');

      setTimeout(() => {
        navigate('/notebook');
      }, 600);

    } catch (err) {
      console.error('Failed to start pipeline:', err);
      setError('Failed to start pipeline. Please try again.');
    } finally {
      setIsPipelineStarting(false);
    }
  };

  // Sub-phase indicators
  const subPhases = [
    { label: 'Ingest', status: preview ? 'done' : isUploading ? 'active' : 'pending' },
    { label: 'Profile', status: hasProfiling ? 'done' : isPrepping ? 'active' : 'pending' },
    { label: 'Clean', status: isPrepDone ? 'done' : (isPrepping && hasProfiling) ? 'active' : 'pending' },
  ];

  return (
    <div className="h-full overflow-y-auto no-scrollbar">
      <div className="max-w-5xl mx-auto px-8 py-10 space-y-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Data Preparation
            </h1>
            {isPrepDone && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold"
                style={{ background: 'rgba(16, 185, 129, 0.15)', color: 'var(--status-success)' }}
              >
                <CheckCircle2 className="w-3 h-3" /> Complete
              </motion.div>
            )}
          </div>
          <p className="text-base" style={{ color: 'var(--text-secondary)' }}>
            Upload, profile, and clean your dataset in one autonomous step.
          </p>
        </motion.div>

        {/* Sub-phase tracker */}
        {(preview || isPrepping || isPrepDone) && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-6 px-5 py-3 rounded-xl"
            style={{ background: 'var(--surface-card)', border: '1px solid var(--border)' }}
          >
            {subPhases.map((phase, i) => (
              <div key={phase.label} className="flex items-center gap-3">
                <PhaseStep label={phase.label} status={phase.status} index={i} />
                {i < subPhases.length - 1 && (
                  <div
                    className="w-8 h-px"
                    style={{
                      background: subPhases[i + 1].status !== 'pending' ? 'var(--accent)' : 'var(--border)',
                    }}
                  />
                )}
              </div>
            ))}
          </motion.div>
        )}

        {/* Agent working indicator */}
        <AnimatePresence>
          {isPrepping && (
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
                  Preparing your data...
                </p>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  The AI is loading, profiling, and cleaning. Watch the Notebook for live output.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Drop Zone — only show if no preview yet */}
        {!preview && !isPrepDone && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.4 }}
          >
            <div
              {...getRootProps()}
              className="relative rounded-2xl border-2 border-dashed cursor-pointer transition-all duration-300 overflow-hidden group"
              style={{
                borderColor: isDragActive ? 'var(--accent)' : error ? 'var(--status-error)' : 'var(--border)',
                background: isDragActive ? 'var(--accent-muted)' : 'var(--surface-card)',
                minHeight: '240px',
              }}
            >
              <input {...getInputProps()} />

              <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
                <motion.div
                  animate={isDragActive ? { scale: 1.1, rotate: -5 } : { scale: 1, rotate: 0 }}
                  transition={{ type: 'spring', stiffness: 300 }}
                  className="w-20 h-20 rounded-2xl flex items-center justify-center mb-6"
                  style={{
                    background: isDragActive ? 'var(--accent)' : 'var(--accent-muted)',
                    color: isDragActive ? 'var(--bg-primary)' : 'var(--accent)',
                  }}
                >
                  {isUploading
                    ? <div className="w-8 h-8 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    : <Upload className="w-8 h-8" />
                  }
                </motion.div>

                <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
                  {isDragActive ? 'Drop it here!' : 'Drag & drop your dataset'}
                </h3>
                <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
                  or click to browse. Up to 100 MB.
                </p>

                <div className="flex items-center gap-3">
                  {['CSV', 'JSON', 'XLSX'].map(fmt => (
                    <span
                      key={fmt}
                      className="px-3 py-1 rounded-lg text-xs font-bold"
                      style={{ background: 'var(--surface-raised)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
                    >
                      .{fmt}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm"
              style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--status-error)', border: '1px solid rgba(239,68,68,0.2)' }}
            >
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              {error}
              <button onClick={() => setError(null)} className="ml-auto"><X className="w-4 h-4" /></button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Preview — shows after upload */}
        <AnimatePresence>
          {preview && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.4 }}
              className="space-y-6"
            >
              {/* File Stats */}
              <div className="grid grid-cols-3 gap-4">
                <StandardCard compact icon={<FileSpreadsheet className="w-4 h-4" />}>
                  <div className="mt-2">
                    <p className="text-[10px] uppercase tracking-wider font-bold" style={{ color: 'var(--text-muted)' }}>File</p>
                    <p className="text-sm font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{uploadedFile?.name}</p>
                  </div>
                </StandardCard>
                <StandardCard compact icon={<Rows3 className="w-4 h-4" />}>
                  <div className="mt-2">
                    <p className="text-[10px] uppercase tracking-wider font-bold" style={{ color: 'var(--text-muted)' }}>Rows</p>
                    <p className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>{preview.totalRows.toLocaleString()}</p>
                  </div>
                </StandardCard>
                <StandardCard compact icon={<Columns3 className="w-4 h-4" />}>
                  <div className="mt-2">
                    <p className="text-[10px] uppercase tracking-wider font-bold" style={{ color: 'var(--text-muted)' }}>Columns</p>
                    <p className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>{preview.headers.length}</p>
                  </div>
                </StandardCard>
              </div>

              {/* Data Table Preview */}
              <StandardCard title="Preview (first 5 rows)" icon={<Table2 className="w-4 h-4" />}>
                <div className="overflow-x-auto -mx-2">
                  <table className="w-full text-sm">
                    <thead>
                      <tr>
                        {preview.headers.map((h, i) => (
                          <th
                            key={i}
                            className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wider whitespace-nowrap"
                            style={{ color: 'var(--accent)', borderBottom: '1px solid var(--border)' }}
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.rows.map((row, rIdx) => (
                        <tr
                          key={rIdx}
                          className="transition-colors"
                          style={{ borderBottom: '1px solid var(--border)' }}
                          onMouseEnter={(e) => e.currentTarget.style.background = 'var(--accent-muted)'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        >
                          {row.map((cell, cIdx) => (
                            <td
                              key={cIdx}
                              className="px-4 py-2.5 whitespace-nowrap font-mono text-xs"
                              style={{ color: 'var(--text-secondary)' }}
                            >
                              {cell || '—'}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </StandardCard>

              {/* Profiling output (appears after AI processes) */}
              {hasProfiling && (
                <StandardCard title="Profiling Summary" icon={<BarChart3 className="w-4 h-4" />}>
                  <pre
                    className="text-xs font-mono whitespace-pre-wrap overflow-x-auto p-4 rounded-lg max-h-[400px] overflow-y-auto"
                    style={{ background: 'rgba(0,0,0,0.2)', color: 'var(--text-secondary)' }}
                  >
                    {visualizationPayload.profiling_output}
                  </pre>
                </StandardCard>
              )}

              {/* CTA */}
              {!isPrepDone && (
                <div className="flex justify-end">
                  <button
                    onClick={handleStartPipeline}
                    disabled={isPipelineStarting || !isConnected}
                    className="btn-primary text-base px-8 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isPipelineStarting ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Starting...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        Start Pipeline <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* Completed badge */}
              {isPrepDone && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-3 px-5 py-4 rounded-xl"
                  style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid var(--status-success)' }}
                >
                  <CheckCircle2 className="w-5 h-5" style={{ color: 'var(--status-success)' }} />
                  <div>
                    <p className="text-sm font-semibold" style={{ color: 'var(--status-success)' }}>
                      Data Preparation complete
                    </p>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      Dataset loaded, profiled, and cleaned. Proceed to EDA Exploration.
                    </p>
                  </div>
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Empty state when nothing uploaded and prep not done */}
        {!preview && isPrepDone && (
          <StandardCard title="Data Prepared" icon={<Wand2 className="w-4 h-4" />}>
            <div className="py-12 text-center" style={{ color: 'var(--text-muted)' }}>
              <CheckCircle2 className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--status-success)', opacity: 0.5 }} />
              <p className="text-sm font-medium mb-1">This stage is complete.</p>
              <p className="text-xs opacity-70">Check the Notebook for the full data preparation report.</p>
            </div>
          </StandardCard>
        )}
      </div>
    </div>
  );
}
