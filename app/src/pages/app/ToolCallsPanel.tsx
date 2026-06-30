import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useTravel } from '@/contexts/TravelContext';
import type { ToolCallLog } from './mockData';

const categoryColors: Record<string, string> = {
  DB: '#219EBC',
  API: '#2EC4B6',
  CALC: '#FF9F1C',
  SAFETY: '#E29578',
};

function LogEntryCard({ log, index }: { log: ToolCallLog; index: number }) {
  const [isOpen, setIsOpen] = useState(false);
  const catColor = categoryColors[log.category] || '#219EBC';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03, duration: 0.25 }}
      className="rounded-lg overflow-hidden"
      style={{ background: 'rgba(255,255,255,0.03)' }}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-white/[0.02]"
      >
        {/* Status dot */}
        <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: '#06D6A0' }} />

        {/* Category tag */}
        <span
          className="flex-shrink-0 text-[10px] px-1.5 py-0.5 rounded font-medium"
          style={{
            background: `${catColor}15`,
            color: catColor,
            fontFamily: "'JetBrains Mono Variable', monospace",
          }}
        >
          {log.category}
        </span>

        {/* Function name */}
        <span
          className="flex-1 min-w-0 text-xs truncate"
          style={{ color: '#2EC4B6', fontFamily: "'JetBrains Mono Variable', monospace" }}
        >
          {log.function}
        </span>

        {/* Duration */}
        <span className="flex-shrink-0 text-[10px]" style={{ color: 'rgba(255,255,255,0.3)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
          {log.duration}ms
        </span>

        {/* Timestamp */}
        <span className="flex-shrink-0 text-[10px]" style={{ color: 'rgba(255,255,255,0.25)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
          {log.timestamp.split('.')[0]}
        </span>

        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="flex-shrink-0"
        >
          <ChevronDown className="w-3.5 h-3.5" style={{ color: 'rgba(255,255,255,0.3)' }} />
        </motion.div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 space-y-2 border-t border-white/[0.04]">
              {/* Parameters */}
              <div className="pt-2">
                <span className="text-[10px] uppercase tracking-wider" style={{ color: '#8ECAE6', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                  Parameters
                </span>
                <pre
                  className="mt-1 p-2 rounded text-[10px] overflow-x-auto"
                  style={{
                    background: 'rgba(0,0,0,0.2)',
                    color: 'rgba(255,255,255,0.6)',
                    fontFamily: "'JetBrains Mono Variable', monospace",
                  }}
                >
                  {log.params}
                </pre>
              </div>

              {/* Result */}
              <div>
                <span className="text-[10px] uppercase tracking-wider" style={{ color: '#2EC4B6', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                  Result
                </span>
                <p
                  className="mt-1 p-2 rounded text-[10px]"
                  style={{
                    background: 'rgba(0,0,0,0.2)',
                    color: 'rgba(255,255,255,0.6)',
                    fontFamily: "'JetBrains Mono Variable', monospace",
                  }}
                >
                  {log.result} ({log.duration}ms)
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function ToolCallsPanel() {
  const { dashboardData } = useTravel();
  const toolCallLogs = dashboardData.toolCallLogs;

  const stats = {
    total: toolCallLogs.length,
    success: toolCallLogs.filter((l) => !l.result.startsWith('Error')).length,
    pending: 0,
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 px-4 pt-4 pb-3 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-white" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
            Tool Calls
          </h3>
        </div>
        <p className="text-[11px]" style={{ color: 'rgba(255,255,255,0.4)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
          {stats.total} calls · <span className="text-[#06D6A0]">{stats.success} success</span> · {stats.pending} pending
        </p>
      </div>

      {/* Log List */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-1.5">
          {toolCallLogs.map((log, i) => (
            <LogEntryCard key={log.id} log={log} index={i} />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
