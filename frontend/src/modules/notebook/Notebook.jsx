import useAppStore from '../../store/appStore';
import NotebookEditor from './NotebookEditor';
import { motion } from 'framer-motion';
import { Bot, Loader2, Sparkles } from 'lucide-react';

/**
 * Notebook — Wrapper that feeds agent-generated cells into the NotebookEditor.
 * When the pipeline triggers, cells appear here automatically.
 */
export default function Notebook() {
  const { notebookCells, agentWorking, agentStage } = useAppStore();

  // Convert store cells to the format NotebookEditor expects
  const editorCells = notebookCells.length > 0
    ? notebookCells.map((cell) => ({
        id: cell.id,
        cell_type: cell.cell_type || 'code',
        source: cell.source || [],
        metadata: cell.metadata || { language: 'python' },
        outputs: cell.outputs || [],
        execution_count: cell.execution_count || 0,
      }))
    : undefined; // Let NotebookEditor use its defaults

  return (
    <div className="h-full flex flex-col">
      {/* Agent Working Banner */}
      {agentWorking && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="flex items-center gap-3 px-6 py-3 border-b"
          style={{
            background: 'linear-gradient(135deg, var(--accent-muted), transparent)',
            borderColor: 'var(--border)',
          }}
        >
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: 'var(--accent)', color: 'var(--bg-primary)' }}
          >
            <Loader2 className="w-4 h-4 animate-spin" />
          </div>
          <div>
            <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
              <Sparkles className="w-3.5 h-3.5 inline mr-1.5" style={{ color: 'var(--accent)' }} />
              DS-Copilot is working...
            </p>
            <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
              {agentStage
                ? `Current stage: ${agentStage.charAt(0).toUpperCase() + agentStage.slice(1)}`
                : 'Generating analysis code'}
            </p>
          </div>
        </motion.div>
      )}

      {/* Empty State — when no cells and not working */}
      {notebookCells.length === 0 && !agentWorking ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
          >
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6"
              style={{ background: 'var(--accent-muted)', color: 'var(--accent)' }}
            >
              <Bot className="w-8 h-8" />
            </div>
            <h2 className="text-xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
              Notebook
            </h2>
            <p className="text-sm max-w-sm" style={{ color: 'var(--text-muted)' }}>
              Upload a dataset and click <strong>Start Pipeline</strong> to auto-generate
              analysis cells here. You can also chat with the agent to generate code.
            </p>
          </motion.div>
        </div>
      ) : (
        <NotebookEditor initialCells={editorCells} />
      )}
    </div>
  );
}
