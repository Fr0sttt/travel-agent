import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Target, Route, BookOpen, AlertTriangle, ShieldCheck, ChevronDown, FileText } from 'lucide-react';
import { useTravel } from '@/contexts/TravelContext';
import { useNavigate } from 'react-router';
import type { Metric } from './mockData';

const iconMap: Record<string, React.ElementType> = {
  Target,
  Route,
  BookOpen,
  AlertTriangle,
  ShieldCheck,
};

const scoreColor = (score: number) => {
  if (score >= 90) return '#06D6A0';
  if (score >= 80) return '#8ECAE6';
  if (score >= 70) return '#FFD166';
  return '#EF476F';
};

function CircularScore({ score }: { score: number }) {
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = scoreColor(score);

  return (
    <div className="relative flex items-center justify-center">
      <svg width="140" height="140" viewBox="0 0 140 140">
        {/* Track */}
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="8"
        />
        {/* Fill */}
        <motion.circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke="url(#scoreGradient)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] }}
          transform="rotate(-90 70 70)"
        />
        <defs>
          <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#2EC4B6" />
            <stop offset="100%" stopColor="#219EBC" />
          </linearGradient>
        </defs>
      </svg>
      {/* Score text */}
      <div className="absolute flex flex-col items-center">
        <motion.span
          className="text-4xl font-bold text-white"
          style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          {score}
        </motion.span>
        <span className="text-[10px] uppercase tracking-wider" style={{ color: 'rgba(255,255,255,0.4)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
          Overall
        </span>
      </div>
      {/* Grade badge */}
      <div
        className="absolute -top-1 -right-1 w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold text-white"
        style={{ background: color, fontFamily: "'Outfit Variable', Outfit, sans-serif" }}
      >
        {score >= 90 ? 'A' : score >= 80 ? 'B' : score >= 70 ? 'C' : 'D'}
      </div>
    </div>
  );
}

function MetricBar({ metric, index, onViewReport }: { metric: Metric; index: number; onViewReport?: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const Icon = iconMap[metric.icon] || Target;

  return (
    <div className="rounded-lg" style={{ background: 'rgba(255,255,255,0.03)' }}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between"
      >
        <div className="flex items-center gap-2.5">
          <Icon className="w-4 h-4" style={{ color: metric.color }} />
          <span className="text-xs text-[#EDF6F9]" style={{ fontFamily: "'Inter Variable', Inter, sans-serif" }}>
            {metric.label}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="text-sm font-medium"
            style={{ color: metric.color, fontFamily: "'JetBrains Mono Variable', monospace" }}
          >
            {metric.score}%
          </span>
          <motion.div
            animate={{ rotate: expanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown className="w-3.5 h-3.5" style={{ color: 'rgba(255,255,255,0.3)' }} />
          </motion.div>
        </div>
      </button>

      {/* Progress Bar */}
      <div className="px-4 pb-3">
        <div className="h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.08)' }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: metric.color }}
            initial={{ width: 0 }}
            animate={{ width: `${metric.score}%` }}
            transition={{ duration: 1, delay: index * 0.1, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] }}
          />
        </div>
      </div>

      {/* Expanded Detail */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-1 border-t border-white/[0.04]">
              <p className="text-xs leading-relaxed mb-2" style={{ color: 'rgba(255,255,255,0.5)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
                {metric.description}
              </p>
              {metric.hardFailures && metric.hardFailures.length > 0 && (
                <div className="mb-2 text-[11px] text-[#EF476F]">
                  硬规则：{metric.hardFailures.join('、')}
                </div>
              )}
              {metric.judgeReason && (
                <div className="mb-2 text-[11px] leading-relaxed text-[rgba(255,255,255,0.42)]">
                  Judge：{metric.judgeReason}
                </div>
              )}
              <button
                onClick={onViewReport}
                className="inline-flex items-center gap-1.5 text-[11px] transition-colors hover:underline"
                style={{ color: '#8ECAE6' }}
              >
                <FileText className="w-3.5 h-3.5" />
                查看完整报告
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function MetricsPanel() {
  const { dashboardData, sessionState } = useTravel();
  const navigate = useNavigate();
  const { metrics, overallScore } = dashboardData;
  const evaluation = sessionState?.evaluation;
  const isRealEvaluation = evaluation?.status === 'completed' && Boolean(evaluation.report);
  const viewReport = () => {
    if (sessionState?.session_id) {
      navigate(`/evaluation?session=${encodeURIComponent(sessionState.session_id)}`);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Overall Score */}
      <div className="flex flex-col items-center py-6 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <CircularScore key={overallScore} score={overallScore} />
        <span className="mt-3 text-[10px]" style={{ color: 'rgba(255,255,255,0.3)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
          实时评估
        </span>
      </div>

      {evaluation?.run_id && (
        <div className="px-4 py-2 border-b border-white/[0.04] flex items-center gap-2">
          <span className="flex-1 text-[9px] text-[rgba(255,255,255,0.28)] font-mono">
            {isRealEvaluation ? '真实评测完成' : `评测${evaluation.status}`} · {evaluation.run_id}
          </span>
          <button
            onClick={viewReport}
            className="inline-flex items-center gap-1 text-[10px] text-[#8ECAE6] hover:text-white transition-colors"
          >
            <FileText className="w-3 h-3" />
            完整报告
          </button>
        </div>
      )}

      {/* Individual Metrics */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {metrics.map((metric, i) => (
          <MetricBar key={metric.id} metric={metric} index={i} onViewReport={viewReport} />
        ))}
      </div>
    </div>
  );
}
