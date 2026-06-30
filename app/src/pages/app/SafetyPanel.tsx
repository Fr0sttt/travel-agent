import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Shield, Info, AlertTriangle, AlertCircle } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useTravel } from '@/contexts/TravelContext';
import type { SafetyEvent } from './mockData';

const severityConfig: Record<string, { icon: React.ElementType; color: string; border: string; label: string }> = {
  info: { icon: Info, color: '#06D6A0', border: '#06D6A0', label: 'Info' },
  warning: { icon: AlertTriangle, color: '#FFD166', border: '#FFD166', label: 'Warning' },
  critical: { icon: AlertCircle, color: '#EF476F', border: '#EF476F', label: 'Critical' },
};

const statusConfig: Record<string, { color: string; bg: string }> = {
  resolved: { color: '#06D6A0', bg: 'rgba(6,214,160,0.1)' },
  pending: { color: '#FFD166', bg: 'rgba(255,209,102,0.1)' },
  requires_action: { color: '#EF476F', bg: 'rgba(239,71,111,0.1)' },
};

function EventCard({ event, index }: { event: SafetyEvent; index: number }) {
  const sev = severityConfig[event.severity];
  const st = statusConfig[event.status];
  const SeverityIcon = sev.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.3 }}
      className="glass-card overflow-hidden"
      style={{ borderLeft: `3px solid ${sev.border}` }}
    >
      <div className="p-3.5">
        <div className="flex items-start justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-2">
            <SeverityIcon className="w-3.5 h-3.5 flex-shrink-0" style={{ color: sev.color }} />
            <h5 className="text-xs font-semibold text-white" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
              {event.title}
            </h5>
          </div>
          <span
            className="flex-shrink-0 text-[10px] px-2 py-0.5 rounded-full font-medium"
            style={{
              background: st.bg,
              color: st.color,
              fontFamily: "'JetBrains Mono Variable', monospace",
            }}
          >
            {event.status.replace('_', ' ')}
          </span>
        </div>

        <p className="text-[11px] leading-relaxed mb-2 pl-5.5" style={{ color: 'rgba(255,255,255,0.5)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
          {event.description}
        </p>

        <div className="flex items-center justify-between pl-5.5">
          <span className="text-[10px]" style={{ color: 'rgba(255,255,255,0.25)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
            {event.timestamp}
          </span>

          {event.status === 'requires_action' && (
            <button
              className="px-3 py-1 rounded-md text-[10px] font-semibold text-white transition-all hover:scale-[1.02]"
              style={{ background: '#E29578' }}
            >
              Review
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function SafetyGauge({ score }: { score: number }) {
  const radius = 60;
  const circumference = Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <div className="relative">
        <svg width="140" height="80" viewBox="0 0 140 80">
          {/* Track - half circle */}
          <path
            d={`M 10 70 A ${radius} ${radius} 0 0 1 130 70`}
            fill="none"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth="8"
            strokeLinecap="round"
          />
          {/* Fill */}
          <motion.path
            d={`M 10 70 A ${radius} ${radius} 0 0 1 130 70`}
            fill="none"
            stroke="#2EC4B6"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] }}
          />
        </svg>
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 flex flex-col items-center">
          <motion.span
            className="text-2xl font-bold text-white"
            style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            {score}
          </motion.span>
        </div>
      </div>
      <span className="mt-2 text-[11px]" style={{ color: 'rgba(255,255,255,0.4)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
        Safety Score
      </span>
    </div>
  );
}

export default function SafetyPanel() {
  const { dashboardData } = useTravel();
  const { safetyEvents } = dashboardData;

  const safetyScore = useMemo(() => {
    const safetyMetric = dashboardData.metrics.find((m) => m.id === 'm5');
    return safetyMetric ? safetyMetric.score : 100;
  }, [dashboardData.metrics]);

  const alertCount = safetyEvents.filter((e) => e.severity === 'warning' || e.severity === 'critical').length;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 p-4 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-2 mb-1">
          <Shield className="w-4 h-4 text-[#2EC4B6]" />
          <h3 className="text-sm font-semibold text-white" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
            Safety & Compliance
          </h3>
        </div>
        <div className="flex items-center gap-2 mt-2">
          {alertCount === 0 ? (
            <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: 'rgba(6,214,160,0.1)', color: '#06D6A0' }}>
              All clear
            </span>
          ) : (
            <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: 'rgba(255,209,102,0.1)', color: '#FFD166' }}>
              {alertCount} alerts
            </span>
          )}
        </div>
      </div>

      {/* Event List */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-2.5">
          {safetyEvents.map((event, i) => (
            <EventCard key={event.id} event={event} index={i} />
          ))}
        </div>
      </ScrollArea>

      {/* Safety Gauge */}
      <div className="flex-shrink-0 p-4 border-t" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="flex justify-center">
          <SafetyGauge key={safetyScore} score={safetyScore} />
        </div>
      </div>
    </div>
  );
}
