import { useState } from 'react';
import { motion } from 'framer-motion';
import { Star, Building2, Gem, Users, Home, Umbrella, Tent } from 'lucide-react';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Check } from 'lucide-react';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
  },
};

const travelStyleTags = [
  '独自旅行',
  '情侣',
  '家庭',
  '团体',
  '背包旅行',
  '奢华',
  '冒险',
  '文化',
  '放松',
  '美食',
  '摄影',
  '商务',
];

const accommodationOptions = [
  { id: 'hotels', label: '酒店', icon: Building2 },
  { id: 'boutique', label: '精品酒店', icon: Gem },
  { id: 'hostels', label: '青年旅舍', icon: Users },
  { id: 'airbnb', label: 'Airbnb', icon: Home },
  { id: 'resorts', label: '度假村', icon: Umbrella },
  { id: 'camping', label: '露营', icon: Tent },
];

const activities = [
  '观光',
  '博物馆',
  '自然和登山',
  '美食和餐饮',
  '购物',
  '夜生活',
  '海滩和水上活动',
  '历史遗迹',
  '本地文化',
  '摄影',
  '运动',
  '健康和水疗',
];

const dietaryTags = [
  '无限制',
  '素食',
  '纯素',
  '清真',
  '犹太食',
  '无麸质',
  '坚果过敏',
  '乳糖不耐受',
];

const budgetPresets = [
  { label: '经济', range: [50, 150] as [number, number] },
  { label: '中等', range: [150, 400] as [number, number] },
  { label: '奢华', range: [400, 1000] as [number, number] },
];

export default function TravelPreferencesTab() {
  const [budget, setBudget] = useState<number[]>([150, 400]);
  const [selectedStyles, setSelectedStyles] = useState<string[]>(['Cultural', 'Foodie', 'Photography']);
  const [selectedAccommodation, setSelectedAccommodation] = useState<string>('boutique');
  const [activityRatings, setActivityRatings] = useState<Record<string, number>>({
    Sightseeing: 4,
    Museums: 3,
    'Nature & Hikes': 5,
    'Food & Dining': 5,
    Shopping: 3,
    Nightlife: 2,
    'Beach & Water': 4,
    'Historical Sites': 5,
    'Local Culture': 5,
    Photography: 5,
    Sports: 3,
    'Wellness & Spa': 4,
  });
  const [selectedDietary, setSelectedDietary] = useState<string[]>(['No Restrictions']);
  const [mobilityEnabled, setMobilityEnabled] = useState(false);
  const [mobilityNote, setMobilityNote] = useState('');
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved'>('idle');

  const toggleStyle = (tag: string) => {
    setSelectedStyles((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const toggleDietary = (tag: string) => {
    if (tag === 'No Restrictions') {
      setSelectedDietary(['No Restrictions']);
      return;
    }
    setSelectedDietary((prev) => {
      const filtered = prev.filter((t) => t !== 'No Restrictions');
      if (filtered.includes(tag)) {
        const next = filtered.filter((t) => t !== tag);
        return next.length === 0 ? ['No Restrictions'] : next;
      }
      return [...filtered, tag];
    });
  };

  const setRating = (activity: string, rating: number) => {
    setActivityRatings((prev) => ({ ...prev, [activity]: rating }));
  };

  const handleBudgetPreset = (range: [number, number]) => {
    setBudget([...range]);
  };

  const handleSave = () => {
    setSaveState('saving');
    setTimeout(() => {
      setSaveState('saved');
      setTimeout(() => setSaveState('idle'), 2000);
    }, 800);
  };

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="visible">
      {/* Header */}
      <motion.div variants={itemVariants}>
        <h2 className="font-display text-[2.5rem] font-semibold text-white leading-tight">
          旅行偏好
        </h2>
        <p className="mt-2 text-base" style={{ color: 'rgba(255,255,255,0.5)' }}>
          帮助我们了解您的旅行风格，为您提供更好的建议
        </p>
      </motion.div>

      {/* Budget Range */}
      <motion.div
        variants={itemVariants}
        className="mt-8 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">典型旅行预算</h3>
        <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
          每人每天（不含航班）
        </p>

        <div className="mt-6 flex items-center gap-6">
          <div className="flex-1">
            <Slider
              value={budget}
              onValueChange={setBudget}
              min={50}
              max={1000}
              step={10}
              className="w-full"
            />
          </div>
          <span className="font-mono text-lg text-[#2EC4B6] whitespace-nowrap">
            ${budget[0]} - ${budget[1]}
          </span>
        </div>

        {/* Preset Buttons */}
        <div className="mt-4 flex flex-wrap gap-3">
          {budgetPresets.map((preset) => (
            <button
              key={preset.label}
              onClick={() => handleBudgetPreset(preset.range)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
                budget[0] === preset.range[0] && budget[1] === preset.range[1]
                  ? 'bg-[#1A659E] text-white'
                  : 'bg-[rgba(255,255,255,0.06)] text-[#EDF6F9] hover:bg-[rgba(255,255,255,0.1)]'
              }`}
            >
              {preset.label} (${preset.range[0]}-{preset.range[1]})
            </button>
          ))}
        </div>
      </motion.div>

      {/* Travel Style */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">旅行风格</h3>
        <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
          选择所有适用的选项
        </p>
        <div className="mt-4 flex flex-wrap gap-2.5">
          {travelStyleTags.map((tag) => (
            <button
              key={tag}
              onClick={() => toggleStyle(tag)}
              className={`px-4 py-2 rounded-full text-sm transition-all duration-200 ${
                selectedStyles.includes(tag)
                  ? 'bg-[#219EBC] text-white border border-[#219EBC]'
                  : 'bg-[rgba(255,255,255,0.06)] text-[#EDF6F9] border border-[rgba(255,255,255,0.1)] hover:bg-[rgba(255,255,255,0.1)]'
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Accommodation Preference */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">您的住宿偏好</h3>
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
          {accommodationOptions.map((option) => {
            const Icon = option.icon;
            return (
              <button
                key={option.id}
                onClick={() => setSelectedAccommodation(option.id)}
                className={`flex flex-col items-center gap-2 p-4 rounded-[8px] border transition-all duration-200 ${
                  selectedAccommodation === option.id
                    ? 'border-[#219EBC] bg-[rgba(33,158,188,0.1)]'
                    : 'border-[rgba(255,255,255,0.08)] bg-transparent hover:bg-[rgba(255,255,255,0.03)]'
                }`}
              >
                <Icon className="w-8 h-8 text-[#8ECAE6]" />
                <span className="text-sm text-[#EDF6F9]">{option.label}</span>
              </button>
            );
          })}
        </div>
      </motion.div>

      {/* Activity Preferences */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">最喜爱的活动</h3>
        <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
          评分您的兴趣（1-5 星）
        </p>
        <div className="mt-4 space-y-3">
          {activities.map((activity) => (
            <div key={activity} className="flex items-center justify-between">
              <span className="text-base text-[#EDF6F9]">{activity}</span>
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    onClick={() => setRating(activity, star)}
                    className="p-0.5 transition-transform hover:scale-110"
                  >
                    <Star
                      className={`w-5 h-5 transition-colors ${
                        star <= (activityRatings[activity] || 0)
                          ? 'text-[#FF9F1C] fill-[#FF9F1C]'
                          : 'text-[rgba(255,255,255,0.15)]'
                      }`}
                    />
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Dietary Restrictions */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">饮食需求</h3>
        <div className="mt-4 flex flex-wrap gap-2.5">
          {dietaryTags.map((tag) => (
            <button
              key={tag}
              onClick={() => toggleDietary(tag)}
              className={`px-4 py-2 rounded-full text-sm transition-all duration-200 ${
                selectedDietary.includes(tag)
                  ? 'bg-[#219EBC] text-white border border-[#219EBC]'
                  : 'bg-[rgba(255,255,255,0.06)] text-[#EDF6F9] border border-[rgba(255,255,255,0.1)] hover:bg-[rgba(255,255,255,0.1)]'
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Mobility Considerations */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-white">行动不便需求</h3>
            <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
              我有行动不便的考虑
            </p>
          </div>
          <Switch
            checked={mobilityEnabled}
            onCheckedChange={setMobilityEnabled}
            className="data-[state=checked]:bg-[#2EC4B6]"
          />
        </div>
        {mobilityEnabled && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            transition={{ duration: 0.3 }}
            className="mt-4"
          >
            <Textarea
              value={mobilityNote}
              onChange={(e) => setMobilityNote(e.target.value)}
              placeholder="描述任何行动不便的需求（轮椅通道、行走受限等）"
              className="min-h-[80px] bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white placeholder:text-[rgba(255,255,255,0.3)] focus:border-[#219EBC] rounded-[8px]"
            />
          </motion.div>
        )}
      </motion.div>

      {/* Save Button */}
      <motion.div variants={itemVariants} className="mt-8">
        <Button
          onClick={handleSave}
          disabled={saveState !== 'idle'}
          className="h-12 px-8 text-base font-semibold text-white rounded-[8px] transition-all duration-300 hover:scale-[1.02] hover:shadow-glow-coral"
          style={{ background: '#E29578' }}
        >
          {saveState === 'saving' && (
            <span className="inline-flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              保存中...
            </span>
          )}
          {saveState === 'saved' && (
            <span className="inline-flex items-center gap-2 text-[#06D6A0]">
              <Check className="w-4 h-4" />
              已保存！
            </span>
          )}
          {saveState === 'idle' && '保存更改'}
        </Button>
      </motion.div>
    </motion.div>
  );
}
