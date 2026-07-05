import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Clock, Crosshair, Layers, Star, X } from 'lucide-react';
import { useTravel } from '@/contexts/TravelContext';
import type { POI } from './mockData';

type AMapGlobal = typeof window & {
  AMap?: any;
  _AMapSecurityConfig?: {
    securityJsCode?: string;
  };
};

type AMapOverlay = {
  setMap?: (map: any) => void;
};

type RouteGroup = {
  day: number;
  pois: POI[];
  path: [number, number][];
};

const categoryColors: Record<string, string> = {
  attraction: '#219EBC',
  restaurant: '#E29578',
  hotel: '#2EC4B6',
  transport: '#FF9F1C',
};

const categoryLabels: Record<string, string> = {
  attraction: '景点',
  restaurant: '餐厅',
  hotel: '酒店',
  transport: '交通',
};

const dayColors = ['#219EBC', '#2EC4B6', '#E29578', '#FF9F1C', '#06D6A0', '#8ECAE6'];

const fallbackCenter = {
  lng: 135.7681,
  lat: 35.0116,
};

let amapScriptPromise: Promise<void> | null = null;

function getWindow(): AMapGlobal | null {
  if (typeof window === 'undefined') return null;
  return window as AMapGlobal;
}

function loadAmapScript(): Promise<void> {
  const globalWindow = getWindow();
  if (!globalWindow) {
    return Promise.reject(new Error('浏览器环境不可用'));
  }

  if (globalWindow.AMap) {
    return Promise.resolve();
  }

  if (amapScriptPromise) {
    return amapScriptPromise;
  }

  const key = import.meta.env.VITE_AMAP_KEY?.trim();
  if (!key) {
    return Promise.reject(new Error('未配置 VITE_AMAP_KEY，无法加载高德地图'));
  }

  const securityJsCode = import.meta.env.VITE_AMAP_SECURITY_JS_CODE?.trim();
  if (securityJsCode) {
    globalWindow._AMapSecurityConfig = { securityJsCode };
  }

  amapScriptPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-amap-jsapi="true"]');
    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error('高德地图脚本加载失败')), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.async = true;
    script.defer = true;
    script.dataset.amapJsapi = 'true';
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(key)}`;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('高德地图脚本加载失败'));
    document.head.appendChild(script);
  });

  return amapScriptPromise;
}

function hasValidCoords(poi: POI): boolean {
  return Number.isFinite(poi.lat) && Number.isFinite(poi.lng) && Math.abs(poi.lat) > 0.0001 && Math.abs(poi.lng) > 0.0001;
}

function getCenterFromPois(pois: POI[]) {
  const validPois = pois.filter(hasValidCoords);
  if (validPois.length === 0) {
    return fallbackCenter;
  }

  const lat = validPois.reduce((sum, poi) => sum + poi.lat, 0) / validPois.length;
  const lng = validPois.reduce((sum, poi) => sum + poi.lng, 0) / validPois.length;
  return { lat, lng };
}

function buildRouteGroups(pois: POI[]): RouteGroup[] {
  const dayMap = new Map<number, POI[]>();
  pois.filter(hasValidCoords).forEach((poi) => {
    const list = dayMap.get(poi.day) || [];
    list.push(poi);
    dayMap.set(poi.day, list);
  });

  return Array.from(dayMap.entries())
    .sort(([a], [b]) => a - b)
    .map(([day, dayPois]) => {
      const sortedPois = [...dayPois].sort((a, b) => a.badge.localeCompare(b.badge, 'en', { numeric: true }));
      return {
        day,
        pois: sortedPois,
        // 兜底路径：仅当后端未返回真实道路坐标时使用，直连 POI 点
        path: sortedPois.map((poi) => [poi.lng, poi.lat] as [number, number]),
      };
    });
}

function createMarkerContent(
  poi: POI,
  color: string,
  isSelected: boolean,
  isHovered: boolean,
) {
  const wrapper = document.createElement('div');
  wrapper.style.cssText = [
    'display:flex',
    'flex-direction:column',
    'align-items:center',
    'justify-content:center',
    'gap:4px',
    'transform:translate(-50%, -100%)',
    'pointer-events:auto',
    'user-select:none',
  ].join(';');

  const marker = document.createElement('div');
  const size = isSelected ? 22 : isHovered ? 18 : 16;
  marker.style.cssText = [
    `width:${size}px`,
    `height:${size}px`,
    'border-radius:9999px',
    `background:${color}`,
    'border:2px solid rgba(255,255,255,0.95)',
    'box-shadow:0 10px 24px rgba(0,0,0,0.35), 0 0 0 6px rgba(255,255,255,0.06)',
    'display:flex',
    'align-items:center',
    'justify-content:center',
    'color:white',
    'font-size:10px',
    'font-weight:700',
    'line-height:1',
    'transition:all 0.15s ease',
  ].join(';');
  marker.textContent = poi.badge;

  const name = document.createElement('div');
  name.textContent = poi.name;
  name.style.cssText = [
    'max-width:120px',
    'padding:2px 8px',
    'border-radius:9999px',
    'background:rgba(8,12,24,0.82)',
    'border:1px solid rgba(255,255,255,0.12)',
    'color:#EDF6F9',
    'font-size:11px',
    'line-height:1.4',
    'text-align:center',
    'white-space:nowrap',
    'overflow:hidden',
    'text-overflow:ellipsis',
    'backdrop-filter:blur(8px)',
    'opacity:0',
    'transform:translateY(2px)',
    'transition:all 0.15s ease',
  ].join(';');

  if (isHovered || isSelected) {
    name.style.opacity = '1';
    name.style.transform = 'translateY(0)';
  }

  wrapper.appendChild(marker);
  wrapper.appendChild(name);
  return wrapper;
}

export default function MapPanel() {
  const { dashboardData } = useTravel();
  const pois = dashboardData.pois;
  const routePolyline = dashboardData.routePolyline;
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<any>(null);
  const markerRefs = useRef<AMapOverlay[]>([]);
  const polylineRefs = useRef<AMapOverlay[]>([]);

  const [selectedPoi, setSelectedPoi] = useState<POI | null>(null);
  const [hoveredPoi, setHoveredPoi] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);

  const center = useMemo(() => getCenterFromPois(pois), [pois]);
  const routeGroups = useMemo(() => buildRouteGroups(pois), [pois]);

  const clearOverlays = useCallback(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    [...markerRefs.current, ...polylineRefs.current].forEach((overlay) => {
      try {
        map.remove(overlay);
      } catch {
        // 忽略单个图层移除失败
      }
    });
    markerRefs.current = [];
    polylineRefs.current = [];
  }, []);

  const fitAll = useCallback(() => {
    const map = mapInstanceRef.current;
    if (!map || (!markerRefs.current.length && !polylineRefs.current.length)) return;
    try {
      map.setFitView([...markerRefs.current, ...polylineRefs.current]);
    } catch {
      // 兜底不打断用户操作
    }
  }, []);

  const focusPoi = useCallback((poi: POI | null) => {
    const map = mapInstanceRef.current;
    if (!map || !poi || !hasValidCoords(poi)) return;
    try {
      map.setZoomAndCenter(14, [poi.lng, poi.lat]);
    } catch {
      // 兜底不打断用户操作
    }
  }, []);

  const zoomBy = useCallback((delta: number) => {
    const map = mapInstanceRef.current;
    if (!map) return;
    try {
      const currentZoom = Number(map.getZoom?.() ?? 12);
      const nextZoom = Math.max(3, Math.min(20, currentZoom + delta));
      map.setZoom(nextZoom);
    } catch {
      // 兜底不打断用户操作
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function initMap() {
      try {
        await loadAmapScript();
        if (cancelled || !mapContainerRef.current) return;

        const globalWindow = getWindow();
        if (!globalWindow?.AMap) {
          throw new Error('高德地图脚本未正确初始化');
        }

        if (mapInstanceRef.current) {
          return;
        }

        mapInstanceRef.current = new globalWindow.AMap.Map(mapContainerRef.current, {
          viewMode: '2D',
          zoom: 12,
          center: [center.lng, center.lat],
          resizeEnable: true,
          dragEnable: true,
          zoomEnable: true,
          mapStyle: 'amap://styles/dark',
        });

        globalWindow.AMap.plugin(['AMap.ToolBar', 'AMap.Scale'], () => {
          if (cancelled || !mapInstanceRef.current) return;
          const toolbar = new globalWindow.AMap.ToolBar({ position: 'RB' });
          const scale = new globalWindow.AMap.Scale({ position: 'LB' });
          mapInstanceRef.current.addControl(toolbar);
          mapInstanceRef.current.addControl(scale);
        });

        setMapReady(true);
        setMapError(null);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        setMapError(message);
      }
    }

    initMap();

    return () => {
      cancelled = true;
      clearOverlays();
      if (mapInstanceRef.current) {
        try {
          mapInstanceRef.current.destroy();
        } catch {
          // 组件卸载时不阻断
        }
        mapInstanceRef.current = null;
      }
    };
  }, [center.lat, center.lng, clearOverlays]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    const globalWindow = getWindow();
    if (!map || !globalWindow?.AMap || !mapReady) return;

    clearOverlays();
    setHoveredPoi(null);

    if (pois.length === 0) {
      setSelectedPoi(null);
      return;
    }

    const validPois = pois.filter(hasValidCoords);
    const nextSelected = selectedPoi && validPois.some((poi) => poi.id === selectedPoi.id) ? selectedPoi : null;
    if (selectedPoi && !nextSelected) {
      setSelectedPoi(null);
    }

    validPois.forEach((poi) => {
      const isSelected = nextSelected?.id === poi.id;
      const isHovered = hoveredPoi === poi.id;
      const color = categoryColors[poi.category] || '#219EBC';
      const marker = new globalWindow.AMap.Marker({
        position: [poi.lng, poi.lat],
        offset: new globalWindow.AMap.Pixel(0, 0),
        anchor: 'center',
        zIndex: isSelected ? 130 : 100,
        content: createMarkerContent(poi, color, isSelected, isHovered),
      });

      marker.on('click', () => {
        setSelectedPoi(poi);
        setHoveredPoi(null);
        focusPoi(poi);
      });

      marker.on('mouseover', () => {
        setHoveredPoi(poi.id);
      });

      marker.on('mouseout', () => {
        setHoveredPoi((current) => (current === poi.id ? null : current));
      });

      map.add(marker);
      markerRefs.current.push(marker);
    });

    if (routePolyline.length >= 2) {
      // 优先使用后端返回的真实道路坐标（高德路径规划 polyline），
      // 而不是把 POI 两两直连成一条直线。
      const polyline = new globalWindow.AMap.Polyline({
        path: routePolyline,
        strokeColor: dayColors[0],
        strokeWeight: 6,
        strokeOpacity: 0.7,
        strokeStyle: 'solid',
        lineJoin: 'round',
        lineCap: 'round',
        zIndex: 80,
        showDir: true,
      });

      map.add(polyline);
      polylineRefs.current.push(polyline);
    } else {
      // 兜底：没有真实路径数据时，按天把 POI 直连（明显是估算连线，非实际路网）
      routeGroups.forEach((group) => {
        if (group.path.length < 2) return;

        const polyline = new globalWindow.AMap.Polyline({
          path: group.path,
          strokeColor: dayColors[(group.day - 1) % dayColors.length],
          strokeWeight: 4,
          strokeOpacity: 0.4,
          strokeStyle: 'dashed',
          lineJoin: 'round',
          lineCap: 'round',
          zIndex: 80,
        });

        map.add(polyline);
        polylineRefs.current.push(polyline);
      });
    }

    try {
      map.setFitView([...markerRefs.current, ...polylineRefs.current]);
    } catch {
      // 兜底不打断用户操作
    }
  }, [clearOverlays, focusPoi, hoveredPoi, mapReady, pois, routeGroups, routePolyline, selectedPoi]);

  const selectedColor = selectedPoi ? categoryColors[selectedPoi.category] || '#219EBC' : '#219EBC';

  return (
    <div className="relative w-full h-full overflow-hidden" style={{ background: '#081C4B' }}>
      <div ref={mapContainerRef} className="absolute inset-0" />

      {!mapReady && !mapError && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#081C4B] text-[#EDF6F9]">
          <div className="rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm">
            正在加载高德地图...
          </div>
        </div>
      )}

      {mapError && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#081C4B] text-[#EDF6F9]">
          <div className="max-w-sm rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm leading-relaxed">
            <p className="font-semibold mb-1">地图未能加载</p>
            <p className="text-white/70">{mapError}</p>
            <p className="mt-2 text-white/50">
              请在前端环境变量里配置 `VITE_AMAP_KEY`，如需安全密钥再补 `VITE_AMAP_SECURITY_JS_CODE`。
            </p>
          </div>
        </div>
      )}

      <div className="absolute bottom-4 right-4 z-20 flex flex-col gap-2">
        <button
          type="button"
          onClick={() => focusPoi(selectedPoi)}
          className="w-9 h-9 rounded-lg glass-card flex items-center justify-center text-[#EDF6F9] hover:text-[#8ECAE6] transition-colors"
          aria-label="定位到当前选中地点"
          title="定位到当前选中地点"
        >
          <Crosshair className="w-4 h-4" />
        </button>
        <button
          type="button"
          onClick={fitAll}
          className="w-9 h-9 rounded-lg glass-card flex items-center justify-center text-[#EDF6F9] hover:text-[#8ECAE6] transition-colors"
          aria-label="适配全部路线"
          title="适配全部路线"
        >
          <Layers className="w-4 h-4" />
        </button>
        <button
          type="button"
          onClick={() => zoomBy(1)}
          className="w-9 h-9 rounded-lg glass-card flex items-center justify-center text-[#EDF6F9] hover:text-[#8ECAE6] text-lg font-bold transition-colors"
          aria-label="放大"
          title="放大"
        >
          +
        </button>
        <button
          type="button"
          onClick={() => zoomBy(-1)}
          className="w-9 h-9 rounded-lg glass-card flex items-center justify-center text-[#EDF6F9] hover:text-[#8ECAE6] text-lg font-bold transition-colors"
          aria-label="缩小"
          title="缩小"
        >
          −
        </button>
      </div>

      <AnimatePresence>
        {selectedPoi && (
          <motion.div
            initial={{ opacity: 0, scale: 0.92, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 12 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] }}
            className="absolute top-4 left-4 z-20 w-72 glass-card overflow-hidden"
          >
            <div
              className="h-28 w-full"
              style={{
                background: `linear-gradient(135deg, ${selectedColor}55 0%, ${selectedColor}25 100%)`,
              }}
            />
            <button
              type="button"
              onClick={() => setSelectedPoi(null)}
              className="absolute top-2 right-2 w-7 h-7 rounded-full bg-black/40 flex items-center justify-center text-white hover:bg-black/60 transition-colors"
              aria-label="关闭详情"
            >
              <X className="w-4 h-4" />
            </button>
            <div className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <span
                  className="text-[10px] px-2 py-0.5 rounded-full font-medium uppercase"
                  style={{
                    background: `${selectedColor}25`,
                    color: selectedColor,
                    fontFamily: "'Inter Variable', Inter, sans-serif",
                  }}
                >
                  {categoryLabels[selectedPoi.category] || selectedPoi.category}
                </span>
                <div className="flex items-center gap-1">
                  <Star className="w-3 h-3 text-[#FF9F1C]" fill="#FF9F1C" />
                  <span className="text-xs text-[#EDF6F9]">{selectedPoi.rating}</span>
                </div>
              </div>

              <h3 className="text-base font-semibold text-white mb-1.5" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
                {selectedPoi.name}
              </h3>

              <p
                className="text-xs leading-relaxed mb-3"
                style={{ color: 'rgba(255,255,255,0.6)', fontFamily: "'Inter Variable', Inter, sans-serif" }}
              >
                {selectedPoi.description}
              </p>

              <div className="flex items-center gap-1.5 mb-3">
                <Clock className="w-3 h-3" style={{ color: 'rgba(255,255,255,0.4)' }} />
                <span
                  className="text-[11px]"
                  style={{ color: 'rgba(255,255,255,0.4)', fontFamily: "'JetBrains Mono Variable', monospace" }}
                >
                  {selectedPoi.timeEstimate}
                </span>
              </div>

              <button
                type="button"
                onClick={() => focusPoi(selectedPoi)}
                className="w-full py-2 rounded-lg text-xs font-semibold text-white transition-all hover:scale-[1.02] hover:shadow-glow-coral"
                style={{ background: '#E29578' }}
              >
                定位到地图
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {hoveredPoi && !selectedPoi && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute bottom-4 left-4 z-20 glass-card px-3 py-2"
          >
            <p className="text-xs font-medium text-white">{pois.find((poi) => poi.id === hoveredPoi)?.name}</p>
            <p className="text-[10px]" style={{ color: 'rgba(255,255,255,0.4)' }}>
              {pois.find((poi) => poi.id === hoveredPoi)?.badge} · {pois.find((poi) => poi.id === hoveredPoi)?.day} day
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
