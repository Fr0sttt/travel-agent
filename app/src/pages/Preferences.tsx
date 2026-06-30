import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  User,
  Heart,
  Bell,
  Shield,
  Palette,
  Globe,
  Settings,
} from 'lucide-react';
import ProfileTab from './preferences/ProfileTab';
import TravelPreferencesTab from './preferences/TravelPreferencesTab';
import NotificationsTab from './preferences/NotificationsTab';
import PrivacySafetyTab from './preferences/PrivacySafetyTab';
import AppearanceTab from './preferences/AppearanceTab';
import LanguageRegionTab from './preferences/LanguageRegionTab';

const navItems = [
  { key: 'profile', label: 'Profile', icon: User },
  { key: 'travel', label: 'Travel Preferences', icon: Heart },
  { key: 'notifications', label: 'Notifications', icon: Bell },
  { key: 'privacy', label: 'Privacy & Safety', icon: Shield },
  { key: 'appearance', label: 'Appearance', icon: Palette },
  { key: 'language', label: 'Language & Region', icon: Globe },
];

const tabContentVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: { duration: 0.2, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
  },
};

export default function Preferences() {
  const [activeTab, setActiveTab] = useState('profile');

  const renderTabContent = () => {
    switch (activeTab) {
      case 'profile':
        return <ProfileTab />;
      case 'travel':
        return <TravelPreferencesTab />;
      case 'notifications':
        return <NotificationsTab />;
      case 'privacy':
        return <PrivacySafetyTab />;
      case 'appearance':
        return <AppearanceTab />;
      case 'language':
        return <LanguageRegionTab />;
      default:
        return <ProfileTab />;
    }
  };

  return (
    <div className="min-h-[100dvh] w-full" style={{ background: '#0A2463' }}>
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Page Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] }}
          className="mb-8"
        >
          <div className="flex items-center gap-3">
            <Settings className="w-8 h-8 text-[#8ECAE6]" />
            <h1
              className="font-display text-[2.5rem] sm:text-[3.5rem] font-bold text-white leading-tight"
              style={{ letterSpacing: '-0.02em' }}
            >
              Settings
            </h1>
          </div>
          <p className="mt-2 text-base sm:text-lg" style={{ color: 'rgba(255,255,255,0.5)' }}>
            Customize your WanderMind experience
          </p>
        </motion.div>

        {/* Layout: Sidebar + Content */}
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Left Sidebar Navigation */}
          <motion.nav
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] as [number, number, number, number], delay: 0.1 }}
            className="lg:w-[240px] shrink-0"
          >
            <div
              className="lg:sticky lg:top-24 rounded-[12px] border border-[rgba(255,255,255,0.08)] overflow-hidden"
              style={{ background: 'rgba(10, 36, 99, 0.95)' }}
            >
              {/* Mobile: horizontal scroll */}
              <div className="flex lg:flex-col overflow-x-auto lg:overflow-x-visible py-2 lg:py-4">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = activeTab === item.key;
                  return (
                    <button
                      key={item.key}
                      onClick={() => setActiveTab(item.key)}
                      className={`relative flex items-center gap-3 px-4 lg:px-6 py-3 text-left whitespace-nowrap transition-all duration-200 flex-shrink-0 lg:flex-shrink ${
                        isActive
                          ? 'lg:bg-[rgba(33,158,188,0.08)]'
                          : 'hover:bg-[rgba(255,255,255,0.05)]'
                      }`}
                    >
                      {/* Active indicator - left border on desktop */}
                      {isActive && (
                        <motion.div
                          layoutId="activeTabIndicator"
                          className="hidden lg:block absolute left-0 top-0 bottom-0 w-[3px] bg-[#219EBC]"
                          transition={{
                            type: 'spring',
                            stiffness: 300,
                            damping: 30,
                          }}
                        />
                      )}
                      {/* Active indicator - bottom border on mobile */}
                      {isActive && (
                        <motion.div
                          layoutId="activeTabIndicatorMobile"
                          className="lg:hidden absolute bottom-0 left-4 right-4 h-[2px] bg-[#219EBC]"
                          transition={{
                            type: 'spring',
                            stiffness: 300,
                            damping: 30,
                          }}
                        />
                      )}
                      <Icon
                        className={`w-5 h-5 transition-colors duration-200 ${
                          isActive ? 'text-white' : 'text-[rgba(255,255,255,0.4)]'
                        }`}
                      />
                      <span
                        className={`text-sm transition-colors duration-200 ${
                          isActive
                            ? 'text-white font-medium'
                            : 'text-[rgba(255,255,255,0.5)]'
                        }`}
                      >
                        {item.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </motion.nav>

          {/* Right Content Area */}
          <div className="flex-1 min-w-0">
            <div
              className="rounded-[12px] border border-[rgba(255,255,255,0.08)] p-6 sm:p-8 lg:p-10"
              style={{
                background: 'rgba(255,255,255,0.05)',
                backdropFilter: 'blur(16px)',
              }}
            >
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeTab}
                  variants={tabContentVariants}
                  initial="hidden"
                  animate="visible"
                  exit="exit"
                >
                  {renderTabContent()}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
