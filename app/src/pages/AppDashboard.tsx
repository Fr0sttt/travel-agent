import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Map, Clock, Calendar, BarChart3, Terminal, Brain, Shield, ChevronUp, ChevronDown, Activity, Sparkles } from 'lucide-react';
import { useTravel } from '@/contexts/TravelContext';
import ChatPanel from './app/ChatPanel';
import MapPanel from './app/MapPanel';
import TimelinePanel from './app/TimelinePanel';
import CalendarPanel from './app/CalendarPanel';
import MetricsPanel from './app/MetricsPanel';
import ToolCallsPanel from './app/ToolCallsPanel';
import MemoryPanel from './app/MemoryPanel';
import SafetyPanel from './app/SafetyPanel';

type CenterTab = 'map' | 'timeline' | 'calendar';
type RightTab = 'metrics' | 'tools' | 'memory' | 'safety';
type BottomTab = 'log' | 'stream';

const centerTabs: { id: CenterTab; label: string; icon: React.ElementType }[] = [
  { id: 'map', label: 'Map', icon: Map },
  { id: 'timeline', label: 'Timeline', icon: Clock },
  { id: 'calendar', label: 'Calendar', icon: Calendar },
];

const rightTabs: { id: RightTab; label: string; icon: React.ElementType }[] = [
  { id: 'metrics', label: 'Metrics', icon: BarChart3 },
  { id: 'tools', label: 'Tools', icon: Terminal },
  { id: 'memory', label: 'Memory', icon: Brain },
  { id: 'safety', label: 'Safety', icon: Shield },
];

export default function AppDashboard() {
  const { dashboardData } = useTravel();
  const toolCallLogs = dashboardData.toolCallLogs;
  const [centerTab, setCenterTab] = useState<CenterTab>('map');
  const [rightTab, setRightTab] = useState<RightTab>('metrics');
  const [bottomOpen, setBottomOpen] = useState(false);
  const [bottomTab, setBottomTab] = useState<BottomTab>('log');

  const renderCenterPanel = () => {
    switch (centerTab) {
      case 'map': return <MapPanel />;
      case 'timeline': return <TimelinePanel />;
      case 'calendar': return <CalendarPanel />;
      default: return <MapPanel />;
    }
  };

  const renderRightPanel = () => {
    switch (rightTab) {
      case 'metrics': return <MetricsPanel />;
      case 'tools': return <ToolCallsPanel />;
      case 'memory': return <MemoryPanel />;
      case 'safety': return <SafetyPanel />;
      default: return <MetricsPanel />;
    }
  };

  const categoryColors: Record<string, string> = {
    DB: '#219EBC',
    API: '#2EC4B6',
    CALC: '#FF9F1C',
    SAFETY: '#E29578',
  };

  return (
    <div className="flex flex-col w-full" style={{ height: 'calc(100dvh - 64px)', background: '#0A2463' }}>
      {/* Main 3-Panel Layout */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left Panel — Chat (340px) */}
        <div
          className="flex-shrink-0 border-r overflow-hidden"
          style={{
            width: '340px',
            background: 'rgba(10, 36, 99, 0.95)',
            borderColor: 'rgba(255,255,255,0.06)',
          }}
        >
          <ChatPanel />
        </div>

        {/* Center Panel — Map/Timeline/Calendar (flex-1) */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* View Toggle Bar */}
          <div
            className="flex-shrink-0 h-12 flex items-center justify-end px-4 gap-2 border-b"
            style={{ borderColor: 'rgba(255,255,255,0.06)' }}
          >
            {centerTabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = centerTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setCenterTab(tab.id)}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs transition-all"
                  style={{
                    background: isActive ? '#1A659E' : 'rgba(255,255,255,0.06)',
                    color: isActive ? '#FFFFFF' : 'rgba(255,255,255,0.5)',
                    fontFamily: "'Inter Variable', Inter, sans-serif",
                  }}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Center Content */}
          <div className="flex-1 min-h-0 overflow-hidden">
            <AnimatePresence mode="wait">
              <motion.div
                key={centerTab}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="w-full h-full"
              >
                {renderCenterPanel()}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        {/* Right Panel — Evaluation (360px) */}
        <div
          className="flex-shrink-0 border-l overflow-hidden flex flex-col"
          style={{
            width: '360px',
            background: 'rgba(10, 36, 99, 0.95)',
            borderColor: 'rgba(255,255,255,0.06)',
          }}
        >
          {/* Right Panel Tabs */}
          <div
            className="flex-shrink-0 h-11 flex items-center border-b"
            style={{ borderColor: 'rgba(255,255,255,0.06)' }}
          >
            {rightTabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = rightTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setRightTab(tab.id)}
                  className="flex-1 h-full flex items-center justify-center gap-1.5 text-xs transition-all relative"
                  style={{
                    color: isActive ? '#FFFFFF' : 'rgba(255,255,255,0.4)',
                    fontFamily: "'Inter Variable', Inter, sans-serif",
                  }}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span className="hidden xl:inline">{tab.label}</span>
                  {isActive && (
                    <motion.div
                      layoutId="rightTabIndicator"
                      className="absolute bottom-0 left-2 right-2 h-[2px] rounded-full"
                      style={{ background: '#219EBC' }}
                      transition={{ duration: 0.2 }}
                    />
                  )}
                </button>
              );
            })}
          </div>

          {/* Right Panel Content */}
          <div className="flex-1 min-h-0 overflow-hidden">
            <AnimatePresence mode="wait">
              <motion.div
                key={rightTab}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="w-full h-full"
              >
                {renderRightPanel()}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Bottom Panel (Collapsible) */}
      <div
        className="border-t transition-all duration-300 overflow-hidden"
        style={{
          height: bottomOpen ? '240px' : '36px',
          background: 'rgba(8, 28, 75, 0.98)',
          borderColor: 'rgba(255,255,255,0.06)',
        }}
      >
        {/* Bottom Panel Toggle Bar */}
        <div className="h-9 flex items-center justify-between px-4">
          <div className="flex items-center gap-2">
            {bottomOpen && (
              <>
                <button
                  onClick={() => setBottomTab('log')}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs transition-all"
                  style={{
                    background: bottomTab === 'log' ? 'rgba(33,158,188,0.15)' : 'transparent',
                    color: bottomTab === 'log' ? '#8ECAE6' : 'rgba(255,255,255,0.4)',
                  }}
                >
                  <Activity className="w-3 h-3" />
                  Live Log
                </button>
                <button
                  onClick={() => setBottomTab('stream')}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs transition-all"
                  style={{
                    background: bottomTab === 'stream' ? 'rgba(33,158,188,0.15)' : 'transparent',
                    color: bottomTab === 'stream' ? '#8ECAE6' : 'rgba(255,255,255,0.4)',
                  }}
                >
                  <Brain className="w-3 h-3" />
                  Memory Stream
                </button>
              </>
            )}
          </div>
          <button
            onClick={() => setBottomOpen(!bottomOpen)}
            className="flex items-center gap-1 text-[10px transition-colors hover:text-[#8ECAE6]"
            style={{ color: 'rgba(255,255,255,0.4)' }}
          >
            {bottomOpen ? (
              <>
                <span className="text-[10px]">Collapse</span>
                <ChevronDown className="w-3.5 h-3.5" />
              </>
            ) : (
              <>
                <span className="text-[10px]">Live Tool Calls</span>
                <ChevronUp className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>

        {/* Bottom Panel Content */}
        {bottomOpen && (
          <div className="h-[200px] overflow-hidden">
            {bottomTab === 'log' ? (
              <div className="h-full px-4 pb-2 overflow-y-auto font-mono space-y-1">
                {toolCallLogs.map((log, i) => (
                  <motion.div
                    key={log.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.02 }}
                    className="flex items-center gap-3 text-[11px]"
                  >
                    <span style={{ color: '#8ECAE6', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                      [{log.timestamp}]
                    </span>
                    <span
                      className="px-1 rounded text-[10px] font-medium"
                      style={{
                        background: `${categoryColors[log.category]}15`,
                        color: categoryColors[log.category],
                        fontFamily: "'JetBrains Mono Variable', monospace",
                      }}
                    >
                      [{log.category}]
                    </span>
                    <span style={{ color: '#2EC4B6', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                      {log.function}
                    </span>
                    <span style={{ color: 'rgba(255,255,255,0.4)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                      {log.params}
                    </span>
                    <span style={{ color: 'rgba(255,255,255,0.6)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                      → {log.result}
                    </span>
                    <span style={{ color: 'rgba(255,255,255,0.25)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                      ({log.duration}ms)
                    </span>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="h-full flex items-center justify-center px-4 pb-2">
                <div className="flex items-center gap-8">
                  {/* Memory Stream Visualization */}
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-32 h-10 rounded-lg flex items-center justify-center text-xs text-white" style={{ background: '#1A659E' }}>
                      Query
                    </div>
                    <div className="w-0.5 h-8" style={{ background: 'linear-gradient(180deg, #1A659E, #2EC4B6)' }} />
                    <motion.div
                      animate={{ scale: [1, 1.05, 1] }}
                      transition={{ duration: 2, repeat: Infinity }}
                      className="w-36 h-10 rounded-lg flex items-center justify-center text-xs text-white"
                      style={{ background: '#2EC4B6' }}
                    >
                      <Sparkles className="w-3 h-3 mr-1.5" />
                      Retrieval
                    </motion.div>
                    <div className="w-0.5 h-8" style={{ background: 'linear-gradient(180deg, #2EC4B6, #06D6A0)' }} />
                    <div className="w-32 h-10 rounded-lg flex items-center justify-center text-xs text-white" style={{ background: '#06D6A0' }}>
                      Results
                    </div>
                  </div>

                  {/* Retrieved Memories */}
                  <div className="space-y-2">
                    <p className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'rgba(255,255,255,0.4)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                      Retrieved Memories
                    </p>
                    {[
                      { label: 'Boutique hotel preference', score: 92 },
                      { label: 'Early morning photography', score: 88 },
                      { label: 'Vegetarian dining', score: 72 },
                    ].map((item, i) => (
                      <motion.div
                        key={item.label}
                        initial={{ width: 0 }}
                        animate={{ width: `${item.score * 2}px` }}
                        transition={{ delay: 0.5 + i * 0.2, duration: 0.8, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] }}
                        className="h-6 rounded flex items-center px-2"
                        style={{
                          background: item.score >= 80 ? 'rgba(6,214,160,0.15)' : 'rgba(255,209,102,0.15)',
                          maxWidth: '200px',
                        }}
                      >
                        <span className="text-[10px] truncate" style={{ color: item.score >= 80 ? '#06D6A0' : '#FFD166', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                          {item.label} ({item.score}%)
                        </span>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
