import { useState } from 'react';
import { motion } from 'framer-motion';
import { Zap, Database, Search } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useTravel } from '@/contexts/TravelContext';

function RelevanceBadge({ score }: { score: number }) {
  const color = score >= 80 ? '#06D6A0' : score >= 50 ? '#FFD166' : '#EF476F';
  return (
    <span
      className="text-[10px] px-1.5 py-0.5 rounded font-medium"
      style={{
        background: `${color}15`,
        color,
        fontFamily: "'JetBrains Mono Variable', monospace",
      }}
    >
      {score}%
    </span>
  );
}

export default function MemoryPanel() {
  const { dashboardData } = useTravel();
  const { memoryItems } = dashboardData;
  const [searchQuery, setSearchQuery] = useState('');

  const filteredItems = searchQuery.trim()
    ? memoryItems.filter((m) => m.content.toLowerCase().includes(searchQuery.toLowerCase()))
    : memoryItems;

  const shortTerm = filteredItems.filter((m) => m.type === 'short');
  const longTerm = filteredItems.filter((m) => m.type === 'long');

  return (
    <div className="h-full flex flex-col">
      {/* Search */}
      <div className="flex-shrink-0 p-4 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5" style={{ color: 'rgba(255,255,255,0.3)' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索记忆..."
            className="w-full h-9 rounded-full pl-9 pr-4 text-xs outline-none focus:border-[#219EBC]"
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#FFFFFF',
              fontFamily: "'Inter Variable', Inter, sans-serif",
            }}
          />
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          {/* Short-Term Memory */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Zap className="w-4 h-4 text-[#FFD166]" />
              <h4 className="text-sm font-semibold text-white" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
                短期记忆
              </h4>
            </div>
            <p className="text-[11px] mb-3" style={{ color: 'rgba(255,255,255,0.4)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
              当前对话上下文
            </p>

            <div className="flex flex-wrap gap-2">
              {shortTerm.map((item, i) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.05, duration: 0.2 }}
                  className="px-3 py-1.5 rounded-full text-xs transition-colors hover:bg-white/[0.1]"
                  style={{
                    background: 'rgba(255,255,255,0.06)',
                    color: '#EDF6F9',
                    borderLeft: '2px solid #FFD166',
                    fontFamily: "'Inter Variable', Inter, sans-serif",
                  }}
                >
                  {item.content}
                </motion.div>
              ))}
            </div>
          </div>

          {/* Divider */}
          <div className="h-px" style={{ background: 'rgba(255,255,255,0.06)' }} />

          {/* Long-Term Memory */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Database className="w-4 h-4 text-[#219EBC]" />
              <h4 className="text-sm font-semibold text-white" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
                长期记忆
              </h4>
            </div>
            <p className="text-[11px] mb-3" style={{ color: 'rgba(255,255,255,0.4)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
              从过去的交互中检索
            </p>

            <div className="space-y-2.5">
              {longTerm.map((item, i) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.08, duration: 0.3 }}
                  className="glass-card p-3"
                >
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <p className="text-xs leading-relaxed flex-1" style={{ color: '#EDF6F9', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
                      {item.content}
                    </p>
                    {item.relevance && <RelevanceBadge score={item.relevance} />}
                  </div>
                  {item.source && (
                    <p className="text-[10px]" style={{ color: 'rgba(255,255,255,0.3)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                      {item.source}
                    </p>
                  )}
                  {item.timestamp && (
                    <p className="text-[10px] mt-0.5" style={{ color: 'rgba(255,255,255,0.2)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                      {item.timestamp}
                    </p>
                  )}
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
