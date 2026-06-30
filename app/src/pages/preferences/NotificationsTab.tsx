import { useState } from 'react';
import { motion } from 'framer-motion';
import { Bell, Mail, Smartphone, Check } from 'lucide-react';
import { Switch } from '@/components/ui/switch';
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

interface NotificationCategory {
  title: string;
  masterKey: string;
  items: { key: string; label: string }[];
}

const categories: NotificationCategory[] = [
  {
    title: 'Travel Alerts',
    masterKey: 'travelAlerts',
    items: [
      { key: 'safetyAlerts', label: 'Safety alerts for my destination' },
      { key: 'weatherWarnings', label: 'Weather warnings' },
      { key: 'travelAdvisory', label: 'Travel advisory updates' },
      { key: 'flightChanges', label: 'Flight/transport changes' },
    ],
  },
  {
    title: 'Trip Reminders',
    masterKey: 'tripReminders',
    items: [
      { key: 'dayBeforeSummary', label: 'Day-before trip summary' },
      { key: 'dailyItinerary', label: 'Daily itinerary reminders' },
      { key: 'reservationConfirmations', label: 'Reservation confirmations' },
    ],
  },
  {
    title: 'AI Agent Updates',
    masterKey: 'aiUpdates',
    items: [
      { key: 'itineraryReady', label: 'When itinerary is ready' },
      { key: 'evaluationUpdates', label: 'Evaluation score updates' },
      { key: 'safetyReview', label: 'Safety review completed' },
    ],
  },
];

const channelOptions = [
  { key: 'inApp', label: 'In-App', icon: Bell },
  { key: 'email', label: 'Email', icon: Mail },
  { key: 'push', label: 'Push', icon: Smartphone },
];

const frequencyOptions = [
  { key: 'realtime', label: 'Real-time' },
  { key: 'daily', label: 'Daily digest' },
  { key: 'weekly', label: 'Weekly digest' },
];

export default function NotificationsTab() {
  const [switches, setSwitches] = useState<Record<string, boolean>>({
    travelAlerts: true,
    safetyAlerts: true,
    weatherWarnings: true,
    travelAdvisory: false,
    flightChanges: true,
    tripReminders: true,
    dayBeforeSummary: true,
    dailyItinerary: false,
    reservationConfirmations: true,
    aiUpdates: true,
    itineraryReady: true,
    evaluationUpdates: false,
    safetyReview: true,
  });

  const [channels, setChannels] = useState<Record<string, boolean>>({
    inApp: true,
    email: true,
    push: false,
  });

  const [frequency, setFrequency] = useState('realtime');
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved'>('idle');

  const toggleSwitch = (key: string) => {
    setSwitches((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const toggleChannel = (key: string) => {
    setChannels((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const isMasterOn = (category: NotificationCategory) => {
    return switches[category.masterKey] ?? false;
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
          Notifications
        </h2>
        <p className="mt-2 text-base" style={{ color: 'rgba(255,255,255,0.5)' }}>
          Choose how and when we contact you
        </p>
      </motion.div>

      {/* Notification Categories */}
      <div className="mt-8 space-y-4">
        {categories.map((category) => (
          <motion.div
            key={category.masterKey}
            variants={itemVariants}
            className="p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
            style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-semibold text-white">{category.title}</h3>
              <Switch
                checked={isMasterOn(category)}
                onCheckedChange={() => toggleSwitch(category.masterKey)}
                className="data-[state=checked]:bg-[#2EC4B6]"
              />
            </div>
            <div className="mt-4 ml-0 md:ml-6 space-y-3">
              {category.items.map((item) => (
                <div key={item.key} className="flex items-center justify-between">
                  <span className="text-sm text-[#EDF6F9]">{item.label}</span>
                  <Switch
                    checked={switches[item.key] ?? false}
                    onCheckedChange={() => toggleSwitch(item.key)}
                    disabled={!isMasterOn(category)}
                    className="data-[state=checked]:bg-[#2EC4B6]"
                  />
                </div>
              ))}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Communication Channels */}
      <motion.div
        variants={itemVariants}
        className="mt-6 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">Send notifications via</h3>
        <div className="mt-4 flex flex-wrap gap-6">
          {channelOptions.map((channel) => {
            const Icon = channel.icon;
            return (
              <div key={channel.key} className="flex items-center gap-3">
                <Switch
                  checked={channels[channel.key] ?? false}
                  onCheckedChange={() => toggleChannel(channel.key)}
                  className="data-[state=checked]:bg-[#2EC4B6]"
                />
                <Icon className="w-5 h-5 text-[#8ECAE6]" />
                <span className="text-sm text-[#EDF6F9]">{channel.label}</span>
              </div>
            );
          })}
        </div>
      </motion.div>

      {/* Frequency */}
      <motion.div
        variants={itemVariants}
        className="mt-5 p-6 rounded-[12px] border border-[rgba(255,255,255,0.08)]"
        style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
      >
        <h3 className="text-xl font-semibold text-white">Notification Frequency</h3>
        <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
          How often would you like to receive non-urgent notifications?
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          {frequencyOptions.map((option) => (
            <button
              key={option.key}
              onClick={() => setFrequency(option.key)}
              className={`px-5 py-2.5 rounded-[8px] text-sm font-medium transition-all duration-200 ${
                frequency === option.key
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
