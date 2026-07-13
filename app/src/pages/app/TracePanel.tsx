import { Activity, AlertTriangle, CheckCircle2, Clock3, ExternalLink } from 'lucide-react';
import { Link } from 'react-router';
import { useTravel } from '@/contexts/TravelContext';

function value(input: unknown, fallback = '-') {
  return input === undefined || input === null || input === '' ? fallback : String(input);
}

export default function TracePanel() {
  const { sessionId, sessionState } = useTravel();
  const snapshots = Array.isArray(sessionState?.node_snapshots)
    ? sessionState.node_snapshots as Array<Record<string, unknown>>
    : [];
  const trajectory = Array.isArray(sessionState?.trajectory)
    ? sessionState.trajectory as Array<Record<string, unknown>>
    : [];

  return (
    <div className="flex h-full flex-col">
      <div className="flex-shrink-0 border-b border-white/[0.06] px-4 pb-3 pt-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Activity className="h-4 w-4 text-[#2EC4B6]" />
            执行轨迹
          </div>
          {sessionId ? (
            <Link
              to={`/trace?session=${encodeURIComponent(sessionId)}`}
              className="inline-flex shrink-0 items-center gap-1 rounded-md border border-[#2EC4B6]/25 bg-[#2EC4B6]/10 px-2 py-1 text-[10px] text-[#8DE9DF] transition-colors hover:border-[#2EC4B6]/50 hover:bg-[#2EC4B6]/20"
            >
              <ExternalLink className="h-3 w-3" />
              查看完整轨迹
            </Link>
          ) : (
            <span className="rounded-md border border-white/[0.08] px-2 py-1 text-[10px] text-white/25">暂无会话</span>
          )}
        </div>
        <div className="mt-2 space-y-1 font-mono text-[10px] text-[rgba(255,255,255,0.42)]">
          <div>Trace ID: {value(sessionState?.trace_id)}</div>
          <div>节点: {snapshots.length} · 工具事件: {trajectory.filter((item) => item.type === 'tool_call').length}</div>
        </div>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {snapshots.length === 0 && (
          <div className="py-10 text-center text-xs text-[rgba(255,255,255,0.35)]">完整规划完成后显示节点执行链路</div>
        )}
        {snapshots.map((item, index) => {
          const state = (item.state || {}) as Record<string, unknown>;
          const hasRisk = Number(state.risk_alert_count || 0) > 0;
          return (
            <div key={`${value(item.node)}-${index}`} className="rounded-lg bg-white/[0.03] p-3">
              <div className="flex items-center gap-2">
                {hasRisk ? <AlertTriangle className="h-3.5 w-3.5 text-[#FFD166]" /> : <CheckCircle2 className="h-3.5 w-3.5 text-[#06D6A0]" />}
                <span className="flex-1 font-mono text-xs text-[#EDF6F9]">{value(item.node)}</span>
                <span className="flex items-center gap-1 font-mono text-[10px] text-[rgba(255,255,255,0.35)]"><Clock3 className="h-3 w-3" />{value(item.duration_ms, '0')}ms</span>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 font-mono text-[10px] text-[rgba(255,255,255,0.4)]">
                <span>POI {value(state.poi_count, '0')}</span>
                <span>路线 {value(state.route_count, '0')}</span>
                <span>工具 {value(state.tool_call_count, '0')}</span>
                <span>风险 {value(state.risk_alert_count, '0')}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
