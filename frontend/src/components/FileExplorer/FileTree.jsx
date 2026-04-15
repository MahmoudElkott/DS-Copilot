// frontend/src/components/FileExplorer/FileTree.jsx
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, ChevronDown, File, Folder, FolderOpen, Download, FolderTree as FolderTreeIcon } from 'lucide-react';
import useAppStore from '../../store/appStore';
import { getFileTree } from '../../utils/api';

const FILE_ICONS = {
  '.py': '🐍', '.csv': '📊', '.json': '📋', '.md': '📝', '.txt': '📄',
  '.yml': '⚙️', '.yaml': '⚙️', '.pkl': '🧠', '.png': '🖼️', '.jpg': '🖼️',
};

function TreeNode({ name, value, path, depth = 0 }) {
  const [isOpen, setIsOpen] = useState(depth < 2);
  const isDir = value !== null && typeof value === 'object';
  const ext = name.includes('.') ? '.' + name.split('.').pop() : '';
  const icon = FILE_ICONS[ext] || (isDir ? null : '📄');

  return (
    <div>
      <button
        onClick={() => isDir && setIsOpen(!isOpen)}
        className={`w-full flex items-center gap-1.5 px-2 py-1 rounded text-sm hover:bg-white/5 transition-colors ${isDir ? 'text-gray-300' : 'text-gray-400'}`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {isDir ? (
          <>
            {isOpen ? <ChevronDown className="w-3 h-3 text-gray-500 flex-shrink-0" /> : <ChevronRight className="w-3 h-3 text-gray-500 flex-shrink-0" />}
            {isOpen ? <FolderOpen className="w-4 h-4 text-amber-400 flex-shrink-0" /> : <Folder className="w-4 h-4 text-amber-400/60 flex-shrink-0" />}
          </>
        ) : (
          <>
            <span className="w-3 flex-shrink-0" />
            <span className="text-sm flex-shrink-0">{icon}</span>
          </>
        )}
        <span className="truncate">{name}</span>
      </button>

      <AnimatePresence>
        {isDir && isOpen && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.15 }}>
            {Object.entries(value)
              .sort(([a, av], [b, bv]) => {
                const aDir = av !== null && typeof av === 'object';
                const bDir = bv !== null && typeof bv === 'object';
                if (aDir !== bDir) return aDir ? -1 : 1;
                return a.localeCompare(b);
              })
              .map(([childName, childValue]) => (
                <TreeNode key={childName} name={childName} value={childValue} path={`${path}/${childName}`} depth={depth + 1} />
              ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function FileTree() {
  const { fileTree, setFileTree, currentSessionId } = useAppStore();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (currentSessionId) {
      setLoading(true);
      getFileTree(currentSessionId)
        .then(r => setFileTree(r.data.tree))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [currentSessionId, setFileTree]);

  const hasFiles = Object.keys(fileTree).length > 0;

  return (
    <div className="h-full flex flex-col">
      <div className="panel-header flex-shrink-0">
        <div className="flex items-center gap-2">
          <FolderTreeIcon className="w-4 h-4 text-brand-400" />
          <span className="text-sm font-semibold text-gray-300">Project Files</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 no-scrollbar">
        {loading ? (
          <div className="space-y-2 p-2">{[...Array(5)].map((_, i) => <div key={i} className="skeleton h-6 rounded" />)}</div>
        ) : hasFiles ? (
          Object.entries(fileTree)
            .sort(([a, av], [b, bv]) => {
              const aDir = av !== null && typeof av === 'object';
              const bDir = bv !== null && typeof bv === 'object';
              if (aDir !== bDir) return aDir ? -1 : 1;
              return a.localeCompare(b);
            })
            .map(([name, value]) => (
              <TreeNode key={name} name={name} value={value} path={name} />
            ))
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <FolderTreeIcon className="w-10 h-10 text-gray-700 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">No files yet</p>
              <p className="text-gray-600 text-xs mt-1">Run a pipeline to generate project files</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
