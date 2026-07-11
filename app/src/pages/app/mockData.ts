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
  hardFailures?: string[];
  judgeReason?: string;
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
    content: '我想计划一次5天的京都之旅，时间在6月份。预算大约5000美元。我喜欢寺庙、传统花园和正宗的日本料理。',
    timestamp: '10:15 AM',
  },
  {
    id: '2',
    role: 'agent',
    content: "我很乐意为您规划京都之行！根据您对寺庙、花园和美食的偏好，我将为6月制作一份丰富的5天行程。让我先收集关于最佳景点、餐厅的信息，并优化您的路线。",
    timestamp: '10:15 AM',
    reasoningChain: [
      { step: 1, description: '识别用户约束：5天、京都、6月、$5000预算、对寺庙/花园/美食感兴趣', confidence: 100 },
      { step: 2, description: '确定6月的最佳季节活动（初夏、绣球花季节）', confidence: 95 },
      { step: 3, description: '优先考虑联合国教科文组织世界遗产地和著名寺庙群', confidence: 90 },
      { step: 4, description: '选择与美食兴趣相匹配的怀石料理餐厅和本地美食体验', confidence: 88 },
    ],
    toolCalls: [
      {
        id: 'tc1',
        name: 'search_pois',
        params: { city: 'Kyoto', types: ['temple', 'garden', 'restaurant'], budget: 5000 },
        result: '发现42个景点：18座寺庙、12座花园、12家餐厅',
        status: 'completed',
        duration: 234,
        category: 'api',
      },
      {
        id: 'tc2',
        name: 'check_seasonal_events',
        params: { month: 'June', city: 'Kyoto' },
        result: '6月京都的绣球花季在三室户寺，祇园祭准备，初夏灯光秀',
        status: 'completed',
        duration: 189,
        category: 'api',
      },
    ],
  },
  {
    id: '3',
    role: 'user',
    content: '听起来太好了！我还想在传统旅馆住至少2晚。你能把嵯峨野竹林加进去吗？',
    timestamp: '10:18 AM',
  },
  {
    id: '4',
    role: 'agent',
    content: "当然！我已经在第3天上午把嵯峨野竹林加入了行程，并找到了两家漂亮的旅馆在祇园地区的第1-2晚。旅馆体验包括传统怀石晚餐和温泉浴——完全符合您的兴趣！这是您的优化行程和路线规划。",
    timestamp: '10:19 AM',
    reasoningChain: [
      { step: 1, description: '将嵯峨野竹林加入行程，优化早晨游览时间', confidence: 96 },
      { step: 2, description: '在祇园/东山地区搜索传统旅馆并确认可用性', confidence: 92 },
      { step: 3, description: '优化每日路线以最小化景点间的交通时间', confidence: 90 },
      { step: 4, description: '确保预算分配：住宿$1800、饮食$1200、交通$400、活动$1600', confidence: 85 },
    ],
    toolCalls: [
      {
        id: 'tc3',
        name: 'search_ryokans',
        params: { area: 'Gion', nights: 2, budget_per_night: 400 },
        result: '发现5家旅馆：祇园半中(评分9.2)、Yuzuya旅馆(评分9.0)、京都花园旅馆(评分8.8)',
        status: 'completed',
        duration: 312,
        category: 'db',
      },
      {
        id: 'tc4',
        name: 'optimize_route',
        params: { waypoints: ['Kinkakuji', 'Arashiyama', 'Fushimi Inari', 'Gion', 'Kiyomizudera'] },
        result: '最优5天路线：西北→西→南→东→中心片区，平均每日行走4.2公里',
        status: 'completed',
        duration: 145,
        category: 'calc',
      },
    ],
  },
  {
    id: '5',
    role: 'user',
    content: '完美！你能也检查一下6月份京都有没有安全问题或旅行警告吗？',
    timestamp: '10:22 AM',
  },
  {
    id: '6',
    role: 'agent',
    content: "您6月访京都一切安全！我已检查安全状况——京都没有重大旅行警告。天气温和(20-28°C)，偶有降雨，建议携带轻薄雨伞。一个小提示：哲学家之路有一些不平整的石阶。我已确认您选择的怀石餐厅都可预订。您的旅行已准备好最终确认！",
    timestamp: '10:23 AM',
    reasoningChain: [
      { step: 1, description: '查询京都、日本旅行警告的安全数据库', confidence: 98 },
      { step: 2, description: '检查6月天气模式：雨季、温度范围', confidence: 95 },
      { step: 3, description: '验证景点的无障碍注意事项和行动能力考量', confidence: 92 },
      { step: 4, description: '确认选定怀石餐厅的预订可用性', confidence: 88 },
    ],
    toolCalls: [
      {
        id: 'tc5',
        name: 'check_safety_db',
        params: { location: 'Kyoto, Japan', month: 'June' },
        result: '无现役警告。天气：20-28°C，湿度60%，雨季从6月中旬开始',
        status: 'completed',
        duration: 156,
        category: 'safety',
      },
      {
        id: 'tc6',
        name: 'check_restaurant_availability',
        params: { restaurants: ['Kikunoi Roan', 'Giro Giro Hitoshina', 'Hyotei'], dates: 'June 15-20' },
        result: '所有3家餐厅在指定日期都有可用位置',
        status: 'completed',
        duration: 267,
        category: 'api',
      },
    ],
  },
];

// --- POIs ---
export const pois: POI[] = [
  { id: '1', name: 'Kinkaku-ji (金阁寺)', category: 'attraction', lat: 35.0394, lng: 135.7292, day: 1, badge: '1A', description: '标志性禅宗寺庙，金叶覆盖，坐落在宁静的池塘旁。', rating: 4.8, timeEstimate: '1.5小时' },
  { id: '2', name: 'Ryoan-ji Temple(龙安寺)', category: 'attraction', lat: 35.0345, lng: 135.7183, day: 1, badge: '1B', description: '以神秘的岩石花园闻名，是禅宗艺术的杰作。', rating: 4.7, timeEstimate: '1小时' },
  { id: '3', name: 'Nishiki Market(锦市场)', category: 'restaurant', lat: 35.0050, lng: 135.7649, day: 1, badge: '1C', description: "京都的厨房——400年历史的市场，汇集街头美食和本地特色。", rating: 4.6, timeEstimate: '2小时' },
  { id: '4', name: 'Kiyomizu-dera(清水寺)', category: 'attraction', lat: 34.9949, lng: 135.7850, day: 2, badge: '2A', description: '历史悠久的木结构寺庙，有俯瞰城市的宽阔平台。', rating: 4.9, timeEstimate: '2小时' },
  { id: '5', name: 'Gion District(祇园)', category: 'attraction', lat: 35.0037, lng: 135.7778, day: 2, badge: '2B', description: "京都最著名的艺伎区，有传统木制町屋建筑。", rating: 4.7, timeEstimate: '2小时' },
  { id: '6', name: 'Yuzuya Ryokan(柚子屋旅馆)', category: 'hotel', lat: 35.0010, lng: 135.7785, day: 2, badge: '2H', description: '祇园传统旅馆，榻榻米房间和怀石晚餐。', rating: 4.8, timeEstimate: '整晚' },
  { id: '7', name: 'Arashiyama Bamboo Grove(嵯峨野竹林)', category: 'attraction', lat: 35.0094, lng: 135.6670, day: 3, badge: '3A', description: '迷人的竹林小径——京都最上镜的景点之一。', rating: 4.8, timeEstimate: '1.5小时' },
  { id: '8', name: 'Tenryu-ji Temple(天龙寺)', category: 'attraction', lat: 35.0158, lng: 135.6738, day: 3, badge: '3B', description: '联合国教科文组织世界遗产禅宗寺庙，有绝妙的山景花园。', rating: 4.7, timeEstimate: '1.5小时' },
  { id: '9', name: 'Fushimi Inari Shrine(伏见稻荷大社)', category: 'attraction', lat: 34.9671, lng: 135.7727, day: 4, badge: '4A', description: '以数千个朱红色鸟居隧道闻名，蜿蜒上山。', rating: 4.9, timeEstimate: '3小时' },
  { id: '10', name: 'Tofuku-ji Temple(东福寺)', category: 'attraction', lat: 34.9764, lng: 135.7736, day: 4, badge: '4B', description: '壮观的禅宗花园和雄伟的通天桥。', rating: 4.6, timeEstimate: '1.5小时' },
  { id: '11', name: 'Philosopher\'s Path(哲学家之路)', category: 'attraction', lat: 35.0213, lng: 135.7952, day: 5, badge: '5A', description: '樱花树林立的运河小径，连接银阁寺和南禅寺。', rating: 4.7, timeEstimate: '2小时' },
  { id: '12', name: 'Ginkaku-ji (Silver Pavilion)(银阁寺)', category: 'attraction', lat: 35.0271, lng: 135.7982, day: 5, badge: '5B', description: '禅宗寺庙，有美丽的苔藓花园和沙雕。', rating: 4.6, timeEstimate: '1.5小时' },
];

// --- Timeline ---
export const timelineDays: TimelineDay[] = [
  {
    day: 1,
    title: '抵达日 — 北部寺庙',
    date: '6月15日',
    activities: [
      { id: 'a1', time: '9:00 AM', title: '抵达金阁寺', location: '北区金阁寺町', duration: '1.5小时', notes: '早上光线最好。门票：¥400。', category: 'temple' },
      { id: 'a2', time: '11:00 AM', title: '龙安寺岩石花园', location: '龙安寺御陵下町13号', duration: '1小时', notes: '联合国教科文组织遗产地。花时间冥想岩石花园。', category: 'temple' },
      { id: 'a3', time: '12:30 PM', title: '中午在Omen乌冬面', location: '银阁寺附近', duration: '1小时', notes: '著名手工乌冬面。约¥1,200/人。', category: 'restaurant' },
      { id: 'a4', time: '2:30 PM', title: '探索锦市场', location: '中京区', duration: '2小时', notes: '尝试豆腐皮、抹茶糕点和腌制蔬菜。', category: 'shopping' },
      { id: 'a5', time: '6:00 PM', title: '入住：柚子屋旅馆', location: '祇园、东山', duration: '—', notes: '传统榻榻米房间，有花园景观。', category: 'hotel' },
    ],
  },
  {
    day: 2,
    title: '东部寺庙和祇园',
    date: '6月16日',
    activities: [
      { id: 'a6', time: '6:00 AM', title: '清水寺日出', location: '东山区清水1-294', duration: '2小时', notes: '早晨气氛最佳，人也较少。', category: 'temple' },
      { id: 'a7', time: '9:30 AM', title: '散步三年坂和二年坂', location: '东山', duration: '1.5小时', notes: '保存完好的历史街道，传统店铺。', category: 'walking' },
      { id: 'a8', time: '12:00 PM', title: '怀石午餐在Giro Giro Hitoshina', location: '清水町通', duration: '1.5小时', notes: '现代怀石料理，¥4,000。需要预订。', category: 'restaurant' },
      { id: 'a9', time: '3:00 PM', title: '探索祇园区', location: '祇园、东山', duration: '2小时', notes: '在花见小路散步。看艺妓和舞妓。', category: 'culture' },
      { id: 'a10', time: '7:00 PM', title: '旅馆怀石晚餐', location: '柚子屋旅馆', duration: '2小时', notes: '多道菜式传统晚餐，在房间内享用。', category: 'restaurant' },
    ],
  },
  {
    day: 3,
    title: '嵯峨野和西京都',
    date: '6月17日',
    activities: [
      { id: 'a11', time: '7:00 AM', title: '嵯峨野竹林', location: '京都市右京区嵯峨', duration: '1.5小时', notes: '早到避免人群。竹子间的光线魔幻。', category: 'nature' },
      { id: 'a12', time: '9:30 AM', title: '天龙寺和花园', location: '68号嵯峨天龙寺须磨之場町', duration: '1.5小时', notes: '联合国教科文组织遗产地。泷月池花园壮观。', category: 'temple' },
      { id: 'a13', time: '12:00 PM', title: '在Shoraian午餐', location: '嵯峨野', duration: '1.5小时', notes: '河边豆腐料理。约¥3,500。', category: 'restaurant' },
      { id: 'a14', time: '3:00 PM', title: '渡月桥和猴子公园', location: '嵯峨野', duration: '2小时', notes: '保津川谷的绝妙景色。', category: 'nature' },
      { id: 'a15', time: '6:00 PM', title: '入住：京都花园旅馆', location: '左京区', duration: '—', notes: '精品旅馆，有私人温泉。', category: 'hotel' },
    ],
  },
  {
    day: 4,
    title: '南京都 — 伏见',
    date: '6月18日',
    activities: [
      { id: 'a16', time: '8:00 AM', title: '伏见稻荷大社登顶', location: '伏见区', duration: '3小时', notes: '登山顶部以看到更少人群和城市景色。', category: 'temple' },
      { id: 'a17', time: '12:00 PM', title: '在朱雀咖啡厅午餐', location: '伏见', duration: '1小时', notes: '神社门附近的咖啡厅。很棒的咖啡。', category: 'restaurant' },
      { id: 'a18', time: '2:00 PM', title: '东福寺', location: '东山区本町15-778', duration: '1.5小时', notes: '四个禅宗花园由Shigemori Mirei设计。', category: 'temple' },
      { id: 'a19', time: '4:30 PM', title: '伏见酒区', location: '伏见区', duration: '2小时', notes: '参观月桂冠大仓酒博物馆。包括品酒。', category: 'culture' },
      { id: 'a20', time: '7:30 PM', title: '在菊乃在怀石晚餐', location: '118号Saitocho，下河原', duration: '2小时', notes: '米其林2星。吧台怀石。约¥15,000。', category: 'restaurant' },
    ],
  },
  {
    day: 5,
    title: '北东山和离开',
    date: '6月19日',
    activities: [
      { id: 'a21', time: '7:30 AM', title: '哲学家之路散步', location: '左京区', duration: '2小时', notes: '沿运河2公里散步。6月绣球花盛开。', category: 'walking' },
      { id: 'a22', time: '10:00 AM', title: '银阁寺', location: '左京区银阁寺町2号', duration: '1.5小时', notes: '著名沙池花园和苔藓地。', category: 'temple' },
      { id: 'a23', time: '12:00 PM', title: '在Hyotei午餐', location: '草川町35号，南禅寺', duration: '1.5小时', notes: '400年历史餐厅。传奇鸡蛋菜。约¥8,000。', category: 'restaurant' },
      { id: 'a24', time: '2:30 PM', title: '南禅寺和水渠', location: '南禅寺福地町，左京', duration: '1.5小时', notes: '大型禅宗寺庙，配明治时代砖砌水渠。', category: 'temple' },
      { id: 'a25', time: '5:00 PM', title: '离开', location: '京都站', duration: '—', notes: '乘坐Haruka快车到关西机场(75分钟)。', category: 'transport' },
    ],
  },
];

// --- 日历事件 ---
export const calendarEvents: CalendarEvent[] = [
  { id: 'e1', day: 15, title: '金阁寺', time: '9:00 AM', type: 'attraction', color: '#219EBC' },
  { id: 'e2', day: 15, title: '龙安寺', time: '11:00 AM', type: 'attraction', color: '#219EBC' },
  { id: 'e3', day: 15, title: '锦市场', time: '2:30 PM', type: 'activity', color: '#FF9F1C' },
  { id: 'e4', day: 15, title: '旅馆入住', time: '6:00 PM', type: 'hotel', color: '#2EC4B6' },
  { id: 'e5', day: 16, title: '清水寺', time: '6:00 AM', type: 'attraction', color: '#219EBC' },
  { id: 'e6', day: 16, title: '祇园区', time: '3:00 PM', type: 'activity', color: '#FF9F1C' },
  { id: 'e7', day: 16, title: '怀石晚餐', time: '7:00 PM', type: 'restaurant', color: '#E29578' },
  { id: 'e8', day: 17, title: '竹林', time: '7:00 AM', type: 'attraction', color: '#219EBC' },
  { id: 'e9', day: 17, title: '天龙寺', time: '9:30 AM', type: 'attraction', color: '#219EBC' },
  { id: 'e10', day: 17, title: '渡月桥', time: '3:00 PM', type: 'activity', color: '#FF9F1C' },
  { id: 'e11', day: 18, title: '伏见稻荷', time: '8:00 AM', type: 'attraction', color: '#219EBC' },
  { id: 'e12', day: 18, title: '东福寺', time: '2:00 PM', type: 'attraction', color: '#219EBC' },
  { id: 'e13', day: 18, title: '菊乃在', time: '7:30 PM', type: 'restaurant', color: '#E29578' },
  { id: 'e14', day: 19, title: '哲学家之路', time: '7:30 AM', type: 'activity', color: '#FF9F1C' },
  { id: 'e15', day: 19, title: '银阁寺', time: '10:00 AM', type: 'attraction', color: '#219EBC' },
  { id: 'e16', day: 19, title: '离开', time: '5:00 PM', type: 'transport', color: '#FFD166' },
];

// --- 指标 ---
export const metrics: Metric[] = [
  { id: 'm1', label: '约束满足度', icon: 'Target', score: 94, color: '#06D6A0', description: '行程约束(预算、时长、日期)得到很好满足。' },
  { id: 'm2', label: '路线合理性', icon: 'Route', score: 87, color: '#06D6A0', description: '日程路线在地理上聚集，最小化交通时间。' },
  { id: 'm3', label: '来源可溯性', icon: 'BookOpen', score: 100, color: '#06D6A0', description: '所有事实和建议都有适当的来源。' },
  { id: 'm4', label: '不确定性披露', icon: 'AlertTriangle', score: 78, color: '#FFD166', description: '天气预报和预订可用性存在一定的不确定性。' },
  { id: 'm5', label: '安全合规性', icon: 'ShieldCheck', score: 96, color: '#06D6A0', description: '所有景点都已验证了安全条件。' },
];

export const overallScore = 91;

// --- 记忆项 ---
export const memoryItems: MemoryItem[] = [
  { id: 'mem1', type: 'short', content: '目的地：日本京都' },
  { id: 'mem2', type: 'short', content: '日期：2025年6月15-19日(5天)' },
  { id: 'mem3', type: 'short', content: '预算：约$5,000美元' },
  { id: 'mem4', type: 'short', content: '兴趣：寺庙、花园、怀石料理' },
  { id: 'mem5', type: 'short', content: '住宿：优先传统旅馆(2晚以上)' },
  { id: 'mem6', type: 'long', content: '用户偏好精品酒店而非连锁酒店，重视真实的文化体验。', source: '来自2024年3月的巴塞罗那之旅', relevance: 92, timestamp: '2024年3月15日' },
  { id: 'mem7', type: 'long', content: '用户喜欢在地标早晨进行摄影，避免人群。', source: '来自2023年9月的冰岛之旅', relevance: 88, timestamp: '2023年9月22日' },
  { id: 'mem8', type: 'long', content: '用户有素食友好的饮食偏好。', source: '来自2024年1月的曼谷之旅', relevance: 72, timestamp: '2024年1月8日' },
];

// --- 安全事件 ---
export const safetyEvents: SafetyEvent[] = [
  { id: 's1', title: '京都天气：6月状况', description: '6月中旬开始雨季。建议携带雨伞和防水鞋。温度：20-28°C。', severity: 'info', status: 'resolved', timestamp: '10:23 AM' },
  { id: 's2', title: '哲学家之路：无障碍提示', description: '部分路段有不平的石阶。需要一定行动能力。可选铺装路线。', severity: 'warning', status: 'pending', timestamp: '10:23 AM' },
  { id: 's3', title: '伏见稻荷登山：山道状况', description: '山路部分路段较陡。往返约2-3小时。带足够的水。', severity: 'info', status: 'resolved', timestamp: '10:23 AM' },
];

// --- 工具调用日志 ---
export const toolCallLogs: ToolCallLog[] = [
  { id: 'l1', timestamp: '10:23:45.234', category: 'DB', function: '查询_安全_数据库', params: '{"location": "Kyoto, Japan"}', result: '找到3条记录', duration: 145 },
  { id: 'l2', timestamp: '10:23:47.891', category: 'API', function: '搜索_景点', params: '{"city": "Kyoto", "type": "temple"}', result: '找到18座寺庙', duration: 234 },
  { id: 'l3', timestamp: '10:23:48.123', category: 'API', function: '搜索_景点', params: '{"city": "Kyoto", "type": "garden"}', result: '找到12座花园', duration: 189 },
  { id: 'l4', timestamp: '10:23:50.456', category: 'CALC', function: '路线优化', params: '{"waypoints": 5}', result: '平均每日4.2公里', duration: 89 },
  { id: 'l5', timestamp: '10:23:51.789', category: 'DB', function: '搜索_旅馆', params: '{"area": "Gion"}', result: '找到5家旅馆', duration: 312 },
  { id: 'l6', timestamp: '10:23:52.012', category: 'API', function: '检查_天气', params: '{"city": "Kyoto", "dates": "June 15-19"}', result: '20-28°C，湿度60%', duration: 156 },
  { id: 'l7', timestamp: '10:23:53.345', category: 'SAFETY', function: '检查_旅行_警告', params: '{"country": "Japan"}', result: '无现役警告', duration: 98 },
  { id: 'l8', timestamp: '10:23:54.678', category: 'API', function: '检查_餐厅_可用性', params: '{"restaurant": "Kikunoi Roan"}', result: '可用', duration: 267 },
  { id: 'l9', timestamp: '10:23:55.901', category: 'API', function: '检查_餐厅_可用性', params: '{"restaurant": "Giro Giro"}', result: '可用', duration: 198 },
  { id: 'l10', timestamp: '10:23:56.234', category: 'CALC', function: '预算优化器', params: '{"budget": 5000, "days": 5}', result: '已生成分配计划', duration: 67 },
  { id: 'l11', timestamp: '10:23:57.567', category: 'DB', function: '获取_景点_详情', params: '{"poi_id": "kinkakuji"}', result: '已检索详情', duration: 123 },
  { id: 'l12', timestamp: '10:23:58.890', category: 'DB', function: '获取_景点_详情', params: '{"poi_id": "fushimi_inari"}', result: '已检索详情', duration: 112 },
  { id: 'l13', timestamp: '10:23:59.123', category: 'API', function: '获取_季节_事件', params: '{"month": "June"}', result: '绣球花季节活跃', duration: 178 },
  { id: 'l14', timestamp: '10:24:00.456', category: 'CALC', function: '计算_旅行_时间', params: '{"from": "Gion", "to": "Arashiyama"}', result: '火车35分钟', duration: 45 },
  { id: 'l15', timestamp: '10:24:01.789', category: 'SAFETY', function: '检查_无障碍', params: '{"location": "Philosophers Path"}', result: '已注意不平石阶', duration: 134 },
  { id: 'l16', timestamp: '10:24:02.012', category: 'API', function: '获取_评价', params: '{"poi": "Yuzuya Ryokan"}', result: '来自342条评价的4.8/5', duration: 256 },
];

export const quickActionChips = [
  '预算明细',
  '调整时间线',
  '偏好设置',
  '交通选项',
  '餐厅预订',
  '天气预报',
];
