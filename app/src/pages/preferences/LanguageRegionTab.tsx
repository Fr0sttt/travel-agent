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
  { key: 'CNY', label: 'CNY (¥) - Chinese Yuan' },
  { key: 'USD', label: 'USD ($) - US Dollar' },
  { key: 'EUR', label: 'EUR (€) - Euro' },
  { key: 'JPY', label: 'JPY (¥) - Japanese Yen' },
  { key: 'GBP', label: 'GBP (£) - British Pound' },
  { key: 'KRW', label: 'KRW (₩) - Korean Won' },
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
          Language &amp; Region
        </h2>
        <p className="mt-2 text-base" style={{ color: 'rgba(255,255,255,0.5)' }}>
          Set your language, region, and formatting preferences
        </p>
      </motion.div>

      {/* Interface Language */}
      <motion.div
        variants={itemVariants}
        className="mt-8 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <Label className="text-xl font-semibold text-white block mb-1">
          Interface Language
        </Label>
        <p className="text-sm mb-4" style={{ color: 'rgba(255,255,255,0.4)' }}>
          The language used throughout the WanderMind interface
        </p>
        <Select value={language} onValueChange={setLanguage}>
          <SelectTrigger className="h-11 bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white focus:border-[#219EBC] rounded-[8px] w-full max-w-md">
            <SelectValue placeholder="Select language" />
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
          Default Region
        </Label>
        <p className="text-sm mb-4" style={{ color: 'rgba(255,255,255,0.5)' }}>
          Used for currency, date formats, and local recommendations
        </p>
        <Select value={region} onValueChange={setRegion}>
          <SelectTrigger className="h-11 bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white focus:border-[#219EBC] rounded-[8px] w-full max-w-md">
            <SelectValue placeholder="Select country" />
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
          Preferred Currency
        </Label>
        <p className="text-sm mb-4" style={{ color: 'rgba(255,255,255,0.4)' }}>
          Currency used for displaying prices and budgets
        </p>
        <Select value={currency} onValueChange={setCurrency}>
          <SelectTrigger className="h-11 bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white focus:border-[#219EBC] rounded-[8px] w-full max-w-md">
            <SelectValue placeholder="Select currency" />
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
          Date Format
        </Label>
        <p className="text-sm mb-4" style={{ color: 'rgba(255,255,255,0.4)' }}>
          How dates are displayed throughout the app
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
            <h3 className="text-xl font-semibold text-white">Time Format</h3>
            <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Use 24-hour time format
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
            <h3 className="text-xl font-semibold text-white">Distance Unit</h3>
            <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Display distances in kilometers or miles
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
            <h3 className="text-xl font-semibold text-white">Temperature Unit</h3>
            <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Display temperatures in Celsius or Fahrenheit
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
              Saving...
            </span>
          )}
          {saveState === 'saved' && (
            <span className="inline-flex items-center gap-2 text-[#06D6A0]">
              <Check className="w-4 h-4" />
              Saved!
            </span>
          )}
          {saveState === 'idle' && 'Save Changes'}
        </Button>
      </motion.div>
    </motion.div>
  );
}
