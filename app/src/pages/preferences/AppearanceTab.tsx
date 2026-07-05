import { useState } from 'react';
import { motion } from 'framer-motion';
import { Check, Monitor, Sun, Moon } from 'lucide-react';
import { Slider } from '@/components/ui/slider';
import { Button } from '@/components/ui/button';

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

const themes = [
  {
    key: 'deep-sea',
    label: '深蓝海',
    description: '默认深蓝色',
    icon: Monitor,
    preview: 'linear-gradient(135deg, #0A2463 0%, #1A659E 50%, #219EBC 100%)',
  },
  {
    key: 'midnight',
    label: '午夜',
    description: '纯黑色',
    icon: Moon,
    preview: 'linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%)',
  },
  {
    key: 'ocean-light',
    label: '海洋浅色',
    description: '浅蓝色',
    icon: Sun,
    preview: 'linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 50%, #80deea 100%)',
  },
];

const densityOptions = [
  { key: 'compact', label: '紧凑' },
  { key: 'comfortable', label: '舒适' },
  { key: 'spacious', label: '宽敞' },
];

const fontSizeOptions = [
  { key: 'small', label: '小', scale: 0.9 },
  { key: 'medium', label: '中', scale: 1.0 },
  { key: 'large', label: '大', scale: 1.1 },
];

const accentColors = [
  { key: 'blue', label: '蓝色', hex: '#219EBC' },
  { key: 'green', label: '绿色', hex: '#2EC4B6' },
  { key: 'coral', label: '珊瑚色', hex: '#E29578' },
  { key: 'purple', label: '紫色', hex: '#9B5DE5' },
];

const animationOptions = [
  { key: 'full', label: '完整' },
  { key: 'reduced', label: '减弱' },
  { key: 'none', label: '无' },
];

export default function AppearanceTab() {
  const [theme, setTheme] = useState('deep-sea');
  const [density, setDensity] = useState('comfortable');
  const [fontSize, setFontSize] = useState('medium');
  const [fontScale, setFontScale] = useState([100]);
  const [accentColor, setAccentColor] = useState('blue');
  const [animationLevel, setAnimationLevel] = useState('full');
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved'>('idle');

  const selectedFontSize = fontSizeOptions.find((f) => f.key === fontSize);
  const previewScale = (fontScale[0] / 100) * (selectedFontSize?.scale || 1);

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
          外观
        </h2>
        <p className="mt-2 text-base" style={{ color: 'rgba(255,255,255,0.5)' }}>
          自定义 WanderMind 的外观和感受
        </p>
      </motion.div>

      {/* Theme Selection */}
      <motion.div
        variants={itemVariants}
        className="mt-8 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">主题</h3>
        <div className="mt-4 flex flex-wrap gap-4">
          {themes.map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.key}
                onClick={() => setTheme(t.key)}
                className={`flex flex-col items-center gap-2 p-3 rounded-[12px] border-2 transition-all duration-200 ${
                  theme === t.key
                    ? 'border-[#219EBC] bg-[rgba(33,158,188,0.08)]'
                    : 'border-[rgba(255,255,255,0.1)] hover:border-[rgba(255,255,255,0.2)]'
                }`}
              >
                <div
                  className="w-[120px] h-[72px] rounded-[8px]"
                  style={{ background: t.preview }}
                />
                <div className="flex items-center gap-1.5 mt-1">
                  <Icon className="w-4 h-4 text-[#8ECAE6]" />
                  <span className="text-sm text-[#EDF6F9]">{t.label}</span>
                </div>
                <span className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
                  {t.description}
                </span>
              </button>
            );
          })}
        </div>
      </motion.div>

      {/* Interface Density */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">界面密度</h3>
        <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
          控制界面的紧凑度或宽敞度
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          {densityOptions.map((option) => (
            <button
              key={option.key}
              onClick={() => setDensity(option.key)}
              className={`px-5 py-2.5 rounded-[8px] text-sm font-medium transition-all duration-200 ${
                density === option.key
                  ? 'bg-[#1A659E] text-white'
                  : 'bg-[rgba(255,255,255,0.06)] text-[#EDF6F9] hover:bg-[rgba(255,255,255,0.1)]'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Font Size */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">字体大小</h3>
        <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
          调整整个界面的文本大小
        </p>

        {/* Font Scale Slider */}
        <div className="mt-4 flex items-center gap-4">
          <span className="text-xs text-[rgba(255,255,255,0.4)]">80%</span>
          <div className="flex-1">
            <Slider
              value={fontScale}
              onValueChange={setFontScale}
              min={80}
              max={120}
              step={10}
              className="w-full"
            />
          </div>
          <span className="text-xs text-[rgba(255,255,255,0.4)]">120%</span>
          <span className="font-mono text-sm text-[#2EC4B6] w-12 text-right">{fontScale[0]}%</span>
        </div>

        {/* Preset Buttons */}
        <div className="mt-4 flex flex-wrap gap-3">
          {fontSizeOptions.map((option) => (
            <button
              key={option.key}
              onClick={() => setFontSize(option.key)}
              className={`px-5 py-2.5 rounded-[8px] text-sm font-medium transition-all duration-200 ${
                fontSize === option.key
                  ? 'bg-[#1A659E] text-white'
                  : 'bg-[rgba(255,255,255,0.06)] text-[#EDF6F9] hover:bg-[rgba(255,255,255,0.1)]'
              }`}
              style={{ fontSize: `${option.scale}rem` }}
            >
              {option.label}
            </button>
          ))}
        </div>

        {/* Live Preview */}
        <div className="mt-6 p-4 rounded-[8px] bg-[rgba(0,0,0,0.2)] border border-[rgba(255,255,255,0.06)]">
          <p className="text-xs mb-2" style={{ color: 'rgba(255,255,255,0.3)' }}>
            实时预览
          </p>
          <p
            className="text-white"
            style={{ fontSize: `${previewScale}rem`, transition: 'font-size 0.3s ease' }}
          >
            快速的棕色狐狸跳过懒狗。
          </p>
          <p
            className="mt-1"
            style={{
              color: 'rgba(255,255,255,0.5)',
              fontSize: `${previewScale * 0.875}rem`,
              transition: 'font-size 0.3s ease',
            }}
          >
            收拾行囊——您在东京、日本的下一场冒险在等待您！
          </p>
        </div>
      </motion.div>

      {/* Accent Color */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">强调色</h3>
        <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
          选择您首选的强调色
        </p>
        <div className="mt-4 flex flex-wrap gap-4">
          {accentColors.map((color) => (
            <button
              key={color.key}
              onClick={() => setAccentColor(color.key)}
              className={`flex flex-col items-center gap-2 p-3 rounded-[12px] border-2 transition-all duration-200 ${
                accentColor === color.key
                  ? 'border-[#219EBC] bg-[rgba(33,158,188,0.08)]'
                  : 'border-[rgba(255,255,255,0.1)] hover:border-[rgba(255,255,255,0.2)]'
              }`}
            >
              <div
                className="w-10 h-10 rounded-full"
                style={{ background: color.hex }}
              />
              <span className="text-sm text-[#EDF6F9]">{color.label}</span>
            </button>
          ))}
        </div>
      </motion.div>

      {/* Animation Level */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">动画级别</h3>
        <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
          控制界面中的运动量
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          {animationOptions.map((option) => (
            <button
              key={option.key}
              onClick={() => setAnimationLevel(option.key)}
              className={`px-5 py-2.5 rounded-[8px] text-sm font-medium transition-all duration-200 ${
                animationLevel === option.key
                  ? 'bg-[#1A659E] text-white'
                  : 'bg-[rgba(255,255,255,0.06)] text-[#EDF6F9] hover:bg-[rgba(255,255,255,0.1)]'
              }`}
            >
              {option.label}
            </button>
          ))}
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
