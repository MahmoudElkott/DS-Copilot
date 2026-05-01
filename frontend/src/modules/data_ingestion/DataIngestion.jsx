import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload,
  FileSpreadsheet,
  HardDrive,
  CheckCircle2,
  AlertTriangle,
  X,
  ArrowRight,
  Database,
  Table2,
  Rows3,
  Columns3,
  Loader2,
} from 'lucide-react';
import StandardCard from '../../components/shared/StandardCard';
import useAppStore from '../../store/appStore';
import useAgent from '../../hooks/useAgent';

export default function DataIngestion() {
  const {
    uploadedFile,
    addMessage,
    isConnected,
    currentSessionId,
    settings,
    setAgentWorking,
  } = useAppStore();
  const { handleUpload } = useAgent();
  const navigate = useNavigate();
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isPipelineStarting, setIsPipelineStarting] = useState(false);

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
      // 1. Upload to backend
      const uploadData = await handleUpload(file);
      
      // 2. Local preview for better UX
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
    maxSize: 100 * 1024 * 1024, // 100MB
  });

  const handleStartPipeline = async () => {
    if (!uploadedFile || !isConnected) return;

    setIsPipelineStarting(true);

    try {
      // 1. Send the START_PIPELINE command via WebSocket
      const commandPayload = JSON.stringify({
        command: 'START_PIPELINE',
        file: uploadedFile.name,
        task: 'Initial Analysis',
      });

      window.dispatchEvent(new CustomEvent('ds-copilot:send', {
        detail: {
          message: commandPayload,
          type: 'command',
        },
      }));

      // 2. Add a system message to chat
      addMessage({
        role: 'system',
        content: `🚀 Pipeline started for **${uploadedFile.name}**. Switching to Notebook...`,
      });

      // 3. Mark agent as working
      setAgentWorking(true, 'profiling');

      // 4. Navigate to the Notebook view after a brief delay for UX
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

  return (
    <div className="h-full overflow-y-auto no-scrollbar">
      <div className="max-w-5xl mx-auto px-8 py-10 space-y-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <h1 className="text-3xl font-bold tracking-tight mb-2" style={{ color: 'var(--text-primary)' }}>
            Data Ingestion
          </h1>
          <p className="text-base" style={{ color: 'var(--text-secondary)' }}>
            Upload your dataset. Supported formats: CSV, JSON, Excel.
          </p>
        </motion.div>

        {/* Drop Zone */}
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

        {/* Preview */}
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

              {/* CTA */}
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
                      Start Pipeline <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
