import { Link } from 'react-router';
import {
  ArrowRight,
  Brain,
  CloudSun,
  FileText,
  Layers3,
  MapPinned,
  MessageSquareText,
  Puzzle,
  Route,
  Search,
  ShieldCheck,
  Workflow,
} from 'lucide-react';

const toc = [
  { id: 'overview', label: '1. 项目定位' },
  { id: 'architecture', label: '2. 总体架构' },
  { id: 'flow', label: '3. 核心流程' },
  { id: 'agent', label: '4. Agent 与 Skill 设计' },
  { id: 'context', label: '5. 上下文工程' },
  { id: 'memory', label: '6. 记忆与会话' },
  { id: 'tools', label: '7. MCP 与外部工具' },
  { id: 'safety', label: '8. 安全设计' },
  { id: 'evaluation', label: '9. 评测设计' },
  { id: 'tradeoff', label: '10. 设计取舍与扩展点' },
];

const architectureItems = [
  {
    title: '前端展示层',
    desc: '负责承接用户输入、展示规划结果、查看地图 / 时间线 / 记忆 / 工具调用日志，并把后端流式结果同步出来。',
  },
  {
    title: '后端编排层',
    desc: 'FastAPI 作为统一入口，把用户意图、会话状态、工具结果和安全检查串成一条可追踪的执行链路。',
  },
  {
    title: 'Agent 调度层',
    desc: 'Planning Agent 负责推进任务，Review Agent 负责检查质量，具体动作由 Skill 承担。',
  },
  {
    title: '工具与数据层',
    desc: '通过 MCP / API 接入高德、路线、天气、搜索等能力，并把原始结果和压缩结果分开保存。',
  },
];

const flowSteps = [
  '用户输入自然语言需求，例如“成都 3 天游玩，预算 3000，偏好美食和轻松节奏”。',
  '后端先做上下文整理：会话历史、当前约束、工具输出、用户偏好一起进入 ContextManager。',
  'Planning Agent 根据当前状态决定下一步走哪个节点，必要时调用地图、路线、天气等 Skill。',
  'Review Agent 在最后做安全检查、格式整理和结果收口，避免把不稳定内容直接返回给前端。',
];

const skillItems = [
  {
    icon: Search,
    title: '搜索 Skill',
    desc: '负责 POI 检索和地点补充，优先返回可直接用于规划的结果，而不是把原始大段数据直接塞给模型。',
  },
  {
    icon: Route,
    title: '路线 Skill',
    desc: '负责根据地点顺序和交通方式做路线估算，输出更适合展示给用户的距离和耗时信息。',
  },
  {
    icon: CloudSun,
    title: '天气 Skill',
    desc: '负责把多天预报整理成简短描述，供行程安排和风险提示使用。',
  },
  {
    icon: MapPinned,
    title: '地图 Skill',
    desc: '负责地理定位和可视化数据准备，给前端地图展示和导航链路提供坐标信息。',
  },
];

const contextItems = [
  'L1：原始工具结果，只落盘不直接进 Prompt，方便回看和排障。',
  'L2：压缩上下文，把 POI、路线、天气等数据压成结构化摘要，减少 token 浪费。',
  'L3：约束上下文，把预算、天数、节奏、偏好等硬软约束单独管理。',
  'L4：最终 Prompt，只放本轮任务真正需要的最小信息。',
];

const memoryItems = [
  {
    title: '短期记忆',
    desc: '保存最近几轮对话和当前会话状态，保证追问时系统不会丢上下文。',
  },
  {
    title: '长期记忆',
    desc: '保存稳定偏好和历史习惯，例如用户喜欢的节奏、餐饮倾向、出行风格等。',
  },
  {
    title: '会话历史',
    desc: '把每次对话按会话维度存起来，方便前端切换历史会话，也方便后端回放问题。',
  },
];

const safetyItems = [
  '输入侧先识别缺失约束，例如目的地、天数、预算不完整时先追问，不直接硬生成。',
  '工具侧做白名单、参数校验和结果校验，避免异常数据污染后续链路。',
  '输出侧做格式收口和风险提示，保证前端拿到的是可展示、可继续追问的内容。',
  '敏感能力前置拦截，避免模型绕开业务规则直接生成不合规内容。',
];

const evaluationItems = [
  '保留每次规划的工具调用、节点流转和结果快照，方便回放和定位问题。',
  '针对“地点搜索、路线规划、天气整理、预算估算”这些关键能力做样本检查，看输出是否稳定。',
  '把失败案例单独沉淀下来，后续可以针对提示词、技能拆分和上下文压缩规则做回归验证。',
  '评测结果不只看“能不能出方案”，也看“是否遵守约束、是否可读、是否能持续追问”。',
];

const tradeoffItems = [
  {
    title: '为什么不是更多 Agent',
    desc: 'Agent 数量一多，调度复杂度会快速上升。当前方案把复杂度压在 2 个核心 Agent 上，其他能力都沉到底层 Skill。',
  },
  {
    title: '为什么要做上下文压缩',
    desc: '原始工具返回非常长，如果直接进模型，很容易把窗口撑爆。压缩后既保留关键信息，也方便复用和排障。',
  },
  {
    title: '为什么要保留会话历史',
    desc: '用户常常会继续追问、改预算、换节奏。没有会话历史，系统就只能“单轮问答”，很难形成真实可用的产品体验。',
  },
  {
    title: '后续可以继续扩展什么',
    desc: '后面可以继续加强长短期记忆、检索排序、评测闭环和多城市行程编排，但前提是先把当前这条主链路跑稳。',
  },
];

export default function HowItWorks() {
  return (
    <div className="min-h-[calc(100dvh-64px)] bg-[#F7FAFF] text-[#0A2463]">
      <div className="max-w-[1280px] mx-auto px-6 py-10 lg:py-14">
        <div className="max-w-4xl mb-10">
          <div
            className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium mb-4"
            style={{ background: 'rgba(33,158,188,0.12)', color: '#1A659E' }}
          >
            <FileText className="w-3.5 h-3.5" />
            项目技术文档
          </div>
          <h1 className="text-4xl font-bold tracking-tight mb-4" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
            WanderMind 多 Agent 旅行代理全栈实现
          </h1>
          <p
            className="text-base leading-8 max-w-3xl"
            style={{ color: 'rgba(10,36,99,0.78)', fontFamily: "'Inter Variable', Inter, sans-serif" }}
          >
            这一页按技术文档的方式组织，目标是让读者快速理解系统是怎么分层、怎么流转、怎么落地的。内容不展开到逐行实现，但会把设计思路和关键实现讲清楚。
          </p>
        </div>

        <div className="grid lg:grid-cols-[240px_minmax(0,1fr)] gap-6">
          <aside className="lg:sticky lg:top-20 self-start rounded-2xl border border-[#D7E7F3] bg-white p-5 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
            <p className="text-xs font-semibold uppercase tracking-wider mb-4" style={{ color: 'rgba(10,36,99,0.5)' }}>
              目录
            </p>
            <nav className="space-y-2">
              {toc.map((item) => (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  className="block text-sm leading-6 hover:text-[#1A659E] transition-colors"
                  style={{ color: 'rgba(10,36,99,0.82)' }}
                >
                  {item.label}
                </a>
              ))}
            </nav>
          </aside>

          <main className="space-y-6">
            <section id="overview" className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
              <h2 className="text-2xl font-semibold mb-4">1. 项目定位</h2>
              <div className="space-y-3 text-sm leading-7" style={{ color: 'rgba(10,36,99,0.82)' }}>
                <p>
                  WanderMind 是一个面向旅行规划场景的 Agent 化应用。用户输入目的地、天数、预算、偏好之后，系统会自动拆解需求、调用外部工具、组织行程，并把结果流式返回前端。
                </p>
                <p>
                  这个项目的目标不是简单生成一份游记式文案，而是把 Agent 调度、上下文工程、记忆、工具调用、安全检查和评测串成一个完整闭环，让系统既能做事，也能解释自己为什么这么做。
                </p>
              </div>
            </section>

            <section id="architecture" className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
              <h2 className="text-2xl font-semibold mb-4">2. 总体架构</h2>
              <div className="grid md:grid-cols-2 gap-4">
                {architectureItems.map((item) => (
                  <div key={item.title} className="rounded-xl border border-[#E6EEF6] p-4">
                    <h3 className="text-base font-semibold mb-2">{item.title}</h3>
                    <p className="text-sm leading-7" style={{ color: 'rgba(10,36,99,0.78)' }}>
                      {item.desc}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            <section id="flow" className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
              <h2 className="text-2xl font-semibold mb-4">3. 核心流程</h2>
              <div className="space-y-4">
                {flowSteps.map((item, index) => (
                  <div key={item} className="flex gap-3">
                    <div
                      className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold text-white flex-shrink-0"
                      style={{ background: '#1A659E' }}
                    >
                      {index + 1}
                    </div>
                    <p className="text-sm leading-7" style={{ color: 'rgba(10,36,99,0.82)' }}>
                      {item}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            <section id="agent" className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
              <div className="flex items-center gap-2 mb-4">
                <Workflow className="w-4 h-4 text-[#1A659E]" />
                <h2 className="text-2xl font-semibold">4. Agent 与 Skill 设计</h2>
              </div>
              <div className="space-y-4 text-sm leading-7" style={{ color: 'rgba(10,36,99,0.82)' }}>
                <p>
                  这里采用“2 Agent + 多 Skill”的方式。Planning Agent 负责调度和推进，Review Agent 负责校验和收口，具体的搜索、路线、天气、地图等能力沉到 Skill 里。
                </p>
                <p>
                  这样设计的好处是：Agent 数量不会膨胀得太快，流程更稳定；能力扩展时主要加 Skill，不需要把每一步都变成一个新的 Agent；同时也更利于排查问题和做日志追踪。
                </p>
              </div>
              <div className="grid md:grid-cols-2 gap-4 mt-5">
                {skillItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <div key={item.title} className="rounded-xl border border-[#E6EEF6] p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Icon className="w-4 h-4 text-[#2EC4B6]" />
                        <h3 className="font-semibold">{item.title}</h3>
                      </div>
                      <p className="text-sm leading-7" style={{ color: 'rgba(10,36,99,0.78)' }}>
                        {item.desc}
                      </p>
                    </div>
                  );
                })}
              </div>
            </section>

            <section id="context" className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
              <div className="flex items-center gap-2 mb-4">
                <Layers3 className="w-4 h-4 text-[#2EC4B6]" />
                <h2 className="text-2xl font-semibold">5. 上下文工程</h2>
              </div>
              <div className="space-y-3">
                {contextItems.map((item) => (
                  <div key={item} className="flex gap-3 text-sm leading-7" style={{ color: 'rgba(10,36,99,0.82)' }}>
                    <span className="text-[#1A659E] font-semibold">•</span>
                    <span>{item}</span>
                  </div>
                ))}
              </div>
              <p className="text-sm leading-7 mt-4" style={{ color: 'rgba(10,36,99,0.78)' }}>
                这部分的重点是不要把所有原始数据都塞给模型。原始工具结果会保留在外部存储里，模型真正看到的是压缩后的结构化摘要和本轮需要的最小信息。
              </p>
            </section>

            <section id="memory" className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
              <div className="flex items-center gap-2 mb-4">
                <Brain className="w-4 h-4 text-[#FF9F1C]" />
                <h2 className="text-2xl font-semibold">6. 记忆与会话</h2>
              </div>
              <div className="grid md:grid-cols-3 gap-4">
                {memoryItems.map((item) => (
                  <div key={item.title} className="rounded-xl border border-[#E6EEF6] p-4">
                    <h3 className="font-semibold mb-2">{item.title}</h3>
                    <p className="text-sm leading-7" style={{ color: 'rgba(10,36,99,0.78)' }}>
                      {item.desc}
                    </p>
                  </div>
                ))}
              </div>
              <p className="text-sm leading-7 mt-4" style={{ color: 'rgba(10,36,99,0.78)' }}>
                这个设计的目的不是“无限记忆”，而是让系统在当前会话里记得住、跨会话里记得准。对产品来说，这样才可以支持追问、修改预算和连续优化。
              </p>
            </section>

            <section id="tools" className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
              <div className="flex items-center gap-2 mb-4">
                <Puzzle className="w-4 h-4 text-[#E29578]" />
                <h2 className="text-2xl font-semibold">7. MCP 与外部工具</h2>
              </div>
              <div className="space-y-3 text-sm leading-7" style={{ color: 'rgba(10,36,99,0.82)' }}>
                <p>
                  外部能力主要通过工具层接入，核心思路是把搜索、地图、路线、天气等能力统一抽象成可调用工具，而不是让 Agent 直接绑定具体供应商的接口细节。
                </p>
                <p>
                  这样做的好处有两个：一是后续替换数据源时影响更小，二是工具调用可以被统一记录、统一回放，也更方便做异常降级和可观测性分析。
                </p>
              </div>
            </section>

            <section id="safety" className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
              <div className="flex items-center gap-2 mb-4">
                <ShieldCheck className="w-4 h-4 text-[#06D6A0]" />
                <h2 className="text-2xl font-semibold">8. 安全设计</h2>
              </div>
              <div className="space-y-3">
                {safetyItems.map((item) => (
                  <div key={item} className="flex gap-3 text-sm leading-7" style={{ color: 'rgba(10,36,99,0.82)' }}>
                    <span className="text-[#1A659E] font-semibold">•</span>
                    <span>{item}</span>
                  </div>
                ))}
              </div>
              <p className="text-sm leading-7 mt-4" style={{ color: 'rgba(10,36,99,0.78)' }}>
                这一层的核心是前置拦截和降级兜底。与其让模型带着问题一路跑到最终输出，不如在关键节点上先把问题挡住，减少后续返工。
              </p>
            </section>

            <section id="evaluation" className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
              <div className="flex items-center gap-2 mb-4">
                <MessageSquareText className="w-4 h-4 text-[#1A659E]" />
                <h2 className="text-2xl font-semibold">9. 评测设计</h2>
              </div>
              <div className="space-y-3">
                {evaluationItems.map((item) => (
                  <div key={item} className="flex gap-3 text-sm leading-7" style={{ color: 'rgba(10,36,99,0.82)' }}>
                    <span className="text-[#1A659E] font-semibold">•</span>
                    <span>{item}</span>
                  </div>
                ))}
              </div>
              <p className="text-sm leading-7 mt-4" style={{ color: 'rgba(10,36,99,0.78)' }}>
                评测不只是看“能不能生成结果”，还要看“是否遵守约束、是否可读、是否能继续追问、是否在异常输入下仍然稳定”。
              </p>
            </section>

            <section id="tradeoff" className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
              <div className="flex items-center gap-2 mb-4">
                <ArrowRight className="w-4 h-4 text-[#1A659E]" />
                <h2 className="text-2xl font-semibold">10. 设计取舍与扩展点</h2>
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                {tradeoffItems.map((item) => (
                  <div key={item.title} className="rounded-xl border border-[#E6EEF6] p-4">
                    <h3 className="text-base font-semibold mb-2">{item.title}</h3>
                    <p className="text-sm leading-7" style={{ color: 'rgba(10,36,99,0.78)' }}>
                      {item.desc}
                    </p>
                  </div>
                ))}
              </div>
              <div className="mt-5 rounded-xl p-4 text-sm leading-7" style={{ background: 'rgba(33,158,188,0.06)', border: '1px dashed rgba(33,158,188,0.28)' }}>
                这页后面如果要继续扩展，可以优先补“更细的记忆策略”“更完整的评测样本”和“多城市行程编排”三块，但前提还是先把当前主链路稳定住。
              </div>
            </section>

            <div className="flex items-center justify-between rounded-2xl border border-[#D7E7F3] bg-white px-6 py-4 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
              <div>
                <p className="text-sm font-medium">返回应用</p>
                <p className="text-xs mt-1" style={{ color: 'rgba(10,36,99,0.6)' }}>
                  文档页看完以后，可以回到实际产品页面。
                </p>
              </div>
              <Link
                to="/app"
                className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white"
                style={{ background: '#E29578' }}
              >
                回到应用
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
