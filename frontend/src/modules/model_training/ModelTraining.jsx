import { motion } from 'framer-motion';
import { Brain } from 'lucide-react';
import StandardCard from '../../components/shared/StandardCard';

export default function ModelTraining() {
  return (
    <div className="h-full overflow-y-auto no-scrollbar">
      <div className="max-w-5xl mx-auto px-8 py-10 space-y-8">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold tracking-tight mb-2" style={{ color: 'var(--text-primary)' }}>Model Training</h1>
          <p className="text-base" style={{ color: 'var(--text-secondary)' }}>The Lab — train, tune, and compare ML models.</p>
        </motion.div>
        <StandardCard title="Training Workspace" icon={<Brain className="w-4 h-4" />}>
          <div className="py-16 text-center" style={{ color: 'var(--text-muted)' }}>
            <Brain className="w-12 h-12 mx-auto mb-4 opacity-30" />
            <p className="text-sm font-medium">Configure features before training</p>
          </div>
        </StandardCard>
      </div>
    </div>
  );
}
