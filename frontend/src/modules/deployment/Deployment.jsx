import { motion } from 'framer-motion';
import { Rocket } from 'lucide-react';
import StandardCard from '../../components/shared/StandardCard';
import useAppStore from '../../store/appStore';

export default function Deployment() {
  const pipelineSteps = useAppStore((state) => state.pipelineSteps);
  const artifacts = useAppStore((state) => state.artifacts);

  const evaluationStep = pipelineSteps.find((s) => s.key === 'evaluation');
  const evaluationComplete = evaluationStep?.status === 'completed'
    || Boolean(artifacts?.evaluation?.evaluation_metrics)
    || Boolean(artifacts?.evaluation?.evaluation_output);

  return (
    <div className="h-full overflow-y-auto no-scrollbar">
      <div className="max-w-5xl mx-auto px-8 py-10 space-y-8">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold tracking-tight mb-2" style={{ color: 'var(--text-primary)' }}>Deployment</h1>
          <p className="text-base" style={{ color: 'var(--text-secondary)' }}>Package, export, and deploy your trained model.</p>
        </motion.div>
        <StandardCard title="Deployment Options" icon={<Rocket className="w-4 h-4" />}>
          {!evaluationComplete ? (
            <div className="py-16 text-center" style={{ color: 'var(--text-muted)' }}>
              <Rocket className="w-12 h-12 mx-auto mb-4 opacity-30" />
              <p className="text-sm font-medium">Complete evaluation to enable deployment</p>
            </div>
          ) : (
            <div className="py-16 text-center" style={{ color: 'var(--text-primary)' }}>
              <Rocket className="w-12 h-12 mx-auto mb-4 text-green-500" />
              <h2 className="text-xl font-bold mb-2">Ready for Deployment</h2>
              <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Your model has been evaluated and is ready to deploy.</p>
              <button className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition font-medium">
                Deploy Model
              </button>
            </div>
          )}
        </StandardCard>
      </div>
    </div>
  );
}
