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
    desc: '负责承接用户输入、展示规划结果、查看地图 / 时间线 / 记忆 / 工具调用日志，并把后端流式结果同步出来。页面本身按面板拆分，方便把不同能力单独展示。',
  },
  {
    title: '后端编排层',
    desc: 'FastAPI 作为统一入口，把用户意图、会话状态、工具结果和安全检查串成一条可追踪的执行链路。这里更像一个工作流调度器，而不是单纯的接口转发层。',
  },
  {
    title: 'Agent 调度层',
    desc: 'Planning Agent 负责推进任务，Review Agent 负责检查质量，具体动作由 Skill 承担。这样做的核心是把“决策”和“执行”分开。',
  },
  {
    title: '工具与数据层',
    desc: '通过 MCP / API 接入高德、路线、天气、搜索等能力，并把原始结果和压缩结果分开保存。工具层负责数据接入，文案生成留给上层。',
  },
];

const flowSteps = [
  '用户输入自然语言需求，例如“成都 3 天游玩，预算 3000，偏好美食和轻松节奏”。',
  '后端先做上下文整理：会话历史、当前约束、工具输出、用户偏好一起进入 ContextManager。',
  'Planning Agent 根据当前状态决定下一步走哪个节点，必要时调用地图、路线、天气等 Skill。',
  'Review Agent 在最后做安全检查、格式整理和结果收口，避免把不稳定内容直接返回给前端。',
  '规划完成后，把本轮结果、工具调用和记忆写入持久化存储，方便后续追问和历史切换。',
];

const skillItems = [
  {
    icon: Search,
    title: '搜索 Skill',
    desc: '负责 POI 检索和地点补充，优先返回可直接用于规划的结果，而不是把原始大段数据直接塞给模型。对冷门地点时，会先做地点抽取，再进入搜索链路。',
  },
  {
    icon: Route,
    title: '路线 Skill',
    desc: '负责根据地点顺序和交通方式做路线估算，输出更适合展示给用户的距离和耗时信息。路线结果会作为后续日程排序的约束之一。',
  },
  {
    icon: CloudSun,
    title: '天气 Skill',
    desc: '负责把多天预报整理成简短描述，供行程安排和风险提示使用。天气信息不会原样灌进 Prompt，而是先压缩成白天 / 夜间 / 温度区间。',
  },
  {
    icon: MapPinned,
    title: '地图 Skill',
    desc: '负责地理定位和可视化数据准备，给前端地图展示和导航链路提供坐标信息。地图层同时承担了“找得到”和“看得懂”两个职责。',
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
    desc: '保存最近几轮对话和当前会话状态，保证追问时系统不会丢上下文。它更像会话工作区，而不是长期知识库。',
  },
  {
    title: '语义记忆',
    desc: '保存稳定偏好和历史习惯，例如用户喜欢的节奏、餐饮倾向、出行风格等。它解决的是“这个用户一直喜欢什么”。',
  },
  {
    title: '情景记忆',
    desc: '保存具体发生过的规划片段和成功案例，便于后续检索同类会话时复用经验。它解决的是“类似场景怎么做过”。',
  },
  {
    title: '过程记忆',
    desc: '保存常用规则、提示词模板和工具调用套路，属于方法层记忆。它解决的是“系统应该按什么方式工作”。',
  },
];

const safetyItems = [
  {
    title: '输入侧',
    desc: '先识别缺失约束，例如目的地、天数、预算不完整时先追问，不直接硬生成。这个层主要防止任务定义不完整导致后面整条链路跑偏。',
  },
  {
    title: '工具侧',
    desc: '做白名单、参数校验和结果校验，避免异常数据污染后续链路。工具层一旦发现返回值不稳定，会直接降级到更保守的策略。',
  },
  {
    title: '日志侧',
    desc: '对日志、记忆、trace 做脱敏处理，避免手机号、邮箱和其他敏感字段进入审计面板。这样既能排障，也不会把原文泄漏出去。',
  },
  {
    title: '动作侧',
    desc: '把高风险动作拦在真正执行前，必要时触发确认流程。系统只给建议和官方入口，不直接越过业务边界替用户完成危险动作。',
  },
];

const evaluationItems = [
  {
    title: 'RACE',
    desc: '用来做场景化综合评分。这里参考的是 RACE 的动态权重思路，不同旅行场景会对“计划完整度、可执行性、约束遵守、表达清晰度”赋予不同权重，而不是所有场景一个分数模板。',
  },
  {
    title: 'DoVer',
    desc: '用来做解释和归因检查。它更关注“为什么会得出这个结论”，以及中间的理由是否前后一致，避免模型只给结果不给依据。',
  },
  {
    title: 'AgentWorld',
    desc: '用来检查行动顺序和状态流转。旅行规划不是只看最后答案，还要看工具调用、节点跳转和回退路径是否合理，所以需要对动作链做一致性核验。',
  },
  {
    title: 'FACT',
    desc: '用来做事实和来源校验。正文里涉及的 POI、路线、天气、预算等信息都要能回到 source_map，避免凭空编造，把“有出处”作为硬要求。',
  },
];

const evaluationLoop = [
  '规划运行时把每次工具调用、节点流转和结果快照都写入 trace，方便回放。',
  '评测时按场景加载权重，分别算出四个维度的分数和失败原因。',
  '失败样本会写入 `failures.jsonl`，后续再按类别聚合，更新规则和提示词。',
  '如果某类问题频繁复发，就回写到规则库和提示词模板，形成轻量自进化闭环。',
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
    desc: '用户常常会继续追问、改预算、换节奏。没有会话历史，系统就只能单轮应答，很难形成真实可用的产品体验。',
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
              <div className="grid md:grid-cols-2 gap-4">
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
                <p>
                  其中目的地搜索会先做地点抽取，再融合攻略类来源和地图验证。这样可以避免地图附近搜索只返回商场、停车场这类“附近设施”，而找不到真正适合规划的景点。
                </p>
              </div>
            </section>

            <section id="safety" className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
              <div className="flex items-center gap-2 mb-4">
                <ShieldCheck className="w-4 h-4 text-[#06D6A0]" />
                <h2 className="text-2xl font-semibold">8. 安全设计</h2>
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                {safetyItems.map((item) => (
                  <div key={item.title} className="rounded-xl border border-[#E6EEF6] p-4">
                    <h3 className="font-semibold mb-2">{item.title}</h3>
                    <p className="text-sm leading-7" style={{ color: 'rgba(10,36,99,0.78)' }}>
                      {item.desc}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            <section id="evaluation" className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
              <div className="flex items-center gap-2 mb-4">
                <MessageSquareText className="w-4 h-4 text-[#1A659E]" />
                <h2 className="text-2xl font-semibold">9. 评测设计</h2>
              </div>
              <div className="space-y-4">
                {evaluationItems.map((item) => (
                  <div key={item.title} className="rounded-xl border border-[#E6EEF6] p-4">
                    <h3 className="text-base font-semibold mb-2">{item.title}</h3>
                    <p className="text-sm leading-7" style={{ color: 'rgba(10,36,99,0.78)' }}>
                      {item.desc}
                    </p>
                  </div>
                ))}
              </div>
              <div className="mt-5 space-y-3 text-sm leading-7" style={{ color: 'rgba(10,36,99,0.82)' }}>
                <p>
                  这里的评测不是单纯看“模型有没有输出”，而是参考了 RACE、DoVer、AgentWorld、FACT 这几类工作的不同视角，把旅行规划拆成“场景分数、归因解释、动作顺序、事实来源”四个正交维度。
                </p>
                <p>
                  RACE 负责给不同场景配置动态权重，比如亲子、自由行、预算紧张的权重侧重点不一样；DoVer 负责检查结论和解释是否一致；AgentWorld 负责看工具调用和状态流转是否顺序正确；FACT 负责检查正文里的 POI、路线、天气、预算是否都能回到 source_map。
                </p>
                <p>
                  评测运行时，会把每次规划的工具调用、节点流转和结果快照写进 trace，随后按场景加载权重算出四维结果。失败样本会进入 `failures.jsonl`，再按类别聚合回写到规则和提示词里，形成一个轻量的持续改进闭环。
                </p>
                <p>
                  这样做的重点是：不是只判断“答得像不像”，而是判断“是否可执行、是否遵守约束、是否有来源、是否能解释自己为什么这么做”。
                </p>
              </div>
              <div className="mt-5 rounded-xl p-4 text-sm leading-7" style={{ background: 'rgba(33,158,188,0.06)', border: '1px dashed rgba(33,158,188,0.28)' }}>
                流程上会先记录 trace，再跑四维评测，最后把失败样本做聚合和回写。这样评测结果不仅能看，也能反向驱动规则更新。
              </div>
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
                这页后面如果要继续扩展，可以优先补“更细的记忆策略”“更完整的评测样本”和“多城市行程编排”三块，但前提还是先把当前主链路跑稳。
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
