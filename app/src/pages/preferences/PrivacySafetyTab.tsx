import { useState } from 'react';
import { motion } from 'framer-motion';
import { Check, AlertTriangle } from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

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

const memoryOptions = [
  { key: '30days', label: '30 天' },
  { key: '90days', label: '90 天' },
  { key: '1year', label: '1 年' },
  { key: 'forever', label: '永久（直到删除）' },
];

const dataSharingOptions = [
  { key: 'travelHistory', label: '允许 AI 访问我的旅行历史以获得更好的建议' },
  { key: 'anonymizedData', label: '共享匿名数据以改进服务' },
  { key: 'thirdPartyMaps', label: '允许第三方地图服务用于路由' },
];

const confirmOptions = [
  { key: 'bookings', label: '预订' },
  { key: 'payments', label: '支付' },
  { key: 'dataExport', label: '数据导出' },
  { key: 'thirdPartySharing', label: '第三方共享' },
];

export default function PrivacySafetyTab() {
  const [memoryRetention, setMemoryRetention] = useState('1year');
  const [dataSharing, setDataSharing] = useState<Record<string, boolean>>({
    travelHistory: true,
    anonymizedData: true,
    thirdPartyMaps: false,
  });
  const [safetyLevel, setSafetyLevel] = useState([2]);
  const [autoConfirmLowRisk, setAutoConfirmLowRisk] = useState(false);
  const [confirmSettings, setConfirmSettings] = useState<Record<string, boolean>>({
    bookings: true,
    payments: true,
    dataExport: true,
    thirdPartySharing: true,
  });
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [clearConfirmText, setClearConfirmText] = useState('');
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved'>('idle');

  const safetyLabels = ['宽松', '中等', '标准', '严格', '最大'];

  const toggleDataSharing = (key: string) => {
    setDataSharing((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const toggleConfirm = (key: string) => {
    setConfirmSettings((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleClearData = () => {
    if (clearConfirmText === '清除所有数据') {
      setClearDialogOpen(false);
      setClearConfirmText('');
      setSaveState('saving');
      setTimeout(() => {
        setSaveState('saved');
        setTimeout(() => setSaveState('idle'), 2000);
      }, 800);
    }
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
          隐私和安全
        </h2>
        <p className="mt-2 text-base" style={{ color: 'rgba(255,255,255,0.5)' }}>
          控制您的数据和安全偏好
        </p>
      </motion.div>

      {/* Memory Retention */}
      <motion.div
        variants={itemVariants}
        className="mt-8 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">对话内存</h3>
        <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.5)' }}>
          我们应该保留您的对话历史和衍生偏好多长时间？
        </p>
        <div className="mt-4 space-y-3">
          {memoryOptions.map((option) => (
            <label
              key={option.key}
              className="flex items-center gap-3 cursor-pointer group"
            >
              <button
                onClick={() => setMemoryRetention(option.key)}
                className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                  memoryRetention === option.key
                    ? 'border-[#219EBC]'
                    : 'border-[rgba(255,255,255,0.2)] group-hover:border-[rgba(255,255,255,0.4)]'
                }`}
              >
                {memoryRetention === option.key && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="w-2 h-2 rounded-full bg-[#219EBC]"
                  />
                )}
              </button>
              <span className="text-base text-[#EDF6F9]">{option.label}</span>
            </label>
          ))}
        </div>
      </motion.div>

      {/* Data Sharing */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">数据共享</h3>
        <div className="mt-4 space-y-4">
          {dataSharingOptions.map((option) => (
            <div key={option.key} className="flex items-center justify-between">
              <span className="text-sm text-[#EDF6F9] max-w-[80%]">{option.label}</span>
              <Switch
                checked={dataSharing[option.key] ?? false}
                onCheckedChange={() => toggleDataSharing(option.key)}
                className="data-[state=checked]:bg-[#2EC4B6]"
              />
            </div>
          ))}
        </div>
      </motion.div>

      {/* Safety Level */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">安全敏感度</h3>
        <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.5)' }}>
          我们应该多严格地评估安全性？
        </p>
        <div className="mt-6 px-2">
          <Slider
            value={safetyLevel}
            onValueChange={setSafetyLevel}
            min={0}
            max={4}
            step={1}
            className="w-full"
          />
          <div className="mt-3 flex justify-between">
            {safetyLabels.map((label, i) => (
              <span
                key={label}
                className={`text-xs transition-colors ${
                  i === safetyLevel[0] ? 'text-[#2EC4B6] font-medium' : 'text-[rgba(255,255,255,0.3)]'
                }`}
              >
                {label}
              </span>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Auto-confirm Low Risk */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-white">自动确认低风险操作</h3>
            <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
              无需询问即自动确认低风险操作
            </p>
          </div>
          <Switch
            checked={autoConfirmLowRisk}
            onCheckedChange={setAutoConfirmLowRisk}
            className="data-[state=checked]:bg-[#2EC4B6]"
          />
        </div>
      </motion.div>

      {/* Require Confirmation For */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">需要确认的操作</h3>
        <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
          这些操作将始终要求您的确认
        </p>
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {confirmOptions.map((option) => (
            <label key={option.key} className="flex items-center gap-3 cursor-pointer group">
              <div
                className={`w-5 h-5 rounded-[4px] border flex items-center justify-center transition-all ${
                  confirmSettings[option.key]
                    ? 'bg-[#219EBC] border-[#219EBC]'
                    : 'border-[rgba(255,255,255,0.2)] group-hover:border-[rgba(255,255,255,0.4)]'
                }`}
                onClick={() => toggleConfirm(option.key)}
              >
                {confirmSettings[option.key] && <Check className="w-3 h-3 text-white" />}
              </div>
              <span className="text-sm text-[#EDF6F9]">{option.label}</span>
            </label>
          ))}
        </div>
      </motion.div>

      {/* Danger Zone */}
      <motion.div
        variants={itemVariants}
        className="mt-8 p-6 rounded-[12px] border border-[#EF476F]"
        style={{ background: 'rgba(239,71,111,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-[#EF476F]" />
          <h3 className="text-xl font-semibold text-[#EF476F]">危险区域</h3>
        </div>
        <p className="text-sm mt-2" style={{ color: 'rgba(255,255,255,0.5)' }}>
          清除所有内存数据后无法恢复。请确保您的选择。
        </p>

        <Dialog open={clearDialogOpen} onOpenChange={setClearDialogOpen}>
          <DialogTrigger asChild>
            <Button
              variant="outline"
              className="mt-4 h-10 px-6 text-sm font-medium border-[#EF476F] text-[#EF476F] bg-transparent hover:bg-[#EF476F] hover:text-white transition-all rounded-[8px]"
            >
              清除所有内存数据
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#0A2463] border-[rgba(255,255,255,0.1)] text-white max-w-md">
            <DialogHeader>
              <DialogTitle className="font-display text-xl text-[#EF476F]">
                清除所有内存数据
              </DialogTitle>
              <DialogDescription className="text-[rgba(255,255,255,0.5)]">
                此操作将永久删除您的所有对话历史、偏好设置和已保存的旅行数据。这无法撤消。
              </DialogDescription>
            </DialogHeader>
            <div className="mt-4">
              <Label className="text-sm text-[#EDF6F9]">
                输入 <strong>清除所有数据</strong> 以确认：
              </Label>
              <input
                type="text"
                value={clearConfirmText}
                onChange={(e) => setClearConfirmText(e.target.value)}
                placeholder="清除所有数据"
                className="mt-2 w-full h-11 bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.1)] text-white placeholder:text-[rgba(255,255,255,0.3)] focus:border-[#EF476F] rounded-[8px] px-4 text-sm"
              />
            </div>
            <DialogFooter className="mt-4">
              <Button
                onClick={() => {
                  setClearDialogOpen(false);
                  setClearConfirmText('');
                }}
                className="border-[rgba(255,255,255,0.2)] text-white bg-transparent hover:bg-[rgba(255,255,255,0.1)]"
              >
                取消
              </Button>
              <Button
                onClick={handleClearData}
                disabled={clearConfirmText !== '清除所有数据'}
                className="bg-[#EF476F] text-white hover:bg-[#d93d60] disabled:opacity-50"
              >
                清除所有数据
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </motion.div>

      {/* Save Button */}
      <motion.div variants={itemVariants} className="mt-8 mb-8">
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
