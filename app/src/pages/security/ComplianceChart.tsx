import { useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import { complianceTrendData } from './data';

interface TooltipPayloadItem {
  value: number;
  payload: { day: string; score: number; date: string };
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const data = payload[0];
  return (
    <div
      className="rounded-xl px-4 py-3 border"
      style={{
        background: 'rgba(10, 36, 99, 0.95)',
        borderColor: 'rgba(255,255,255,0.1)',
        backdropFilter: 'blur(16px)',
      }}
    >
      <p className="text-xs font-mono mb-1" style={{ color: 'rgba(255,255,255,0.5)' }}>
        {data.payload.date}
      </p>
      <p className="text-sm font-semibold" style={{ color: '#2EC4B6' }}>
        Score: {data.value}%
      </p>
    </div>
  );
}

export default function ComplianceChart() {
  const avgScore = useMemo(() => {
    const sum = complianceTrendData.reduce((acc, d) => acc + d.score, 0);
    return Math.round((sum / complianceTrendData.length) * 10) / 10;
  }, []);

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
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-6">
        <div>
          <h2
            className="text-3xl sm:text-4xl font-semibold tracking-tight"
            style={{
              color: '#FFFFFF',
              fontFamily: "'Outfit Variable', Outfit, sans-serif",
            }}
          >
            Compliance Trend
          </h2>
          <p className="text-base mt-2" style={{ color: 'rgba(255,255,255,0.5)' }}>
            Safety compliance score over the last 30 days
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-3 h-0.5 rounded-full" style={{ background: '#2EC4B6' }} />
            <span className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Score
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className="w-3 h-0.5 rounded-full border-dashed"
              style={{ borderTop: '2px dashed #FFD166', height: 0 }}
            />
            <span className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Target (80%)
            </span>
          </div>
          <div className="px-3 py-1.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.05)' }}>
            <span className="text-xs font-mono" style={{ color: '#2EC4B6' }}>
              Avg: {avgScore}%
            </span>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div
        className="rounded-2xl border p-6 sm:p-8"
        style={{
          background: 'rgba(255,255,255,0.05)',
          borderColor: 'rgba(255,255,255,0.08)',
          backdropFilter: 'blur(16px)',
        }}
      >
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart
            data={complianceTrendData}
            margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
          >
            <defs>
              <linearGradient id="complianceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#2EC4B6" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#2EC4B6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.04)"
              vertical={false}
            />
            <XAxis
              dataKey="day"
              tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}
              axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
              tickLine={false}
              interval={4}
            />
            <YAxis
              domain={[60, 100]}
              tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}
              axisLine={false}
              tickLine={false}
              ticks={[60, 70, 80, 90, 100]}
              tickFormatter={(v: number) => `${v}%`}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine
              y={80}
              stroke="#FFD166"
              strokeDasharray="6 4"
              strokeWidth={1}
            />
            <ReferenceLine
              y={90}
              stroke="#06D6A0"
              strokeDasharray="4 6"
              strokeWidth={1}
              strokeOpacity={0.3}
            />
            <Area
              type="monotone"
              dataKey="score"
              stroke="#2EC4B6"
              strokeWidth={2}
              fill="url(#complianceGradient)"
              dot={false}
              activeDot={{
                r: 5,
                fill: '#2EC4B6',
                stroke: '#0A2463',
                strokeWidth: 2,
              }}
              animationDuration={2000}
              animationEasing="ease-out"
            />
          </AreaChart>
        </ResponsiveContainer>

        {/* Zone indicators */}
        <div className="flex items-center justify-center gap-6 mt-4 pt-4 border-t border-white/[0.06]">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#06D6A0' }} />
            <span className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Green Zone (90–100%)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#FFD166' }} />
            <span className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Yellow Zone (70–90%)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#EF476F' }} />
            <span className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Red Zone (0–70%)
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
