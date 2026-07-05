import { useState } from 'react';
import { Link } from 'react-router';
import { Menu, X, Compass } from 'lucide-react';

const navLinks = [
  { label: '首页', path: '/' },
  { label: '应用', path: '/app' },
  { label: '偏好设置', path: '/preferences' },
  { label: '安全', path: '/security' },
];

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-[100] w-full h-16 border-b border-white/[0.06]" style={{ background: 'rgba(10, 36, 99, 0.9)', backdropFilter: 'blur(12px)' }}>
      <div className="max-w-[1440px] mx-auto h-full flex items-center justify-between px-6">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2">
          <Compass className="w-5 h-5 text-[#EDF6F9] animate-spin-slow" />
          <span className="font-display text-xl font-bold text-white tracking-tight">
            WanderMind
          </span>
        </Link>

        {/* Desktop Nav Links */}
        <div className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              className="text-sm font-medium text-[#EDF6F9] hover:text-[#8ECAE6] transition-colors duration-300"
              style={{ fontFamily: "'Inter Variable', Inter, sans-serif" }}
            >
              {link.label}
            </Link>
          ))}
        </div>

        {/* CTA Button */}
        <div className="hidden md:block">
          <Link
            to="/app"
            className="inline-flex items-center justify-center px-6 py-2.5 rounded-full text-sm font-semibold text-white transition-all duration-300 hover:scale-105 hover:shadow-glow-coral"
            style={{ background: '#E29578' }}
          >
            开始规划
          </Link>
        </div>

        {/* Mobile Hamburger */}
        <button
          className="md:hidden text-white p-2"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 top-16 z-[99]" style={{ background: 'rgba(10, 36, 99, 0.98)' }}>
          <div className="flex flex-col items-center pt-12 gap-8">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setMobileOpen(false)}
                className="text-lg font-medium text-[#EDF6F9] hover:text-[#8ECAE6] transition-colors duration-300"
              >
                {link.label}
              </Link>
            ))}
            <Link
              to="/app"
              onClick={() => setMobileOpen(false)}
              className="mt-4 inline-flex items-center justify-center px-8 py-3 rounded-full text-base font-semibold text-white transition-all duration-300 hover:scale-105"
              style={{ background: '#E29578' }}
            >
              开始规划
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
