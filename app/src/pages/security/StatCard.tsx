import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  icon: LucideIcon;
  iconColor: string;
  iconBgColor: string;
  value: number;
  suffix?: string;
  label: string;
  trend: string;
  trendColor?: string;
  index: number;
}

export default function StatCard({
  icon: Icon,
  iconColor,
  iconBgColor,
  value,
  suffix = '',
  label,
  trend,
  trendColor = '#06D6A0',
  index,
}: StatCardProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const [hasAnimated, setHasAnimated] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !hasAnimated) {
          setHasAnimated(true);
        }
      },
      { threshold: 0.3 }
    );
    if (cardRef.current) observer.observe(cardRef.current);
    return () => observer.disconnect();
  }, [hasAnimated]);

  useEffect(() => {
    if (!hasAnimated) return;
    const duration = 1500;
    const startTime = Date.now();
    const timer = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(Math.round(eased * value * 10) / 10);
      if (progress >= 1) clearInterval(timer);
    }, 16);
    return () => clearInterval(timer);
  }, [hasAnimated, value]);

  const formattedValue =
    value % 1 !== 0
      ? displayValue.toFixed(1)
      : Math.round(displayValue).toString();

  return (
    <motion.div
      ref={cardRef}
      initial={{ opacity: 0, y: 30, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        duration: 0.6,
        delay: index * 0.1,
        ease: [0.16, 1, 0.3, 1] as [number, number, number, number],
      }}
      className="flex-1 min-w-0 rounded-2xl p-6 border transition-all duration-300 hover:-translate-y-1 group"
      style={{
        background: 'rgba(255,255,255,0.05)',
        borderColor: 'rgba(255,255,255,0.08)',
        backdropFilter: 'blur(16px)',
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor =
          'rgba(33,158,188,0.4)';
        (e.currentTarget as HTMLElement).style.boxShadow =
          '0 0 20px rgba(33,158,188,0.3)';
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor =
          'rgba(255,255,255,0.08)';
        (e.currentTarget as HTMLElement).style.boxShadow = 'none';
      }}
    >
      <div
        className="w-10 h-10 rounded-full flex items-center justify-center mb-4"
        style={{ background: iconBgColor }}
      >
        <Icon className="w-5 h-5" style={{ color: iconColor }} />
      </div>
      <div
        className="text-4xl font-bold tracking-tight"
        style={{
          fontFamily: "'Outfit Variable', Outfit, sans-serif",
          color: '#FFFFFF',
        }}
      >
        {formattedValue}
        {suffix}
      </div>
      <div
        className="text-sm mt-1"
        style={{ color: 'rgba(255,255,255,0.5)' }}
      >
        {label}
      </div>
      <div
        className="text-xs mt-2 font-mono flex items-center gap-1"
        style={{ color: trendColor }}
      >
        {trend}
      </div>
    </motion.div>
  );
}
