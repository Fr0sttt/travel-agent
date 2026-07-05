import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { toast } from 'sonner';
import type { ChatMessage, ToolCall } from '@/pages/app/mockData';
import {
  checkHealth,
  deleteSession as deleteSessionApi,
  getSession,
  listSessions,
  streamChat,
  streamPlan,
  type SessionSummary,
  type SessionState,
  type SSEvent,
} from '@/lib/api';
import { buildDashboardData, type DashboardData } from '@/lib/transform';

type TravelStatus = 'idle' | 'processing' | 'needs_input' | 'error' | 'complete';

interface TravelState {
  messages: ChatMessage[];
  sessionId: string | null;
  sessions: SessionSummary[];
  status: TravelStatus;
  sessionState: SessionState | null;
  error: string | null;
  isBackendHealthy: boolean | null;
}

interface TravelContextValue extends TravelState {
  sendMessage: (text: string) => Promise<void>;
  resetSession: () => void;
  refreshSessions: () => Promise<void>;
  switchSession: (targetSessionId: string) => Promise<void>;
  deleteSession: (targetSessionId: string) => Promise<void>;
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
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [status, setStatus] = useState<TravelStatus>('idle');
  const [sessionState, setSessionState] = useState<SessionState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const assistantMessageIdRef = useRef<string | null>(null);
  const requestIdRef = useRef(0);

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
        routePolyline: [],
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

  const refreshSessions = useCallback(async () => {
    try {
      const payload = await listSessions();
      setSessions(payload.sessions || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      toast.error('无法加载会话列表', { description: message });
    }
  }, []);

  const loadSession = useCallback(async (targetSessionId: string) => {
    const state = await getSession(targetSessionId);
    setSessionId(targetSessionId);
    setSessionState(state);

    const history = Array.isArray(state.messages) ? state.messages : [];
    const restoredMessages: ChatMessage[] = history.map((item, idx) => ({
      id: `${targetSessionId}-${idx}-${item.timestamp || idx}`,
      role: item.role === 'assistant' ? 'agent' : 'user',
      content: item.content,
      timestamp: item.timestamp
        ? new Date(String(item.timestamp)).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : nowTimestamp(),
      reasoningChain: [],
      toolCalls: [],
      isStreaming: false,
    }));

    setMessages(restoredMessages);
    assistantMessageIdRef.current = null;
    setStatus(state.needs_clarification ? 'needs_input' : restoredMessages.length > 0 ? 'complete' : 'idle');
    setError(null);
  }, []);

  const switchSession = useCallback(async (targetSessionId: string) => {
    if (!targetSessionId || targetSessionId === sessionId) return;
    try {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      requestIdRef.current += 1;
      setStatus('processing');
      await loadSession(targetSessionId);
      await refreshSessions();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setStatus('error');
      setError(message);
      toast.error('切换会话失败', { description: message });
    }
  }, [loadSession, refreshSessions, sessionId]);

  const deleteSession = useCallback(async (targetSessionId: string) => {
    if (!targetSessionId) return;
    try {
      await deleteSessionApi(targetSessionId);
      // 删除的正是当前打开的会话，清空聊天视图，避免继续展示已删除的内容
      if (targetSessionId === sessionId) {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
          abortControllerRef.current = null;
        }
        requestIdRef.current += 1;
        setMessages([]);
        setSessionId(null);
        setSessionState(null);
        setStatus('idle');
        setError(null);
        assistantMessageIdRef.current = null;
      }
      await refreshSessions();
      toast.success('会话已删除');
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      toast.error('删除会话失败', { description: message });
    }
  }, [refreshSessions, sessionId]);

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
        console.log(
          `[handleEvent] 收到 complete 事件 session_id=${event.session_id} itinerary长度=${event.itinerary?.length ?? 0} assistantMessageId=${assistantMessageIdRef.current}`,
        );
        setSessionId(event.session_id);
        setStatus('complete');
        updateAssistantMessage((msg) => ({
          ...msg,
          // itinerary 是完整的行程 Markdown，event.message 只是固定的状态提示
          // ("行程规划完成！")，之前直接用 message 会把完整行程内容丢掉。
          content: event.itinerary || event.message || '行程规划完成！',
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
          await refreshSessions();
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
  }, [updateAssistantMessage, refreshSessions]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim()) return;

      // 调试用：定位"一次发送产生两条完整回复"的问题，确认 sendMessage
      // 是否被意外调用了多次（双击、Enter+按钮竞态等）。
      console.log(
        `[sendMessage] 调用 requestId(调用前)=${requestIdRef.current} text=${text.slice(0, 30)} sessionId=${sessionId} isProcessing(status)=${status}`,
      );

      // Cancel any in-flight request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const controller = new AbortController();
      const requestId = requestIdRef.current + 1;
      requestIdRef.current = requestId;
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
        if (requestIdRef.current !== requestId) return;
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
        if (requestIdRef.current === requestId) {
          abortControllerRef.current = null;
          setStatus((prev) => (prev === 'processing' ? 'idle' : prev));
        }
      }
    },
    [sessionId, appendUserMessage, appendAssistantMessage, handleEvent, updateAssistantMessage],
  );

  const resetSession = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    requestIdRef.current += 1;
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

  useEffect(() => {
    void refreshSessions();
  }, [refreshSessions]);

  const value = useMemo<TravelContextValue>(
    () => ({
      messages,
      sessionId,
      sessions,
      status,
      sessionState,
      error,
      isBackendHealthy,
      sendMessage,
      resetSession,
      refreshSessions,
      switchSession,
      deleteSession,
      clearError,
      checkBackendHealth,
      dashboardData,
    }),
    [
      messages,
      sessionId,
      sessions,
      status,
      sessionState,
      error,
      isBackendHealthy,
      sendMessage,
      resetSession,
      refreshSessions,
      switchSession,
      deleteSession,
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
