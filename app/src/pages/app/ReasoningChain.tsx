import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, ChevronDown } from 'lucide-react';
import type { ReasoningStep } from './mockData';

interface ReasoningChainProps {
  steps: ReasoningStep[];
}

export default function ReasoningChain({ steps }: ReasoningChainProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{ background: 'rgba(255,255,255,0.03)', borderLeft: '2px solid #219EBC' }}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3 py-2.5 text-left transition-colors hover:bg-white/[0.02]"
      >
        <div className="flex items-center gap-2">
          <Brain className="w-3.5 h-3.5 text-[#8ECAE6]" />
          <span
            className="text-sm font-medium"
            style={{ color: '#8ECAE6', fontFamily: "'Inter Variable', Inter, sans-serif" }}
          >
            Reasoning Chain
          </span>
          <span
            className="text-xs px-1.5 py-0.5 rounded-full"
            style={{ background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.4)', fontFamily: "'JetBrains Mono Variable', monospace" }}
          >
            {steps.length} steps
          </span>
        </div>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="w-4 h-4" style={{ color: 'rgba(255,255,255,0.4)' }} />
        </motion.div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 space-y-2">
              {steps.map((step, i) => (
                <motion.div
                  key={step.step}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.08, duration: 0.25 }}
                  className="flex items-start gap-2.5"
                >
                  <span
                    className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-medium"
                    style={{
                      background: step.confidence >= 90 ? 'rgba(6,214,160,0.15)' : step.confidence >= 80 ? 'rgba(255,209,102,0.15)' : 'rgba(239,71,111,0.15)',
                      color: step.confidence >= 90 ? '#06D6A0' : step.confidence >= 80 ? '#FFD166' : '#EF476F',
                      fontFamily: "'JetBrains Mono Variable', monospace",
                    }}
                  >
                    {step.step}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.7)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
                      {step.description}
                    </p>
                  </div>
                  <span
                    className="flex-shrink-0 text-xs font-medium"
                    style={{
                      color: step.confidence >= 90 ? '#06D6A0' : step.confidence >= 80 ? '#FFD166' : '#EF476F',
                      fontFamily: "'JetBrains Mono Variable', monospace",
                    }}
                  >
                    {step.confidence}%
                  </span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
