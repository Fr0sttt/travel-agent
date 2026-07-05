import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import { motion, useInView } from 'framer-motion';
import CountUp from 'react-countup';
import {
  ShieldAlert,
  EyeOff,
  Database,
  Shield,
  MessageSquare,
  Calendar,
  Map,
  Eye,
  Brain,
  ChevronDown,
  Wrench,
  BarChart3,
  Target,
  Route,
  BookOpen,
  AlertTriangle,
  ShieldCheck,
  Terminal,
  Quote,
  Star,
  Sparkles,
  Loader2,
  Crosshair,
  Compass,
} from 'lucide-react';

const easeOutExpo = [0.16, 1, 0.3, 1] as [number, number, number, number];
const easeSpring = [0.175, 0.885, 0.32, 1.275] as [number, number, number, number];



/* ──────────────────────── GLOBE 3D ──────────────────────── */

function Globe3D() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rotationRef = useRef(0);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const size = 320;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    const radius = 140;
    const dots: { lat: number; lon: number }[] = [];
    for (let i = 0; i < 80; i++) {
      dots.push({
        lat: Math.acos(2 * Math.random() - 1) - Math.PI / 2,
        lon: Math.random() * Math.PI * 2,
      });
    }

    function project(lat: number, lon: number, rotY: number) {
      const x3d = Math.cos(lat) * Math.sin(lon + rotY);
      const y3d = Math.sin(lat);
      const z3d = Math.cos(lat) * Math.cos(lon + rotY);
      const scale = radius / (radius * 0.5 + z3d * radius * 0.5 + 200);
      return {
        x: size / 2 + x3d * radius * 200 * scale,
        y: size / 2 - y3d * radius * 200 * scale,
        z: z3d,
        scale,
      };
    }

    function draw() {
      if (!ctx) return;
      ctx.clearRect(0, 0, size, size);
      rotationRef.current += 0.002;
      const rotY = rotationRef.current;

      // Wireframe circles
      ctx.strokeStyle = 'rgba(33, 158, 188, 0.15)';
      ctx.lineWidth = 1;

      // Latitude lines
      for (let lat = -Math.PI / 2 + 0.3; lat < Math.PI / 2; lat += 0.3) {
        ctx.beginPath();
        for (let lon = 0; lon <= Math.PI * 2; lon += 0.05) {
          const p = project(lat, lon, rotY);
          if (lon === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        }
        ctx.stroke();
      }

      // Longitude lines
      for (let lon = 0; lon < Math.PI * 2; lon += 0.3) {
        ctx.beginPath();
        for (let lat = -Math.PI / 2; lat <= Math.PI / 2; lat += 0.05) {
          const p = project(lat, lon, rotY);
          if (lat === -Math.PI / 2) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        }
        ctx.stroke();
      }

      // Outline
      ctx.beginPath();
      ctx.arc(size / 2, size / 2, radius, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(33, 158, 188, 0.25)';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Dots (POI markers)
      dots.forEach((dot, i) => {
        const p = project(dot.lat, dot.lon, rotY);
        if (p.z > -0.2) {
          const pulse = Math.sin(Date.now() * 0.003 + i) * 0.3 + 0.7;
          ctx.beginPath();
          ctx.arc(p.x, p.y, 2.5 * p.scale * 100, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(46, 196, 182, ${0.6 * pulse})`;
          ctx.fill();

          // Glow
          ctx.beginPath();
          ctx.arc(p.x, p.y, 6 * p.scale * 100, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(46, 196, 182, ${0.15 * pulse})`;
          ctx.fill();
        }
      });

      animRef.current = requestAnimationFrame(draw);
    }

    draw();
    return () => cancelAnimationFrame(animRef.current);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: '320px', height: '320px' }}
      className="opacity-0 animate-fade-in"
    />
  );
}

/* ──────────────────────── FLOATING PARTICLES ──────────────────────── */

function FloatingParticles() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = window.innerWidth;
    const h = 400;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    const particles = Array.from({ length: 30 }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      size: 2 + Math.random() * 4,
      speed: 0.2 + Math.random() * 0.5,
      opacity: 0.1 + Math.random() * 0.15,
    }));

    function draw() {
      if (!ctx) return;
      ctx.clearRect(0, 0, w, h);

      particles.forEach((p) => {
        p.y -= p.speed;
        if (p.y < -10) {
          p.y = h + 10;
          p.x = Math.random() * w;
        }
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(46, 196, 182, ${p.opacity})`;
        ctx.fill();
      });

      animRef.current = requestAnimationFrame(draw);
    }

    draw();
    return () => cancelAnimationFrame(animRef.current);
  }, []);

  return <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', zIndex: 0, pointerEvents: 'none' }} />;
}

/* ──────────────────────── CIRCULAR PROGRESS ──────────────────────── */

function CircularProgress({ value, size, strokeWidth, delay = 0 }: { value: number; size: number; strokeWidth: number; delay?: number }) {
  const [inView, setInView] = useState(false);
  const ref = useRef<SVGSVGElement>(null);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setInView(true); observer.disconnect(); } },
      { threshold: 0.3 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <svg ref={ref} width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={strokeWidth} />
      <circle
        cx={size / 2} cy={size / 2} r={radius}
        fill="none"
        stroke="#2EC4B6"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={inView ? circumference * (1 - value / 100) : circumference}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        style={{ transition: `stroke-dashoffset 2s cubic-bezier(0.16, 1, 0.3, 1) ${delay}s` }}
      />
    </svg>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
                              HOME PAGE
   ═══════════════════════════════════════════════════════════════════════ */

export default function Home() {
  return (
    <div className="overflow-x-hidden">
      <HeroSection />
      <ProblemSection />
      <SolutionSection />
      <LiveDemoSection />
      <FeatureGridSection />
      <HowItWorksSection />
      <MetricsDashboardSection />
      <TestimonialsSection />
      <CTASection />
    </div>
  );
}

/* ═══════════════════════ SECTION 1: HERO ═══════════════════════ */

function HeroSection() {
  return (
    <section className="relative min-h-[100dvh] flex items-center justify-center overflow-hidden">
      {/* Background map */}
      <div className="absolute inset-0 z-0">
        <img
          src="/hero-world-map.png"
          alt=""
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, rgba(10,36,99,0.7) 0%, rgba(10,36,99,0.85) 100%)' }} />
      </div>

      {/* 3D Globe centered */}
      <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none">
        <div className="scale-75 md:scale-100 lg:scale-125">
          <Globe3D />
        </div>
      </div>

      {/* Content */}
      <div className="relative z-20 text-center px-6 max-w-[800px] mx-auto">
        <motion.h1
          className="font-display text-4xl sm:text-5xl md:text-6xl lg:text-[4.5rem] font-bold text-white leading-[1.1] tracking-[-0.02em]"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: easeOutExpo, delay: 0.5 }}
        >
          更智能的旅行规划，透明的AI决策
        </motion.h1>

        <motion.p
          className="mt-6 text-base sm:text-lg leading-relaxed max-w-[560px] mx-auto"
          style={{ color: 'rgba(255,255,255,0.7)' }}
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: easeOutExpo, delay: 1.0 }}
        >
          WanderMind为您规划完美旅行，并清晰展示思考过程——每一次工具调用、每一段记忆、每一个决定。
        </motion.p>

        <motion.div
          className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: easeSpring, delay: 1.3 }}
        >
          <Link
            to="/app"
            className="inline-flex items-center justify-center px-8 py-3.5 rounded-full text-white font-semibold text-lg transition-all duration-300 hover:scale-105 hover:shadow-glow-coral"
            style={{ background: '#E29578' }}
          >
            开始规划
          </Link>
          <a
            href="#how-it-works"
            className="inline-flex items-center justify-center px-8 py-3.5 rounded-full text-white font-semibold text-lg border border-white/30 transition-all duration-300 hover:bg-white/10"
          >
            查看工作流程
          </a>
        </motion.div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.8, duration: 0.5 }}
      >
        <ChevronDown className="w-8 h-8 text-[#8ECAE6] animate-bounce-gentle" />
      </motion.div>
    </section>
  );
}

/* ═════════════════════ SECTION 2: PROBLEM ═════════════════════ */

function ProblemSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-20%' });

  const painPoints = [
    { icon: EyeOff, title: '推理过程不透明', desc: '无法了解AI如何做出决定或使用了哪些数据' },
    { icon: Database, title: '隐藏的假设', desc: '您的偏好可能被忽视，而您甚至不知道' },
    { icon: Shield, title: '安全盲点', desc: '关键安全考虑可能被无声地忽视' },
  ];

  return (
    <section className="bg-[#EDF6F9] py-24 sm:py-32 px-6" ref={ref}>
      <div className="max-w-[1200px] mx-auto flex flex-col lg:flex-row gap-16">
        {/* Left Column */}
        <motion.div
          className="lg:w-[55%]"
          initial={{ opacity: 0, x: -50 }}
          animate={inView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.7, ease: easeOutExpo }}
        >
          <span className="text-xs font-mono uppercase tracking-[0.1em] text-[#2EC4B6]">
            问题所在
          </span>
          <h2 className="mt-4 font-display text-3xl sm:text-4xl md:text-[2.5rem] font-semibold text-[#0A2463] leading-[1.2] tracking-[-0.01em]">
            大多数AI旅行代理是黑匣子
          </h2>
          <p className="mt-5 text-base text-[rgba(10,36,99,0.7)] leading-relaxed max-w-[480px]">
            您请求一个行程计划，得到一个完美的行程表——但您不知道它是如何制作的。预算被尊重了吗？建议基于真实数据吗？您能相信建议的安全性吗？
          </p>

          {/* Stat Card */}
          <div className="mt-8 p-6 rounded-xl" style={{ background: 'rgba(10,36,99,0.03)', border: '1px solid rgba(10,36,99,0.08)' }}>
            <ShieldAlert className="w-7 h-7 text-[#EF476F]" />
            <div className="mt-3 font-mono text-5xl font-bold text-[#EF476F]">
              73%
            </div>
            <p className="mt-2 text-sm text-[rgba(10,36,99,0.6)]">
              73%的旅客不相信没有透明度的AI生成的行程
            </p>
          </div>
        </motion.div>

        {/* Right Column - Pain Point Cards */}
        <div className="lg:w-[45%] flex flex-col gap-4">
          {painPoints.map((point, i) => (
            <motion.div
              key={point.title}
              className="p-5 rounded-lg glass-card-dark-bg"
              initial={{ opacity: 0, y: 30 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, ease: easeOutExpo, delay: 0.12 * i }}
            >
              <point.icon className="w-7 h-7 text-[#0A2463]" />
              <h3 className="mt-3 font-display text-xl font-semibold text-[#0A2463]">
                {point.title}
              </h3>
              <p className="mt-2 text-sm text-[rgba(10,36,99,0.6)]">
                {point.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ═════════════════════ SECTION 3: SOLUTION ═════════════════════ */

function SolutionSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-20%' });

  return (
    <section className="bg-[#0A2463] py-24 sm:py-32 px-6" ref={ref}>
      <div className="max-w-[900px] mx-auto text-center">
        <motion.span
          className="text-xs font-mono uppercase tracking-[0.1em] text-[#2EC4B6]"
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: easeOutExpo }}
        >
          解决方案
        </motion.span>

        <motion.h2
          className="mt-4 font-display text-3xl sm:text-4xl md:text-[3.5rem] font-bold text-white leading-[1.15] tracking-[-0.02em]"
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: easeOutExpo, delay: 0.1 }}
        >
          完全透明，从始至终
        </motion.h2>

        <motion.p
          className="mt-5 text-base sm:text-lg leading-relaxed max-w-[560px] mx-auto"
          style={{ color: 'rgba(255,255,255,0.6)' }}
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: easeOutExpo, delay: 0.2 }}
        >
          WanderMind公开其所有推理步骤——从工具调用到记忆检索到不确定性披露——让您可以信任并优化您的旅行计划。
        </motion.p>

        {/* Rotating Cube */}
        <motion.div
          className="mt-16 flex justify-center perspective-1000"
          initial={{ opacity: 0, scale: 0.5 }}
          animate={inView ? { opacity: 1, scale: 1 } : {}}
          transition={{ duration: 1, ease: easeSpring, delay: 0.3 }}
        >
          <RotatingCube />
        </motion.div>
      </div>
    </section>
  );
}

/* Rotating Cube */

function RotatingCube() {
  const rotation = useRef(0);
  const rafRef = useRef(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function animate() {
      rotation.current += 0.003;
      if (containerRef.current) {
        containerRef.current.style.transform = `rotateX(${rotation.current * 0.7 * 57.3}deg) rotateY(${rotation.current * 57.3}deg)`;
      }
      rafRef.current = requestAnimationFrame(animate);
    }
    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  const faceIcons = [
    { icon: MessageSquare, label: '聊天' },
    { icon: MapPin, label: '地图' },
    { icon: Brain, label: '推理' },
    { icon: Shield, label: '安全' },
    { icon: Compass, label: '规划' },
    { icon: Database, label: '记忆' },
  ];

  const transforms = [
    'translateZ(100px)',
    'rotateY(180deg) translateZ(100px)',
    'rotateY(-90deg) translateZ(100px)',
    'rotateY(90deg) translateZ(100px)',
    'rotateX(90deg) translateZ(100px)',
    'rotateX(-90deg) translateZ(100px)',
  ];

  return (
    <div className="relative w-[200px] h-[200px] preserve-3d" style={{ transformStyle: 'preserve-3d' }} ref={containerRef}>
      {faceIcons.map((face, i) => (
        <div
          key={face.label}
          className="absolute inset-0 flex flex-col items-center justify-center backface-hidden"
          style={{
            transform: transforms[i],
            background: 'rgba(255,255,255,0.1)',
            border: '2px solid rgba(33,158,188,0.5)',
            width: '200px',
            height: '200px',
          }}
        >
          <face.icon className="w-10 h-10 text-white" />
          <span className="mt-2 text-xs text-white/70">{face.label}</span>
        </div>
      ))}
    </div>
  );
}

// MapPin needs to be defined since lucide doesn't have it directly
function MapPin({ className }: { className?: string }) {
  return <Crosshair className={className} />;
}

/* ═══════════════════ SECTION 4: LIVE DEMO ═══════════════════ */

function LiveDemoSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-25%' });

  const metrics = [
    { label: '约束满足度', value: 94, color: '#06D6A0' },
    { label: '路线合理性', value: 87, color: '#06D6A0' },
    { label: '来源可溯性', value: 100, color: '#06D6A0' },
    { label: '不确定性披露', value: 78, color: '#FFD166' },
    { label: '安全合规性', value: 96, color: '#06D6A0' },
  ];

  return (
    <section className="bg-[#EDF6F9] py-24 sm:py-32 px-6" ref={ref}>
      <div className="max-w-[1400px] mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: easeOutExpo }}
        >
          <span className="text-xs font-mono uppercase tracking-[0.1em] text-[#1A659E]">
            实时演示
          </span>
          <h2 className="mt-3 font-display text-3xl sm:text-4xl md:text-[2.5rem] font-semibold text-[#0A2463] leading-[1.2] tracking-[-0.01em]">
            实时观看AI的思考过程
          </h2>
          <p className="mt-3 text-base text-[rgba(10,36,99,0.6)] max-w-[600px]">
            观看每一次工具调用、每一次记忆检索和每一个推理步骤，看您的行程如何逐步生成。
          </p>
        </motion.div>

        {/* Demo Container */}
        <motion.div
          className="mt-12 p-6 sm:p-10 rounded-[24px]"
          style={{ background: 'rgba(10,36,99,0.02)', border: '1px solid rgba(10,36,99,0.1)' }}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={inView ? { opacity: 1, scale: 1 } : {}}
          transition={{ duration: 0.8, ease: easeOutExpo }}
        >
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Left Panel - Chat */}
            <motion.div
              className="lg:w-[35%] flex flex-col gap-3"
              initial={{ opacity: 0, x: -40 }}
              animate={inView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.6, ease: easeOutExpo, delay: 0.2 }}
            >
              {/* User message */}
              <div className="flex items-start gap-2">
                <div className="w-8 h-8 rounded-full bg-[#0A2463] flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-xs font-bold">U</span>
                </div>
                <div className="p-3 rounded-xl text-sm text-[#0A2463]" style={{ background: 'rgba(10,36,99,0.05)' }}>
                  我想规划一个5天的东京之旅，预算$2,000。我喜欢寺庙、拉面和摄影。
                </div>
              </div>

              {/* AI response */}
              <div className="flex items-start gap-2">
                <div className="w-8 h-8 rounded-full bg-[#1A659E] flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <div className="p-3 rounded-xl text-sm text-white bg-[#1A659E]">
                  很好的选择！我为您规划一个东京之旅。让我先检查安全条件并搜索景点...
                </div>
              </div>

              {/* AI Thinking Indicator */}
              <div className="flex items-center gap-1 ml-10">
                <div className="w-2 h-2 rounded-full bg-[#219EBC] animate-pulse" />
                <div className="w-2 h-2 rounded-full bg-[#219EBC] animate-pulse" style={{ animationDelay: '0.2s' }} />
                <div className="w-2 h-2 rounded-full bg-[#219EBC] animate-pulse" style={{ animationDelay: '0.4s' }} />
              </div>
            </motion.div>

            {/* Center Panel - Tool Calls */}
            <motion.div
              className="lg:w-[30%]"
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, ease: easeOutExpo, delay: 0.4 }}
            >
              <div className="flex items-center gap-2 mb-4">
                <Wrench className="w-5 h-5 text-[#0A2463]" />
                <h3 className="font-display text-xl font-semibold text-[#0A2463]">工具调用</h3>
              </div>

              <div className="space-y-3">
                <div className="p-3 rounded-lg font-mono text-xs" style={{ background: 'rgba(10,36,99,0.05)', borderLeft: '3px solid #118AB2' }}>
                  <div className="text-[#2EC4B6] font-medium">search_safety_db</div>
                  <div className="text-[rgba(10,36,99,0.6)] mt-1">{`{location: "Tokyo"}`}</div>
                  <div className="flex items-center gap-2 mt-2">
                    <Loader2 className="w-3 h-3 animate-spin text-[#118AB2]" />
                    <span className="text-[#118AB2]">Running...</span>
                  </div>
                </div>

                <div className="p-3 rounded-lg font-mono text-xs" style={{ background: 'rgba(10,36,99,0.05)', borderLeft: '3px solid #118AB2' }}>
                  <div className="text-[#2EC4B6] font-medium">search_pois</div>
                  <div className="text-[rgba(10,36,99,0.6)] mt-1">{`{city: "Tokyo", interests: ["temples", "ramen"]}`}</div>
                  <div className="mt-2 text-[rgba(10,36,99,0.4)]">Pending</div>
                </div>
              </div>
            </motion.div>

            {/* Right Panel - Evaluation */}
            <motion.div
              className="lg:w-[35%]"
              initial={{ opacity: 0, x: 40 }}
              animate={inView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.6, ease: easeOutExpo, delay: 0.6 }}
            >
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="w-5 h-5 text-[#0A2463]" />
                <h3 className="font-display text-xl font-semibold text-[#0A2463]">评估指标</h3>
              </div>

              <div className="space-y-3">
                {metrics.map((m) => (
                  <div key={m.label} className="flex items-center gap-3">
                    <span className="text-xs text-[rgba(10,36,99,0.7)] flex-1 min-w-0 truncate">{m.label}</span>
                    <div className="w-24 h-1 rounded-full bg-[rgba(10,36,99,0.08)] overflow-hidden">
                      <motion.div
                        className="h-full rounded-full"
                        style={{ background: `linear-gradient(90deg, #2EC4B6 0%, ${m.color} 100%)` }}
                        initial={{ width: 0 }}
                        animate={inView ? { width: `${m.value}%` } : { width: 0 }}
                        transition={{ duration: 1.5, ease: easeOutExpo, delay: 1 }}
                      />
                    </div>
                    <span className="text-xs font-mono font-semibold w-8 text-right" style={{ color: m.color }}>
                      {inView ? <CountUp end={m.value} duration={1.5} delay={1} /> : 0}%
                    </span>
                  </div>
                ))}
              </div>

              {/* Overall Score */}
              <div className="mt-6 flex items-center justify-center">
                <div className="relative">
                  <CircularProgress value={91} size={80} strokeWidth={6} delay={1.2} />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="font-mono text-lg font-bold text-[#0A2463]">
                      {inView ? <CountUp end={91} duration={1.5} delay={1.2} /> : 0}%
                    </span>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

/* ═══════════════════ SECTION 5: FEATURE GRID ═══════════════════ */

function FeatureGridSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-20%' });

  const features = [
    { icon: MessageSquare, title: '智能聊天', desc: '与您的AI旅行代理自然对话。用您自己的话描述您梦想的旅行，观看它理解您的意图。' },
    { icon: Calendar, title: '可视化行程', desc: '您的旅行显示为漂亮的时间线，包含每日活动、时间估计和位置标记。' },
    { icon: Map, title: '交互式地图', desc: '在交互式地图上查看每个景点，包含优化路线、步行方向和旅行时间。' },
    { icon: Eye, title: '可解释的AI', desc: '每个决定都有解释。查看推理链、工具调用、记忆使用和置信度分数，获得完全的透明度。' },
    { icon: Shield, title: '安全第一', desc: '针对全球数据库的实时安全检查。每条建议都经过审查以了解当前条件和警告。' },
    { icon: Brain, title: '记忆和学习', desc: '代理在会话之间记住您的偏好，建立旅行档案，改进每条建议。' },
  ];

  return (
    <section className="bg-[#0A2463] py-24 sm:py-32 px-6" ref={ref}>
      <div className="max-w-[1400px] mx-auto">
        <div className="text-center">
          <motion.span
            className="text-xs font-mono uppercase tracking-[0.1em] text-[#2EC4B6]"
            initial={{ opacity: 0, y: 30 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, ease: easeOutExpo }}
          >
            功能特性
          </motion.span>
          <motion.h2
            className="mt-4 font-display text-3xl sm:text-4xl md:text-[3.5rem] font-bold text-white leading-[1.15] tracking-[-0.02em] max-w-[700px] mx-auto"
            initial={{ opacity: 0, y: 30 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, ease: easeOutExpo, delay: 0.1 }}
          >
            自信规划所需的一切
          </motion.h2>
        </div>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-2 gap-6">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              className="glass-card p-8 rounded-xl group cursor-default"
              initial={{ opacity: 0, y: 40 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.7, ease: easeOutExpo, delay: 0.1 * i }}
              whileHover={{ y: -8, transition: { duration: 0.4, ease: [0.4, 0, 0.2, 1] } }}
            >
              <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ background: 'rgba(255,255,255,0.08)' }}>
                <feature.icon className="w-5 h-5 text-[#8ECAE6]" />
              </div>
              <h3 className="mt-5 font-display text-2xl font-semibold text-white">
                {feature.title}
              </h3>
              <p className="mt-3 text-base leading-relaxed" style={{ color: 'rgba(255,255,255,0.6)' }}>
                {feature.desc}
              </p>
              <span className="mt-4 inline-block text-sm text-[#8ECAE6] group-hover:text-[#E29578] transition-colors duration-300">
                了解更多 &rarr;
              </span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ═══════════════════ SECTION 6: HOW IT WORKS ═══════════════════ */

function HowItWorksSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-30%' });

  const steps = [
    { title: '描述您的旅行', desc: '告诉AI您想去的地方、预算、旅行日期、兴趣和任何约束。细节越多，计划越好。' },
    { title: 'AI推理过程', desc: '观看代理调用工具、搜索数据库、检索记忆和评估选项——所有过程都实时可见。' },
    { title: '审查并优化', desc: '获得完整的行程表，包括地图可视化、评估分数和解释面板。根据需要调整任何内容。' },
    { title: '自信地旅行', desc: '导出您的行程表、接收安全提醒并享受通过完全透明和AI驱动的智能规划的旅行。' },
  ];

  return (
    <section id="how-it-works" className="bg-[#EDF6F9] py-24 sm:py-32 px-6" ref={ref}>
      <div className="max-w-[1200px] mx-auto">
        <div className="text-center">
          <motion.span
            className="text-xs font-mono uppercase tracking-[0.1em] text-[#1A659E]"
            initial={{ opacity: 0, y: 30 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, ease: easeOutExpo }}
          >
            工作流程
          </motion.span>
          <motion.h2
            className="mt-4 font-display text-3xl sm:text-4xl md:text-[2.5rem] font-semibold text-[#0A2463] leading-[1.2] tracking-[-0.01em]"
            initial={{ opacity: 0, y: 30 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, ease: easeOutExpo, delay: 0.1 }}
          >
            从对话到行程表的4个步骤
          </motion.h2>
        </div>

        {/* Timeline */}
        <div className="mt-16 relative">
          {/* Vertical Line */}
          <div className="absolute left-1/2 top-0 bottom-0 w-[3px] bg-[#2EC4B6] -translate-x-1/2 hidden lg:block" />

          <div className="space-y-12 lg:space-y-0">
            {steps.map((step, i) => (
              <motion.div
                key={step.title}
                className={`relative lg:w-[45%] ${i % 2 === 0 ? 'lg:mr-auto lg:pr-12' : 'lg:ml-auto lg:pl-12'} lg:mb-16 last:lg:mb-0`}
                initial={{ opacity: 0, x: i % 2 === 0 ? -50 : 50 }}
                animate={inView ? { opacity: 1, x: 0 } : {}}
                transition={{ duration: 0.7, ease: easeOutExpo, delay: 0.15 * i }}
              >
                {/* Step Node */}
                <div className="hidden lg:flex absolute top-0 w-12 h-12 rounded-full bg-[#1A659E] items-center justify-center z-10"
                  style={{
                    [i % 2 === 0 ? 'right' : 'left']: '-24px',
                    boxShadow: '0 0 20px rgba(46,196,182,0.3)',
                  }}
                >
                  <span className="text-white font-display font-bold text-lg">{i + 1}</span>
                </div>

                <div className="lg:hidden flex items-center gap-4 mb-4">
                  <div className="w-10 h-10 rounded-full bg-[#1A659E] flex items-center justify-center">
                    <span className="text-white font-display font-bold">{i + 1}</span>
                  </div>
                  <div className="w-12 h-[2px] bg-[#2EC4B6]" />
                </div>

                <div className="p-7 rounded-lg glass-card-dark-bg">
                  <h3 className="font-display text-2xl font-semibold text-[#0A2463]">{step.title}</h3>
                  <p className="mt-3 text-base leading-relaxed text-[rgba(10,36,99,0.7)]">{step.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ═════════════════ SECTION 7: METRICS DASHBOARD ═════════════════ */

function MetricsDashboardSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-25%' });

  const metrics = [
    { icon: Target, label: '约束满足度', value: 94, badge: 'green' },
    { icon: Route, label: '路线合理性', value: 87, badge: 'green' },
    { icon: BookOpen, label: '来源可溯性', value: 100, badge: 'green' },
    { icon: AlertTriangle, label: '不确定性披露', value: 78, badge: 'amber' },
    { icon: ShieldCheck, label: '安全合规性', value: 96, badge: 'green' },
  ];

  const toolCalls = [
    '[10:23:45] 查询_安全_数据库(地点="东京") → 找到3个警告',
    '[10:23:47] 搜索_景点(城市="东京", 兴趣=["寺庙"]) → 12个结果',
    '[10:23:50] 计算_路线(路点=[...]) → 总长4.2公里',
  ];

  return (
    <section className="bg-[#0A2463] py-24 sm:py-32 px-6" ref={ref}>
      <div className="max-w-[1100px] mx-auto">
        <div className="text-center">
          <motion.span
            className="text-xs font-mono uppercase tracking-[0.1em] text-[#2EC4B6]"
            initial={{ opacity: 0, y: 30 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, ease: easeOutExpo }}
          >
            评估仪表板
          </motion.span>
          <motion.h2
            className="mt-4 font-display text-3xl sm:text-4xl md:text-[3.5rem] font-bold text-white leading-[1.15] tracking-[-0.02em]"
            initial={{ opacity: 0, y: 30 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, ease: easeOutExpo, delay: 0.1 }}
          >
            内置质量保证
          </motion.h2>
          <motion.p
            className="mt-4 text-base sm:text-lg leading-relaxed max-w-[600px] mx-auto"
            style={{ color: 'rgba(255,255,255,0.6)' }}
            initial={{ opacity: 0, y: 30 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, ease: easeOutExpo, delay: 0.2 }}
          >
            每个行程表都会自动在5个关键维度中进行评估。查看分数并深入了解详情。
          </motion.p>
        </div>

        {/* Dashboard Container */}
        <motion.div
          className="mt-16 glass-card rounded-[24px] p-6 sm:p-10"
          initial={{ opacity: 0, y: 40 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8, ease: easeOutExpo, delay: 0.3 }}
        >
          <div className="flex flex-col lg:flex-row gap-10">
            {/* Left - Metric Cards */}
            <div className="lg:w-[60%] space-y-4">
              {metrics.map((m, i) => (
                <motion.div
                  key={m.label}
                  className="flex items-center gap-4 p-5 rounded-lg"
                  style={{ background: 'rgba(255,255,255,0.03)' }}
                  initial={{ opacity: 0, x: -30 }}
                  animate={inView ? { opacity: 1, x: 0 } : {}}
                  transition={{ duration: 0.6, ease: easeOutExpo, delay: 0.1 * i + 0.5 }}
                >
                  <m.icon className="w-6 h-6 text-[#8ECAE6] flex-shrink-0" />
                  <span className="text-sm flex-1 min-w-0" style={{ color: 'rgba(255,255,255,0.7)' }}>{m.label}</span>
                  <div className="w-[120px] h-1.5 rounded-full bg-white/[0.08] overflow-hidden hidden sm:block">
                    <motion.div
                      className="h-full rounded-full"
                      style={{ background: m.badge === 'green' ? '#06D6A0' : '#FFD166' }}
                      initial={{ width: 0 }}
                      animate={inView ? { width: `${m.value}%` } : { width: 0 }}
                      transition={{ duration: 1.5, ease: easeOutExpo, delay: 0.5 + 0.1 * i }}
                    />
                  </div>
                  <span className="font-mono text-lg font-bold flex-shrink-0" style={{ color: m.badge === 'green' ? '#06D6A0' : '#FFD166' }}>
                    {inView ? <CountUp end={m.value} duration={2} delay={0.5 + 0.1 * i} /> : 0}%
                  </span>
                </motion.div>
              ))}
            </div>

            {/* Right - Overall Score */}
            <div className="lg:w-[40%] flex flex-col items-center justify-center">
              <div className="relative">
                <CircularProgress value={91} size={160} strokeWidth={10} delay={0.5} />
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="font-display text-5xl font-bold text-white">
                    {inView ? <CountUp end={91} duration={2} delay={0.5} /> : 0}
                  </span>
                  <span className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.5)' }}>总体评分</span>
                </div>
                {/* Grade badge */}
                <motion.div
                  className="absolute -top-2 -right-2 w-12 h-12 rounded-full bg-[#2EC4B6] flex items-center justify-center"
                  initial={{ scale: 0 }}
                  animate={inView ? { scale: 1 } : {}}
                  transition={{ duration: 0.5, ease: easeSpring, delay: 1.5 }}
                >
                  <span className="text-white font-display font-bold text-xl">A</span>
                </motion.div>
              </div>
            </div>
          </div>

          {/* Tool Call Log Preview */}
          <div className="mt-8 pt-6 border-t border-white/[0.06]">
            <div className="flex items-center gap-2 mb-4">
              <Terminal className="w-5 h-5 text-white" />
              <h3 className="font-display text-xl font-semibold text-white">最近的工具调用</h3>
            </div>
            <div className="space-y-2">
              {toolCalls.map((log, i) => (
                <motion.div
                  key={i}
                  className="p-2.5 rounded font-mono text-xs"
                  style={{ background: 'rgba(255,255,255,0.03)' }}
                  initial={{ opacity: 0 }}
                  animate={inView ? { opacity: 1 } : {}}
                  transition={{ duration: 0.3, delay: 1 + 0.3 * i }}
                >
                  <span className="text-[#8ECAE6]">{log.match(/\[.*?\]/)?.[0]}</span>
                  {' '}
                  <span className="text-[#2EC4B6]">{log.match(/search_\w+/)?.[0]}</span>
                  <span className="text-white/60">{log.replace(/\[.*?\]\s*search_\w+/, '')}</span>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

/* ═══════════════════ SECTION 8: TESTIMONIALS ═══════════════════ */

function TestimonialsSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-20%' });

  const testimonials = [
    {
      name: 'Sarah Chen',
      role: '旅行摄影师',
      avatar: '/avatar-1.jpg',
      quote: "透明度是让我信服的原因。我可以准确看到为什么它推荐每个地点，它使用了哪个工具，它的信心程度如何。就像有一个旅行代理解释每一个决定。",
    },
    {
      name: 'Marcus Johnson',
      role: '商务旅客',
      avatar: '/avatar-2.jpg',
      quote: "我一年规划20多次旅行。WanderMind的评估仪表板让我确信我的约束实际上得到满足——预算、时间、安全。记忆功能完美记住了我的偏好。",
    },
    {
      name: 'David Park',
      role: '独自背包客',
      avatar: '/avatar-3.jpg',
      quote: "安全合规功能发现了一个我不知道的旅行警告。代理标记了它、解释了不确定性并提供了替代方案。这正是我需要的透明度。",
    },
  ];

  return (
    <section className="bg-[#EDF6F9] py-24 sm:py-32 px-6" ref={ref}>
      <div className="max-w-[1200px] mx-auto">
        <div className="text-center">
          <motion.span
            className="text-xs font-mono uppercase tracking-[0.1em] text-[#1A659E]"
            initial={{ opacity: 0, y: 30 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, ease: easeOutExpo }}
          >
            用户评价
          </motion.span>
          <motion.h2
            className="mt-4 font-display text-3xl sm:text-4xl md:text-[2.5rem] font-semibold text-[#0A2463] leading-[1.2] tracking-[-0.01em]"
            initial={{ opacity: 0, y: 30 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, ease: easeOutExpo, delay: 0.1 }}
          >
            受全球旅客信赖
          </motion.h2>
        </div>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6">
          {testimonials.map((t, i) => (
            <motion.div
              key={t.name}
              className="bg-white rounded-xl p-8 shadow-md relative"
              style={{ border: '1px solid rgba(10,36,99,0.08)' }}
              initial={{ opacity: 0, y: 40, scale: 0.95 }}
              animate={inView ? { opacity: 1, y: 0, scale: 1 } : {}}
              transition={{ duration: 0.7, ease: easeOutExpo, delay: 0.15 * i }}
            >
              <Quote className="w-8 h-8 text-[#8ECAE6] opacity-30" />
              <p className="mt-4 text-base sm:text-lg italic leading-relaxed text-[#0A2463]">
                &ldquo;{t.quote}&rdquo;
              </p>

              <div className="w-10 h-[2px] bg-[#8ECAE6] my-5" />

              <div className="flex items-center gap-3">
                <img src={t.avatar} alt={t.name} className="w-12 h-12 rounded-full object-cover" />
                <div>
                  <div className="font-display text-lg font-semibold text-[#0A2463]">{t.name}</div>
                  <div className="text-sm text-[rgba(10,36,99,0.5)]">{t.role}</div>
                </div>
              </div>

              <div className="flex items-center gap-1 mt-3">
                {[...Array(5)].map((_, j) => (
                  <Star key={j} className="w-4 h-4 fill-[#FF9F1C] text-[#FF9F1C]" />
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ═════════════════════ SECTION 9: CTA ═════════════════════ */

function CTASection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-20%' });

  return (
    <section className="relative bg-[#0A2463] py-24 sm:py-32 px-6 overflow-hidden" ref={ref}>
      {/* Decorative particles */}
      <FloatingParticles />

      <div className="relative z-10 max-w-[700px] mx-auto text-center">
        <motion.h2
          className="font-display text-3xl sm:text-4xl md:text-[3.5rem] font-bold text-white leading-[1.15] tracking-[-0.02em]"
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8, ease: easeOutExpo }}
        >
          准备好规划您的下一场冒险了吗？
        </motion.h2>

        <motion.p
          className="mt-5 text-base sm:text-lg leading-relaxed max-w-[500px] mx-auto"
          style={{ color: 'rgba(255,255,255,0.6)' }}
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: easeOutExpo, delay: 0.2 }}
        >
          加入数千名有信心规划旅行的旅客。立即开始您的透明AI驱动的旅程。
        </motion.p>

        <motion.div
          className="mt-10"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={inView ? { opacity: 1, scale: 1 } : {}}
          transition={{ duration: 0.5, ease: easeSpring, delay: 0.4 }}
        >
          <Link
            to="/app"
            className="inline-flex items-center justify-center px-10 py-4 rounded-full text-white font-semibold text-xl transition-all duration-300 hover:scale-105 hover:shadow-glow-coral"
            style={{ background: '#E29578' }}
          >
            免费开始
          </Link>
        </motion.div>

        <motion.div
          className="mt-4"
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.5, delay: 0.6 }}
        >
          <a href="#" className="text-base text-[#8ECAE6] hover:text-[#E29578] transition-colors duration-300">
            查看演示 &rarr;
          </a>
        </motion.div>
      </div>
    </section>
  );
}
