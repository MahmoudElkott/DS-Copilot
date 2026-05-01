import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BarChart3, RefreshCw, FileSpreadsheet, AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import StandardCard from '../../components/shared/StandardCard';
import useAppStore from '../../store/appStore';

/**
 * Parse a text-table (like pandas describe/head output) into structured data.
 * Returns { headers: string[], rows: string[][] }
 */
function parseTextTable(text) {
  if (!text) return null;

  const lines = text.trim().split('\n').filter(Boolean);
  if (lines.length < 2) return null;

  // Try to detect if first line is headers
  const rows = lines.map(line =>
    line.split(/\s{2,}/).map(c => c.trim()).filter(Boolean)
  );

  // Use first row as headers if it looks like labels
  const headers = rows[0];
  const data = rows.slice(1);

  if (headers.length < 2 || data.length < 1) return null;

  return { headers, rows: data };
}

/**
 * Stat card for showing a key metric.
 */
function StatCard({ label, value, icon: Icon, accent = false }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="rounded-xl border p-4"
      style={{
        background: accent ? 'var(--accent-muted)' : 'var(--surface-card)',
        borderColor: accent ? 'var(--accent)' : 'var(--border)',
      }}
    >
      <div className="flex items-center gap-2 mb-2">
        {Icon && <Icon className="w-4 h-4" style={{ color: 'var(--accent)' }} />}
        <span className="text-[10px] uppercase tracking-wider font-bold" style={{ color: 'var(--text-muted)' }}>
          {label}
        </span>
      </div>
      <p className="text-xl font-bold font-mono" style={{ color: 'var(--text-primary)' }}>
        {value}
      </p>
    </motion.div>
  );
}

/**
 * Renders a parsed table from profiling output.
 */
function DataTable({ title, data }) {
  if (!data) return null;

  return (
    <StandardCard title={title} icon={<BarChart3 className="w-4 h-4" />}>
      <div className="overflow-x-auto -mx-2">
        <table className="w-full text-sm">
          <thead>
            <tr>
              {data.headers.map((h, i) => (
                <th
                  key={i}
                  className="px-3 py-2 text-left text-[11px] font-bold uppercase tracking-wider whitespace-nowrap"
                  style={{ color: 'var(--accent)', borderBottom: '1px solid var(--border)' }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, rIdx) => (
              <tr
                key={rIdx}
                style={{ borderBottom: '1px solid var(--border)' }}
                className="transition-colors hover:bg-[var(--accent-muted)]"
              >
                {row.map((cell, cIdx) => (
                  <td
                    key={cIdx}
                    className="px-3 py-2 whitespace-nowrap font-mono text-xs"
                    style={{ color: cIdx === 0 ? 'var(--text-primary)' : 'var(--text-secondary)' }}
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
  );
}

export default function DataProfiling() {
  const { visualizationPayload, uploadedFile, agentWorking, agentStage } = useAppStore();
  const [parsedData, setParsedData] = useState(null);

  // Parse profiling_output when it arrives
  useEffect(() => {
    const raw = visualizationPayload?.profiling_output;
    if (!raw) return;

    // Try to split into sections (shape, describe, head, etc.)
    const sections = raw.split(/\n(?=\S.*:?\n[-=]+|\S+\s+\S+)/);
    const tables = sections
      .map(section => parseTextTable(section))
      .filter(Boolean);

    if (tables.length > 0) {
      setParsedData(tables);
    } else {
      // Fallback: treat the entire output as one block
      setParsedData([{ raw }]);
    }
  }, [visualizationPayload?.profiling_output]);

  const hasProfiling = visualizationPayload?.profiling_output;
  const isWorkingOnProfiling = agentWorking && agentStage === 'profiling';

  return (
    <div className="h-full overflow-y-auto no-scrollbar">
      <div className="max-w-5xl mx-auto px-8 py-10 space-y-8">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold tracking-tight mb-2" style={{ color: 'var(--text-primary)' }}>
            Data Profiling
          </h1>
          <p className="text-base" style={{ color: 'var(--text-secondary)' }}>
            Automated statistical profiling and data quality analysis.
          </p>
        </motion.div>

        {/* Working indicator */}
        <AnimatePresence>
          {isWorkingOnProfiling && (
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
                  Generating profiling results...
                </p>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  The AI agent is analyzing your dataset. Results will appear here in real-time.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* File info */}
        {uploadedFile && (
          <div className="grid grid-cols-2 gap-4">
            <StatCard label="Dataset" value={uploadedFile.name} icon={FileSpreadsheet} />
            <StatCard
              label="Status"
              value={hasProfiling ? 'Profiled ✓' : 'Pending'}
              icon={hasProfiling ? CheckCircle2 : AlertTriangle}
              accent={!!hasProfiling}
            />
          </div>
        )}

        {/* Profiling Results */}
        {hasProfiling ? (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Raw output display */}
            <StandardCard title="Statistical Summary" icon={<BarChart3 className="w-4 h-4" />}>
              <pre
                className="text-xs font-mono whitespace-pre-wrap overflow-x-auto p-4 rounded-lg max-h-[500px] overflow-y-auto"
                style={{ background: 'rgba(0,0,0,0.2)', color: 'var(--text-secondary)' }}
              >
                {visualizationPayload.profiling_output}
              </pre>
            </StandardCard>

            {/* Parsed tables if available */}
            {parsedData && parsedData.filter(d => d.headers).map((table, i) => (
              <DataTable key={i} title={`Table ${i + 1}`} data={table} />
            ))}

            {visualizationPayload.profiling_timestamp && (
              <p className="text-xs text-right" style={{ color: 'var(--text-muted)' }}>
                Last updated: {new Date(visualizationPayload.profiling_timestamp).toLocaleString()}
              </p>
            )}
          </motion.div>
        ) : (
          <StandardCard title="Profiling Results" icon={<BarChart3 className="w-4 h-4" />}>
            <div className="py-16 text-center" style={{ color: 'var(--text-muted)' }}>
              <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-30" />
              <p className="text-sm font-medium mb-1">No profiling data yet</p>
              <p className="text-xs opacity-70">
                Start the pipeline from Data Ingestion, then run the profiling code cell in the Notebook.
              </p>
            </div>
          </StandardCard>
        )}
      </div>
    </div>
  );
}
