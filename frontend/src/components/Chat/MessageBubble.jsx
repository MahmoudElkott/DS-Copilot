// frontend/src/components/Chat/MessageBubble.jsx
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, Bot, User, AlertCircle, Cpu } from 'lucide-react';
import { useState } from 'react';

const AGENT_COLORS = {
  data_ingest: 'text-blue-400',
  data_cleaning: 'text-emerald-400',
  eda: 'text-purple-400',
  model_selection: 'text-amber-400',
  code_writing: 'text-cyan-400',
  testing: 'text-pink-400',
  optimization: 'text-orange-400',
  documentation: 'text-teal-400',
};

const AGENT_ICONS = {
  data_ingest: '📥',
  data_cleaning: '🧹',
  eda: '📊',
  model_selection: '🤖',
  code_writing: '✍️',
  testing: '🧪',
  optimization: '⚡',
  documentation: '📝',
};

export default function MessageBubble({ message }) {
  const { role, content, agent_name, timestamp } = message;
  const [copied, setCopied] = useState(false);

  const isUser = role === 'user';
  const isError = role === 'error';
  const isSystem = role === 'system';
  const isAgent = role === 'agent';

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const timeString = timestamp
    ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''} mb-4`}
    >
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
        isUser
          ? 'bg-brand-600 shadow-lg shadow-brand-500/20'
          : isError
          ? 'bg-red-500/20 border border-red-500/30'
          : isAgent
          ? 'bg-surface-700 border border-surface-200/10'
          : 'bg-gradient-to-br from-brand-500 to-purple-600 shadow-lg shadow-brand-500/20'
      }`}>
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : isError ? (
          <AlertCircle className="w-4 h-4 text-red-400" />
        ) : isAgent && agent_name ? (
          <span className="text-sm">{AGENT_ICONS[agent_name] || '🔧'}</span>
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Agent badge */}
        {agent_name && (
          <div className={`text-xs font-medium mb-1 ${AGENT_COLORS[agent_name] || 'text-gray-400'}`}>
            {AGENT_ICONS[agent_name]} {agent_name.replace(/_/g, ' ')}
          </div>
        )}

        <div className={`rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-brand-600 text-white rounded-tr-sm'
            : isError
            ? 'bg-red-500/10 border border-red-500/20 text-red-200 rounded-tl-sm'
            : isSystem
            ? 'bg-surface-700/50 border border-surface-700 text-gray-300 rounded-tl-sm'
            : 'bg-surface-800 border border-surface-700 text-gray-200 rounded-tl-sm'
        }`}>
          <div className="prose prose-sm prose-invert max-w-none break-words">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ node, inline, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const codeString = String(children).replace(/\n$/, '');
                  
                  if (!inline && match) {
                    return (
                      <div className="relative group my-2">
                        <div className="flex items-center justify-between bg-surface-900 px-3 py-1.5 rounded-t-lg border border-surface-700 border-b-0">
                          <span className="text-xs text-gray-500 font-mono">{match[1]}</span>
                          <button
                            onClick={() => handleCopy(codeString)}
                            className="text-gray-500 hover:text-gray-300 transition-colors"
                          >
                            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                        <SyntaxHighlighter
                          style={oneDark}
                          language={match[1]}
                          PreTag="div"
                          customStyle={{
                            margin: 0,
                            borderTopLeftRadius: 0,
                            borderTopRightRadius: 0,
                            border: '1px solid rgba(255,255,255,0.1)',
                            borderTop: 'none',
                            fontSize: '0.8rem',
                          }}
                          {...props}
                        >
                          {codeString}
                        </SyntaxHighlighter>
                      </div>
                    );
                  }
                  return <code className="bg-surface-700 px-1.5 py-0.5 rounded text-sm text-brand-300 font-mono" {...props}>{children}</code>;
                },
                table({ children }) {
                  return (
                    <div className="overflow-x-auto my-2">
                      <table className="w-full text-sm border border-surface-700 rounded-lg overflow-hidden">{children}</table>
                    </div>
                  );
                },
                th({ children }) {
                  return <th className="bg-surface-700 px-3 py-2 text-left text-gray-300 font-medium">{children}</th>;
                },
                td({ children }) {
                  return <td className="px-3 py-2 border-t border-surface-700 text-gray-400">{children}</td>;
                },
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        </div>

        {/* Timestamp */}
        <div className={`text-[10px] text-gray-600 mt-1 px-1 ${isUser ? 'text-right' : ''}`}>
          {timeString}
        </div>
      </div>
    </motion.div>
  );
}
