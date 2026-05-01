import { motion } from 'framer-motion';
import { FileText } from 'lucide-react';
import StandardCard from '../../components/shared/StandardCard';

export default function Reporting() {
  return (
    <div className="h-full overflow-y-auto no-scrollbar">
      <div className="max-w-5xl mx-auto px-8 py-10 space-y-8">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold tracking-tight mb-2" style={{ color: 'var(--text-primary)' }}>Reporting</h1>
          <p className="text-base" style={{ color: 'var(--text-secondary)' }}>Auto-generated analysis reports and documentation.</p>
        </motion.div>
        <StandardCard title="Report Output" icon={<FileText className="w-4 h-4" />}>
          <div className="py-16 text-center" style={{ color: 'var(--text-muted)' }}>
            <FileText className="w-12 h-12 mx-auto mb-4 opacity-30" />
            <p className="text-sm font-medium">Complete the pipeline to generate a report</p>
          </div>
        </StandardCard>
      </div>
    </div>
  );
}
