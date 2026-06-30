import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MapPin, Clock, ChevronDown, Utensils, Mountain, ShoppingBag, Hotel, Car, Trees, Camera, Footprints, Landmark, Sparkles } from 'lucide-react';
import { useTravel } from '@/contexts/TravelContext';
import type { TimelineActivity } from './mockData';

const categoryIconMap: Record<string, React.ReactNode> = {
  temple: <Landmark className="w-4 h-4" />,
  restaurant: <Utensils className="w-4 h-4" />,
  shopping: <ShoppingBag className="w-4 h-4" />,
  hotel: <Hotel className="w-4 h-4" />,
  transport: <Car className="w-4 h-4" />,
  nature: <Trees className="w-4 h-4" />,
  walking: <Footprints className="w-4 h-4" />,
  culture: <Sparkles className="w-4 h-4" />,
  activity: <Camera className="w-4 h-4" />,
  default: <Mountain className="w-4 h-4" />,
};

const categoryColors: Record<string, string> = {
  temple: '#219EBC',
  restaurant: '#E29578',
  shopping: '#FF9F1C',
  hotel: '#2EC4B6',
  transport: '#FFD166',
  nature: '#06D6A0',
  walking: '#8ECAE6',
  culture: '#E29578',
  activity: '#FF9F1C',
  default: '#219EBC',
};

function ActivityCard({ activity, index }: { activity: TimelineActivity; index: number }) {
  const isLeft = index % 2 === 0;
  const icon = categoryIconMap[activity.category] || categoryIconMap.default;
  const color = categoryColors[activity.category] || categoryColors.default;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] }}
      className={`flex items-start gap-0 ${isLeft ? 'flex-row' : 'flex-row-reverse'}`}
    >
      {/* Card */}
      <div className={`w-[45%] ${isLeft ? 'text-right' : 'text-left'}`}>
        <div className="glass-card p-4 relative">
          {/* Category Icon */}
          <div
            className="absolute top-3 right-3 w-7 h-7 rounded-full flex items-center justify-center"
            style={{ background: `${color}20`, color }}
          >
            {icon}
          </div>

          {/* Time Badge */}
          <div className="flex items-center gap-1.5 mb-2" style={{ justifyContent: isLeft ? 'flex-end' : 'flex-start' }}>
            <Clock className="w-3 h-3 text-[#2EC4B6]" />
            <span
              className="text-[11px] font-medium"
              style={{ color: '#2EC4B6', fontFamily: "'JetBrains Mono Variable', monospace" }}
            >
              {activity.time}
            </span>
          </div>

          <h4 className="text-sm font-semibold text-white mb-1.5 pr-8" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
            {activity.title}
          </h4>

          <div className={`flex items-center gap-1.5 mb-1.5 ${isLeft ? 'justify-end' : 'justify-start'}`}>
            <MapPin className="w-3 h-3 flex-shrink-0" style={{ color: 'rgba(255,255,255,0.4)' }} />
            <span className="text-[11px]" style={{ color: 'rgba(255,255,255,0.4)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
              {activity.location}
            </span>
          </div>

          <div className={`flex items-center gap-1.5 mb-2 ${isLeft ? 'justify-end' : 'justify-start'}`}>
            <Clock className="w-3 h-3 flex-shrink-0" style={{ color: 'rgba(255,255,255,0.3)' }} />
            <span className="text-[11px]" style={{ color: 'rgba(255,255,255,0.3)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
              {activity.duration}
            </span>
          </div>

          <p className="text-[11px] leading-relaxed" style={{ color: 'rgba(255,255,255,0.5)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
            {activity.notes}
          </p>
        </div>
      </div>

      {/* Center Dot */}
      <div className="flex-shrink-0 w-[10%] flex justify-center pt-5">
        <div className="w-3 h-3 rounded-full border-2 border-[#2EC4B6] bg-[#0A2463]" />
      </div>

      {/* Spacer */}
      <div className="w-[45%]" />
    </motion.div>
  );
}

export default function TimelinePanel() {
  const { dashboardData } = useTravel();
  const { timelineDays } = dashboardData;

  const defaultExpanded = useMemo(() => timelineDays.map((d) => d.day), [timelineDays]);
  const [manualExpanded, setManualExpanded] = useState<number[] | null>(null);
  const expandedDays = manualExpanded ?? defaultExpanded;

  const toggleDay = (day: number) => {
    const current = expandedDays;
    const next = current.includes(day)
      ? current.filter((d) => d !== day)
      : [...current, day];
    setManualExpanded(next);
  };

  return (
    <div className="h-full overflow-y-auto p-6" style={{ background: '#0A2463' }}>
      {/* Timeline Container */}
      <div className="relative max-w-3xl mx-auto">
        {/* Vertical Line */}
        <div
          className="absolute left-1/2 top-0 bottom-0 w-[3px] -translate-x-1/2"
          style={{ background: 'linear-gradient(180deg, #2EC4B6 0%, #219EBC 100%)' }}
        />

        {/* Day Groups */}
        <div className="space-y-8">
          {timelineDays.map((day) => (
            <div key={day.day}>
              {/* Day Header */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="relative z-10 flex justify-center mb-6"
              >
                <button
                  onClick={() => toggleDay(day.day)}
                  className="flex items-center gap-3 px-6 py-3 rounded-xl transition-all hover:scale-[1.02]"
                  style={{ background: '#1A659E' }}
                >
                  <h3 className="text-sm font-semibold text-white" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
                    Day {day.day} — {day.date}
                  </h3>
                  <p className="text-xs" style={{ color: 'rgba(255,255,255,0.6)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
                    {day.title}
                  </p>
                  <motion.div
                    animate={{ rotate: expandedDays.includes(day.day) ? 0 : -90 }}
                    transition={{ duration: 0.2 }}
                  >
                    <ChevronDown className="w-4 h-4 text-white/60" />
                  </motion.div>
                </button>
              </motion.div>

              {/* Activities */}
              <AnimatePresence>
                {expandedDays.includes(day.day) && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] }}
                    className="overflow-hidden"
                  >
                    <div className="space-y-4">
                      {day.activities.map((activity, i) => (
                        <ActivityCard key={activity.id} activity={activity} index={i} />
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
