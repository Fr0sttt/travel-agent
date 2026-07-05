import type {
  CalendarEvent,
  MemoryItem,
  Metric,
  POI,
  SafetyEvent,
  TimelineActivity,
  TimelineDay,
  ToolCallLog,
} from '@/pages/app/mockData';
import type { SessionState } from './api';

export interface DashboardData {
  pois: POI[];
  timelineDays: TimelineDay[];
  calendarEvents: CalendarEvent[];
  metrics: Metric[];
  overallScore: number;
  memoryItems: MemoryItem[];
  safetyEvents: SafetyEvent[];
  toolCallLogs: ToolCallLog[];
  riskAlerts: string[];
  /** 后端返回的真实道路路径点（按段拼接），[lon, lat] 顺序，取自高德路径规划 polyline。
   * 为空时前端应退化为 POI 直线连接。 */
  routePolyline: [number, number][];
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function mapPoiCategory(category?: string): POI['category'] {
  const c = (category || '').toLowerCase();
  if (c.includes('restaurant') || c.includes('food') || c.includes('cafe')) return 'restaurant';
  if (c.includes('hotel') || c.includes('hostel') || c.includes('resort') || c.includes('homestay')) return 'hotel';
  if (c.includes('transport') || c.includes('station') || c.includes('airport')) return 'transport';
  return 'attraction';
}

function mapActivityCategory(category?: string): string {
  const c = (category || '').toLowerCase();
  if (c.includes('restaurant') || c.includes('food') || c.includes('cafe')) return 'restaurant';
  if (c.includes('hotel')) return 'hotel';
  if (c.includes('transport') || c.includes('station')) return 'transport';
  if (c.includes('natural') || c.includes('park') || c.includes('nature')) return 'nature';
  if (c.includes('historic') || c.includes('culture') || c.includes('museum') || c.includes('temple')) return 'culture';
  if (c.includes('shop') || c.includes('market')) return 'shopping';
  return 'temple';
}

function mapToolCategory(toolName: string): ToolCallLog['category'] {
  const name = toolName.toLowerCase();
  if (name.includes('search') || name.includes('geocode') || name.includes('weather') || name.includes('route')) return 'API';
  if (name.includes('db') || name.includes('memory') || name.includes('fetch_poi')) return 'DB';
  if (name.includes('safety') || name.includes('advisory') || name.includes('risk')) return 'SAFETY';
  return 'CALC';
}

function eventColor(category: string): string {
  switch (category) {
    case 'restaurant':
      return '#E29578';
    case 'hotel':
      return '#2EC4B6';
    case 'transport':
      return '#FFD166';
    case 'nature':
    case 'activity':
      return '#FF9F1C';
    default:
      return '#219EBC';
  }
}

function eventType(category: string): CalendarEvent['type'] {
  if (category === 'restaurant') return 'restaurant';
  if (category === 'hotel') return 'hotel';
  if (category === 'transport') return 'transport';
  if (category === 'nature' || category === 'activity') return 'activity';
  return 'attraction';
}

export function buildDashboardData(state: SessionState): DashboardData {
  const preference = (state.preference || {}) as Record<string, unknown>;
  const constraints = (state.constraints || {}) as Record<string, unknown>;
  const destination = String(preference.destination || '目的地');
  const durationDays = Math.max(1, Number(preference.duration_days || 3));
  const budgetCny = Number(preference.budget_cny || 0);

  const poiList = Array.isArray(state.poi_list) ? state.poi_list : [];
  const route = Array.isArray(state.route) ? state.route : [];
  const weather = Array.isArray(state.weather) ? state.weather : [];
  const totalBudget = (state.total_budget_estimate || { min: 0, max: 0 }) as { min: number; max: number };
  const riskAlerts = Array.isArray(state.risk_alerts) ? state.risk_alerts : [];
  const confirmations = Array.isArray(state.confirmation_required) ? state.confirmation_required : [];
  const toolCalls = Array.isArray(state.tool_calls) ? state.tool_calls : [];

  // POIs
  const poiCount = poiList.length;
  const basePerDay = durationDays > 0 ? Math.floor(poiCount / durationDays) : 3;
  const poisPerDay = Math.max(2, Math.min(4, basePerDay || 2));

  const pois: POI[] = poiList.map((p, idx) => {
    const coords = (p.coordinates || {}) as Record<string, number>;
    const day = Math.floor(idx / poisPerDay) + 1;
    const badgeIndex = idx % poisPerDay;
    const category = mapPoiCategory(String(p.category || ''));
    return {
      id: `poi-${idx}`,
      name: String(p.name || '未知景点'),
      category,
      lat: Number(coords.lat || 0),
      lng: Number(coords.lon || 0),
      day,
      badge: `${day}${String.fromCharCode(65 + badgeIndex)}`,
      description: String(p.description || `${destination}热门${p.category || '景点'}`),
      rating: Number(p.rating || 4.5),
      timeEstimate: '1.5 hours',
    };
  });

  // Timeline
  const timeSlots = [
    { start: '09:00', end: '11:00' },
    { start: '11:30', end: '12:30' },
    { start: '14:00', end: '16:00' },
    { start: '16:30', end: '17:30' },
    { start: '18:00', end: '19:30' },
  ];

  const timelineDays: TimelineDay[] = Array.from({ length: durationDays }, (_, dayIdx) => {
    const day = dayIdx + 1;
    const dayPois = pois.filter((p) => p.day === day);
    const dayWeather = weather[dayIdx] as Record<string, unknown> | undefined;
    const dateStr = dayWeather?.date ? String(dayWeather.date) : `Day ${day}`;
    const themeSet = new Set(dayPois.slice(0, 2).map((p) => mapActivityCategory(p.category)));
    const theme = Array.from(themeSet).join('/') || '自由探索';

    const activities: TimelineActivity[] = [];
    dayPois.slice(0, timeSlots.length).forEach((p, i) => {
      const slot = timeSlots[i];
      activities.push({
        id: `a-${day}-${i}`,
        time: `${slot.start}-${slot.end}`,
        title: p.name,
        location: destination,
        duration: p.timeEstimate,
        notes: p.description,
        category: mapActivityCategory(p.category),
      });
    });

    if (activities.length >= 2) {
      activities.splice(1, 0, {
        id: `a-${day}-lunch`,
        time: '12:00-13:00',
        title: '午餐',
        location: destination,
        duration: '1 hour',
        notes: '品尝当地美食',
        category: 'restaurant',
      });
    }
    if (activities.length >= 5) {
      activities.push({
        id: `a-${day}-dinner`,
        time: '19:30-20:30',
        title: '晚餐',
        location: destination,
        duration: '1 hour',
        notes: '推荐当地特色餐厅',
        category: 'restaurant',
      });
    }

    if (activities.length === 0) {
      activities.push({
        id: `a-${day}-free`,
        time: '全天',
        title: '自由安排',
        location: destination,
        duration: '—',
        notes: '建议探索当地特色街区和美食',
        category: 'walking',
      });
    }

    return {
      day,
      title: `${destination} - ${theme}`,
      date: dateStr,
      activities,
    };
  });

  // Calendar
  const calendarEvents: CalendarEvent[] = [];
  timelineDays.forEach((day) => {
    const dayOfMonth = Number(day.date.split('-').pop()) || day.day;
    day.activities.forEach((activity) => {
      const startTime = activity.time.split('-')[0];
      calendarEvents.push({
        id: `e-${day.day}-${activity.id}`,
        day: dayOfMonth,
        title: activity.title,
        time: startTime,
        type: eventType(activity.category),
        color: eventColor(activity.category),
      });
    });
  });

  // Metrics
  const missingFields = Array.isArray(state.missing_fields) ? state.missing_fields : [];
  const hasAllCritical = missingFields.length === 0;
  const budgetOk = budgetCny > 0 && totalBudget.max <= budgetCny;
  const constraintSatisfaction = hasAllCritical ? (budgetOk ? 96 : 82) : 65;

  const routeScore = route.length > 0 ? Math.min(95, 80 + Math.min(15, route.length * 2)) : 60;
  const uncertaintyScore = riskAlerts.length > 0 ? 78 : 92;
  const safetyScore = confirmations.some((c) => (c as Record<string, unknown>).requires_confirmation) ? 72 : 96;

  const metrics: Metric[] = [
    {
      id: 'm1',
      label: 'Constraint Satisfaction',
      icon: 'Target',
      score: constraintSatisfaction,
      color: constraintSatisfaction >= 90 ? '#06D6A0' : '#FFD166',
      description: hasAllCritical
        ? `Trip constraints (${budgetCny ? `budget ¥${budgetCny}, ` : ''}${durationDays} days) analyzed.`
        : `Missing preferences: ${missingFields.join(', ')}.`,
    },
    {
      id: 'm2',
      label: 'Route Rationality',
      icon: 'Route',
      score: routeScore,
      color: routeScore >= 80 ? '#06D6A0' : '#FFD166',
      description: route.length > 0
        ? `Route optimized across ${route.length + 1} POIs.`
        : 'Route data not available.',
    },
    {
      id: 'm3',
      label: 'Source Attribution',
      icon: 'BookOpen',
      score: 100,
      color: '#06D6A0',
      description: 'Data sourced from OpenTripMap, OpenStreetMap, Open-Meteo and OSRM.',
    },
    {
      id: 'm4',
      label: 'Uncertainty Disclosure',
      icon: 'AlertTriangle',
      score: uncertaintyScore,
      color: uncertaintyScore >= 90 ? '#06D6A0' : '#FFD166',
      description: riskAlerts.length > 0
        ? `${riskAlerts.length} weather/budget advisory note(s) disclosed.`
        : 'No outstanding uncertainty alerts.',
    },
    {
      id: 'm5',
      label: 'Safety Compliance',
      icon: 'ShieldCheck',
      score: safetyScore,
      color: safetyScore >= 90 ? '#06D6A0' : '#E29578',
      description: safetyScore >= 90
        ? 'No high-risk actions requiring confirmation.'
        : 'High-risk action detected; human confirmation required.',
    },
  ];

  const overallScore = Math.round(metrics.reduce((sum, m) => sum + m.score, 0) / metrics.length);

  // Memory
  const memoryItems: MemoryItem[] = [];
  const now = formatTime(new Date());
  if (preference.destination) {
    memoryItems.push({ id: 'mem-dest', type: 'short', content: `Destination: ${preference.destination}` });
  }
  if (preference.travel_dates) {
    const dates = preference.travel_dates as Record<string, string>;
    memoryItems.push({ id: 'mem-dates', type: 'short', content: `Dates: ${dates.start || ''} ~ ${dates.end || ''}` });
  }
  if (preference.budget_cny) {
    memoryItems.push({ id: 'mem-budget', type: 'short', content: `Budget: ¥${preference.budget_cny}` });
  }
  if (Array.isArray(preference.interests) && preference.interests.length > 0) {
    memoryItems.push({
      id: 'mem-interests',
      type: 'short',
      content: `Interests: ${preference.interests.join(', ')}`,
    });
  }
  if (preference.companions) {
    memoryItems.push({ id: 'mem-companions', type: 'short', content: `Companions: ${preference.companions}` });
  }
  if (preference.accommodation_type) {
    memoryItems.push({
      id: 'mem-accommodation',
      type: 'short',
      content: `Accommodation: ${preference.accommodation_type}`,
    });
  }
  const implicitNeeds = Array.isArray(constraints.implicit_needs) ? constraints.implicit_needs : [];
  implicitNeeds.forEach((need: unknown, idx: number) => {
    memoryItems.push({
      id: `mem-implicit-${idx}`,
      type: 'long',
      content: String(need),
      source: 'Derived from constraints',
      relevance: 85,
      timestamp: now,
    });
  });

  // Safety
  const safetyEvents: SafetyEvent[] = [
    ...riskAlerts.map((alert, idx) => ({
      id: `risk-${idx}`,
      title: alert.split('，')[0] || 'Travel Advisory',
      description: alert,
      severity: (alert.includes('超出预算') ? 'warning' : 'info') as SafetyEvent['severity'],
      status: 'pending' as const,
      timestamp: now,
    })),
    ...confirmations.map((c, idx) => {
      const item = c as Record<string, unknown>;
      const requires = Boolean(item.requires_confirmation);
      return {
        id: `confirm-${idx}`,
        title: String(item.type || 'Confirmation Item'),
        description: String(item.message || ''),
        severity: (requires ? 'critical' : 'info') as SafetyEvent['severity'],
        status: (requires ? 'requires_action' : 'resolved') as SafetyEvent['status'],
        timestamp: now,
      };
    }),
  ];

  // Tool call logs
  const toolCallLogs: ToolCallLog[] = toolCalls.map((tc, idx) => {
    const call = tc as Record<string, unknown>;
    const ts = String(call.timestamp || new Date().toISOString());
    return {
      id: `log-${idx}`,
      timestamp: new Date(ts).toLocaleTimeString('en-GB', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }) + `.${String(new Date(ts).getMilliseconds()).padStart(3, '0')}`,
      category: mapToolCategory(String(call.tool_name || '')),
      function: String(call.tool_name || 'unknown'),
      params: JSON.stringify(call.input || {}),
      result: call.success === false
        ? `Error: ${call.error_message || 'failed'}`
        : JSON.stringify(call.output || {}),
      duration: Number(call.latency_ms || 0),
    };
  });

  // 真实道路路径：把每段 route 里高德返回的 polyline 坐标依次拼接。
  // route_planner 按贪心排序生成的每一段都带 polyline（若高德可用），
  // 拼起来就是整条行程的实际道路轨迹，而不是 POI 两两直连。
  const routePolyline: [number, number][] = [];
  route.forEach((segment) => {
    const seg = segment as Record<string, unknown>;
    const points = Array.isArray(seg.polyline) ? seg.polyline : [];
    points.forEach((point) => {
      if (Array.isArray(point) && point.length === 2) {
        const lon = Number(point[0]);
        const lat = Number(point[1]);
        if (Number.isFinite(lon) && Number.isFinite(lat)) {
          routePolyline.push([lon, lat]);
        }
      }
    });
  });

  return {
    pois,
    timelineDays,
    calendarEvents,
    metrics,
    overallScore,
    memoryItems,
    safetyEvents,
    toolCallLogs,
    riskAlerts,
    routePolyline,
  };
}
