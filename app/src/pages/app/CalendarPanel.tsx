import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronLeft, ChevronRight, X, Clock } from 'lucide-react';
import { useTravel } from '@/contexts/TravelContext';

const typeColors: Record<string, string> = {
  attraction: '#219EBC',
  restaurant: '#E29578',
  hotel: '#2EC4B6',
  transport: '#FFD166',
  activity: '#FF9F1C',
};

const DAYS = ['日', '一', '二', '三', '四', '五', '六'];
const MONTH_NAMES = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];

export default function CalendarPanel() {
  const { dashboardData } = useTravel();
  const { calendarEvents } = dashboardData;

  const initialDate = useMemo(() => {
    if (calendarEvents.length === 0) return { month: 5, year: 2025 };
    // Try to infer month/year from first event (YYYY-MM-DD or day-of-month)
    const first = calendarEvents[0];
    const d = new Date();
    d.setDate(first.day);
    return { month: d.getMonth(), year: d.getFullYear() };
  }, [calendarEvents]);

  const [currentMonth, setCurrentMonth] = useState(initialDate.month);
  const [currentYear, setCurrentYear] = useState(initialDate.year);
  const [selectedDay, setSelectedDay] = useState<number | null>(null);

  const firstDayOfMonth = new Date(currentYear, currentMonth, 1).getDay();
  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();

  const prevMonth = () => {
    setCurrentMonth((m) => {
      if (m === 0) {
        setCurrentYear((y) => y - 1);
        return 11;
      }
      return m - 1;
    });
  };

  const nextMonth = () => {
    setCurrentMonth((m) => {
      if (m === 11) {
        setCurrentYear((y) => y + 1);
        return 0;
      }
      return m + 1;
    });
  };

  const getEventsForDay = (day: number) => calendarEvents.filter((e) => e.day === day);

  const selectedEvents = selectedDay ? getEventsForDay(selectedDay) : [];

  return (
    <div className="h-full flex flex-col p-6" style={{ background: '#0A2463' }}>
      {/* Month Navigation */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={prevMonth}
          className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors hover:bg-white/[0.05]"
        >
          <ChevronLeft className="w-4 h-4 text-[#EDF6F9]" />
        </button>
        <h3 className="text-base font-semibold text-white" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
          {MONTH_NAMES[currentMonth]} {currentYear}
        </h3>
        <button
          onClick={nextMonth}
          className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors hover:bg-white/[0.05]"
        >
          <ChevronRight className="w-4 h-4 text-[#EDF6F9]" />
        </button>
      </div>

      {/* Day Headers */}
      <div className="grid grid-cols-7 mb-2">
        {DAYS.map((day) => (
          <div
            key={day}
            className="text-center text-xs font-medium uppercase py-2"
            style={{ color: '#8ECAE6', fontFamily: "'Inter Variable', Inter, sans-serif" }}
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7 flex-1">
        {/* Empty cells for offset */}
        {Array.from({ length: firstDayOfMonth }).map((_, i) => (
          <div key={`empty-${i}`} className="border border-white/[0.03] p-1" />
        ))}

        {/* Day cells */}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const day = i + 1;
          const events = getEventsForDay(day);
          const isSelected = selectedDay === day;

          return (
            <motion.button
              key={day}
              whileHover={{ backgroundColor: 'rgba(255,255,255,0.04)' }}
              onClick={() => setSelectedDay(isSelected ? null : day)}
              className={`border p-1.5 text-left transition-colors relative ${isSelected ? 'border-[#219EBC]/40 bg-[rgba(33,158,188,0.08)]' : 'border-white/[0.03]'}`}
              style={{ minHeight: '80px' }}
            >
              <span
                className="text-xs font-medium"
                style={{
                  color: isSelected ? '#219EBC' : '#EDF6F9',
                  fontFamily: "'Inter Variable', Inter, sans-serif",
                }}
              >
                {day}
              </span>

              {/* Event dots/bars */}
              <div className="mt-1.5 space-y-1">
                {events.slice(0, 3).map((event) => (
                  <div
                    key={event.id}
                    className="text-[9px] truncate px-1 py-0.5 rounded"
                    style={{
                      background: `${typeColors[event.type]}20`,
                      color: typeColors[event.type],
                      fontFamily: "'Inter Variable', Inter, sans-serif",
                    }}
                  >
                    {event.title}
                  </div>
                ))}
                {events.length > 3 && (
                  <span className="text-[9px]" style={{ color: 'rgba(255,255,255,0.3)' }}>
                    +{events.length - 3} more
                  </span>
                )}
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* Event Detail Popover */}
      {selectedDay && selectedEvents.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 glass-card p-4"
        >
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-white" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
              {MONTH_NAMES[currentMonth]} {selectedDay} Events
            </h4>
            <button
              onClick={() => setSelectedDay(null)}
              className="w-6 h-6 rounded-full flex items-center justify-center hover:bg-white/[0.05] transition-colors"
            >
              <X className="w-3.5 h-3.5 text-[rgba(255,255,255,0.4)]" />
            </button>
          </div>
          <div className="space-y-2">
            {selectedEvents.map((event) => (
              <div key={event.id} className="flex items-center gap-3 p-2 rounded-lg" style={{ background: 'rgba(255,255,255,0.03)' }}>
                <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: typeColors[event.type] }} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-white truncate" style={{ fontFamily: "'Inter Variable', Inter, sans-serif" }}>
                    {event.title}
                  </p>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <Clock className="w-3 h-3" style={{ color: 'rgba(255,255,255,0.3)' }} />
                  <span className="text-[10px]" style={{ color: 'rgba(255,255,255,0.3)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                    {event.time}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
