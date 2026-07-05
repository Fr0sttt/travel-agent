import { useState } from 'react';
import { motion } from 'framer-motion';
import { Check } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';

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

const languages = [
  { key: 'en', label: 'English' },
  { key: 'zh', label: '简体中文' },
  { key: 'ja', label: '日本語' },
  { key: 'es', label: 'Español' },
  { key: 'fr', label: 'Français' },
  { key: 'de', label: 'Deutsch' },
];

const currencies = [
  { key: 'CNY', label: 'CNY (¥) - 中文元' },
  { key: 'USD', label: 'USD ($) - 美元' },
  { key: 'EUR', label: 'EUR (€) - 欧元' },
  { key: 'JPY', label: 'JPY (¥) - 日元' },
  { key: 'GBP', label: 'GBP (£) - 英镑' },
  { key: 'KRW', label: 'KRW (₩) - 韩元' },
];

const dateFormats = [
  { key: 'yyyy-mm-dd', label: 'YYYY-MM-DD' },
  { key: 'mm-dd-yyyy', label: 'MM/DD/YYYY' },
  { key: 'dd-mm-yyyy', label: 'DD/MM/YYYY' },
];

const popularCountries = [
  'China',
  'United States',
  'Japan',
  'United Kingdom',
  'Germany',
  'France',
  'South Korea',
  'Singapore',
  'Australia',
  'Canada',
  'Thailand',
  'Italy',
];

export default function LanguageRegionTab() {
  const [language, setLanguage] = useState('en');
  const [region, setRegion] = useState('China');
  const [currency, setCurrency] = useState('CNY');
  const [dateFormat, setDateFormat] = useState('yyyy-mm-dd');
  const [timeFormat24h, setTimeFormat24h] = useState(true);
  const [distanceUnit, setDistanceUnit] = useState<'km' | 'miles'>('km');
  const [temperatureUnit, setTemperatureUnit] = useState<'celsius' | 'fahrenheit'>('celsius');
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved'>('idle');

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
          语言和地区
        </h2>
        <p className="mt-2 text-base" style={{ color: 'rgba(255,255,255,0.5)' }}>
          设置您的语言、地区和格式偏好
        </p>
      </motion.div>

      {/* Interface Language */}
      <motion.div
        variants={itemVariants}
        className="mt-8 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <Label className="text-xl font-semibold text-white block mb-1">
          界面语言
        </Label>
        <p className="text-sm mb-4" style={{ color: 'rgba(255,255,255,0.4)' }}>
          在整个 WanderMind 界面中使用的语言
        </p>
        <Select value={language} onValueChange={setLanguage}>
          <SelectTrigger className="h-11 bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white focus:border-[#219EBC] rounded-[8px] w-full max-w-md">
            <SelectValue placeholder="选择语言" />
          </SelectTrigger>
          <SelectContent className="bg-[#0A2463] border-[rgba(255,255,255,0.1)] text-white">
            {languages.map((lang) => (
              <SelectItem key={lang.key} value={lang.key} className="text-white focus:bg-[rgba(33,158,188,0.2)]">
                {lang.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </motion.div>

      {/* Region */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <Label className="text-xl font-semibold text-white block mb-1">
          默认地区
        </Label>
        <p className="text-sm mb-4" style={{ color: 'rgba(255,255,255,0.5)' }}>
          用于货币、日期格式和本地建议
        </p>
        <Select value={region} onValueChange={setRegion}>
          <SelectTrigger className="h-11 bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white focus:border-[#219EBC] rounded-[8px] w-full max-w-md">
            <SelectValue placeholder="选择国家" />
          </SelectTrigger>
          <SelectContent className="bg-[#0A2463] border-[rgba(255,255,255,0.1)] text-white">
            {popularCountries.map((country) => (
              <SelectItem key={country} value={country} className="text-white focus:bg-[rgba(33,158,188,0.2)]">
                {country}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </motion.div>

      {/* Currency */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <Label className="text-xl font-semibold text-white block mb-1">
          首选货币
        </Label>
        <p className="text-sm mb-4" style={{ color: 'rgba(255,255,255,0.4)' }}>
          用于显示价格和预算的货币
        </p>
        <Select value={currency} onValueChange={setCurrency}>
          <SelectTrigger className="h-11 bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white focus:border-[#219EBC] rounded-[8px] w-full max-w-md">
            <SelectValue placeholder="选择货币" />
          </SelectTrigger>
          <SelectContent className="bg-[#0A2463] border-[rgba(255,255,255,0.1)] text-white">
            {currencies.map((curr) => (
              <SelectItem key={curr.key} value={curr.key} className="text-white focus:bg-[rgba(33,158,188,0.2)]">
                {curr.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </motion.div>

      {/* Date Format */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <Label className="text-xl font-semibold text-white block mb-1">
          日期格式
        </Label>
        <p className="text-sm mb-4" style={{ color: 'rgba(255,255,255,0.4)' }}>
          日期在整个应用中的显示方式
        </p>
        <div className="flex flex-wrap gap-3">
          {dateFormats.map((format) => (
            <button
              key={format.key}
              onClick={() => setDateFormat(format.key)}
              className={`px-5 py-2.5 rounded-[8px] text-sm font-medium transition-all duration-200 ${
                dateFormat === format.key
                  ? 'bg-[#1A659E] text-white'
                  : 'bg-[rgba(255,255,255,0.06)] text-[#EDF6F9] hover:bg-[rgba(255,255,255,0.1)]'
              }`}
            >
              {format.label}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Time Format */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-white">时间格式</h3>
            <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
              使用 24 小时制时间格式
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-sm ${!timeFormat24h ? 'text-[#EDF6F9] font-medium' : 'text-[rgba(255,255,255,0.3)]'}`}>
              12h
            </span>
            <Switch
              checked={timeFormat24h}
              onCheckedChange={setTimeFormat24h}
              className="data-[state=checked]:bg-[#2EC4B6]"
            />
            <span className={`text-sm ${timeFormat24h ? 'text-[#EDF6F9] font-medium' : 'text-[rgba(255,255,255,0.3)]'}`}>
              24h
            </span>
          </div>
        </div>
      </motion.div>

      {/* Distance Unit */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-white">距离单位</h3>
            <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
              以公里或英里显示距离
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setDistanceUnit('km')}
              className={`px-5 py-2.5 rounded-[8px] text-sm font-medium transition-all duration-200 ${
                distanceUnit === 'km'
                  ? 'bg-[#1A659E] text-white'
                  : 'bg-[rgba(255,255,255,0.06)] text-[#EDF6F9] hover:bg-[rgba(255,255,255,0.1)]'
              }`}
            >
              km
            </button>
            <button
              onClick={() => setDistanceUnit('miles')}
              className={`px-5 py-2.5 rounded-[8px] text-sm font-medium transition-all duration-200 ${
                distanceUnit === 'miles'
                  ? 'bg-[#1A659E] text-white'
                  : 'bg-[rgba(255,255,255,0.06)] text-[#EDF6F9] hover:bg-[rgba(255,255,255,0.1)]'
              }`}
            >
              miles
            </button>
          </div>
        </div>
      </motion.div>

      {/* Temperature Unit */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-white">温度单位</h3>
            <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
              以摄氏度或华氏度显示温度
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setTemperatureUnit('celsius')}
              className={`px-5 py-2.5 rounded-[8px] text-sm font-medium transition-all duration-200 ${
                temperatureUnit === 'celsius'
                  ? 'bg-[#1A659E] text-white'
                  : 'bg-[rgba(255,255,255,0.06)] text-[#EDF6F9] hover:bg-[rgba(255,255,255,0.1)]'
              }`}
            >
              °C
            </button>
            <button
              onClick={() => setTemperatureUnit('fahrenheit')}
              className={`px-5 py-2.5 rounded-[8px] text-sm font-medium transition-all duration-200 ${
                temperatureUnit === 'fahrenheit'
                  ? 'bg-[#1A659E] text-white'
                  : 'bg-[rgba(255,255,255,0.06)] text-[#EDF6F9] hover:bg-[rgba(255,255,255,0.1)]'
              }`}
            >
              °F
            </button>
          </div>
        </div>
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
