import { useEffect, useRef, useCallback } from 'react';
import useAppStore from '../store/appStore';
import { createWebSocket } from '../utils/api';
import { inferStepKeyFromAgent, normalizeStepKey, stageToRunningStep } from '../utils/pipeline';

const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000];

function applyVisualizationPayload(payload, setVisualizationPayload, setArtifact) {
  if (!payload) return;
  setVisualizationPayload(payload);

  if (payload.profiling_output || payload.profiling_timestamp) {
    setArtifact('data_prep', {
      profiling_output: payload.profiling_output,
      profiling_timestamp: payload.profiling_timestamp,
    });
  }

  if (payload.eda_output || payload.eda_timestamp) {
    setArtifact('eda', {
      eda_output: payload.eda_output,
      eda_timestamp: payload.eda_timestamp,
    });
  }

  if (payload.evaluation_metrics || payload.evaluation_output || payload.evaluation_timestamp) {
    setArtifact('evaluation', {
      evaluation_metrics: payload.evaluation_metrics,
      evaluation_output: payload.evaluation_output,
      evaluation_timestamp: payload.evaluation_timestamp,
    });
  }
}

function applyArtifactsFromMetadata(metadata, agent, setArtifact) {
  if (!metadata) return;
  const artifacts = metadata.artifacts || metadata.artifact;
  if (!artifacts) return;

  const stepKey = normalizeStepKey(metadata.step || metadata.stage) || inferStepKeyFromAgent(agent);
  if (stepKey) {
    setArtifact(stepKey, artifacts);
  }
}

function applyStepCompletions(stepsCompleted, updateStep) {
  (stepsCompleted || []).map(normalizeStepKey).forEach((doneStep) => {
    if (doneStep) updateStep(doneStep, { status: 'completed' });
  });
}

function applyLogArtifacts(agent, content, timestamp, setArtifact, setVisualizationPayload) {
  const stepKey = inferStepKeyFromAgent(agent);
  if (!stepKey || !content) return;

  if (stepKey === 'eda') {
    setArtifact('eda', { eda_output: content, eda_timestamp: timestamp });
    setVisualizationPayload({ eda_output: content, eda_timestamp: timestamp });
  }

  if (stepKey === 'reporting') {
    setArtifact('reporting', { report_output: content, report_timestamp: timestamp });
  }
}

export default function useWebSocket(sessionId) {
  const wsRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef(null);

  const {
    setConnected,
    addMessage,
    updateStep,
    setCodeStream,
    setNotebookStream,
    setActiveCodeStep,
    setPipelineStatus,
    appendTerminalLog,
    setVisualizationPayload,
    addNotebookCell,
    setAgentWorking,
    setArtifact,
    rehydratePipelineState,
  } = useAppStore();

  const connectRef = useRef(null);

  const handleMessage = useCallback((event) => {
    try {
      const data = JSON.parse(event.data);
      const { type, agent, content, metadata, timestamp } = data;

      switch (type) {
        case 'status': {
          const step = normalizeStepKey(metadata?.step);
          const stepsCompleted = metadata?.steps_completed || [];

          // If this is a step_complete event, mark steps as completed (green)
          if (metadata?.step_complete) {
            applyStepCompletions(stepsCompleted, updateStep);
            // Also mark the specific step
            if (step) updateStep(step, { status: 'completed' });
            // Update the agent's current stage
            if (metadata?.stage) {
              setAgentWorking(true, metadata.stage);
            }
          } else {
            // Legacy: batch completed steps
            applyStepCompletions(stepsCompleted, updateStep);

            if (step && step !== 'start') {
              updateStep(step, { status: 'running' });
            }
          }

          if (metadata?.agent_state?.code_cells && Array.isArray(metadata.agent_state.code_cells)) {
            const mappedCells = metadata.agent_state.code_cells.map((c) => ({
              id: c.id,
              cell_type: c.type === 'code' ? 'code' : 'markdown',
              source: Array.isArray(c.content) ? c.content : c.content.split('\n'),
              metadata: { language: 'python', ...c.metadata },
              outputs: [],
            }));
            useAppStore.getState().setNotebookCells(mappedCells);
          }

          if (metadata?.complete) {
            addMessage({
              role: 'assistant',
              content,
              agent_name: agent,
              timestamp,
            });
            // When streaming completes, agent is done working
            setAgentWorking(false);
          }

          if (content === 'Pipeline started') {
            setPipelineStatus('running');
          }
          break;
        }

        case 'code': {
          const step = normalizeStepKey(metadata?.step);
          if (!step) break;

          setCodeStream(step, content || '');
          if (metadata?.notebook) {
            setNotebookStream(step, metadata.notebook);
          }

          const activeCodeStep = useAppStore.getState().activeCodeStep;
          if (!activeCodeStep || activeCodeStep === 'training') {
            setActiveCodeStep(step);
          }
          break;
        }

        case 'progress': {
          const step = normalizeStepKey(metadata?.step);
          if (step && metadata?.progress !== undefined) {
            updateStep(step, { progress: metadata.progress });
          }
          if (content) {
            addMessage({
              role: 'system',
              content: content,
              timestamp,
            });
          }
          break;
        }

        // ── NEW: Agent action notification (pipeline state) ──
        case 'agent_action': {
          const action = metadata?.action;
          const stage = metadata?.stage;

          // Mark agent as working + set the step to "running" (glowing)
          setAgentWorking(true, stage);
          if (stage) {
            const runningStep = stageToRunningStep(stage);
            if (runningStep) updateStep(runningStep, { status: 'running' });
          }

          // Show the action message in the chat
          addMessage({
            role: 'assistant',
            content,
            agent_name: agent || 'orchestrator',
            timestamp,
            metadata: { action, stage },
          });
          break;
        }

        // ── Notebook cell from LLM mixed-content parsing ──
        case 'notebook_cell': {
          const cellType = metadata?.cell_type || 'code';
          const stage = metadata?.stage || '';
          const language = metadata?.language || 'python';

          // Add the cell to the notebook
          addNotebookCell({
            cell_type: cellType,
            source: content,
            language,
            stage,
          });

          // Only show system message for code cells (avoid chat clutter)
          if (cellType === 'code') {
            const stageLabel = stage ? ` (${stage})` : '';
            addMessage({
              role: 'system',
              content: `📓 Code cell added to Notebook${stageLabel}`,
              timestamp,
            });
          }
          break;
        }

        case 'terminal': {
          appendTerminalLog({
            stream: metadata?.stream || 'stdout',
            content,
            timestamp,
          });
          break;
        }

        case 'log': {
          applyArtifactsFromMetadata(metadata, agent, setArtifact);
          applyLogArtifacts(agent, content, timestamp, setArtifact, setVisualizationPayload);
          addMessage({
            role: 'agent',
            content,
            agent_name: agent,
            timestamp,
          });
          break;
        }

        case 'artifact': {
          applyArtifactsFromMetadata(metadata, agent, setArtifact);
          if (!metadata?.artifacts && !metadata?.artifact && content) {
            const stepKey = normalizeStepKey(metadata?.step || metadata?.stage) || inferStepKeyFromAgent(agent);
            if (stepKey) {
              setArtifact(stepKey, { raw_output: content });
            }
          }
          break;
        }

        case 'error': {
          addMessage({
            role: 'error',
            content,
            agent_name: agent,
            timestamp,
          });
          const step = normalizeStepKey(metadata?.step || metadata?.stage) || inferStepKeyFromAgent(agent);
          if (step && step !== 'orchestrator' && step !== 'system') {
            updateStep(step, { status: 'failed' });
          }
          setPipelineStatus('failed');
          setAgentWorking(false);
          break;
        }

        case 'result': {
          const resultStatus = metadata?.status || 'completed';
          applyStepCompletions(metadata?.steps_completed, updateStep);

          // Only set pipeline to 'completed' for final completion, not intermediate stages
          if (resultStatus === 'completed' || resultStatus === 'pipeline_complete') {
            setPipelineStatus('completed');
          } else if (resultStatus === 'failed') {
            setPipelineStatus('failed');
          }

          if (metadata?.visualization_payload) {
            applyVisualizationPayload(metadata.visualization_payload, setVisualizationPayload, setArtifact);
          }

          if (metadata?.training_result) {
            setArtifact('training', { training_result: metadata.training_result });
            setVisualizationPayload({ training_result: metadata.training_result });
          }

          if (metadata?.agent_state?.code_cells && Array.isArray(metadata.agent_state.code_cells)) {
            const mappedCells = metadata.agent_state.code_cells.map((c) => ({
              id: c.id,
              cell_type: c.type === 'code' ? 'code' : 'markdown',
              source: Array.isArray(c.content) ? c.content : c.content.split('\n'),
              metadata: { language: 'python', ...c.metadata },
              outputs: [],
            }));
            useAppStore.getState().setNotebookCells(mappedCells);
          }

          if (metadata?.final_report) {
            setArtifact('reporting', { final_report: metadata.final_report });
          }

          applyArtifactsFromMetadata(metadata, agent, setArtifact);

          addMessage({
            role: 'assistant',
            content,
            agent_name: agent,
            timestamp,
            metadata,
          });
          setAgentWorking(false);
          break;
        }

        case 'file': {
          addMessage({
            role: 'system',
            content: `File created: ${content}`,
            timestamp,
          });
          break;
        }

        default:
          console.log('[WS] Unknown message type:', type);
      }
    } catch (err) {
      console.error('[WS] Message parse error:', err);
    }
  }, [
    addMessage,
    addNotebookCell,
    appendTerminalLog,
    setActiveCodeStep,
    setAgentWorking,
    setCodeStream,
    setNotebookStream,
    setPipelineStatus,
    setArtifact,
    setVisualizationPayload,
    updateStep,
  ]);

  const connect = useCallback(() => {
    if (!sessionId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = createWebSocket(sessionId);
      wsRef.current = ws;

      ws.onopen = async () => {
        setConnected(true);
        reconnectAttemptRef.current = 0;
        await rehydratePipelineState(sessionId);
      };

      ws.onmessage = handleMessage;

      ws.onclose = (event) => {
        setConnected(false);

        if (!event.wasClean) {
          const delay = RECONNECT_DELAYS[
            Math.min(reconnectAttemptRef.current, RECONNECT_DELAYS.length - 1)
          ];
          reconnectTimerRef.current = setTimeout(() => {
            reconnectAttemptRef.current += 1;
            connectRef.current?.();
          }, delay);
        }
      };

      ws.onerror = (error) => {
        console.error('[WS] Error:', error);
      };
    } catch (err) {
      console.error('[WS] Connection failed:', err);
    }
  }, [sessionId, handleMessage, setConnected, rehydratePipelineState]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnect');
      wsRef.current = null;
    }
    setConnected(false);
  }, [setConnected]);

  const sendMessage = useCallback((type, payloadContent) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type,
        content: payloadContent,
        session_id: sessionId,
      }));
    }
  }, [sessionId]);

  useEffect(() => {
    if (sessionId) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [sessionId, connect, disconnect]);

  return { connect, disconnect, sendMessage, ws: wsRef };
}
