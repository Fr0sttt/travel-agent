import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Camera, Check, User, Mail, Phone, MapPin, Globe, FileText } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const timezones = [
  'UTC-12:00',
  'UTC-11:00',
  'UTC-10:00',
  'UTC-09:00',
  'UTC-08:00 (Pacific)',
  'UTC-07:00 (Mountain)',
  'UTC-06:00 (Central)',
  'UTC-05:00 (Eastern)',
  'UTC-04:00',
  'UTC-03:00',
  'UTC+00:00 (GMT)',
  'UTC+01:00 (CET)',
  'UTC+02:00',
  'UTC+03:00',
  'UTC+04:00',
  'UTC+05:00',
  'UTC+05:30',
  'UTC+08:00 (CST)',
  'UTC+09:00 (JST)',
  'UTC+10:00',
];

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

export default function ProfileTab() {
  const [form, setForm] = useState({
    displayName: 'Alex Wanderer',
    email: 'alex.wanderer@example.com',
    phone: '+86 138 0000 8888',
    homeCity: 'Shanghai',
    timezone: 'UTC+08:00 (CST)',
    bio: 'Passionate traveler exploring the world one city at a time. Love street food, hidden gems, and sunset photography.',
  });
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved'>('idle');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const updateField = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleAvatarUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setAvatarUrl(reader.result as string);
      };
      reader.readAsDataURL(file);
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
          您的个人资料
        </h2>
        <p className="mt-2 text-base" style={{ color: 'rgba(255,255,255,0.5)' }}>
          管理您的账户信息和旅行身份
        </p>
      </motion.div>

      {/* Avatar Section */}
      <motion.div variants={itemVariants} className="mt-8 flex flex-col items-center">
        <div
          className="relative w-24 h-24 rounded-full overflow-hidden border-[3px] border-[#219EBC] cursor-pointer"
          onClick={() => fileInputRef.current?.click()}
        >
          {avatarUrl ? (
            <img src={avatarUrl} alt="Avatar" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-[rgba(255,255,255,0.06)]">
              <User className="w-10 h-10 text-[#8ECAE6]" />
            </div>
          )}
          <div className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 hover:opacity-100 transition-opacity">
            <Camera className="w-6 h-6 text-white" />
          </div>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleAvatarUpload}
        />
        <div className="mt-4 flex items-center gap-4">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="text-sm text-[#8ECAE6] hover:underline transition-all"
          >
            更改照片
          </button>
          {avatarUrl && (
            <button
              onClick={() => setAvatarUrl(null)}
              className="text-sm text-[#EF476F] hover:underline transition-all"
            >
              删除
            </button>
          )}
        </div>
      </motion.div>

      {/* Form Fields */}
      <motion.div variants={itemVariants} className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Display Name */}
        <div className="space-y-1.5">
          <Label className="text-sm font-medium text-[#EDF6F9]">显示名称</Label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgba(255,255,255,0.3)]" />
            <Input
              value={form.displayName}
              onChange={(e) => updateField('displayName', e.target.value)}
              placeholder="我们应该怎样称呼您？"
              className="h-11 bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white placeholder:text-[rgba(255,255,255,0.3)] focus:border-[#219EBC] rounded-[8px] pl-10"
            />
          </div>
        </div>

        {/* Email */}
        <div className="space-y-1.5">
          <Label className="text-sm font-medium text-[#EDF6F9]">电子邮件</Label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgba(255,255,255,0.3)]" />
            <Input
              type="email"
              value={form.email}
              onChange={(e) => updateField('email', e.target.value)}
              placeholder="your@email.com"
              className="h-11 bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white placeholder:text-[rgba(255,255,255,0.3)] focus:border-[#219EBC] rounded-[8px] pl-10"
            />
          </div>
        </div>

        {/* Phone */}
        <div className="space-y-1.5">
          <Label className="text-sm font-medium text-[#EDF6F9]">电话</Label>
          <div className="relative">
            <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgba(255,255,255,0.3)]" />
            <Input
              type="tel"
              value={form.phone}
              onChange={(e) => updateField('phone', e.target.value)}
              placeholder="+1 (555) 000-0000"
              className="h-11 bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white placeholder:text-[rgba(255,255,255,0.3)] focus:border-[#219EBC] rounded-[8px] pl-10"
            />
          </div>
        </div>

        {/* Home City */}
        <div className="space-y-1.5">
          <Label className="text-sm font-medium text-[#EDF6F9]">所在城市</Label>
          <div className="relative">
            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgba(255,255,255,0.3)]" />
            <Input
              value={form.homeCity}
              onChange={(e) => updateField('homeCity', e.target.value)}
              placeholder="您位于何处？"
              className="h-11 bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white placeholder:text-[rgba(255,255,255,0.3)] focus:border-[#219EBC] rounded-[8px] pl-10"
            />
          </div>
        </div>

        {/* Timezone */}
        <div className="space-y-1.5 md:col-span-2">
          <Label className="text-sm font-medium text-[#EDF6F9]">时区</Label>
          <div className="relative">
            <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgba(255,255,255,0.3)] z-10" />
            <Select value={form.timezone} onValueChange={(value) => updateField('timezone', value)}>
              <SelectTrigger className="h-11 bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white focus:border-[#219EBC] rounded-[8px] pl-10 w-full">
                <SelectValue placeholder="选择时区" />
              </SelectTrigger>
              <SelectContent className="bg-[#0A2463] border-[rgba(255,255,255,0.1)] text-white">
                {timezones.map((tz) => (
                  <SelectItem key={tz} value={tz} className="text-white focus:bg-[rgba(33,158,188,0.2)]">
                    {tz}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Bio */}
        <div className="space-y-1.5 md:col-span-2">
          <Label className="text-sm font-medium text-[#EDF6F9]">个人简介</Label>
          <div className="relative">
            <FileText className="absolute left-3 top-3 w-4 h-4 text-[rgba(255,255,255,0.3)]" />
            <Textarea
              value={form.bio}
              onChange={(e) => updateField('bio', e.target.value)}
              placeholder="告诉我们您的旅行风格..."
              maxLength={200}
              className="min-h-[100px] resize-y bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white placeholder:text-[rgba(255,255,255,0.3)] focus:border-[#219EBC] rounded-[8px] pl-10"
            />
            <span className="absolute bottom-2 right-3 text-xs font-mono" style={{ color: 'rgba(255,255,255,0.3)' }}>
              {form.bio.length}/200
            </span>
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
