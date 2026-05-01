// frontend/src/hooks/useAgent.js
import { useCallback } from 'react';
import useAppStore from '../store/appStore';
import { startPipeline, getPipelineStatus, uploadFile } from '../utils/api';
import { normalizeStepKey } from '../utils/pipeline';
import { toast } from 'sonner';

export default function useAgent() {
  const {
    currentSessionId,
    setCurrentSession,
    setPipelineStatus,
    resetPipeline,
    setRightPanelTab,
    setUploadedFile,
    addMessage,
    setLoading,
    updateStep,
  } = useAppStore();

  const handleUpload = useCallback(async (file) => {
    try {
      setLoading(true);
      const response = await uploadFile(file);
      setUploadedFile({
        name: file.name,
        path: response.data.filepath,
        size: response.data.size_bytes,
      });
      toast.success(`File uploaded: ${file.name}`);
      addMessage({
        role: 'system',
        content: `📁 File uploaded: **${file.name}** (${(response.data.size_bytes / 1024).toFixed(1)} KB)`,
      });
      return response.data;
    } catch (error) {
      const detail = error.response?.data?.detail;
      const msg = typeof detail === 'object' ? detail.detail : detail || error.message;
      toast.error(`Upload failed: ${msg}`);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [setLoading, setUploadedFile, addMessage]);

  const startRun = useCallback(async (config) => {
    try {
      setLoading(true);
      resetPipeline();

      const response = await startPipeline(config);
      const sessionId = response.data.session_id;
      setCurrentSession(sessionId);
      setPipelineStatus('running');
      setRightPanelTab('terminal');

      addMessage({
        role: 'system',
        content: `🚀 Pipeline started for **${config.project_name}**. Session: \`${sessionId}\``,
      });

      toast.success('Pipeline started!');
      return sessionId;
    } catch (error) {
      toast.error(`Pipeline start failed: ${error.message}`);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [setLoading, resetPipeline, setCurrentSession, setPipelineStatus, addMessage, setRightPanelTab]);

  const refreshStatus = useCallback(async () => {
    if (!currentSessionId) return null;
    try {
      const response = await getPipelineStatus(currentSessionId);
      const status = response.data;

      // Update steps from API response
      status.steps?.forEach((step) => {
        const stepKey = normalizeStepKey(step.key || step.name);
        if (stepKey) {
          updateStep(stepKey, { status: step.status, error: step.error || null });
        }
      });

      setPipelineStatus(status.status);
      return status;
    } catch {
      return null;
    }
  }, [currentSessionId, setPipelineStatus, updateStep]);

  return { handleUpload, startRun, refreshStatus };
}
