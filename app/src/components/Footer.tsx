import { Link } from 'react-router';
import { Compass, Github, Twitter, Linkedin } from 'lucide-react';

const productLinks = [
  { label: 'Project Intro', path: '/how-it-works' },
  { label: 'App Dashboard', path: '/app' },
  { label: 'Preferences', path: '/preferences' },
  { label: 'Security', path: '/security' },
];

const resourceLinks = [
  { label: 'Documentation', path: '#' },
  { label: 'API Reference', path: '#' },
  { label: 'Blog', path: '#' },
  { label: 'Support', path: '#' },
];

export default function Footer() {
  return (
    <footer className="w-full bg-[#0A2463] pt-20 pb-10 px-6">
      <div className="max-w-[1200px] mx-auto">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-12">
          {/* Logo + Tagline */}
          <div>
            <Link to="/" className="flex items-center gap-2">
              <Compass className="w-6 h-6 text-[#EDF6F9]" />
              <span className="font-display text-2xl font-bold text-white tracking-tight">
                WanderMind
              </span>
            </Link>
            <p className="mt-4 text-base leading-relaxed" style={{ color: 'rgba(255,255,255,0.6)' }}>
              AI-powered travel planning with transparent reasoning
            </p>
          </div>

          {/* Product Links */}
          <div>
            <h4 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">
              Product
            </h4>
            <ul className="space-y-3">
              {productLinks.map((link) => (
                <li key={link.label}>
                  <Link
                    to={link.path}
                    className="text-sm transition-colors duration-300 hover:text-white"
                    style={{ color: 'rgba(255,255,255,0.5)' }}
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">
              Resources
            </h4>
            <ul className="space-y-3">
              {resourceLinks.map((link) => (
                <li key={link.label}>
                  <Link
                    to={link.path}
                    className="text-sm transition-colors duration-300 hover:text-white"
                    style={{ color: 'rgba(255,255,255,0.5)' }}
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Social */}
          <div>
            <h4 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">
              Connect
            </h4>
            <div className="flex items-center gap-4">
              <a href="#" className="transition-colors duration-300 hover:text-[#8ECAE6]" style={{ color: 'rgba(255,255,255,0.4)' }}>
                <Twitter className="w-5 h-5" />
              </a>
              <a href="#" className="transition-colors duration-300 hover:text-[#8ECAE6]" style={{ color: 'rgba(255,255,255,0.4)' }}>
                <Github className="w-5 h-5" />
              </a>
              <a href="#" className="transition-colors duration-300 hover:text-[#8ECAE6]" style={{ color: 'rgba(255,255,255,0.4)' }}>
                <Linkedin className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-16 pt-6 border-t border-white/[0.06]">
          <p className="text-xs text-center" style={{ color: 'rgba(255,255,255,0.3)' }}>
            &copy; {new Date().getFullYear()} WanderMind. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
