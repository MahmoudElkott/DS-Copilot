import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from 'sonner';
import { ThemeProvider } from './context/ThemeContext';
import MainLayout from './components/layout/MainLayout';

// Modules
import ProjectHub from './modules/project_hub/ProjectHub';
import DataPreparation from './modules/data_preparation/DataPreparation';
import EDAExploration from './modules/eda_exploration/EDAExploration';
import FeatureEngineering from './modules/feature_engineering/FeatureEngineering';
import ModelTraining from './modules/model_training/ModelTraining';
import ModelEvaluation from './modules/model_evaluation/ModelEvaluation';
import Reporting from './modules/reporting/Reporting';
import Deployment from './modules/deployment/Deployment';

import Notebook from './modules/notebook/Notebook';

export default function App() {
  return (
    <ThemeProvider>
      <Toaster
        theme="dark"
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--surface-card)',
            border: '1px solid var(--border)',
            color: 'var(--text-primary)',
          },
        }}
      />

      <BrowserRouter>
        <Routes>
          <Route element={<MainLayout />}>
            <Route index element={<ProjectHub />} />
            <Route path="preparation" element={<DataPreparation />} />
            <Route path="eda" element={<EDAExploration />} />
            <Route path="features" element={<FeatureEngineering />} />
            <Route path="training" element={<ModelTraining />} />
            <Route path="evaluation" element={<ModelEvaluation />} />
            <Route path="reporting" element={<Reporting />} />
            <Route path="deployment" element={<Deployment />} />

            <Route path="notebook" element={<Notebook />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
