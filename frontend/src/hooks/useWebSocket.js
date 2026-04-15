// frontend/src/hooks/useWebSocket.js
import { useEffect, useRef, useCallback } from 'react';
import useAppStore from '../store/appStore';
import { createWebSocket } from '../utils/api';

const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000]; // Exponential backoff

export default function useWebSocket(sessionId) {
  const wsRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef(null);

  const {
    setConnected,
    addMessage,
    updateStep,
    setCodeStream,
    setPipelineStatus,
    setStats,
  } = useAppStore();

  const handleMessage = useCallback((event) => {
    try {
      const data = JSON.parse(event.data);
      const { type, agent, content, metadata, timestamp } = data;

      switch (type) {
        case 'status':
          // Agent status update
          if (agent && agent !== 'system' && agent !== 'orchestrator') {
            const stepsCompleted = metadata?.steps_completed || [];
            stepsCompleted.forEach((step) => {
              updateStep(step, { status: 'completed' });
            });
            if (metadata?.step && !stepsCompleted.includes(metadata.step)) {
              updateStep(metadata.step, { status: 'running' });
            }
          }

          // Pipeline completion
          if (metadata?.complete) {
            addMessage({
              role: 'assistant',
              content,
              agent_name: agent,
              timestamp,
            });
          }
          
          if (content === 'Pipeline started') {
            setPipelineStatus('running');
          }
          break;

        case 'code':
          // Code streaming
          if (metadata?.step) {
            setCodeStream(metadata.step, content);
          }
          break;

        case 'log':
          // Agent log message
          addMessage({
            role: 'agent',
            content,
            agent_name: agent,
            timestamp,
          });
          break;

        case 'error':
          // Error
          addMessage({
            role: 'error',
            content,
            agent_name: agent,
            timestamp,
          });
          if (agent) {
            updateStep(agent, { status: 'failed' });
          }
          break;

        case 'result':
          // Pipeline result
          setPipelineStatus('completed');
          addMessage({
            role: 'assistant',
            content,
            agent_name: agent,
            timestamp,
            metadata,
          });
          break;

        case 'file':
          // New file notification
          addMessage({
            role: 'system',
            content: `📄 File created: ${content}`,
            timestamp,
          });
          break;

        default:
          console.log('[WS] Unknown message type:', type);
      }
    } catch (err) {
      console.error('[WS] Message parse error:', err);
    }
  }, [addMessage, updateStep, setCodeStream, setPipelineStatus, setStats]);

  const connect = useCallback(() => {
    if (!sessionId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = createWebSocket(sessionId);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WS] Connected to session:', sessionId);
        setConnected(true);
        reconnectAttemptRef.current = 0;
      };

      ws.onmessage = handleMessage;

      ws.onclose = (event) => {
        console.log('[WS] Disconnected:', event.code, event.reason);
        setConnected(false);

        // Auto-reconnect with exponential backoff
        if (!event.wasClean) {
          const delay = RECONNECT_DELAYS[
            Math.min(reconnectAttemptRef.current, RECONNECT_DELAYS.length - 1)
          ];
          console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current + 1})`);
          reconnectTimerRef.current = setTimeout(() => {
            reconnectAttemptRef.current += 1;
            connect();
          }, delay);
        }
      };

      ws.onerror = (error) => {
        console.error('[WS] Error:', error);
      };
    } catch (err) {
      console.error('[WS] Connection failed:', err);
    }
  }, [sessionId, handleMessage, setConnected]);

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

  const sendMessage = useCallback((type, content) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type,
        content,
        session_id: sessionId,
      }));
    }
  }, [sessionId]);

  // Connect/disconnect on session change
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
