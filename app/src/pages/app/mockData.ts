// Mock data for Kyoto 5-day trip

export interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: string;
  reasoningChain?: ReasoningStep[];
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
}

export interface ReasoningStep {
  step: number;
  description: string;
  confidence: number;
}

export interface ToolCall {
  id: string;
  name: string;
  params: Record<string, unknown>;
  result?: string;
  status: 'running' | 'completed' | 'failed';
  duration?: number;
  category: 'db' | 'api' | 'calc' | 'safety';
}

export interface POI {
  id: string;
  name: string;
  category: 'attraction' | 'restaurant' | 'hotel' | 'transport';
  lat: number;
  lng: number;
  day: number;
  badge: string;
  description: string;
  rating: number;
  timeEstimate: string;
}

export interface TimelineActivity {
  id: string;
  time: string;
  title: string;
  location: string;
  duration: string;
  notes: string;
  category: string;
}

export interface TimelineDay {
  day: number;
  title: string;
  date: string;
  activities: TimelineActivity[];
}

export interface CalendarEvent {
  id: string;
  day: number;
  title: string;
  time: string;
  type: 'attraction' | 'restaurant' | 'hotel' | 'transport' | 'activity';
  color: string;
}

export interface Metric {
  id: string;
  label: string;
  icon: string;
  score: number;
  color: string;
  description: string;
}

export interface MemoryItem {
  id: string;
  type: 'short' | 'long';
  content: string;
  source?: string;
  relevance?: number;
  timestamp?: string;
}

export interface SafetyEvent {
  id: string;
  title: string;
  description: string;
  severity: 'info' | 'warning' | 'critical';
  status: 'resolved' | 'pending' | 'requires_action';
  timestamp: string;
}

export interface ToolCallLog {
  id: string;
  timestamp: string;
  category: 'DB' | 'API' | 'CALC' | 'SAFETY';
  function: string;
  params: string;
  result: string;
  duration: number;
}

// --- Chat Messages ---
export const chatMessages: ChatMessage[] = [
  {
    id: '1',
    role: 'user',
    content: 'I want to plan a 5-day trip to Kyoto in June. My budget is around $5,000. I love temples, traditional gardens, and authentic Japanese cuisine.',
    timestamp: '10:15 AM',
  },
  {
    id: '2',
    role: 'agent',
    content: "I'd be delighted to help you plan your Kyoto adventure! Based on your preferences for temples, gardens, and cuisine, I'll create a rich 5-day itinerary for June. Let me start by gathering information about the best attractions, restaurants, and optimizing your route.",
    timestamp: '10:15 AM',
    reasoningChain: [
      { step: 1, description: 'Identify user constraints: 5 days, Kyoto, June, $5000 budget, interests in temples/gardens/cuisine', confidence: 100 },
      { step: 2, description: 'Determine optimal seasonal activities for June (early summer, hydrangea season)', confidence: 95 },
      { step: 3, description: 'Prioritize UNESCO World Heritage sites and renowned temple complexes', confidence: 90 },
      { step: 4, description: 'Select kaiseki restaurants and local food experiences matching cuisine interest', confidence: 88 },
    ],
    toolCalls: [
      {
        id: 'tc1',
        name: 'search_pois',
        params: { city: 'Kyoto', types: ['temple', 'garden', 'restaurant'], budget: 5000 },
        result: '42 POIs found: 18 temples, 12 gardens, 12 restaurants',
        status: 'completed',
        duration: 234,
        category: 'api',
      },
      {
        id: 'tc2',
        name: 'check_seasonal_events',
        params: { month: 'June', city: 'Kyoto' },
        result: 'Hydrangea season at Mimurotoji, Gion Matsuri preparations, early summer illuminations',
        status: 'completed',
        duration: 189,
        category: 'api',
      },
    ],
  },
  {
    id: '3',
    role: 'user',
    content: 'That sounds great! I also want to stay in a traditional ryokan for at least 2 nights. Can you include Arashiyama Bamboo Grove?',
    timestamp: '10:18 AM',
  },
  {
    id: '4',
    role: 'agent',
    content: "Absolutely! I've added Arashiyama Bamboo Grove to Day 3 morning, and found two beautiful ryokans for nights 1-2 in the Gion district. The ryokan experience includes a traditional kaiseki dinner and onsen bath — perfect for your interests! Here's your optimized itinerary with route planning.",
    timestamp: '10:19 AM',
    reasoningChain: [
      { step: 1, description: 'Add Arashiyama Bamboo Grove to itinerary, optimize timing for early morning visit', confidence: 96 },
      { step: 2, description: 'Search for traditional ryokans in Gion/Higashiyama area with availability', confidence: 92 },
      { step: 3, description: 'Optimize daily routes to minimize travel time between clusters', confidence: 90 },
      { step: 4, description: 'Ensure budget allocation: accommodation $1800, food $1200, transport $400, activities $1600', confidence: 85 },
    ],
    toolCalls: [
      {
        id: 'tc3',
        name: 'search_ryokans',
        params: { area: 'Gion', nights: 2, budget_per_night: 400 },
        result: '5 ryokans found: Gion Hatanaka (9.2 rating), Yuzuya Ryokan (9.0), Kyoto Garden Ryokan (8.8)',
        status: 'completed',
        duration: 312,
        category: 'db',
      },
      {
        id: 'tc4',
        name: 'optimize_route',
        params: { waypoints: ['Kinkakuji', 'Arashiyama', 'Fushimi Inari', 'Gion', 'Kiyomizudera'] },
        result: 'Optimal 5-day route: NW→West→South→East→Central clusters, 4.2km avg daily walking',
        status: 'completed',
        duration: 145,
        category: 'calc',
      },
    ],
  },
  {
    id: '5',
    role: 'user',
    content: 'Perfect! Can you also check if there are any safety considerations or travel advisories for Kyoto in June?',
    timestamp: '10:22 AM',
  },
  {
    id: '6',
    role: 'agent',
    content: "All clear for your June visit! I've checked safety conditions — there are no critical advisories for Kyoto. Weather will be mild (20-28°C) with occasional rain, so pack a light umbrella. One minor note: the Philosopher's Path has some uneven stone steps. I've also verified restaurant reservations are available for your selected kaiseki venues. Your trip is ready to finalize!",
    timestamp: '10:23 AM',
    reasoningChain: [
      { step: 1, description: 'Query safety database for Kyoto, Japan travel advisories', confidence: 98 },
      { step: 2, description: 'Check June weather patterns: rainy season, temperature range', confidence: 95 },
      { step: 3, description: 'Verify accessibility notes for attractions with mobility considerations', confidence: 92 },
      { step: 4, description: 'Confirm restaurant reservation availability for selected venues', confidence: 88 },
    ],
    toolCalls: [
      {
        id: 'tc5',
        name: 'check_safety_db',
        params: { location: 'Kyoto, Japan', month: 'June' },
        result: 'No active advisories. Weather: 20-28°C, 60% humidity, rainy season starts mid-June',
        status: 'completed',
        duration: 156,
        category: 'safety',
      },
      {
        id: 'tc6',
        name: 'check_restaurant_availability',
        params: { restaurants: ['Kikunoi Roan', 'Giro Giro Hitoshina', 'Hyotei'], dates: 'June 15-20' },
        result: 'All 3 restaurants have availability for requested dates',
        status: 'completed',
        duration: 267,
        category: 'api',
      },
    ],
  },
];

// --- POIs ---
export const pois: POI[] = [
  { id: '1', name: 'Kinkaku-ji (Golden Pavilion)', category: 'attraction', lat: 35.0394, lng: 135.7292, day: 1, badge: '1A', description: 'Iconic Zen Buddhist temple covered in gold leaf, set beside a tranquil pond.', rating: 4.8, timeEstimate: '1.5 hours' },
  { id: '2', name: 'Ryoan-ji Temple', category: 'attraction', lat: 35.0345, lng: 135.7183, day: 1, badge: '1B', description: 'Famous for its mysterious rock garden, a masterpiece of Zen art.', rating: 4.7, timeEstimate: '1 hour' },
  { id: '3', name: 'Nishiki Market', category: 'restaurant', lat: 35.0050, lng: 135.7649, day: 1, badge: '1C', description: "Kyoto's kitchen — 400-year-old market with street food and local specialties.", rating: 4.6, timeEstimate: '2 hours' },
  { id: '4', name: 'Kiyomizu-dera', category: 'attraction', lat: 34.9949, lng: 135.7850, day: 2, badge: '2A', description: 'Historic wooden temple with a large veranda overlooking the city.', rating: 4.9, timeEstimate: '2 hours' },
  { id: '5', name: 'Gion District', category: 'attraction', lat: 35.0037, lng: 135.7778, day: 2, badge: '2B', description: "Kyoto's most famous geisha district with traditional wooden machiya houses.", rating: 4.7, timeEstimate: '2 hours' },
  { id: '6', name: 'Yuzuya Ryokan', category: 'hotel', lat: 35.0010, lng: 135.7785, day: 2, badge: '2H', description: 'Traditional ryokan in Gion with tatami rooms and kaiseki dinner.', rating: 4.8, timeEstimate: 'Overnight' },
  { id: '7', name: 'Arashiyama Bamboo Grove', category: 'attraction', lat: 35.0094, lng: 135.6670, day: 3, badge: '3A', description: 'Mesmerizing bamboo forest path — one of the most photographed spots in Kyoto.', rating: 4.8, timeEstimate: '1.5 hours' },
  { id: '8', name: 'Tenryu-ji Temple', category: 'attraction', lat: 35.0158, lng: 135.6738, day: 3, badge: '3B', description: 'UNESCO World Heritage Zen temple with stunning mountain-view garden.', rating: 4.7, timeEstimate: '1.5 hours' },
  { id: '9', name: 'Fushimi Inari Shrine', category: 'attraction', lat: 34.9671, lng: 135.7727, day: 4, badge: '4A', description: 'Famous for thousands of vermilion torii gates forming tunnels up the mountain.', rating: 4.9, timeEstimate: '3 hours' },
  { id: '10', name: 'Tofuku-ji Temple', category: 'attraction', lat: 34.9764, lng: 135.7736, day: 4, badge: '4B', description: 'Spectacular zen gardens and impressive Tsutenkyo Bridge.', rating: 4.6, timeEstimate: '1.5 hours' },
  { id: '11', name: 'Philosopher\'s Path', category: 'attraction', lat: 35.0213, lng: 135.7952, day: 5, badge: '5A', description: 'Cherry-tree-lined canal path connecting Ginkaku-ji and Nanzen-ji.', rating: 4.7, timeEstimate: '2 hours' },
  { id: '12', name: 'Ginkaku-ji (Silver Pavilion)', category: 'attraction', lat: 35.0271, lng: 135.7982, day: 5, badge: '5B', description: 'Zen temple with beautiful moss garden and sand sculptures.', rating: 4.6, timeEstimate: '1.5 hours' },
];

// --- Timeline ---
export const timelineDays: TimelineDay[] = [
  {
    day: 1,
    title: 'Arrival Day — Northern Temples',
    date: 'June 15',
    activities: [
      { id: 'a1', time: '9:00 AM', title: 'Arrive at Kinkaku-ji (Golden Pavilion)', location: 'Kinkakujicho, Kita Ward', duration: '1.5 hours', notes: 'Best lighting in the morning. Entry fee: ¥400.', category: 'temple' },
      { id: 'a2', time: '11:00 AM', title: 'Visit Ryoan-ji Rock Garden', location: '13 Ryoanji Goryonoshitacho', duration: '1 hour', notes: 'UNESCO site. Take time to contemplate the rock garden.', category: 'temple' },
      { id: 'a3', time: '12:30 PM', title: 'Lunch at Omen Udon', location: 'Near Ginkakuji', duration: '1 hour', notes: 'Famous handmade udon noodles. ~¥1,200/person.', category: 'restaurant' },
      { id: 'a4', time: '2:30 PM', title: 'Explore Nishiki Market', location: 'Nakagyo Ward', duration: '2 hours', notes: 'Try yuba, matcha sweets, and pickled vegetables.', category: 'shopping' },
      { id: 'a5', time: '6:00 PM', title: 'Check-in: Yuzuya Ryokan', location: 'Gion, Higashiyama', duration: '—', notes: 'Traditional tatami room with garden view.', category: 'hotel' },
    ],
  },
  {
    day: 2,
    title: 'Eastern Temples & Gion',
    date: 'June 16',
    activities: [
      { id: 'a6', time: '6:00 AM', title: 'Sunrise at Kiyomizu-dera', location: '1-294 Kiyomizu, Higashiyama', duration: '2 hours', notes: 'Early morning offers the best atmosphere and fewer crowds.', category: 'temple' },
      { id: 'a7', time: '9:30 AM', title: 'Walk through Sannenzaka & Ninenzaka', location: 'Higashiyama', duration: '1.5 hours', notes: 'Preserved historic streets with traditional shops.', category: 'walking' },
      { id: 'a8', time: '12:00 PM', title: 'Kaiseki Lunch at Giro Giro Hitoshina', location: 'Kiyamachi-dori', duration: '1.5 hours', notes: 'Modern kaiseki at ¥4,000. Reservations required.', category: 'restaurant' },
      { id: 'a9', time: '3:00 PM', title: 'Explore Gion District', location: 'Gion, Higashiyama', duration: '2 hours', notes: 'Walk along Hanamikoji Street. Spot geiko and maiko.', category: 'culture' },
      { id: 'a10', time: '7:00 PM', title: 'Kaiseki Dinner at Ryokan', location: 'Yuzuya Ryokan', duration: '2 hours', notes: 'Multi-course traditional dinner served in-room.', category: 'restaurant' },
    ],
  },
  {
    day: 3,
    title: 'Arashiyama & Western Kyoto',
    date: 'June 17',
    activities: [
      { id: 'a11', time: '7:00 AM', title: 'Arashiyama Bamboo Grove', location: 'Arashiyama, Ukyo Ward', duration: '1.5 hours', notes: 'Arrive early to avoid crowds. Magical light filtering through bamboo.', category: 'nature' },
      { id: 'a12', time: '9:30 AM', title: 'Tenryu-ji Temple & Garden', location: '68 Saga Tenryuji Susukinobabacho', duration: '1.5 hours', notes: 'UNESCO site. Sogenchi Pond Garden is stunning.', category: 'temple' },
      { id: 'a13', time: '12:00 PM', title: 'Lunch at Shoraian', location: 'Arashiyama', duration: '1.5 hours', notes: 'Tofu cuisine in a riverside setting. ~¥3,500.', category: 'restaurant' },
      { id: 'a14', time: '3:00 PM', title: 'Togetsukyo Bridge & Monkey Park', location: 'Arashiyama', duration: '2 hours', notes: 'Great views of the Hozu River valley.', category: 'nature' },
      { id: 'a15', time: '6:00 PM', title: 'Check-in: Kyoto Garden Ryokan', location: 'Sakyo Ward', duration: '—', notes: 'Boutique ryokan with private onsen.', category: 'hotel' },
    ],
  },
  {
    day: 4,
    title: 'Southern Kyoto — Fushimi',
    date: 'June 18',
    activities: [
      { id: 'a16', time: '8:00 AM', title: 'Fushimi Inari Shrine Hike', location: 'Fushimi Ward', duration: '3 hours', notes: 'Hike to the summit for fewer crowds and city views.', category: 'temple' },
      { id: 'a17', time: '12:00 PM', title: 'Lunch at Vermillion Cafe', location: 'Fushimi', duration: '1 hour', notes: 'Cafe near the shrine gates. Great coffee.', category: 'restaurant' },
      { id: 'a18', time: '2:00 PM', title: 'Tofuku-ji Temple', location: '15-778 Hommachi, Higashiyama', duration: '1.5 hours', notes: 'Four zen gardens designed by Shigemori Mirei.', category: 'temple' },
      { id: 'a19', time: '4:30 PM', title: 'Fushimi Sake District', location: 'Fushimi Ward', duration: '2 hours', notes: 'Visit Gekkeikan Okura Sake Museum. Sake tasting included.', category: 'culture' },
      { id: 'a20', time: '7:30 PM', title: 'Dinner at Kikunoi Roan', location: '118 Saitocho, Shimogawara', duration: '2 hours', notes: '2 Michelin stars. Counter-seat kaiseki. ~¥15,000.', category: 'restaurant' },
    ],
  },
  {
    day: 5,
    title: 'Northern Higashiyama & Departure',
    date: 'June 19',
    activities: [
      { id: 'a21', time: '7:30 AM', title: 'Philosopher\'s Path Walk', location: 'Sakyo Ward', duration: '2 hours', notes: '2km stroll along the canal. June hydrangeas in bloom.', category: 'walking' },
      { id: 'a22', time: '10:00 AM', title: 'Ginkaku-ji (Silver Pavilion)', location: '2 Ginkakujicho, Sakyo Ward', duration: '1.5 hours', notes: 'Famous sand garden and moss grounds.', category: 'temple' },
      { id: 'a23', time: '12:00 PM', title: 'Lunch at Hyotei', location: '35 Kusagawacho, Nanzenji', duration: '1.5 hours', notes: '400-year-old restaurant. Legendary egg dish. ~¥8,000.', category: 'restaurant' },
      { id: 'a24', time: '2:30 PM', title: 'Nanzen-ji Temple & Aqueduct', location: 'Nanzenji Fukuchicho, Sakyo', duration: '1.5 hours', notes: 'Large zen temple with Meiji-era brick aqueduct.', category: 'temple' },
      { id: 'a25', time: '5:00 PM', title: 'Departure', location: 'Kyoto Station', duration: '—', notes: 'Take Haruka Express to Kansai Airport (75 min).', category: 'transport' },
    ],
  },
];

// --- Calendar Events ---
export const calendarEvents: CalendarEvent[] = [
  { id: 'e1', day: 15, title: 'Kinkaku-ji', time: '9:00 AM', type: 'attraction', color: '#219EBC' },
  { id: 'e2', day: 15, title: 'Ryoan-ji', time: '11:00 AM', type: 'attraction', color: '#219EBC' },
  { id: 'e3', day: 15, title: 'Nishiki Market', time: '2:30 PM', type: 'activity', color: '#FF9F1C' },
  { id: 'e4', day: 15, title: 'Ryokan Check-in', time: '6:00 PM', type: 'hotel', color: '#2EC4B6' },
  { id: 'e5', day: 16, title: 'Kiyomizu-dera', time: '6:00 AM', type: 'attraction', color: '#219EBC' },
  { id: 'e6', day: 16, title: 'Gion District', time: '3:00 PM', type: 'activity', color: '#FF9F1C' },
  { id: 'e7', day: 16, title: 'Kaiseki Dinner', time: '7:00 PM', type: 'restaurant', color: '#E29578' },
  { id: 'e8', day: 17, title: 'Bamboo Grove', time: '7:00 AM', type: 'attraction', color: '#219EBC' },
  { id: 'e9', day: 17, title: 'Tenryu-ji', time: '9:30 AM', type: 'attraction', color: '#219EBC' },
  { id: 'e10', day: 17, title: 'Togetsukyo Bridge', time: '3:00 PM', type: 'activity', color: '#FF9F1C' },
  { id: 'e11', day: 18, title: 'Fushimi Inari', time: '8:00 AM', type: 'attraction', color: '#219EBC' },
  { id: 'e12', day: 18, title: 'Tofuku-ji', time: '2:00 PM', type: 'attraction', color: '#219EBC' },
  { id: 'e13', day: 18, title: 'Kikunoi Roan', time: '7:30 PM', type: 'restaurant', color: '#E29578' },
  { id: 'e14', day: 19, title: 'Philosopher\'s Path', time: '7:30 AM', type: 'activity', color: '#FF9F1C' },
  { id: 'e15', day: 19, title: 'Ginkaku-ji', time: '10:00 AM', type: 'attraction', color: '#219EBC' },
  { id: 'e16', day: 19, title: 'Departure', time: '5:00 PM', type: 'transport', color: '#FFD166' },
];

// --- Metrics ---
export const metrics: Metric[] = [
  { id: 'm1', label: 'Constraint Satisfaction', icon: 'Target', score: 94, color: '#06D6A0', description: 'Trip constraints (budget, duration, dates) are well satisfied.' },
  { id: 'm2', label: 'Route Rationality', icon: 'Route', score: 87, color: '#06D6A0', description: 'Daily routes are geographically clustered to minimize travel time.' },
  { id: 'm3', label: 'Source Attribution', icon: 'BookOpen', score: 100, color: '#06D6A0', description: 'All facts and recommendations are properly sourced.' },
  { id: 'm4', label: 'Uncertainty Disclosure', icon: 'AlertTriangle', score: 78, color: '#FFD166', description: 'Weather forecasts and reservation availability have some uncertainty.' },
  { id: 'm5', label: 'Safety Compliance', icon: 'ShieldCheck', score: 96, color: '#06D6A0', description: 'All attractions have been verified for safety conditions.' },
];

export const overallScore = 91;

// --- Memory Items ---
export const memoryItems: MemoryItem[] = [
  { id: 'mem1', type: 'short', content: 'Destination: Kyoto, Japan' },
  { id: 'mem2', type: 'short', content: 'Dates: June 15-19, 2025 (5 days)' },
  { id: 'mem3', type: 'short', content: 'Budget: ~$5,000 USD' },
  { id: 'mem4', type: 'short', content: 'Interests: Temples, gardens, kaiseki cuisine' },
  { id: 'mem5', type: 'short', content: 'Accommodation: Ryokan preferred (2+ nights)' },
  { id: 'mem6', type: 'long', content: 'User prefers boutique hotels over chain hotels and values authentic cultural experiences.', source: 'From trip to Barcelona, March 2024', relevance: 92, timestamp: 'Mar 15, 2024' },
  { id: 'mem7', type: 'long', content: 'User enjoys early morning photography sessions at landmarks to avoid crowds.', source: 'From trip to Iceland, September 2023', relevance: 88, timestamp: 'Sep 22, 2023' },
  { id: 'mem8', type: 'long', content: 'User has dietary preference for vegetarian-friendly dining options.', source: 'From trip to Bangkok, January 2024', relevance: 72, timestamp: 'Jan 8, 2024' },
];

// --- Safety Events ---
export const safetyEvents: SafetyEvent[] = [
  { id: 's1', title: 'Kyoto Weather: June Conditions', description: 'Rainy season begins mid-June. Pack umbrella and waterproof footwear. Temperature: 20-28°C.', severity: 'info', status: 'resolved', timestamp: '10:23 AM' },
  { id: 's2', title: 'Philosopher\'s Path: Accessibility Note', description: 'Some sections have uneven stone steps. Moderate mobility required. Alternative paved route available.', severity: 'warning', status: 'pending', timestamp: '10:23 AM' },
  { id: 's3', title: 'Fushimi Inari Hike: Trail Conditions', description: 'Mountain trail to summit is steep in sections. Approx. 2-3 hours round trip. Bring water.', severity: 'info', status: 'resolved', timestamp: '10:23 AM' },
];

// --- Tool Call Logs ---
export const toolCallLogs: ToolCallLog[] = [
  { id: 'l1', timestamp: '10:23:45.234', category: 'DB', function: 'search_safety_db', params: '{"location": "Kyoto, Japan"}', result: '3 entries found', duration: 145 },
  { id: 'l2', timestamp: '10:23:47.891', category: 'API', function: 'search_pois', params: '{"city": "Kyoto", "type": "temple"}', result: '18 temples found', duration: 234 },
  { id: 'l3', timestamp: '10:23:48.123', category: 'API', function: 'search_pois', params: '{"city": "Kyoto", "type": "garden"}', result: '12 gardens found', duration: 189 },
  { id: 'l4', timestamp: '10:23:50.456', category: 'CALC', function: 'optimize_route', params: '{"waypoints": 5}', result: '4.2km avg daily', duration: 89 },
  { id: 'l5', timestamp: '10:23:51.789', category: 'DB', function: 'search_ryokans', params: '{"area": "Gion"}', result: '5 ryokans found', duration: 312 },
  { id: 'l6', timestamp: '10:23:52.012', category: 'API', function: 'check_weather', params: '{"city": "Kyoto", "dates": "June 15-19"}', result: '20-28°C, 60% humidity', duration: 156 },
  { id: 'l7', timestamp: '10:23:53.345', category: 'SAFETY', function: 'check_travel_advisory', params: '{"country": "Japan"}', result: 'No active advisories', duration: 98 },
  { id: 'l8', timestamp: '10:23:54.678', category: 'API', function: 'check_restaurant_availability', params: '{"restaurant": "Kikunoi Roan"}', result: 'Available', duration: 267 },
  { id: 'l9', timestamp: '10:23:55.901', category: 'API', function: 'check_restaurant_availability', params: '{"restaurant": "Giro Giro"}', result: 'Available', duration: 198 },
  { id: 'l10', timestamp: '10:23:56.234', category: 'CALC', function: 'budget_optimizer', params: '{"budget": 5000, "days": 5}', result: 'Allocation plan generated', duration: 67 },
  { id: 'l11', timestamp: '10:23:57.567', category: 'DB', function: 'fetch_poi_details', params: '{"poi_id": "kinkakuji"}', result: 'Details retrieved', duration: 123 },
  { id: 'l12', timestamp: '10:23:58.890', category: 'DB', function: 'fetch_poi_details', params: '{"poi_id": "fushimi_inari"}', result: 'Details retrieved', duration: 112 },
  { id: 'l13', timestamp: '10:23:59.123', category: 'API', function: 'get_seasonal_events', params: '{"month": "June"}', result: 'Hydrangea season active', duration: 178 },
  { id: 'l14', timestamp: '10:24:00.456', category: 'CALC', function: 'calculate_travel_time', params: '{"from": "Gion", "to": "Arashiyama"}', result: '35 min by train', duration: 45 },
  { id: 'l15', timestamp: '10:24:01.789', category: 'SAFETY', function: 'check_accessibility', params: '{"location": "Philosophers Path"}', result: 'Uneven stone steps noted', duration: 134 },
  { id: 'l16', timestamp: '10:24:02.012', category: 'API', function: 'fetch_reviews', params: '{"poi": "Yuzuya Ryokan"}', result: '4.8/5 from 342 reviews', duration: 256 },
];

export const quickActionChips = [
  'Budget Breakdown',
  'Timeline Adjust',
  'Preferences',
  'Transport Options',
  'Restaurant Reservations',
  'Weather Forecast',
];
