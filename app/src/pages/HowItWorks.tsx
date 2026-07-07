import { ArrowRight, FileText, Layers3, MessageSquareText, Sparkles, Workflow, Brain, ShieldCheck, Puzzle } from 'lucide-react';
import { Link } from 'react-router';

const flow = [
  '用户输入目的地、天数、预算和偏好。',
  '系统先整理上下文，再判断要调用哪些工具和节点。',
  'Planning Agent 负责推进，Skill 负责执行具体动作。',
  'Review Agent 负责校验安全、格式和一致性，最后把结果回传前端。',
];

const highlights = [
  {
    title: '2 Agent + 多 Skill',
    icon: Workflow,
    text: '不是把每一步都做成一个 Agent，而是用少量 Agent 做调度和校验，具体能力沉到 Skill 里，结构更稳，也更容易扩展。',
  },
  {
    title: '上下文工程',
    icon: Layers3,
    text: '原始工具结果、压缩摘要、约束信息和最终 Prompt 分开处理，避免上下文越来越乱，也避免一次把所有原始数据都塞给模型。',
  },
  {
    title: '记忆与会话历史',
    icon: Brain,
    text: '短期层保存最近几轮交互，长期层保存用户偏好和稳定信息，让系统既记得当前会话，也记得长期习惯。',
  },
  {
    title: 'MCP + 外部工具',
    icon: Puzzle,
    text: '把高德、路线、天气、搜索等能力统一接进工具层，Agent 不直接依赖具体接口，后面替换实现也比较轻。',
  },
  {
    title: '安全与评测',
    icon: ShieldCheck,
    text: '在输出前做安全检查、质量校验和结果整理，避免模型直接把不稳定内容发给用户，也方便后面定位问题。',
  },
];

export default function HowItWorks() {
  return (
    <div className="min-h-[calc(100dvh-64px)] bg-[#F8FBFF] text-[#0A2463]">
      <div className="max-w-5xl mx-auto px-6 py-14">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium mb-5" style={{ background: 'rgba(33,158,188,0.12)', color: '#1A659E' }}>
            <FileText className="w-3.5 h-3.5" />
            项目说明
          </div>
          <h1 className="text-4xl font-bold tracking-tight mb-4" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
            WanderMind 项目技术方案
          </h1>
          <p className="text-base leading-8 max-w-3xl" style={{ color: 'rgba(10,36,99,0.78)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
            这一页是给面试官和学习者快速看的版本。它不追求把实现细到每个函数，而是把系统主线、核心模块和简历里最值得讲的内容讲清楚。
          </p>
        </div>

        <section className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.06)] mt-10">
          <div className="flex items-center gap-2 mb-4">
            <Workflow className="w-4 h-4 text-[#1A659E]" />
            <h2 className="text-lg font-semibold">端到端流程</h2>
          </div>
          <div className="grid gap-3">
            {flow.map((item, index) => (
              <div key={item} className="flex gap-3">
                <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold text-white flex-shrink-0" style={{ background: '#1A659E' }}>
                  {index + 1}
                </div>
                <p className="text-sm leading-7" style={{ color: 'rgba(10,36,99,0.82)' }}>
                  {item}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-5">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-4 h-4 text-[#FF9F1C]" />
            <h2 className="text-lg font-semibold">简历里最值得讲的几条</h2>
          </div>
          <div className="grid md:grid-cols-2 gap-5">
            {highlights.map((item) => {
              const Icon = item.icon;
              return (
                <article key={item.title} className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.06)]">
                  <div className="flex items-center gap-2 mb-3">
                    <Icon className="w-4 h-4 text-[#2EC4B6]" />
                    <h3 className="text-lg font-semibold">{item.title}</h3>
                  </div>
                  <p className="text-sm leading-7" style={{ color: 'rgba(10,36,99,0.82)' }}>
                    {item.text}
                  </p>
                </article>
              );
            })}
          </div>
        </section>

        <section className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.06)] mt-5">
          <div className="flex items-center gap-2 mb-4">
            <MessageSquareText className="w-4 h-4 text-[#E29578]" />
            <h2 className="text-lg font-semibold">一句话怎么讲</h2>
          </div>
          <p className="text-sm leading-7 mb-3" style={{ color: 'rgba(10,36,99,0.82)' }}>
            这个项目可以理解成一个旅行规划 Agent 平台：用户输入需求后，系统先做上下文整理，再由 Agent 调度工具、生成方案、检查输出，最终把结果稳定地交给前端展示。
          </p>
          <p className="text-sm leading-7" style={{ color: 'rgba(10,36,99,0.82)' }}>
            面试时可以把重点放在三件事上：怎么控制上下文，怎么把能力拆成少量 Agent + 多个 Skill，怎么把记忆、工具调用和安全检查串成一条可追踪的链路。
          </p>
        </section>

        <section className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.06)] mt-5">
          <div className="flex items-center gap-2 mb-4">
            <ArrowRight className="w-4 h-4 text-[#1A659E]" />
            <h2 className="text-lg font-semibold">继续看完整版本</h2>
          </div>
          <div className="flex flex-col gap-3">
            <p className="text-sm leading-7" style={{ color: 'rgba(10,36,99,0.82)' }}>
              如果你想看更完整的设计细节，可以继续参考 `docs/tech-design-final.md`。这个页面只保留面试够用的主线，方便快速理解和临场表达。
            </p>
            <Link to="/app" className="inline-flex w-fit items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white" style={{ background: '#E29578' }}>
              回到应用
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
