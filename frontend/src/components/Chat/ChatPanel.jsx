// frontend/src/components/Chat/ChatPanel.jsx
import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone } from 'react-dropzone';
import { Send, Upload, Loader2, Sparkles, FileUp } from 'lucide-react';
import useAppStore from '../../store/appStore';
import useAgent from '../../hooks/useAgent';
import useWebSocket from '../../hooks/useWebSocket';
import MessageBubble from './MessageBubble';

export default function ChatPanel() {
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef(null);

  const {
    messages, addMessage, currentSessionId, isLoading, uploadedFile,
  } = useAppStore();

  const { handleUpload, startRun } = useAgent();
  const { sendMessage } = useWebSocket(currentSessionId);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // File drop
  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      await handleUpload(acceptedFiles[0]);
    }
  }, [handleUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/json': ['.json'],
    },
    maxSize: 100 * 1024 * 1024,
    multiple: false,
    noClick: true,
    noKeyboard: true,
  });

  const handleSend = async () => {
    if (!input.trim() || isSending) return;

    const userMessage = input.trim();
    setInput('');
    setIsSending(true);

    addMessage({ role: 'user', content: userMessage });

    // Check if this is a pipeline start command
    if (uploadedFile && (
      userMessage.toLowerCase().includes('start') ||
      userMessage.toLowerCase().includes('run') ||
      userMessage.toLowerCase().includes('analyze') ||
      userMessage.toLowerCase().includes('pipeline')
    )) {
      try {
        await startRun({
          dataset_path: uploadedFile.path,
          project_name: uploadedFile.name.replace(/\.[^/.]+$/, ''),
          execution_env: 'local',
        });
      } catch {
        // Error already handled in useAgent
      }
    } else if (currentSessionId) {
      // Send via WebSocket for streaming
      sendMessage('chat', userMessage);
    } else {
      // No session — send via REST
      try {
        const { sendChatMessage } = await import('../../utils/api');
        const response = await sendChatMessage(userMessage, currentSessionId);
        addMessage({
          role: 'assistant',
          content: response.data.content,
          timestamp: response.data.timestamp,
        });
      } catch (error) {
        addMessage({
          role: 'error',
          content: `Failed to get response: ${error.message}`,
        });
      }
    }

    setIsSending(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-full flex flex-col" {...getRootProps()}>
      <input {...getInputProps()} />

      {/* Drag overlay */}
      <AnimatePresence>
        {isDragActive && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50 bg-brand-500/10 backdrop-blur-sm border-2 border-dashed border-brand-500/50 rounded-xl flex items-center justify-center"
          >
            <div className="text-center">
              <FileUp className="w-12 h-12 text-brand-400 mx-auto mb-3" />
              <p className="text-lg font-medium text-brand-300">Drop your dataset here</p>
              <p className="text-sm text-gray-400 mt-1">CSV, Excel, or JSON • Max 100MB</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 no-scrollbar">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <motion.div
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.5, type: 'spring' }}
            >
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center mx-auto mb-6 shadow-2xl shadow-brand-500/30">
                <Sparkles className="w-10 h-10 text-white" />
              </div>
            </motion.div>
            <h2 className="text-2xl font-bold gradient-text mb-2">DS-Copilot</h2>
            <p className="text-gray-400 max-w-md mb-8">
              Your AI data science assistant. Upload a dataset and I'll handle
              cleaning, EDA, model training, testing, and optimization.
            </p>
            <div className="grid grid-cols-2 gap-3 max-w-sm">
              {[
                { icon: '📁', text: 'Upload a CSV dataset' },
                { icon: '🔍', text: 'Run full EDA pipeline' },
                { icon: '🤖', text: 'Train & compare models' },
                { icon: '📊', text: 'Generate reports' },
              ].map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + i * 0.1 }}
                  className="glass-card-hover p-3 text-left cursor-pointer"
                  onClick={() => setInput(item.text)}
                >
                  <span className="text-lg mr-2">{item.icon}</span>
                  <span className="text-sm text-gray-300">{item.text}</span>
                </motion.div>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <MessageBubble key={msg.id || i} message={msg} />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Upload indicator */}
      {uploadedFile && (
        <div className="mx-6 mb-2">
          <div className="flex items-center gap-2 px-3 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-sm">
            <Upload className="w-4 h-4 text-emerald-400" />
            <span className="text-emerald-300 font-medium">{uploadedFile.name}</span>
            <span className="text-gray-500">({(uploadedFile.size / 1024).toFixed(1)} KB)</span>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="p-4 border-t border-surface-700 bg-surface-850/50 backdrop-blur-xl">
        <div className="flex items-end gap-3 max-w-4xl mx-auto">
          {/* Upload Button */}
          <label className="btn-ghost p-2.5 cursor-pointer flex-shrink-0 hover:bg-brand-500/10 hover:text-brand-400 rounded-xl transition-all">
            <input
              type="file"
              className="hidden"
              accept=".csv,.xlsx,.xls,.json"
              onChange={(e) => e.target.files[0] && handleUpload(e.target.files[0])}
            />
            <Upload className="w-5 h-5" />
          </label>

          {/* Text Input */}
          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={uploadedFile
                ? "Type 'start pipeline' or ask a question..."
                : "Upload a dataset or ask a question..."
              }
              rows={1}
              className="input resize-none min-h-[44px] max-h-[160px] pr-12 rounded-xl"
              style={{ height: 'auto', overflow: 'hidden' }}
              onInput={(e) => {
                e.target.style.height = 'auto';
                e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
              }}
            />
          </div>

          {/* Send Button */}
          <button
            onClick={handleSend}
            disabled={!input.trim() || isSending}
            className={`p-2.5 rounded-xl flex-shrink-0 transition-all duration-200 ${
              input.trim() && !isSending
                ? 'bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-500/30 active:scale-95'
                : 'bg-surface-700 text-gray-500 cursor-not-allowed'
            }`}
          >
            {isSending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
