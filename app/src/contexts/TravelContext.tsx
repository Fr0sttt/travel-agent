import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react';
import { toast } from 'sonner';
import type { ChatMessage, ToolCall } from '@/pages/app/mockData';
import {
  checkHealth,
  getSession,
  streamChat,
  streamPlan,
  type SessionState,
  type SSEvent,
} from '@/lib/api';
import { buildDashboardData, type DashboardData } from '@/lib/transform';

type TravelStatus = 'idle' | 'processing' | 'needs_input' | 'error' | 'complete';

interface TravelState {
  messages: ChatMessage[];
  sessionId: string | null;
  status: TravelStatus;
  sessionState: SessionState | null;
  error: string | null;
  isBackendHealthy: boolean | null;
}

interface TravelContextValue extends TravelState {
  sendMessage: (text: string) => Promise<void>;
  resetSession: () => void;
  clearError: () => void;
  checkBackendHealth: () => Promise<void>;
  dashboardData: DashboardData;
}

const TravelContext = createContext<TravelContextValue | null>(null);

function nowTimestamp(): string {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function mapToolCalls(toolCalls: unknown[]): ToolCall[] {
  return toolCalls.map((tc, idx) => {
    const call = tc as Record<string, unknown>;
    const name = String(call.tool_name || 'tool');
    const categoryBase = name.toLowerCase();
    let category: ToolCall['category'] = 'api';
    if (categoryBase.includes('db') || categoryBase.includes('memory')) category = 'db';
    else if (categoryBase.includes('safety') || categoryBase.includes('advisory')) category = 'safety';
    else if (categoryBase.includes('budget') || categoryBase.includes('calc') || categoryBase.includes('route')) category = 'calc';

    return {
      id: `tc-${idx}-${Date.now()}`,
      name,
      params: (call.input || {}) as Record<string, unknown>,
      result: call.success === false
        ? `Error: ${call.error_message || 'failed'}`
        : JSON.stringify(call.output || {}),
      status: call.success === false ? 'failed' : 'completed',
      duration: Number(call.latency_ms || 0),
      category,
    };
  });
}

export function TravelProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<TravelStatus>('idle');
  const [sessionState, setSessionState] = useState<SessionState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const assistantMessageIdRef = useRef<string | null>(null);

  const dashboardData = useMemo(() => {
    if (!sessionState) {
      return {
        pois: [],
        timelineDays: [],
        calendarEvents: [],
        metrics: [],
        overallScore: 0,
        memoryItems: [],
        safetyEvents: [],
        toolCallLogs: [],
        riskAlerts: [],
      };
    }
    return buildDashboardData(sessionState);
  }, [sessionState]);

  const updateAssistantMessage = useCallback((updater: (msg: ChatMessage) => ChatMessage) => {
    const id = assistantMessageIdRef.current;
    if (!id) return;
    setMessages((prev) =>
      prev.map((msg) => (msg.id === id ? updater(msg) : msg))
    );
  }, []);

  const appendAssistantMessage = useCallback((content: string, isStreaming = true) => {
    const id = generateId();
    assistantMessageIdRef.current = id;
    const msg: ChatMessage = {
      id,
      role: 'agent',
      content,
      timestamp: nowTimestamp(),
      reasoningChain: [],
      toolCalls: [],
      isStreaming,
    };
    setMessages((prev) => [...prev, msg]);
    return id;
  }, []);

  const appendUserMessage = useCallback((text: string) => {
    const msg: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: text,
      timestamp: nowTimestamp(),
    };
    setMessages((prev) => [...prev, msg]);
  }, []);

  const handleEvent = useCallback(async (event: SSEvent) => {
    switch (event.type) {
      case 'status': {
        setSessionId(event.session_id);
        updateAssistantMessage((msg) => ({ ...msg, content: event.message }));
        break;
      }
      case 'progress': {
        setSessionId(event.session_id);
        updateAssistantMessage((msg) => {
          const steps = msg.reasoningChain ? [...msg.reasoningChain] : [];
          // Avoid flooding with identical consecutive steps
          if (steps.length === 0 || steps[steps.length - 1].description !== event.message) {
            steps.push({
              step: steps.length + 1,
              description: event.message,
              confidence: event.progress,
            });
          }
          return { ...msg, content: event.message, reasoningChain: steps };
        });
        break;
      }
      case 'warning': {
        updateAssistantMessage((msg) => ({ ...msg, content: event.message }));
        break;
      }
      case 'clarify': {
        setSessionId(event.session_id);
        setStatus('needs_input');
        updateAssistantMessage((msg) => ({
          ...msg,
          content: event.message,
          isStreaming: false,
        }));
        toast.info('需要补充信息', { description: event.message });
        break;
      }
      case 'reply': {
        setStatus('complete');
        updateAssistantMessage((msg) => ({
          ...msg,
          content: event.message,
          isStreaming: false,
        }));
        break;
      }
      case 'complete': {
        setSessionId(event.session_id);
        setStatus('complete');
        updateAssistantMessage((msg) => ({
          ...msg,
          content: event.message || '行程规划完成！',
          isStreaming: false,
        }));
        try {
          const state = await getSession(event.session_id);
          setSessionState(state);
          const toolCalls = Array.isArray(state.tool_calls) ? state.tool_calls : [];
          if (toolCalls.length > 0) {
            updateAssistantMessage((msg) => ({
              ...msg,
              toolCalls: mapToolCalls(toolCalls),
            }));
          }
          toast.success('行程规划完成');
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          toast.error('无法获取行程详情', { description: message });
        }
        break;
      }
      case 'error': {
        setStatus('error');
        setError(event.message);
        updateAssistantMessage((msg) => ({
          ...msg,
          content: `出错了：${event.message}`,
          isStreaming: false,
        }));
        toast.error('请求失败', { description: event.message });
        break;
      }
    }
  }, [updateAssistantMessage]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim()) return;

      // Cancel any in-flight request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const controller = new AbortController();
      abortControllerRef.current = controller;

      appendUserMessage(text);
      appendAssistantMessage('开始处理…');
      setStatus('processing');
      setError(null);

      try {
        if (!sessionId) {
          await streamPlan(
            { user_input: text },
            (event) => handleEvent(event),
            controller.signal,
          );
        } else {
          await streamChat(
            { message: text, session_id: sessionId },
            (event) => handleEvent(event),
            controller.signal,
          );
        }
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        const message = err instanceof Error ? err.message : String(err);
        setStatus('error');
        setError(message);
        updateAssistantMessage((msg) => ({
          ...msg,
          content: `请求失败：${message}`,
          isStreaming: false,
        }));
        toast.error('网络错误', { description: message });
      } finally {
        abortControllerRef.current = null;
      }
    },
    [sessionId, appendUserMessage, appendAssistantMessage, handleEvent, updateAssistantMessage],
  );

  const resetSession = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setMessages([]);
    setSessionId(null);
    setSessionState(null);
    setStatus('idle');
    setError(null);
    assistantMessageIdRef.current = null;
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const checkBackendHealth = useCallback(async () => {
    try {
      await checkHealth();
      setIsBackendHealthy(true);
    } catch (err) {
      setIsBackendHealthy(false);
      toast.error('后端服务未启动', {
        description: err instanceof Error ? err.message : String(err),
      });
    }
  }, []);

  const value = useMemo<TravelContextValue>(
    () => ({
      messages,
      sessionId,
      status,
      sessionState,
      error,
      isBackendHealthy,
      sendMessage,
      resetSession,
      clearError,
      checkBackendHealth,
      dashboardData,
    }),
    [
      messages,
      sessionId,
      status,
      sessionState,
      error,
      isBackendHealthy,
      sendMessage,
      resetSession,
      clearError,
      checkBackendHealth,
      dashboardData,
    ],
  );

  return <TravelContext.Provider value={value}>{children}</TravelContext.Provider>;
}

export function useTravel() {
  const context = useContext(TravelContext);
  if (!context) {
    throw new Error('useTravel must be used within a TravelProvider');
  }
  return context;
}
