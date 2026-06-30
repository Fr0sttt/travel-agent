import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  ShieldAlert,
  AlertTriangle,
  AlertCircle,
  Info,
  Brain,
  BookOpen,
  Lightbulb,
  Check,
  X,
  ArrowUpRight,
} from 'lucide-react';
import type { SecurityEvent } from './data';
import {
  severityColors,
  severityBgColors,
  statusColors,
  statusBgColors,
} from './data';
import type { Status } from './data';

interface EventCardProps {
  event: SecurityEvent;
  index: number;
  isSelected: boolean;
  onSelect: (event: SecurityEvent) => void;
  onStatusChange?: (id: string, newStatus: Status) => void;
}

const severityIcons = {
  Critical: ShieldAlert,
  High: AlertTriangle,
  Medium: AlertCircle,
  Low: Info,
};

function timeAgo(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export default function EventCard({
  event,
  index,
  isSelected,
  onSelect,
  onStatusChange,
}: EventCardProps) {
  const [expanded, setExpanded] = useState(false);
  const SevIcon = severityIcons[event.severity];
  const sevColor = severityColors[event.severity];
  const sevBg = severityBgColors[event.severity];
  const statColor = statusColors[event.status];
  const statBg = statusBgColors[event.status];

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.4,
        delay: index * 0.05,
        ease: [0.16, 1, 0.3, 1] as [number, number, number, number],
      }}
      className="rounded-xl border transition-all duration-200 cursor-pointer overflow-hidden"
      style={{
        background: isSelected
          ? 'rgba(33,158,188,0.08)'
          : 'rgba(255,255,255,0.03)',
        borderColor: isSelected
          ? 'rgba(33,158,188,0.4)'
          : 'rgba(255,255,255,0.08)',
        borderLeftWidth: isSelected ? '3px' : '1px',
        borderLeftColor: isSelected ? '#219EBC' : 'rgba(255,255,255,0.08)',
      }}
      onClick={() => {
        onSelect(event);
        setExpanded(!expanded);
      }}
      onMouseEnter={(e) => {
        if (!isSelected) {
          (e.currentTarget as HTMLElement).style.background =
            'rgba(255,255,255,0.06)';
          (e.currentTarget as HTMLElement).style.transform = 'translateX(4px)';
        }
      }}
      onMouseLeave={(e) => {
        if (!isSelected) {
          (e.currentTarget as HTMLElement).style.background =
            'rgba(255,255,255,0.03)';
          (e.currentTarget as HTMLElement).style.transform = 'translateX(0)';
        }
      }}
    >
      {/* Header row */}
      <div className="flex items-center gap-3 px-4 py-3.5 min-h-[72px]">
        {/* Severity dot */}
        <div
          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
          style={{ background: sevColor }}
        />

        {/* Icon */}
        <div
          className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0"
          style={{ background: sevBg }}
        >
          <SevIcon className="w-4 h-4" style={{ color: sevColor }} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div
            className="text-sm font-medium truncate"
            style={{
              color: '#EDF6F9',
              fontFamily: "'Outfit Variable', Outfit, sans-serif",
            }}
          >
            {event.title}
          </div>
          <div
            className="text-xs mt-0.5 font-mono"
            style={{ color: 'rgba(255,255,255,0.3)' }}
          >
            {timeAgo(event.timestamp)} · {event.category}
          </div>
        </div>

        {/* Status badge */}
        <span
          className="px-2.5 py-1 rounded-full text-xs font-medium flex-shrink-0"
          style={{ background: statBg, color: statColor }}
        >
          {event.status}
        </span>

        {/* Chevron */}
        <ChevronRight
          className="w-4 h-4 flex-shrink-0 transition-transform duration-200"
          style={{
            color: isSelected
              ? 'rgba(255,255,255,0.5)'
              : 'rgba(255,255,255,0.2)',
            transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
          }}
        />
      </div>

      {/* Expandable detail */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] }}
            className="overflow-hidden border-t border-white/[0.06]"
          >
            <div className="px-4 py-4 space-y-4">
              {/* Description */}
              <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.7)' }}>
                {event.description}
              </p>

              {/* AI Reasoning */}
              <div className="rounded-lg p-4" style={{ background: 'rgba(255,255,255,0.03)' }}>
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="w-4 h-4 text-[#8ECAE6]" />
                  <span className="text-sm font-semibold text-[#8ECAE6]">AI Analysis</span>
                </div>
                <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.7)' }}>
                  {event.aiReasoning}
                </p>
                <div className="mt-2 text-xs font-mono" style={{ color: '#2EC4B6' }}>
                  Confidence: {event.confidence}%
                </div>
              </div>

              {/* Sources */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <BookOpen className="w-4 h-4 text-[#8ECAE6]" />
                  <span className="text-sm font-semibold text-[#8ECAE6]">Data Sources</span>
                </div>
                <ul className="space-y-1.5">
                  {event.sources.map((s, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm" style={{ color: '#EDF6F9' }}>
                      <span className="w-1 h-1 rounded-full bg-[#219EBC]" />
                      {s.name}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Recommendations */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Lightbulb className="w-4 h-4 text-[#8ECAE6]" />
                  <span className="text-sm font-semibold text-[#8ECAE6]">Recommendations</span>
                </div>
                <ol className="space-y-1.5">
                  {event.recommendations.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm" style={{ color: '#EDF6F9' }}>
                      <span className="text-[#219EBC] font-mono text-xs mt-0.5">{i + 1}.</span>
                      {r}
                    </li>
                  ))}
                </ol>
              </div>

              {/* Action buttons for Pending */}
              {event.status === 'Pending' && onStatusChange && (
                <div className="flex items-center gap-3 pt-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onStatusChange(event.id, 'Resolved');
                    }}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white transition-all hover:opacity-90"
                    style={{ background: '#06D6A0' }}
                  >
                    <Check className="w-4 h-4" /> Approve
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onStatusChange(event.id, 'Dismissed');
                    }}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all hover:bg-white/[0.08]"
                    style={{
                      border: '1px solid rgba(255,255,255,0.2)',
                      color: '#EDF6F9',
                    }}
                  >
                    <X className="w-4 h-4" /> Dismiss
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                    }}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white transition-all hover:opacity-90"
                    style={{ background: '#E29578' }}
                  >
                    <ArrowUpRight className="w-4 h-4" /> Escalate
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
