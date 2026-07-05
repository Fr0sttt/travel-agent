import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle,
  Clock,
  ChevronRight,
} from 'lucide-react';
import StatCard from './security/StatCard';
import FilterControls from './security/FilterControls';
import type { SeverityFilter, StatusFilter, DateRange } from './security/FilterControls';
import EventTimeline from './security/EventTimeline';
import EventDetailPanel from './security/EventDetailPanel';
import ComplianceChart from './security/ComplianceChart';
import SecurityPolicies from './security/SecurityPolicies';
import { mockEvents } from './security/data';
import type { SecurityEvent, Status } from './security/data';

export default function Security() {
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('All');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('All');
  const [dateRange, setDateRange] = useState<DateRange>('30days');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEvent, setSelectedEvent] = useState<SecurityEvent | null>(null);
  const [events, setEvents] = useState<SecurityEvent[]>(mockEvents);

  // Stats
  const stats = useMemo(() => {
    const threatsBlocked = events.filter(
      (e) => e.severity === 'Critical' || e.severity === 'High'
    ).length;
    const pendingReviews = events.filter((e) => e.status === 'Pending').length;
    const policiesEnforced = 24;
    const complianceScore = 98.5;
    return { threatsBlocked, pendingReviews, policiesEnforced, complianceScore };
  }, [events]);

  // Filtered events
  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      if (severityFilter !== 'All' && event.severity !== severityFilter) return false;
      if (statusFilter !== 'All' && event.status !== statusFilter) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return (
          event.title.toLowerCase().includes(q) ||
          event.description.toLowerCase().includes(q) ||
          event.category.toLowerCase().includes(q) ||
          event.id.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [events, severityFilter, statusFilter, searchQuery]);

  const handleStatusChange = (id: string, newStatus: Status) => {
    setEvents((prev) =>
      prev.map((e) => (e.id === id ? { ...e, status: newStatus } : e))
    );
    setSelectedEvent((prev) =>
      prev && prev.id === id ? { ...prev, status: newStatus } : prev
    );
  };

  return (
    <div
      className="min-h-[100dvh] w-full"
      style={{
        background: '#0A2463',
      }}
    >
      {/* Subtle grid pattern overlay */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
          zIndex: 0,
        }}
      />

      <div className="relative z-10">
        {/* Header Section */}
        <section className="max-w-[1400px] mx-auto px-6 pt-16 pb-10">
          {/* Breadcrumb */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex items-center gap-2 text-sm mb-4"
            style={{ color: 'rgba(255,255,255,0.4)' }}
          >
            <span>仪表盘</span>
            <ChevronRight className="w-3.5 h-3.5" />
            <span>安全</span>
          </motion.div>

          {/* Title */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.05 }}
            className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight"
            style={{
              color: '#FFFFFF',
              fontFamily: "'Outfit Variable', Outfit, sans-serif",
            }}
          >
            安全与合规中心
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-lg mt-3 max-w-[700px] leading-relaxed"
            style={{ color: 'rgba(255,255,255,0.6)' }}
          >
            监控安全检查、审查安全事件，并管理您的 AI 旅行代理的合规设置。
          </motion.p>

          {/* Last audit badge */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-mono"
            style={{
              background: 'rgba(255,255,255,0.06)',
              color: '#2EC4B6',
            }}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            最后审计: 2小时前
          </motion.div>

          {/* Stat Cards */}
          <div className="flex flex-col sm:flex-row gap-5 mt-10">
            <StatCard
              icon={ShieldCheck}
              iconColor="#2EC4B6"
              iconBgColor="rgba(46,196,182,0.15)"
              value={stats.complianceScore}
              suffix="%"
              label="安全合规分数"
              trend="+2% 本月"
              trendColor="#06D6A0"
              index={0}
            />
            <StatCard
              icon={AlertTriangle}
              iconColor="#FFD166"
              iconBgColor="rgba(255,209,102,0.15)"
              value={stats.pendingReviews}
              label="活跃告警"
              trend="需要行动"
              trendColor="#EF476F"
              index={1}
            />
            <StatCard
              icon={CheckCircle}
              iconColor="#219EBC"
              iconBgColor="rgba(33,158,188,0.15)"
              value={stats.threatsBlocked}
              label="今日阻止威胁"
              trend="+12% 本周"
              trendColor="#06D6A0"
              index={2}
            />
            <StatCard
              icon={Clock}
              iconColor="#E29578"
              iconBgColor="rgba(226,149,120,0.15)"
              value={stats.policiesEnforced}
              label="执行的策略"
              trend="全部活跃"
              trendColor="#06D6A0"
              index={3}
            />
          </div>
        </section>

        {/* Main Content: Timeline + Detail Panel */}
        <section className="max-w-[1400px] mx-auto px-6 py-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            {/* Section header */}
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2
                  className="text-2xl sm:text-3xl font-semibold tracking-tight"
                  style={{
                    color: '#FFFFFF',
                    fontFamily: "'Outfit Variable', Outfit, sans-serif",
                  }}
                >
                  安全事件
                </h2>
                <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
                  找到 {filteredEvents.length} 个事件{filteredEvents.length !== 1 ? '们' : ''}
                </p>
              </div>
            </div>

            {/* Filters */}
            <FilterControls
              severityFilter={severityFilter}
              setSeverityFilter={setSeverityFilter}
              statusFilter={statusFilter}
              setStatusFilter={setStatusFilter}
              dateRange={dateRange}
              setDateRange={setDateRange}
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
            />

            {/* Two-column layout */}
            <div className="flex flex-col lg:flex-row gap-6 mt-4">
              {/* Event Timeline */}
              <div className="w-full lg:w-[55%]">
                <EventTimeline
                  events={filteredEvents}
                  selectedEvent={selectedEvent}
                  onSelectEvent={setSelectedEvent}
                  onStatusChange={handleStatusChange}
                />
              </div>

              {/* Event Detail Panel */}
              <div className="w-full lg:w-[45%] min-h-[500px]">
                <EventDetailPanel event={selectedEvent} />
              </div>
            </div>
          </motion.div>
        </section>

        {/* Compliance Chart */}
        <section className="max-w-[1400px] mx-auto px-6 py-10">
          <ComplianceChart />
        </section>

        {/* Security Policies */}
        <section className="max-w-[1400px] mx-auto px-6 py-10 pb-20">
          <SecurityPolicies />
        </section>
      </div>
    </div>
  );
}
