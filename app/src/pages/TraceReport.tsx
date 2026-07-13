import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Braces,
  CheckCircle2,
  ChevronDown,
  CircleDot,
  Clock3,
  Code2,
  GitBranch,
  Loader2,
  Terminal,
  XCircle,
} from 'lucide-react';
import { Link, useLocation } from 'react-router';
import { getSessionTrace, type SessionState } from '@/lib/api';

type JsonRecord = Record<string, unknown>;

function asRecord(input: unknown): JsonRecord {
  return input && typeof input === 'object' && !Array.isArray(input) ? input as JsonRecord : {};
}

function value(input: unknown, fallback = '-') {
  return input === undefined || input === null || input === '' ? fallback : String(input);
}

function prettyJson(input: unknown): string {
  if (input === undefined || input === null || input === '') return '-';
  if (typeof input === 'string') return input;
  try {
    return JSON.stringify(input, null, 2);
  } catch {
    return String(input);
  }
}

function formatTimestamp(input: unknown): string {
  if (!input) return '-';
  const date = new Date(String(input));
  return Number.isNaN(date.getTime()) ? String(input) : date.toLocaleString();
}

function isSuccess(input: unknown): boolean {
  return input !== false && input !== 'false';
}

function eventLabel(type: string): string {
  if (type === 'node') return '节点执行';
  if (type === 'tool_call') return '工具调用';
  if (type === 'state_transition') return '状态流转';
  return type || '可观测事件';
}

function EventIcon({ type, success }: { type: string; success: boolean }) {
  if (!success) return <XCircle className="h-4 w-4 text-[#EF476F]" />;
  if (type === 'tool_call') return <Terminal className="h-4 w-4 text-[#FF9F1C]" />;
  if (type === 'state_transition') return <GitBranch className="h-4 w-4 text-[#8ECAE6]" />;
  if (type === 'node') return <CheckCircle2 className="h-4 w-4 text-[#06D6A0]" />;
  return <CircleDot className="h-4 w-4 text-[#2EC4B6]" />;
}

function JsonDetails({ label, data }: { label: string; data: unknown }) {
  return (
    <details className="group rounded-lg border border-white/[0.07] bg-black/10">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 text-[11px] text-white/55">
        <span className="flex items-center gap-2"><Braces className="h-3.5 w-3.5 text-[#8ECAE6]" />{label}</span>
        <ChevronDown className="h-3.5 w-3.5 text-white/30 transition-transform group-open:rotate-180" />
      </summary>
      <pre className="max-h-[360px] overflow-auto whitespace-pre-wrap break-words border-t border-white/[0.06] px-3 py-3 font-mono text-[10px] leading-5 text-white/55">{prettyJson(data)}</pre>
    </details>
  );
}

function TraceEventCard({ item, index }: { item: JsonRecord; index: number }) {
  const type = value(item.type, 'event');
  const success = isSuccess(item.success);
  const isNode = type === 'node';
  const isTool = type === 'tool_call';
  const node = value(item.node, isTool ? 'tool' : 'unknown');
  const title = isTool ? value(item.tool_name, 'unknown_tool') : node;
  const fromNode = item.from_node ? `从 ${value(item.from_node)} 流转` : null;

  return (
    <article className="relative pl-10">
      <div className="absolute left-0 top-1 flex h-7 w-7 items-center justify-center rounded-full border border-white/10 bg-[#081E53]"><EventIcon type={type} success={success} /></div>
      <div className="rounded-xl border border-white/[0.08] bg-white/[0.035] p-4 transition-colors hover:border-white/[0.14]">
        <div className="flex flex-wrap items-start gap-x-3 gap-y-2">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-[10px] text-white/30">#{String(index + 1).padStart(2, '0')}</span>
              <span className="rounded-full bg-white/[0.07] px-2 py-0.5 text-[10px] uppercase tracking-wider text-white/45">{eventLabel(type)}</span>
              <h3 className="break-all font-mono text-sm font-medium text-[#EDF6F9]">{title}</h3>
              {!success && <span className="rounded-full bg-[#EF476F]/10 px-2 py-0.5 text-[10px] text-[#FF9FB2]">失败</span>}
            </div>
            {fromNode && <div className="mt-1 flex items-center gap-1 text-[11px] text-[#8ECAE6]"><GitBranch className="h-3 w-3" />{fromNode}</div>}
          </div>
          <div className="flex shrink-0 items-center gap-3 text-[10px] text-white/35"><span className="flex items-center gap-1"><Clock3 className="h-3 w-3" />{value(item.duration_ms, '0')}ms</span><span>{formatTimestamp(item.timestamp)}</span></div>
        </div>

        {isNode && <div className="mt-4 grid gap-2 lg:grid-cols-2"><JsonDetails label="节点输入状态" data={item.input} /><JsonDetails label="节点输出状态" data={item.output} /></div>}
        {isTool && <div className="mt-4 space-y-2"><JsonDetails label="工具参数" data={item.arguments || item.input} /><JsonDetails label="工具结果" data={item.result || item.output} />{Boolean(item.error) && <div className="rounded-lg border border-[#EF476F]/20 bg-[#EF476F]/[0.08] px-3 py-2 text-xs text-[#FF9FB2]">{String(item.error)}</div>}</div>}
        {!isNode && !isTool && <JsonDetails label="事件载荷" data={item} />}
      </div>
    </article>
  );
}

function SnapshotCard({ item, index }: { item: JsonRecord; index: number }) {
  const state = asRecord(item.state);
  const hasRisk = Number(state.risk_alert_count || 0) > 0;
  return (
    <details className="group rounded-xl border border-white/[0.08] bg-white/[0.025]">
      <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3">
        {hasRisk ? <AlertTriangle className="h-4 w-4 text-[#FFD166]" /> : <CheckCircle2 className="h-4 w-4 text-[#06D6A0]" />}
        <span className="font-mono text-xs text-[#EDF6F9]">{index + 1}. {value(item.node)}</span>
        <span className="ml-auto flex items-center gap-1 text-[10px] text-white/35"><Clock3 className="h-3 w-3" />{value(item.duration_ms, '0')}ms</span>
        <ChevronDown className="h-3.5 w-3.5 text-white/30 transition-transform group-open:rotate-180" />
      </summary>
      <div className="grid gap-2 border-t border-white/[0.06] px-4 py-3 sm:grid-cols-4"><span className="text-[10px] text-white/45">POI <b className="font-mono text-white/70">{value(state.poi_count, '0')}</b></span><span className="text-[10px] text-white/45">路线 <b className="font-mono text-white/70">{value(state.route_count, '0')}</b></span><span className="text-[10px] text-white/45">工具 <b className="font-mono text-white/70">{value(state.tool_call_count, '0')}</b></span><span className="text-[10px] text-white/45">风险 <b className="font-mono text-white/70">{value(state.risk_alert_count, '0')}</b></span></div>
      <div className="border-t border-white/[0.06] px-4 py-3"><JsonDetails label="完整状态快照" data={state} /></div>
    </details>
  );
}

function ObservationCard({ item, index }: { item: JsonRecord; index: number }) {
  const type = value(item.type, 'observation');
  const name = value(item.name, type);
  const duration = item.startTime && item.endTime
    ? Math.max(0, new Date(String(item.endTime)).getTime() - new Date(String(item.startTime)).getTime())
    : null;
  return (
    <article className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4">
      <div className="flex flex-wrap items-start gap-2">
        <span className="font-mono text-[10px] text-white/30">#{String(index + 1).padStart(2, '0')}</span>
        <span className="rounded-full bg-[#8ECAE6]/10 px-2 py-0.5 text-[10px] uppercase tracking-wider text-[#8ECAE6]">{type}</span>
        <h3 className="min-w-0 flex-1 break-all font-mono text-sm text-[#EDF6F9]">{name}</h3>
        {duration !== null && <span className="font-mono text-[10px] text-white/35">{duration}ms</span>}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-white/35">
        <span>开始: {formatTimestamp(item.startTime)}</span>
        {Boolean(item.parentObservationId) && <span>父 Observation: {value(item.parentObservationId)}</span>}
        {Boolean(item.model) && <span>模型: {value(item.model)}</span>}
      </div>
      <div className="mt-3 grid gap-2 lg:grid-cols-3">
        <JsonDetails label="输入" data={item.input} />
        <JsonDetails label="输出" data={item.output} />
        <JsonDetails label="Metadata / Usage" data={{ metadata: item.metadata, usage: item.usage, level: item.level, statusMessage: item.statusMessage }} />
      </div>
    </article>
  );
}

export default function TraceReport() {
  const location = useLocation();
  const sessionId = new URLSearchParams(location.search).get('session') || '';
  const [session, setSession] = useState<SessionState | null>(null);
  const [observations, setObservations] = useState<Array<JsonRecord>>([]);
  const [hasLangfuse, setHasLangfuse] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    async function load() {
      if (!sessionId) { setError('缺少会话 ID，无法加载完整轨迹。'); setLoading(false); return; }
      try {
        const traceData = await getSessionTrace(sessionId);
        if (active) {
          setSession(traceData.session);
          const nextObservations = traceData.langfuse?.observations || [];
          setObservations(nextObservations as Array<JsonRecord>);
          setHasLangfuse(Boolean(traceData.langfuse));
        }
      } catch (loadError) {
        if (active) setError(loadError instanceof Error ? loadError.message : String(loadError));
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [sessionId]);

  const trajectory = useMemo(() => {
    if (!session || !Array.isArray(session.trajectory)) return [];
    return session.trajectory as Array<JsonRecord>;
  }, [session]);
  const snapshots = Array.isArray(session?.node_snapshots) ? session.node_snapshots as Array<JsonRecord> : [];
  const toolCalls = trajectory.filter((item) => item.type === 'tool_call');
  const nodeEvents = trajectory.filter((item) => item.type === 'node');
  const failedEvents = trajectory.filter((item) => !isSuccess(item.success));
  const totalDuration = trajectory.reduce((sum, item) => sum + (Number(item.duration_ms) || 0), 0);
  const preference = asRecord(session?.preference);
  const riskAlerts = Array.isArray(session?.risk_alerts) ? session.risk_alerts : [];
  const confirmations = Array.isArray(session?.confirmation_required) ? session.confirmation_required : [];
  const citedSources = Array.isArray(session?.cited_sources) ? session.cited_sources : [];
  const replanEvents = Array.isArray(session?.replan_events) ? session.replan_events : [];

  return (
    <div className="min-h-[calc(100dvh-64px)] bg-[#071B4D] px-4 py-8 text-white sm:px-6 lg:px-10">
      <div className="mx-auto max-w-[1440px]">
        <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link to="/app" className="mb-4 inline-flex items-center gap-2 text-sm text-[#8ECAE6] transition-colors hover:text-white"><ArrowLeft className="h-4 w-4" />返回规划工作台</Link>
            <div className="flex items-center gap-3"><h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">完整执行轨迹</h1><span className="rounded-full border border-[#2EC4B6]/30 bg-[#2EC4B6]/10 px-3 py-1 text-xs text-[#6EE7D7]">可观测性</span></div>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-white/45">按发生顺序查看节点流转、工具调用、输入输出、状态快照和错误事件。这里展示运行轨迹，不包含评测分数或 Judge 信息。</p>
          </div>
          {session && <div className="rounded-xl border border-white/[0.08] bg-white/[0.035] px-5 py-4 text-right"><div className="text-[10px] uppercase tracking-[0.2em] text-white/35">Trace Events</div><div className="mt-1 text-3xl font-semibold text-[#2EC4B6]">{trajectory.length}</div></div>}
        </div>

        {loading && <div className="flex min-h-[360px] items-center justify-center gap-3 text-white/55"><Loader2 className="h-5 w-5 animate-spin text-[#2EC4B6]" />正在加载完整轨迹…</div>}
        {!loading && error && <div className="rounded-xl border border-[#EF476F]/20 bg-[#EF476F]/10 p-6 text-sm text-[#FF9FB2]">{error}</div>}

        {!loading && !error && session && <>
          <section className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.025] p-4"><div className="text-[10px] uppercase tracking-wider text-white/35">Trace ID</div><div className="mt-2 truncate font-mono text-xs text-white/65">{value(session.trace_id)}</div></div>
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.025] p-4"><div className="text-[10px] uppercase tracking-wider text-white/35">节点执行</div><div className="mt-2 font-mono text-xl text-[#06D6A0]">{nodeEvents.length}</div></div>
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.025] p-4"><div className="text-[10px] uppercase tracking-wider text-white/35">工具调用</div><div className="mt-2 font-mono text-xl text-[#FF9F1C]">{toolCalls.length}</div></div>
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.025] p-4"><div className="text-[10px] uppercase tracking-wider text-white/35">累计耗时</div><div className="mt-2 font-mono text-xl text-[#8ECAE6]">{Math.round(totalDuration)}ms</div></div>
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.025] p-4"><div className="text-[10px] uppercase tracking-wider text-white/35">异常事件</div><div className="mt-2 font-mono text-xl" style={{ color: failedEvents.length ? '#FF9FB2' : '#06D6A0' }}>{failedEvents.length}</div></div>
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.025] p-4"><div className="text-[10px] uppercase tracking-wider text-white/35">Langfuse Observations</div><div className="mt-2 font-mono text-xl text-[#8ECAE6]">{observations.length}</div></div>
          </section>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
            <section className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4 sm:p-6">
              <div className="mb-5 flex items-center gap-2"><Activity className="h-5 w-5 text-[#2EC4B6]" /><div><h2 className="text-lg font-semibold">Trace 时间线</h2><p className="mt-1 text-xs text-white/40">节点、工具及其他事件按后端记录顺序展示</p></div></div>
              {trajectory.length === 0 ? <div className="rounded-lg border border-dashed border-white/10 px-4 py-10 text-center text-sm text-white/40">当前会话还没有可展示的轨迹事件。</div> : <div className="relative space-y-4 before:absolute before:bottom-4 before:left-[13px] before:top-4 before:w-px before:bg-white/[0.1]">{trajectory.map((item, index) => <TraceEventCard key={`${value(item.type)}-${value(item.timestamp)}-${index}`} item={item} index={index} />)}</div>}
              <div className="mt-8 border-t border-white/[0.08] pt-6">
                <div className="mb-4 flex items-center justify-between gap-3"><div><h2 className="text-lg font-semibold">Langfuse Observations</h2><p className="mt-1 text-xs text-white/40">远端 Trace 中的 Span、Event、Generation 及其输入输出</p></div><span className="rounded-full bg-white/[0.06] px-2 py-1 text-[10px] text-white/40">{hasLangfuse ? '已连接' : '暂无远端数据'}</span></div>
                {observations.length === 0 ? <div className="rounded-lg border border-dashed border-white/10 px-4 py-8 text-center text-sm text-white/40">当前 Langfuse 未返回 Observation，页面仍展示本地完整运行轨迹。</div> : <div className="space-y-3">{observations.map((item, index) => <ObservationCard key={value(item.id, `${value(item.name)}-${index}`)} item={item} index={index} />)}</div>}
              </div>
            </section>

            <aside className="space-y-6">
              <section className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-5"><div className="mb-4 flex items-center gap-2 text-sm font-semibold"><Code2 className="h-4 w-4 text-[#8ECAE6]" />Trace 元数据</div><div className="space-y-3 text-xs"><div><div className="text-[10px] uppercase tracking-wider text-white/30">Session ID</div><div className="mt-1 break-all font-mono text-white/60">{value(session.session_id || sessionId)}</div></div><div><div className="text-[10px] uppercase tracking-wider text-white/30">用户请求</div><div className="mt-1 leading-5 text-white/60">{value(session.user_input)}</div></div><div><div className="text-[10px] uppercase tracking-wider text-white/30">目的地</div><div className="mt-1 text-white/60">{value(preference.destination)}</div></div></div></section>

              <section className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-5"><div className="mb-4 flex items-center gap-2 text-sm font-semibold"><Activity className="h-4 w-4 text-[#2EC4B6]" />节点状态快照 <span className="font-mono text-xs text-white/35">{snapshots.length}</span></div><div className="space-y-2">{snapshots.length === 0 ? <div className="text-xs text-white/40">暂无节点快照</div> : snapshots.map((item, index) => <SnapshotCard key={`${value(item.node)}-${index}`} item={item} index={index} />)}</div></section>

              <section className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-5"><div className="mb-4 flex items-center gap-2 text-sm font-semibold"><AlertTriangle className="h-4 w-4 text-[#FFD166]" />其他运行事件</div><div className="space-y-3 text-xs text-white/55">{riskAlerts.length > 0 && <div><div className="mb-1 text-[10px] uppercase tracking-wider text-[#FFD166]">风险告警</div>{riskAlerts.map((item, index) => <div key={`${String(item)}-${index}`} className="rounded-md bg-[#FFD166]/[0.08] px-3 py-2">{String(item)}</div>)}</div>}{confirmations.length > 0 && <JsonDetails label={`确认/安全事件 (${confirmations.length})`} data={confirmations} />}{citedSources.length > 0 && <JsonDetails label={`来源事件 (${citedSources.length})`} data={citedSources} />}{replanEvents.length > 0 && <JsonDetails label={`重规划事件 (${replanEvents.length})`} data={replanEvents} />}{riskAlerts.length === 0 && confirmations.length === 0 && citedSources.length === 0 && replanEvents.length === 0 && <div className="text-white/35">暂无额外运行事件</div>}</div></section>
            </aside>
          </div>
        </>}
      </div>
    </div>
  );
}
