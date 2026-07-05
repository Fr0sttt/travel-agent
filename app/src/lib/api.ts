const API_BASE = import.meta.env.VITE_API_BASE || '';
const NEEDS_TUNNEL_BYPASS = /loca\.lt$/i.test(API_BASE) || API_BASE.includes('.loca.lt');

export interface PlanRequest {
  user_input: string;
  session_id?: string;
}

export interface ChatRequest {
  message: string;
  session_id: string;
}

export type SSEvent =
  | { type: 'status'; message: string; session_id: string }
  | { type: 'progress'; step: string; message: string; progress: number; session_id: string }
  | { type: 'warning'; message: string; step?: string; session_id: string }
  | { type: 'clarify'; message: string; missing_fields: string[]; session_id: string }
  | { type: 'reply'; message: string; session_id: string }
  | {
      type: 'complete';
      message: string;
      itinerary: string;
      risk_alerts: string[];
      session_id: string;
      response: Record<string, unknown>;
    }
  | { type: 'error'; message: string; session_id?: string; detail?: string };

export interface SessionState {
  session_id: string;
  user_input: string;
  preference?: Record<string, unknown> | null;
  constraints?: Record<string, unknown> | null;
  missing_fields?: string[];
  poi_list?: Array<Record<string, unknown>>;
  route?: Array<Record<string, unknown>>;
  weather?: Array<Record<string, unknown>>;
  budget?: Array<Record<string, unknown>>;
  total_budget_estimate?: { min: number; max: number } | null;
  itinerary?: string;
  confirmation_required?: Array<Record<string, unknown>>;
  risk_alerts?: string[];
  tool_calls?: Array<Record<string, unknown>>;
  messages?: Array<{ role: string; content: string; node?: string; timestamp?: string }>;
  needs_clarification?: boolean;
  [key: string]: unknown;
}

export interface SessionSummary {
  session_id: string;
  title: string;
  preview: string;
  message_count: number;
  created_at: string;
  updated_at: string;
  last_message_at: string;
}

function buildUrl(path: string): string {
  const base = API_BASE.replace(/\/$/, '');
  return `${base}${path}`;
}

function buildHeaders(init: HeadersInit = {}): Headers {
  const headers = new Headers(init);
  if (NEEDS_TUNNEL_BYPASS) {
    headers.set('bypass-tunnel-reminder', '1');
  }
  return headers;
}

async function parseEventData(chunk: string): Promise<SSEvent | null> {
  const dataLines = chunk
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trim());

  if (dataLines.length === 0) return null;

  const payload = dataLines.join('\n');
  try {
    const parsed = JSON.parse(payload);
    return parsed as SSEvent;
  } catch {
    return { type: 'status', message: payload, session_id: '' };
  }
}

async function postSSE(
  path: string,
  body: unknown,
  onEvent: (event: SSEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(buildUrl(path), {
    method: 'POST',
    headers: buildHeaders({ 'Content-Type': 'application/json', Accept: 'text/event-stream' }),
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => 'Unknown error');
    throw new Error(`HTTP ${response.status}: ${text}`);
  }

  if (!response.body) {
    throw new Error('Response body is empty');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const part of parts) {
        if (!part.trim()) continue;
        const event = await parseEventData(part);
        if (event) onEvent(event);
      }
    }

    if (buffer.trim()) {
      const event = await parseEventData(buffer);
      if (event) onEvent(event);
    }
  } finally {
    reader.releaseLock();
  }
}

export async function streamPlan(
  request: PlanRequest,
  onEvent: (event: SSEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  await postSSE('/api/plan/stream', request, onEvent, signal);
}

export async function streamChat(
  request: ChatRequest,
  onEvent: (event: SSEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  await postSSE('/api/chat/stream', request, onEvent, signal);
}

export async function getSession(sessionId: string): Promise<SessionState> {
  const response = await fetch(buildUrl(`/api/session/${sessionId}`), {
    headers: buildHeaders({ Accept: 'application/json' }),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => 'Unknown error');
    throw new Error(`HTTP ${response.status}: ${text}`);
  }

  return (await response.json()) as SessionState;
}

export async function listSessions(): Promise<{ count: number; sessions: SessionSummary[] }> {
  const response = await fetch(buildUrl('/api/sessions'), {
    headers: buildHeaders({ Accept: 'application/json' }),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => 'Unknown error');
    throw new Error(`HTTP ${response.status}: ${text}`);
  }

  return (await response.json()) as { count: number; sessions: SessionSummary[] };
}

export async function deleteSession(sessionId: string): Promise<{ status: string; message: string }> {
  const response = await fetch(buildUrl(`/api/sessions/${sessionId}`), {
    method: 'DELETE',
    headers: buildHeaders({ Accept: 'application/json' }),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => 'Unknown error');
    throw new Error(`HTTP ${response.status}: ${text}`);
  }

  return (await response.json()) as { status: string; message: string };
}

export async function checkHealth(): Promise<{ status: string; version: string; dependencies: Record<string, string> }> {
  const response = await fetch(buildUrl('/health'), {
    headers: buildHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return response.json();
}

export async function listTools(): Promise<{ count: number; tools: Array<Record<string, unknown>> }> {
  const response = await fetch(buildUrl('/api/tools'), {
    headers: buildHeaders({ Accept: 'application/json' }),
  });
  if (!response.ok) {
    throw new Error(`List tools failed: ${response.status}`);
  }
  return response.json();
}
