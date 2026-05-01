import React, { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play,
  Plus,
  Trash2,
  ChevronUp,
  ChevronDown,
  FileCode,
  Type,
  Copy,
  Download,
  Save,
  RotateCcw,
  Check,
  X,
  Maximize2,
  Minimize2,
  AlertTriangle
} from 'lucide-react';
import { toast } from 'sonner';
import useAppStore from '../../store/appStore';

// ═══════════════════════════════════════════════════════════════════════════
// Cell Types
// ═══════════════════════════════════════════════════════════════════════════

const CELL_TYPE = {
  MARKDOWN: 'markdown',
  CODE: 'code'
};

// ═══════════════════════════════════════════════════════════════════════════
// Utility: Simple Markdown Renderer (no external deps)
// ═══════════════════════════════════════════════════════════════════════════

function renderMarkdown(text) {
  if (!text) return '';

  let html = text
    // Headers
    .replace(/^### (.*$)/gim, '<h3 class="text-lg font-bold mt-4 mb-2">$1</h3>')
    .replace(/^## (.*$)/gim, '<h2 class="text-xl font-bold mt-5 mb-2">$1</h2>')
    .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mt-6 mb-3">$1</h1>')
    // Bold & Italic
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-black/20 font-mono text-sm">$1</code>')
    // Code blocks
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="p-3 rounded-lg bg-black/30 overflow-x-auto my-3 whitespace-pre-wrap"><code class="font-mono text-sm block">$2</code></pre>')
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-accent hover:underline" target="_blank" rel="noopener">$1</a>')
    // Unordered lists
    .replace(/^\s*[-*]\s+(.*$)/gim, '<li class="ml-4 list-disc">$1</li>')
    // Ordered lists
    .replace(/^\s*\d+\.\s+(.*$)/gim, '<li class="ml-4 list-decimal">$1</li>')
    // Blockquotes
    .replace(/^>\s+(.*$)/gim, '<blockquote class="border-l-4 border-accent pl-4 py-2 my-3 italic opacity-80">$1</blockquote>')
    // Horizontal rule
    .replace(/^---$/gim, '<hr class="my-6 border-t border-white/10" />')
    // Line breaks
    .replace(/\n/g, '<br />');

  return html;
}

// ═══════════════════════════════════════════════════════════════════════════
// Code Cell Component
// ═══════════════════════════════════════════════════════════════════════════

function CodeCell({ cell, index, onUpdate, onDelete, onMoveUp, onMoveDown, isExpanded, onToggleExpand }) {
  const [isEditing, setIsEditing] = useState(true);
  const [output, setOutput] = useState(cell.outputs?.[0] || null);
  const [isRunning, setIsRunning] = useState(false);
  const textareaRef = useRef(null);

  useEffect(() => {
    setOutput(cell.outputs?.[0] || null);
  }, [cell.outputs]);

  const handleRun = async () => {
    setIsRunning(true);
    setOutput(null);

    const code = Array.isArray(cell.source) ? cell.source.join('\n') : cell.source;

    try {
      const { executeNotebookCell } = await import('../../utils/api');
      const response = await executeNotebookCell(code, 30);
      const { output: stdout, error: stderr, exit_code } = response.data;

      const resultOutput = {
        type: exit_code === 0 ? 'text' : 'error',
        data: exit_code === 0
          ? (stdout || '(no output)')
          : `${stdout || ''}${stderr ? `\n⚠️ Error:\n${stderr}` : ''}`,
        execution_count: (cell.execution_count || 0) + 1,
      };

      setOutput(resultOutput);
      onUpdate(index, {
        outputs: [resultOutput],
        execution_count: resultOutput.execution_count,
      });
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      const errorOutput = {
        type: 'error',
        data: `⚠️ Execution failed: ${detail}`,
        execution_count: (cell.execution_count || 0) + 1,
      };
      setOutput(errorOutput);
      onUpdate(index, { outputs: [errorOutput], execution_count: errorOutput.execution_count });
    } finally {
      setIsRunning(false);
    }
  };

  const handleChange = (e) => {
    onUpdate(index, { source: e.target.value.split('\n') });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="group relative rounded-xl border overflow-hidden mb-3"
      style={{
        background: 'var(--surface-card)',
        borderColor: 'var(--border)'
      }}
    >
      {/* Cell Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: 'var(--border)', background: 'var(--surface-elevated)' }}>
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider font-bold opacity-50 flex items-center gap-1.5">
            <FileCode className="w-3 h-3" />
            Code [{cell.execution_count || ' '}]
            {cell.metadata?.name && <span className="ml-2 px-2 py-0.5 rounded bg-black/20">{cell.metadata.name}</span>}
          </span>
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onClick={onMoveUp} className="p-1 hover:bg-white/5 rounded" title="Move up">
            <ChevronUp className="w-3.5 h-3.5" />
          </button>
          <button onClick={onMoveDown} className="p-1 hover:bg-white/5 rounded" title="Move down">
            <ChevronDown className="w-3.5 h-3.5" />
          </button>
          <button onClick={onToggleExpand} className="p-1 hover:bg-white/5 rounded" title={isExpanded ? 'Collapse' : 'Expand'}>
            {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
          <button onClick={() => setIsEditing(!isEditing)} className="p-1 hover:bg-white/5 rounded" title={isEditing ? 'View only' : 'Edit'}>
            {isEditing ? <Check className="w-3.5 h-3.5" /> : <Type className="w-3.5 h-3.5" />}
          </button>
          <button onClick={handleRun} disabled={isRunning} className="p-1 hover:bg-green-500/20 rounded text-green-400 disabled:opacity-50" title="Run cell">
            <Play className={`w-3.5 h-3.5 ${isRunning ? 'animate-pulse' : ''}`} />
          </button>
          <button onClick={onDelete} className="p-1 hover:bg-red-500/20 rounded text-red-400" title="Delete cell">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Code Editor */}
      <div className={`${isExpanded ? '' : 'max-h-40 overflow-hidden'}`}>
        <textarea
          ref={textareaRef}
          value={Array.isArray(cell.source) ? cell.source.join('\n') : cell.source}
          onChange={handleChange}
          readOnly={!isEditing}
          className={`w-full p-4 font-mono text-sm resize-none focus:outline-none whitespace-pre-wrap overflow-auto ${
            isEditing
              ? 'bg-transparent text-white'
              : 'bg-black/20 text-white/70 cursor-default'
          }`}
          rows={isExpanded ? Math.max(8, (cell.source?.join('\n') || '').split('\n').length) : 4}
          spellCheck={false}
        />
      </div>

      {/* Output Area */}
      <AnimatePresence>
        {output && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t"
            style={{ borderColor: 'var(--border)', background: 'var(--surface-raised)' }}
          >
            <div className="px-4 py-3 font-mono text-sm whitespace-pre-wrap overflow-x-auto max-h-80 overflow-y-auto">
              <div className="text-[10px] uppercase tracking-wider opacity-40 mb-2">
                {output.type === 'error' ? '⚠️ Error Output' : `Output [${output.execution_count || ''}]`}
              </div>
              <div style={{
                color: output.type === 'error' ? 'var(--status-error)' : 'var(--text-secondary)',
              }}>
                {output.data}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Running Indicator */}
      {isRunning && (
        <div className="absolute inset-0 bg-accent/5 flex items-center justify-center pointer-events-none">
          <div className="px-4 py-2 rounded-full bg-accent/20 text-accent text-sm font-semibold flex items-center gap-2">
            <Play className="w-4 h-4 animate-pulse" />
            Running...
          </div>
        </div>
      )}
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Markdown Cell Component
// ═══════════════════════════════════════════════════════════════════════════

function MarkdownCell({ cell, index, onUpdate, onDelete, onMoveUp, onMoveDown }) {
  const [isEditing, setIsEditing] = useState(false);
  const [preview, setPreview] = useState('');

  useEffect(() => {
    setPreview(renderMarkdown(Array.isArray(cell.source) ? cell.source.join('\n') : cell.source));
  }, [cell.source]);

  const handleChange = (e) => {
    onUpdate(index, { source: e.target.value.split('\n') });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="group relative rounded-xl border overflow-hidden mb-3"
      style={{
        background: 'var(--surface-card)',
        borderColor: 'var(--border)'
      }}
    >
      {/* Cell Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: 'var(--border)', background: 'var(--surface-elevated)' }}>
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider font-bold opacity-50 flex items-center gap-1.5">
            <Type className="w-3 h-3" />
            Markdown
          </span>
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onClick={onMoveUp} className="p-1 hover:bg-white/5 rounded" title="Move up">
            <ChevronUp className="w-3.5 h-3.5" />
          </button>
          <button onClick={onMoveDown} className="p-1 hover:bg-white/5 rounded" title="Move down">
            <ChevronDown className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => setIsEditing(!isEditing)} className="p-1 hover:bg-white/5 rounded" title={isEditing ? 'Preview' : 'Edit'}>
            {isEditing ? <Check className="w-3.5 h-3.5" /> : <Type className="w-3.5 h-3.5" />}
          </button>
          <button onClick={onDelete} className="p-1 hover:bg-red-500/20 rounded text-red-400" title="Delete cell">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Content */}
      {isEditing ? (
        <textarea
          value={Array.isArray(cell.source) ? cell.source.join('\n') : cell.source}
          onChange={handleChange}
          className="w-full p-4 font-mono text-sm resize-none focus:outline-none bg-transparent text-white whitespace-pre-wrap overflow-auto"
          rows={Math.max(4, (cell.source?.join('\n') || '').split('\n').length + 2)}
          spellCheck={false}
          placeholder="Enter Markdown content..."
        />
      ) : (
        <div
          className="w-full p-4 prose prose-invert max-w-none"
          style={{ color: 'var(--text-primary)' }}
          dangerouslySetInnerHTML={{ __html: preview || '<span class="opacity-40 italic">Empty markdown cell</span>' }}
        />
      )}
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Main Notebook Editor Component
// ═══════════════════════════════════════════════════════════════════════════

export default function NotebookEditor({
  initialCells = [],
  onSave,
  autoSave = false
}) {
  const { pipelineStatus, resumePipeline } = useAppStore();
  const [cells, setCells] = useState(() =>
    initialCells.length > 0
      ? initialCells
      : [
          {
            id: crypto.randomUUID(),
            cell_type: CELL_TYPE.MARKDOWN,
            source: ['# DS-Copilot Notebook', '', 'Welcome to your interactive data science notebook.'],
            metadata: { language: 'python' }
          },
          {
            id: crypto.randomUUID(),
            cell_type: CELL_TYPE.CODE,
            source: ['import pandas as pd', '', '# Load your dataset', 'df = pd.read_csv("data.csv")', 'df.head()'],
            metadata: { language: 'python' },
            outputs: [],
            execution_count: 0
          }
        ]
  );
  const [expandedCells, setExpandedCells] = useState({});
  const [isDirty, setIsDirty] = useState(false);

  // Sync cells when initialCells changes (e.g., agent adds new cells)
  useEffect(() => {
    if (initialCells && initialCells.length > 0) {
      setCells(initialCells);
    }
  }, [initialCells?.length]);

  // Auto-save effect
  useEffect(() => {
    if (autoSave && isDirty) {
      const timer = setTimeout(() => {
        handleSave();
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [cells, autoSave]);

  const handleUpdateCell = useCallback((index, updates) => {
    setCells(prev => {
      const newCells = [...prev];
      newCells[index] = { ...newCells[index], ...updates };
      return newCells;
    });
    setIsDirty(true);
  }, []);

  const handleDeleteCell = useCallback((index) => {
    setCells(prev => prev.filter((_, i) => i !== index));
    setIsDirty(true);
    toast.success('Cell deleted');
  }, []);

  const handleMoveCell = useCallback((index, direction) => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= cells.length) return;

    setCells(prev => {
      const newCells = [...prev];
      [newCells[index], newCells[newIndex]] = [newCells[newIndex], newCells[index]];
      return newCells;
    });
    setIsDirty(true);
  }, [cells.length]);

  const handleAddCell = useCallback((type, afterIndex) => {
    const newCell = {
      id: crypto.randomUUID(),
      cell_type: type,
      source: type === CELL_TYPE.CODE
        ? ['# New code cell']
        : ['# New markdown cell'],
      metadata: { language: 'python' },
      outputs: type === CELL_TYPE.CODE ? [] : undefined,
      execution_count: type === CELL_TYPE.CODE ? 0 : undefined
    };

    setCells(prev => {
      const newCells = [...prev];
      newCells.splice(afterIndex + 1, 0, newCell);
      return newCells;
    });
    setIsDirty(true);
  }, []);

  const handleToggleExpand = useCallback((index) => {
    setExpandedCells(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  }, []);

  const handleSave = useCallback(() => {
    if (onSave) {
      onSave(cells);
      setIsDirty(false);
      toast.success('Notebook saved');
    }
  }, [cells, onSave]);

  const handleExport = useCallback(() => {
    const notebookJson = {
      cells: cells.map(cell => ({
        cell_type: cell.cell_type,
        source: cell.source,
        metadata: cell.metadata,
        outputs: cell.outputs,
        execution_count: cell.execution_count
      })),
      metadata: {
        kernelspec: { display_name: 'Python 3', language: 'python', name: 'python3' },
        language_info: { name: 'python', version: '3.11.0' }
      },
      nbformat: 4,
      nbformat_minor: 5
    };

    const blob = new Blob([JSON.stringify(notebookJson, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `notebook-${new Date().toISOString().slice(0, 10)}.ipynb`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Notebook exported');
  }, [cells]);

  const handleClearAllOutputs = useCallback(() => {
    setCells(prev => prev.map(cell =>
      cell.cell_type === CELL_TYPE.CODE
        ? { ...cell, outputs: [], execution_count: 0 }
        : cell
    ));
    setIsDirty(true);
    toast.info('All outputs cleared');
  }, []);

  return (
    <div className="h-full flex flex-col" style={{ background: 'var(--bg-primary)' }}>
      {/* Notebook Toolbar */}
      <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: 'var(--border)', background: 'var(--surface-card)' }}>
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
            Notebook Editor
          </h1>
          {isDirty && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 font-medium">
              Unsaved changes
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleClearAllOutputs}
            className="px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-white/5 flex items-center gap-2"
            style={{ color: 'var(--text-secondary)' }}
          >
            <RotateCcw className="w-4 h-4" />
            Clear Outputs
          </button>
          <button
            onClick={handleExport}
            className="px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-white/5 flex items-center gap-2"
            style={{ color: 'var(--text-secondary)' }}
          >
            <Download className="w-4 h-4" />
            Export
          </button>
          <button
            onClick={handleSave}
            disabled={!isDirty}
            className="px-4 py-1.5 rounded-lg text-sm font-bold bg-accent text-black flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed hover:brightness-110 transition-all"
          >
            <Save className="w-4 h-4" />
            Save
          </button>
        </div>
      </div>

      {/* Error / Resume Banner */}
      {pipelineStatus === 'failed' && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-500/10 border-b border-red-500/20 px-6 py-3 flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-red-500/20">
              <AlertTriangle className="w-5 h-5 text-red-500" />
            </div>
            <div>
              <p className="text-sm font-bold text-red-500">Pipeline Execution Stalled</p>
              <p className="text-xs text-red-400">Manual intervention required. Fix the issues in the notebook cells above, then resume.</p>
            </div>
          </div>
          <button
            onClick={resumePipeline}
            className="px-5 py-2 bg-red-600 text-white text-xs font-black uppercase tracking-widest rounded-xl hover:bg-red-500 transition-all flex items-center gap-2 shadow-lg shadow-red-500/20 active:scale-95"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Resume Pipeline
          </button>
        </motion.div>
      )}

      {/* Cells Container */}
      <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
        <div className="max-w-4xl mx-auto">
          <AnimatePresence>
            {cells.map((cell, index) => (
              <React.Fragment key={cell.id}>
                {cell.cell_type === CELL_TYPE.CODE ? (
                  <CodeCell
                    cell={cell}
                    index={index}
                    onUpdate={handleUpdateCell}
                    onDelete={() => handleDeleteCell(index)}
                    onMoveUp={() => handleMoveCell(index, 'up')}
                    onMoveDown={() => handleMoveCell(index, 'down')}
                    isExpanded={expandedCells[index]}
                    onToggleExpand={() => handleToggleExpand(index)}
                  />
                ) : (
                  <MarkdownCell
                    cell={cell}
                    index={index}
                    onUpdate={handleUpdateCell}
                    onDelete={() => handleDeleteCell(index)}
                    onMoveUp={() => handleMoveCell(index, 'up')}
                    onMoveDown={() => handleMoveCell(index, 'down')}
                  />
                )}

                {/* Add Cell Buttons (shown between cells) */}
                <div className="flex items-center gap-2 my-2 opacity-0 hover:opacity-100 transition-opacity">
                  <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
                  <button
                    onClick={() => handleAddCell(CELL_TYPE.MARKDOWN, index)}
                    className="px-3 py-1 rounded-full text-xs font-medium hover:bg-white/10 flex items-center gap-1.5"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    <Plus className="w-3 h-3" />
                    Markdown
                  </button>
                  <button
                    onClick={() => handleAddCell(CELL_TYPE.CODE, index)}
                    className="px-3 py-1 rounded-full text-xs font-medium hover:bg-white/10 flex items-center gap-1.5"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    <Plus className="w-3 h-3" />
                    Code
                  </button>
                  <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
                </div>
              </React.Fragment>
            ))}
          </AnimatePresence>

          {/* Add Cell at End */}
          <div className="flex items-center justify-center gap-3 mt-6 py-4">
            <button
              onClick={() => handleAddCell(CELL_TYPE.MARKDOWN, cells.length - 1)}
              className="px-4 py-2 rounded-lg text-sm font-medium hover:bg-white/5 flex items-center gap-2 transition-all"
              style={{ color: 'var(--text-secondary)', border: '1px dashed var(--border)' }}
            >
              <Plus className="w-4 h-4" />
              Add Markdown Cell
            </button>
            <button
              onClick={() => handleAddCell(CELL_TYPE.CODE, cells.length - 1)}
              className="px-4 py-2 rounded-lg text-sm font-medium hover:bg-white/5 flex items-center gap-2 transition-all"
              style={{ color: 'var(--text-secondary)', border: '1px dashed var(--border)' }}
            >
              <Plus className="w-4 h-4" />
              Add Code Cell
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
