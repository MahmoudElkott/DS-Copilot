import { motion } from 'framer-motion';
import { Wrench } from 'lucide-react';
import StandardCard from '../../components/shared/StandardCard';

export default function FeatureEngineering() {
  return (
    <div className="h-full overflow-y-auto no-scrollbar">
      <div className="max-w-5xl mx-auto px-8 py-10 space-y-8">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold tracking-tight mb-2" style={{ color: 'var(--text-primary)' }}>Feature Engineering</h1>
          <p className="text-base" style={{ color: 'var(--text-secondary)' }}>Automated feature extraction, selection, and encoding.</p>
        </motion.div>
        <StandardCard title="Feature Pipeline" icon={<Wrench className="w-4 h-4" />}>
          <div className="py-16 text-center" style={{ color: 'var(--text-muted)' }}>
            <Wrench className="w-12 h-12 mx-auto mb-4 opacity-30" />
            <p className="text-sm font-medium">Awaiting cleaned dataset</p>
          </div>
        </StandardCard>
      </div>
    </div>
  );
}
