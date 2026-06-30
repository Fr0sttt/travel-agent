import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield,
  Brain,
  BookOpen,
  Lightbulb,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  Clock,
  XCircle,
  FileText,
  History,
  Link2,
} from 'lucide-react';
import type { SecurityEvent } from './data';
import { severityColors, statusColors, statusBgColors } from './data';

interface EventDetailPanelProps {
  event: SecurityEvent | null;
}

function formatDate(ts: string): string {
  return new Date(ts).toLocaleString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

const severityIcons: Record<string, React.ReactNode> = {
  Critical: <Shield className="w-5 h-5" />,
  High: <Shield className="w-5 h-5" />,
  Medium: <Shield className="w-5 h-5" />,
  Low: <Shield className="w-5 h-5" />,
};

export default function EventDetailPanel({ event }: EventDetailPanelProps) {
  const [rawLogOpen, setRawLogOpen] = useState(false);

  return (
    <div
      className="rounded-2xl border h-full flex flex-col"
      style={{
        background: 'rgba(255,255,255,0.05)',
        borderColor: 'rgba(255,255,255,0.08)',
        backdropFilter: 'blur(16px)',
      }}
    >
      <AnimatePresence mode="wait">
        {!event ? (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex-1 flex flex-col items-center justify-center py-20 px-10"
          >
            <Shield
              className="w-12 h-12 mb-4"
              style={{ color: 'rgba(255,255,255,0.1)' }}
            />
            <p
              className="text-base text-center"
              style={{ color: 'rgba(255,255,255,0.3)' }}
            >
              Select an event to view details
            </p>
          </motion.div>
        ) : (
          <motion.div
            key={event.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="flex-1 overflow-y-auto p-6 space-y-5"
          >
            {/* Header */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
                  style={{
                    background: severityColors[event.severity] + '22',
                    color: severityColors[event.severity],
                  }}
                >
                  {severityIcons[event.severity]}
                  {event.severity}
                </span>
                <span
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium"
                  style={{
                    background: statusBgColors[event.status],
                    color: statusColors[event.status],
                  }}
                >
                  {event.status === 'Resolved' && <CheckCircle className="w-3 h-3" />}
                  {event.status === 'Pending' && <Clock className="w-3 h-3" />}
                  {event.status === 'Dismissed' && <XCircle className="w-3 h-3" />}
                  {event.status}
                </span>
              </div>
              <h2
                className="text-2xl font-semibold leading-tight"
                style={{
                  color: '#FFFFFF',
                  fontFamily: "'Outfit Variable', Outfit, sans-serif",
                }}
              >
                {event.title}
              </h2>
              <p className="text-sm font-mono mt-2 text-[#8ECAE6]">
                {formatDate(event.timestamp)}
              </p>
              <p
                className="text-xs font-mono mt-1"
                style={{ color: 'rgba(255,255,255,0.2)' }}
              >
                {event.id}
              </p>
            </div>

            {/* Description */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 }}
            >
              <h3 className="text-sm font-semibold text-[#8ECAE6] mb-2">
                Description
              </h3>
              <p className="text-sm leading-relaxed" style={{ color: '#EDF6F9' }}>
                {event.description}
              </p>
            </motion.div>

            {/* AI Reasoning */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="rounded-lg p-4"
              style={{ background: 'rgba(255,255,255,0.03)' }}
            >
              <div className="flex items-center gap-2 mb-2">
                <Brain className="w-4 h-4 text-[#8ECAE6]" />
                <h3 className="text-sm font-semibold text-[#8ECAE6]">AI Analysis</h3>
              </div>
              <p
                className="text-sm leading-relaxed"
                style={{ color: 'rgba(255,255,255,0.7)' }}
              >
                {event.aiReasoning}
              </p>
              <p className="mt-2 text-xs font-mono" style={{ color: '#2EC4B6' }}>
                Confidence: {event.confidence}%
              </p>
            </motion.div>

            {/* Source Attribution */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
            >
              <div className="flex items-center gap-2 mb-2">
                <BookOpen className="w-4 h-4 text-[#8ECAE6]" />
                <h3 className="text-sm font-semibold text-[#8ECAE6]">Data Sources</h3>
              </div>
              <ul className="space-y-2">
                {event.sources.map((s, i) => (
                  <li
                    key={i}
                    className="flex items-center gap-2 text-sm"
                    style={{ color: '#EDF6F9' }}
                  >
                    <Link2
                      className="w-3.5 h-3.5 flex-shrink-0"
                      style={{ color: 'rgba(255,255,255,0.3)' }}
                    />
                    {s.name}
                  </li>
                ))}
              </ul>
            </motion.div>

            {/* Recommendations */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <div className="flex items-center gap-2 mb-2">
                <Lightbulb className="w-4 h-4 text-[#8ECAE6]" />
                <h3 className="text-sm font-semibold text-[#8ECAE6]">
                  Recommended Actions
                </h3>
              </div>
              <ol className="space-y-2">
                {event.recommendations.map((r, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm"
                    style={{ color: '#EDF6F9' }}
                  >
                    <span className="text-[#219EBC] font-mono text-xs mt-0.5 flex-shrink-0">
                      {i + 1}.
                    </span>
                    {r}
                  </li>
                ))}
              </ol>
            </motion.div>

            {/* Raw Log */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
            >
              <button
                onClick={() => setRawLogOpen(!rawLogOpen)}
                className="flex items-center gap-2 w-full"
              >
                <FileText className="w-4 h-4 text-[#8ECAE6]" />
                <h3 className="text-sm font-semibold text-[#8ECAE6]">Raw Log</h3>
                {rawLogOpen ? (
                  <ChevronUp className="w-4 h-4 text-[rgba(255,255,255,0.3)] ml-auto" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-[rgba(255,255,255,0.3)] ml-auto" />
                )}
              </button>
              <AnimatePresence>
                {rawLogOpen && (
                  <motion.pre
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className="overflow-hidden mt-2"
                  >
                    <code
                      className="block p-3 rounded-lg text-xs font-mono leading-relaxed overflow-x-auto whitespace-pre-wrap"
                      style={{
                        background: 'rgba(0,0,0,0.25)',
                        color: 'rgba(255,255,255,0.7)',
                      }}
                    >
                      {event.rawLog}
                    </code>
                  </motion.pre>
                )}
              </AnimatePresence>
            </motion.div>

            {/* Decision Log */}
            {event.decisionLog && event.decisionLog.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <History className="w-4 h-4 text-[#8ECAE6]" />
                  <h3 className="text-sm font-semibold text-[#8ECAE6]">
                    Decision Log
                  </h3>
                </div>
                <div className="space-y-2">
                  {event.decisionLog.map((entry, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 text-xs font-mono"
                    >
                      <span className="text-[#8ECAE6] flex-shrink-0 w-16">
                        {entry.time}
                      </span>
                      <span style={{ color: 'rgba(255,255,255,0.5)' }}>
                        —
                      </span>
                      <span style={{ color: 'rgba(255,255,255,0.7)' }}>
                        {entry.action}
                      </span>
                      {entry.user && (
                        <span
                          className="ml-auto flex-shrink-0"
                          style={{ color: 'rgba(255,255,255,0.35)' }}
                        >
                          {entry.user}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Related Events */}
            {event.relatedEventIds && event.relatedEventIds.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Link2 className="w-4 h-4 text-[#8ECAE6]" />
                  <h3 className="text-sm font-semibold text-[#8ECAE6]">
                    Related Events
                  </h3>
                </div>
                <div className="space-y-1.5">
                  {event.relatedEventIds.map((rid) => (
                    <div
                      key={rid}
                      className="text-xs font-mono px-2.5 py-1.5 rounded-md"
                      style={{
                        color: '#8ECAE6',
                        background: 'rgba(33,158,188,0.1)',
                      }}
                    >
                      {rid}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
