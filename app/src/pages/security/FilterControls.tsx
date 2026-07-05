import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { severityLabels, statusLabels } from './data';

export type SeverityFilter = 'All' | 'Critical' | 'High' | 'Medium' | 'Low';
export type StatusFilter = 'All' | 'Pending' | 'Resolved' | 'Dismissed';
export type DateRange = '7days' | '30days' | 'custom';

interface FilterControlsProps {
  severityFilter: SeverityFilter;
  setSeverityFilter: (v: SeverityFilter) => void;
  statusFilter: StatusFilter;
  setStatusFilter: (v: StatusFilter) => void;
  dateRange: DateRange;
  setDateRange: (v: DateRange) => void;
  searchQuery: string;
  setSearchQuery: (v: string) => void;
}

const severities: SeverityFilter[] = ['All', 'Critical', 'High', 'Medium', 'Low'];
const statuses: StatusFilter[] = ['All', 'Pending', 'Resolved', 'Dismissed'];
const dateRanges: { key: DateRange; label: string }[] = [
  { key: '7days', label: '过去7天' },
  { key: '30days', label: '过去30天' },
  { key: 'custom', label: '自定义' },
];

export default function FilterControls({
  severityFilter,
  setSeverityFilter,
  statusFilter,
  setStatusFilter,
  dateRange,
  setDateRange,
  searchQuery,
  setSearchQuery,
}: FilterControlsProps) {
  const pillBase =
    'px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 cursor-pointer border';
  const pillInactive =
    'border-white/[0.08] text-[rgba(255,255,255,0.5)] hover:text-white hover:border-white/[0.15]';
  const pillActive = 'text-white border-[#219EBC]/50';

  return (
    <div className="flex flex-wrap items-center gap-3 mb-5">
      {/* Search */}
      <div className="relative w-[220px]">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgba(255,255,255,0.3)]" />
        <Input
          placeholder="搜索事件..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="h-9 pl-9 rounded-lg text-sm border-white/[0.08] bg-white/[0.06] text-white placeholder:text-[rgba(255,255,255,0.3)] focus:border-[#219EBC]/50 focus:ring-1 focus:ring-[#219EBC]/30"
        />
      </div>

      <div className="w-px h-6 bg-white/[0.08] hidden sm:block" />

      {/* Severity Filter */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-[rgba(255,255,255,0.3)] mr-1">严重程度</span>
        {severities.map((s) => (
          <button
            key={s}
            onClick={() => setSeverityFilter(s)}
            className={`${pillBase} ${severityFilter === s ? pillActive : pillInactive}`}
            style={
              severityFilter === s
                ? { background: 'rgba(33,158,188,0.15)' }
                : { background: 'transparent' }
            }
          >
            {s === 'All' ? '全部' : severityLabels[s]}
          </button>
        ))}
      </div>

      <div className="w-px h-6 bg-white/[0.08] hidden sm:block" />

      {/* Status Filter */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-[rgba(255,255,255,0.3)] mr-1">状态</span>
        {statuses.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`${pillBase} ${statusFilter === s ? pillActive : pillInactive}`}
            style={
              statusFilter === s
                ? { background: 'rgba(33,158,188,0.15)' }
                : { background: 'transparent' }
            }
          >
            {s === 'All' ? '全部' : statusLabels[s]}
          </button>
        ))}
      </div>

      <div className="w-px h-6 bg-white/[0.08] hidden sm:block" />

      {/* Date Range */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-[rgba(255,255,255,0.3)] mr-1">范围</span>
        {dateRanges.map((d) => (
          <button
            key={d.key}
            onClick={() => setDateRange(d.key)}
            className={`${pillBase} ${dateRange === d.key ? pillActive : pillInactive}`}
            style={
              dateRange === d.key
                ? { background: 'rgba(33,158,188,0.15)' }
                : { background: 'transparent' }
            }
          >
            {d.label}
          </button>
        ))}
      </div>
    </div>
  );
}
