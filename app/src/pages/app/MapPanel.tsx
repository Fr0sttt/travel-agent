import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, Star, Crosshair, Layers, X } from 'lucide-react';
import { useTravel } from '@/contexts/TravelContext';
import type { POI } from './mockData';

const categoryColors: Record<string, string> = {
  attraction: '#219EBC',
  restaurant: '#E29578',
  hotel: '#2EC4B6',
  transport: '#FF9F1C',
};

const categoryIcons: Record<string, string> = {
  attraction: 'Attraction',
  restaurant: 'Restaurant',
  hotel: 'Hotel',
  transport: 'Transport',
};

function computeBounds(pois: POI[]) {
  if (pois.length === 0) {
    // Fallback bounds for Kyoto demo area
    return { latMin: 34.95, latMax: 35.05, lngMin: 135.65, lngMax: 135.82 };
  }
  const lats = pois.map((p) => p.lat);
  const lngs = pois.map((p) => p.lng);
  const latPad = (Math.max(...lats) - Math.min(...lats)) * 0.15 + 0.02;
  const lngPad = (Math.max(...lngs) - Math.min(...lngs)) * 0.15 + 0.02;
  return {
    latMin: Math.min(...lats) - latPad,
    latMax: Math.max(...lats) + latPad,
    lngMin: Math.min(...lngs) - lngPad,
    lngMax: Math.max(...lngs) + lngPad,
  };
}

function latLngToXY(lat: number, lng: number, w: number, h: number, bounds: ReturnType<typeof computeBounds>) {
  const x = ((lng - bounds.lngMin) / (bounds.lngMax - bounds.lngMin)) * w;
  const y = h - ((lat - bounds.latMin) / (bounds.latMax - bounds.latMin)) * h;
  return { x, y };
}

export default function MapPanel() {
  const { dashboardData } = useTravel();
  const pois = dashboardData.pois;
  const bounds = useMemo(() => computeBounds(pois), [pois]);

  const [selectedPoi, setSelectedPoi] = useState<POI | null>(null);
  const [hoveredPoi, setHoveredPoi] = useState<string | null>(null);

  const mapW = 800;
  const mapH = 500;

  const routeLines = useMemo(() => {
    const lines: { x1: number; y1: number; x2: number; y2: number; day: number }[] = [];
    const days = Array.from(new Set(pois.map((p) => p.day))).sort((a, b) => a - b);
    days.forEach((day) => {
      const dayPois = pois.filter((p) => p.day === day).sort((a, b) => a.badge.localeCompare(b.badge));
      for (let i = 0; i < dayPois.length - 1; i++) {
        const start = latLngToXY(dayPois[i].lat, dayPois[i].lng, mapW, mapH, bounds);
        const end = latLngToXY(dayPois[i + 1].lat, dayPois[i + 1].lng, mapW, mapH, bounds);
        lines.push({ x1: start.x, y1: start.y, x2: end.x, y2: end.y, day });
      }
    });
    return lines;
  }, [pois, bounds]);

  const dayColors = ['#219EBC', '#2EC4B6', '#E29578', '#FF9F1C', '#06D6A0', '#8ECAE6'];

  return (
    <div className="relative w-full h-full overflow-hidden" style={{ background: '#0A2463' }}>
      {/* World Map Background */}
      <div
        className="absolute inset-0 bg-cover bg-center opacity-30"
        style={{ backgroundImage: 'url(/world-map-dark.jpg)' }}
      />

      {/* SVG Map Layer */}
      <svg
        viewBox={`0 0 ${mapW} ${mapH}`}
        className="absolute inset-0 w-full h-full"
        preserveAspectRatio="xMidYMid slice"
      >
        {/* Animated Route Lines */}
        {routeLines.map((line, i) => (
          <g key={i}>
            <line
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke={dayColors[(line.day - 1) % dayColors.length]}
              strokeWidth="3"
              strokeLinecap="round"
              opacity={0.4}
            />
            <line
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke={dayColors[(line.day - 1) % dayColors.length]}
              strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray="8 8"
              opacity={0.8}
            >
              <animate
                attributeName="stroke-dashoffset"
                from="0"
                to="-16"
                dur="2s"
                repeatCount="indefinite"
              />
            </line>
          </g>
        ))}

        {/* POI Markers */}
        {pois.map((poi) => {
          const { x, y } = latLngToXY(poi.lat, poi.lng, mapW, mapH, bounds);
          const isHovered = hoveredPoi === poi.id;
          const isSelected = selectedPoi?.id === poi.id;
          const color = categoryColors[poi.category];

          return (
            <g
              key={poi.id}
              transform={`translate(${x}, ${y})`}
              style={{ cursor: 'pointer' }}
              onMouseEnter={() => setHoveredPoi(poi.id)}
              onMouseLeave={() => setHoveredPoi(null)}
              onClick={() => setSelectedPoi(poi)}
            >
              {/* Pulse ring for selected */}
              {(isSelected || isHovered) && (
                <circle r="18" fill="none" stroke={color} strokeWidth="1.5" opacity="0.5">
                  <animate attributeName="r" from="14" to="24" dur="1.5s" repeatCount="indefinite" />
                  <animate attributeName="opacity" from="0.5" to="0" dur="1.5s" repeatCount="indefinite" />
                </circle>
              )}
              {/* Marker circle */}
              <circle
                r={isHovered ? 14 : 12}
                fill={color}
                stroke="white"
                strokeWidth="2"
                style={{ transition: 'all 0.2s' }}
              />
              {/* Day badge text */}
              <text
                textAnchor="middle"
                dominantBaseline="central"
                fill="white"
                fontSize="10"
                fontWeight="700"
                style={{ fontFamily: "'JetBrains Mono Variable', monospace" }}
                pointerEvents="none"
              >
                {poi.badge}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Map Controls */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-2">
        <button className="w-9 h-9 rounded-lg glass-card flex items-center justify-center text-[#EDF6F9] hover:text-[#8ECAE6]">
          <Crosshair className="w-4 h-4" />
        </button>
        <button className="w-9 h-9 rounded-lg glass-card flex items-center justify-center text-[#EDF6F9] hover:text-[#8ECAE6]">
          <Layers className="w-4 h-4" />
        </button>
        <button className="w-9 h-9 rounded-lg glass-card flex items-center justify-center text-[#EDF6F9] hover:text-[#8ECAE6] text-lg font-bold">
          +
        </button>
        <button className="w-9 h-9 rounded-lg glass-card flex items-center justify-center text-[#EDF6F9] hover:text-[#8ECAE6] text-lg font-bold">
          −
        </button>
      </div>

      {/* POI Info Popup */}
      <AnimatePresence>
        {selectedPoi && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 10 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] }}
            className="absolute top-4 left-4 w-72 glass-card overflow-hidden z-20"
          >
            <div className="relative">
              <div
                className="h-28 w-full"
                style={{
                  background: `linear-gradient(135deg, ${categoryColors[selectedPoi.category]}40 0%, ${categoryColors[selectedPoi.category]}20 100%)`,
                }}
              />
              <button
                onClick={() => setSelectedPoi(null)}
                className="absolute top-2 right-2 w-7 h-7 rounded-full bg-black/40 flex items-center justify-center text-white hover:bg-black/60 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <span
                  className="text-[10px] px-2 py-0.5 rounded-full font-medium uppercase"
                  style={{
                    background: `${categoryColors[selectedPoi.category]}25`,
                    color: categoryColors[selectedPoi.category],
                    fontFamily: "'Inter Variable', Inter, sans-serif",
                  }}
                >
                  {selectedPoi.category}
                </span>
                <div className="flex items-center gap-1">
                  <Star className="w-3 h-3 text-[#FF9F1C]" fill="#FF9F1C" />
                  <span className="text-xs text-[#EDF6F9]">{selectedPoi.rating}</span>
                </div>
              </div>
              <h3 className="text-base font-semibold text-white mb-1.5" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
                {selectedPoi.name}
              </h3>
              <p className="text-xs leading-relaxed mb-3" style={{ color: 'rgba(255,255,255,0.6)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
                {selectedPoi.description}
              </p>
              <div className="flex items-center gap-1.5 mb-3">
                <Clock className="w-3 h-3" style={{ color: 'rgba(255,255,255,0.4)' }} />
                <span className="text-[11px]" style={{ color: 'rgba(255,255,255,0.4)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                  {selectedPoi.timeEstimate}
                </span>
              </div>
              <button
                className="w-full py-2 rounded-lg text-xs font-semibold text-white transition-all hover:scale-[1.02] hover:shadow-glow-coral"
                style={{ background: '#E29578' }}
              >
                Add to Itinerary
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Hover Tooltip */}
      <AnimatePresence>
        {hoveredPoi && !selectedPoi && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute bottom-4 left-4 glass-card px-3 py-2 z-10"
          >
            <p className="text-xs font-medium text-white">{pois.find((p) => p.id === hoveredPoi)?.name}</p>
            <p className="text-[10px]" style={{ color: 'rgba(255,255,255,0.4)' }}>
              {pois.find((p) => p.id === hoveredPoi)?.badge} · {categoryIcons[pois.find((p) => p.id === hoveredPoi)?.category || '']}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
