import { Activity, CheckCircle2, Clock3, AlertTriangle } from 'lucide-react';
import { useTravel } from '@/contexts/TravelContext';

function value(value: unknown, fallback = '-') {
  return value === undefined || value === null || value === '' ? fallback : String(value);
}

export default function TracePanel() {
  const { sessionState } = useTravel();
  const snapshots = Array.isArray(sessionState?.node_snapshots)
    ? sessionState.node_snapshots as Array<Record<string, unknown>>
    : [];
  const trajectory = Array.isArray(sessionState?.trajectory)
    ? sessionState.trajectory as Array<Record<string, unknown>>
    : [];
  const evaluation = sessionState?.evaluation;

  return (
    <div className="h-full flex flex-col">
      <div className="flex-shrink-0 px-4 pt-4 pb-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2 text-sm font-semibold text-white">
          <Activity className="w-4 h-4 text-[#2EC4B6]" />
          执行链路
        </div>
        <div className="mt-2 space-y-1 text-[10px] text-[rgba(255,255,255,0.42)] font-mono">
          <div>Trace ID：{value(sessionState?.trace_id)}</div>
          <div>节点：{snapshots.length} · 工具事件：{trajectory.filter((item) => item.type === 'tool_call').length}</div>
          <div>评测：{evaluation?.status || '未触发'}</div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {snapshots.length === 0 && (
          <div className="py-10 text-center text-xs text-[rgba(255,255,255,0.35)]">
            完整规划完成后显示节点执行链路
          </div>
        )}
        {snapshots.map((item, index) => {
          const state = (item.state || {}) as Record<string, unknown>;
          const hasRisk = Number(state.risk_alert_count || 0) > 0;
          return (
            <div key={`${value(item.node)}-${index}`} className="rounded-lg p-3 bg-white/[0.03]">
              <div className="flex items-center gap-2">
                {hasRisk ? <AlertTriangle className="w-3.5 h-3.5 text-[#FFD166]" /> : <CheckCircle2 className="w-3.5 h-3.5 text-[#06D6A0]" />}
                <span className="flex-1 text-xs text-[#EDF6F9] font-mono">{value(item.node)}</span>
                <span className="flex items-center gap-1 text-[10px] text-[rgba(255,255,255,0.35)] font-mono">
                  <Clock3 className="w-3 h-3" />{value(item.duration_ms, '0')}ms
                </span>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] text-[rgba(255,255,255,0.4)] font-mono">
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

