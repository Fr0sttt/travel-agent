import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, ChevronDown, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import type { ToolCall } from './mockData';

interface ToolCallCardProps {
  toolCall: ToolCall;
}

const categoryColors: Record<string, string> = {
  db: '#219EBC',
  api: '#2EC4B6',
  calc: '#FF9F1C',
  safety: '#E29578',
};

const statusConfig = {
  running: { icon: Loader2, color: '#FFD166', bg: 'rgba(255,209,102,0.1)', spin: true },
  completed: { icon: CheckCircle2, color: '#06D6A0', bg: 'rgba(6,214,160,0.1)', spin: false },
  failed: { icon: XCircle, color: '#EF476F', bg: 'rgba(239,71,111,0.1)', spin: false },
};

export default function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const config = statusConfig[toolCall.status];
  const StatusIcon = config.icon;

  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{ background: '#0E1117', border: '1px solid rgba(255,255,255,0.06)' }}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3 py-2 text-left transition-colors hover:bg-white/[0.02]"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <Terminal className="w-3.5 h-3.5 flex-shrink-0" style={{ color: categoryColors[toolCall.category] || '#2EC4B6' }} />
          <span
            className="text-xs font-medium truncate"
            style={{ color: '#2EC4B6', fontFamily: "'JetBrains Mono Variable', monospace" }}
          >
            {toolCall.name}
          </span>
          <span
            className="flex-shrink-0 text-[10px] px-1.5 py-0.5 rounded"
            style={{ color: categoryColors[toolCall.category] || '#2EC4B6', background: `${categoryColors[toolCall.category]}15` || 'rgba(46,196,182,0.1)', fontFamily: "'JetBrains Mono Variable', monospace" }}
          >
            {toolCall.category.toUpperCase()}
          </span>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <motion.div
            className={config.spin ? 'animate-spin' : ''}
          >
            <StatusIcon className="w-3.5 h-3.5" style={{ color: config.color }} />
          </motion.div>
          <motion.div
            animate={{ rotate: isOpen ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown className="w-3.5 h-3.5" style={{ color: 'rgba(255,255,255,0.3)' }} />
          </motion.div>
        </div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 space-y-2">
              {/* Parameters */}
              <div>
                <span className="text-[10px] uppercase tracking-wider" style={{ color: '#8ECAE6', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                  Parameters
                </span>
                <pre
                  className="mt-1 p-2 rounded text-xs overflow-x-auto"
                  style={{
                    background: 'rgba(0,0,0,0.2)',
                    color: 'rgba(255,255,255,0.7)',
                    fontFamily: "'JetBrains Mono Variable', monospace",
                    fontSize: '0.6875rem',
                  }}
                >
                  {JSON.stringify(toolCall.params, null, 2)}
                </pre>
              </div>

              {/* Result */}
              {toolCall.result && (
                <div>
                  <span className="text-[10px] uppercase tracking-wider" style={{ color: '#2EC4B6', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                    Result
                  </span>
                  <p
                    className="mt-1 p-2 rounded text-xs"
                    style={{
                      background: 'rgba(0,0,0,0.2)',
                      color: 'rgba(255,255,255,0.6)',
                      fontFamily: "'JetBrains Mono Variable', monospace",
                      fontSize: '0.6875rem',
                    }}
                  >
                    {toolCall.result}
                  </p>
                </div>
              )}

              {/* Duration */}
              {toolCall.duration && (
                <div className="flex justify-end">
                  <span
                    className="text-[10px]"
                    style={{ color: 'rgba(255,255,255,0.3)', fontFamily: "'JetBrains Mono Variable', monospace" }}
                  >
                    {toolCall.duration}ms
                  </span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
