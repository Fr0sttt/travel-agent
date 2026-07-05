import { motion } from 'framer-motion';
import {
  ShieldCheck,
  KeyRound,
  MessageSquareWarning,
  Globe,
  UserCheck,
  Database,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { securityPolicies } from './data';

const statusLabels: Record<'active' | 'inactive', string> = {
  active: '活跃',
  inactive: '已禁用',
};

const policyIcons = [
  ShieldCheck,
  KeyRound,
  MessageSquareWarning,
  Globe,
  UserCheck,
  Database,
];

export default function SecurityPolicies() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{
        duration: 0.8,
        ease: [0.16, 1, 0.3, 1] as [number, number, number, number],
      }}
    >
      {/* Header */}
      <div className="mb-6">
        <h2
          className="text-3xl sm:text-4xl font-semibold tracking-tight"
          style={{
            color: '#FFFFFF',
            fontFamily: "'Outfit Variable', Outfit, sans-serif",
          }}
        >
          安全策略
        </h2>
        <p className="text-base mt-2" style={{ color: 'rgba(255,255,255,0.5)' }}>
          保护您的 AI 旅行代理的活跃治理策略
        </p>
      </div>

      {/* Accordion */}
      <Accordion type="multiple" className="space-y-2">
        {securityPolicies.map((policy, index) => {
          const Icon = policyIcons[index] || ShieldCheck;
          return (
            <motion.div
              key={policy.id}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{
                duration: 0.5,
                delay: index * 0.08,
                ease: [0.16, 1, 0.3, 1] as [number, number, number, number],
              }}
            >
              <AccordionItem
                value={policy.id}
                className="rounded-xl border overflow-hidden"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  borderColor: 'rgba(255,255,255,0.08)',
                }}
              >
                <AccordionTrigger className="px-5 py-4 hover:no-underline hover:bg-white/[0.02] transition-colors [&[data-state=open]]:bg-white/[0.02]">
                  <div className="flex items-center gap-3 text-left w-full pr-4">
                    <div
                      className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0"
                      style={{ background: 'rgba(33,158,188,0.12)' }}
                    >
                      <Icon className="w-4 h-4 text-[#219EBC]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className="text-sm font-medium"
                          style={{
                            color: '#EDF6F9',
                            fontFamily: "'Outfit Variable', Outfit, sans-serif",
                          }}
                        >
                          {policy.name}
                        </span>
                        <span
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0"
                          style={{
                            background:
                              policy.status === 'active'
                                ? 'rgba(6,214,160,0.15)'
                                : 'rgba(255,255,255,0.06)',
                            color:
                              policy.status === 'active'
                                ? '#06D6A0'
                                : 'rgba(255,255,255,0.35)',
                          }}
                        >
                          {policy.status === 'active' ? (
                            <CheckCircle className="w-3 h-3" />
                          ) : (
                            <XCircle className="w-3 h-3" />
                          )}
                          {statusLabels[policy.status]}
                        </span>
                      </div>
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-5 pb-4">
                  <div className="pl-12">
                    <p
                      className="text-sm leading-relaxed"
                      style={{ color: 'rgba(255,255,255,0.6)' }}
                    >
                      {policy.description}
                    </p>
                    <p
                      className="text-xs font-mono mt-3"
                      style={{ color: 'rgba(255,255,255,0.3)' }}
                    >
                      最后更新: {policy.lastUpdated}
                    </p>
                  </div>
                </AccordionContent>
              </AccordionItem>
            </motion.div>
          );
        })}
      </Accordion>
    </motion.div>
  );
}
