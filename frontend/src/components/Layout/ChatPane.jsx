import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Paperclip, Loader2, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import useAppStore from '../../store/appStore';

/**
 * Simple inline markdown renderer for chat messages.
 * Handles bold, inline code, and code blocks.
 */
function renderMessageContent(text) {
  if (!text) return null;

  // Split on fenced code blocks
  const parts = text.split(/(```[\s\S]*?```)/g);
  return parts.map((part, i) => {
    // Fenced code block
    if (part.startsWith('```')) {
      const match = part.match(/```(\w*)\n?([\s\S]*?)```/);
      const code = match ? match[2].trim() : part.slice(3, -3).trim();
      return (
        <pre
          key={i}
          className="my-2 p-3 rounded-lg overflow-x-auto font-mono text-xs"
          style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)' }}
        >
          <code>{code}</code>
        </pre>
      );
    }
    // Inline markdown: bold and inline code
    const html = part
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 rounded text-xs font-mono" style="background: rgba(0,0,0,0.2)">$1</code>')
      .replace(/\n/g, '<br/>');
    return <span key={i} dangerouslySetInnerHTML={{ __html: html }} />;
  });
}

export default function ChatPane() {
  const { messages, addMessage, isConnected, uploadedFile, agentWorking, agentStage } = useAppStore();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text) return;

    addMessage({ role: 'user', content: text });
    setInput('');

    // Send to backend via WebSocket
    if (isConnected) {
      window.dispatchEvent(new CustomEvent('ds-copilot:send', { detail: { message: text } }));
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-full flex flex-col" style={{ background: 'var(--bg-secondary)' }}>
      {/* Header */}
      <div
        className="flex-shrink-0 flex items-center justify-between px-5 py-3 border-b"
        style={{ borderColor: 'var(--border)' }}
      >
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: 'var(--accent-muted)', color: 'var(--accent)' }}
          >
            <Bot className="w-3.5 h-3.5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Agent Stream</h2>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 no-scrollbar">
        <AnimatePresence initial={false}>
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex-1 flex flex-col items-center justify-center py-20 text-center"
            >
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
                style={{ background: 'var(--accent-muted)', color: 'var(--accent)' }}
              >
                <Bot className="w-7 h-7" />
              </div>
              <h3 className="text-base font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                Your AI data scientist
              </h3>
              <p className="text-sm max-w-[240px]" style={{ color: 'var(--text-muted)' }}>
                Upload a dataset or type a command to start the autonomous pipeline.
              </p>
            </motion.div>
          ) : (
            messages.map((msg, i) => (
              <motion.div
                key={msg.id || i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
              >
                <div
                  className="w-7 h-7 rounded-lg flex-shrink-0 flex items-center justify-center"
                  style={{
                    background: msg.role === 'user' ? 'var(--accent)' : 'var(--accent-muted)',
                    color: msg.role === 'user' ? 'var(--bg-primary)' : 'var(--accent)',
                  }}
                >
                  {msg.role === 'user' ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                </div>

                <div
                  className="max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed"
                  style={{
                    background: msg.role === 'user' ? 'var(--accent)' : 'var(--surface-card)',
                    color: msg.role === 'user' ? 'var(--bg-primary)' : 'var(--text-primary)',
                    border: msg.role === 'assistant' ? '1px solid var(--border)' : 'none',
                  }}
                >
                  {msg.role === 'user'
                    ? msg.content
                    : renderMessageContent(msg.content)
                  }
                  {msg.timestamp && (
                    <div
                      className="text-[10px] mt-1.5 opacity-60"
                      style={{ color: msg.role === 'user' ? 'var(--bg-secondary)' : 'var(--text-muted)' }}
                    >
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  )}
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>

        {/* Agent working indicator */}
        {agentWorking && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3 px-4 py-3 rounded-xl"
            style={{ background: 'var(--accent-muted)', border: '1px solid var(--border)' }}
          >
            <Loader2 className="w-4 h-4 animate-spin" style={{ color: 'var(--accent)' }} />
            <div>
              <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                <Sparkles className="w-3 h-3 inline mr-1" style={{ color: 'var(--accent)' }} />
                Agent is working...
              </span>
              {agentStage && (
                <span className="text-xs ml-2" style={{ color: 'var(--text-muted)' }}>
                  ({agentStage})
                </span>
              )}
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Upload indicator */}
      {uploadedFile && (
        <div
          className="mx-4 mb-2 px-3 py-2 rounded-lg flex items-center gap-2 text-xs"
          style={{ background: 'var(--accent-muted)', color: 'var(--accent)' }}
        >
          <Paperclip className="w-3 h-3" />
          {uploadedFile.name} ({(uploadedFile.size / 1024).toFixed(1)} KB)
        </div>
      )}

      {/* Input */}
      <div className="flex-shrink-0 px-4 pb-4 pt-2">
        <div
          className="flex items-center gap-2 rounded-xl border px-4 py-2.5 transition-all focus-within:border-[var(--accent)]"
          style={{ background: 'var(--surface-card)', borderColor: 'var(--border)' }}
        >
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask or type 'start pipeline'..."
            className="flex-1 bg-transparent outline-none text-sm"
            style={{ color: 'var(--text-primary)' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="p-2 rounded-lg transition-all"
            style={{
              background: input.trim() ? 'var(--accent)' : 'transparent',
              color: input.trim() ? 'var(--bg-primary)' : 'var(--text-muted)',
              opacity: input.trim() ? 1 : 0.4,
            }}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
