// frontend/src/components/CodeViewer/CodeStream.jsx
import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, Download, ChevronDown, Code2 } from 'lucide-react';
import useAppStore from '../../store/appStore';

const STEP_LABELS = {
  data_ingest: '📥 Data Ingestion',
  data_cleaning: '🧹 Data Cleaning',
  eda: '📊 Exploratory Analysis',
  model_selection: '🤖 Model Selection',
  code_writing: '✍️ Training Pipeline',
  testing: '🧪 Testing',
  optimization: '⚡ Optimization',
  documentation: '📝 Documentation',
};

export default function CodeStream() {
  const { codeStreams, activeCodeStep, setActiveCodeStep, pipelineSteps } = useAppStore();
  const [copied, setCopied] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const codeRef = useRef(null);

  // Auto-scroll to bottom when code is streaming
  useEffect(() => {
    if (codeRef.current) {
      codeRef.current.scrollTop = codeRef.current.scrollHeight;
    }
  }, [codeStreams, activeCodeStep]);

  const currentCode = activeCodeStep ? codeStreams[activeCodeStep] || '' : '';
  const stepsWithCode = Object.keys(codeStreams).filter((k) => codeStreams[k]);

  const handleCopy = () => {
    navigator.clipboard.writeText(currentCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([currentCode], { type: 'text/x-python' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${activeCodeStep || 'code'}.py`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const lineCount = currentCode ? currentCode.split('\n').length : 0;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="panel-header flex-shrink-0">
        <div className="flex items-center gap-2">
          <Code2 className="w-4 h-4 text-brand-400" />
          <span className="text-sm font-semibold text-gray-300">Generated Code</span>
          {lineCount > 0 && (
            <span className="text-[10px] text-gray-500 bg-surface-700 px-1.5 py-0.5 rounded">
              {lineCount} lines
            </span>
          )}
        </div>

        <div className="flex items-center gap-1">
          {currentCode && (
            <>
              <button onClick={handleCopy} className="btn-ghost p-1.5" title="Copy">
                {copied ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
              </button>
              <button onClick={handleDownload} className="btn-ghost p-1.5" title="Download">
                <Download className="w-3.5 h-3.5" />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Step Selector */}
      {stepsWithCode.length > 0 && (
        <div className="px-3 py-2 border-b border-surface-700 relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center justify-between w-full px-3 py-1.5 bg-surface-800 rounded-lg text-sm hover:bg-surface-700 transition-colors"
          >
            <span className="text-gray-300">
              {activeCodeStep ? STEP_LABELS[activeCodeStep] || activeCodeStep : 'Select step...'}
            </span>
            <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {dropdownOpen && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute top-full left-3 right-3 mt-1 bg-surface-800 border border-surface-700 rounded-lg shadow-2xl overflow-hidden z-20"
            >
              {stepsWithCode.map((stepKey) => (
                <button
                  key={stepKey}
                  onClick={() => {
                    setActiveCodeStep(stepKey);
                    setDropdownOpen(false);
                  }}
                  className={`w-full px-3 py-2 text-sm text-left hover:bg-white/5 transition-colors flex items-center gap-2 ${
                    activeCodeStep === stepKey ? 'bg-brand-500/10 text-brand-400' : 'text-gray-400'
                  }`}
                >
                  {STEP_LABELS[stepKey] || stepKey}
                </button>
              ))}
            </motion.div>
          )}
        </div>
      )}

      {/* Code Content */}
      <div ref={codeRef} className="flex-1 overflow-auto no-scrollbar">
        {currentCode ? (
          <SyntaxHighlighter
            language="python"
            style={oneDark}
            showLineNumbers
            wrapLines
            lineNumberStyle={{ color: '#4a5568', fontSize: '0.7rem', paddingRight: '1em' }}
            customStyle={{
              margin: 0,
              padding: '1rem',
              background: 'transparent',
              fontSize: '0.8rem',
              lineHeight: '1.6',
            }}
          >
            {currentCode}
          </SyntaxHighlighter>
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <Code2 className="w-10 h-10 text-gray-700 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">No code generated yet</p>
              <p className="text-gray-600 text-xs mt-1">
                Start a pipeline to see generated code here
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
