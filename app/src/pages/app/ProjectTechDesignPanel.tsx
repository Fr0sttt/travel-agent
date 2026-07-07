import { FileText, Workflow, Layers3, Sparkles, Edit3 } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';

const flowSteps = [
  {
    title: '用户输入',
    desc: '用户用自然语言描述行程目标、天数、预算和偏好，前端把输入传给后端流式接口。',
  },
  {
    title: '上下文整理',
    desc: '后端先收集会话历史、约束信息和工具结果，压缩成当前轮次需要的最小上下文。',
  },
  {
    title: 'Agent 调度',
    desc: 'Planning Agent 负责推进流程，按需调用搜索、路线、天气、预算等 Skill。',
  },
  {
    title: '结果校验',
    desc: 'Review Agent 统一检查安全、格式和一致性，必要时触发补充澄清或降级方案。',
  },
];

const highlights = [
  '2 Agent + 多 Skill，不把每个能力都做成一个独立 Agent，降低编排复杂度。',
  '上下文分层管理，原始数据和压缩数据分开保存，避免提示词被工具输出撑爆。',
  '记忆和会话历史独立管理，既能保留短期交互，也能沉淀长期偏好。',
  '评测、日志和安全检查前置，方便排查问题，也方便后面继续扩展。',
];

export default function ProjectTechDesignPanel() {
  return (
    <div className="h-full flex flex-col">
      <div className="flex-shrink-0 p-4 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center"
            style={{ background: 'rgba(33,158,188,0.16)', color: '#8ECAE6' }}
          >
            <FileText className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
              项目技术方案
            </h3>
            <p className="text-[11px]" style={{ color: 'rgba(255,255,255,0.45)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
              给面试官看的轻量版流程说明
            </p>
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          <section className="glass-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-[#8ECAE6]" />
              <h4 className="text-sm font-semibold text-white" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
                项目定位
              </h4>
            </div>
            <p className="text-xs leading-relaxed" style={{ color: '#EDF6F9', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
              这是一个面向旅行规划场景的 Agent 化应用。用户输入目的地、天数、预算和偏好后，系统会自动拆解需求、调用外部工具、组织行程，并把生成结果以流式方式返回前端。
            </p>
          </section>

          <section className="glass-card p-4">
            <div className="flex items-center gap-2 mb-3">
              <Workflow className="w-4 h-4 text-[#219EBC]" />
              <h4 className="text-sm font-semibold text-white" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
                核心流程
              </h4>
            </div>
            <div className="space-y-3">
              {flowSteps.map((step, index) => (
                <div key={step.title} className="flex gap-3">
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-semibold flex-shrink-0"
                    style={{ background: 'rgba(255,255,255,0.08)', color: '#8ECAE6' }}
                  >
                    {index + 1}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-white" style={{ fontFamily: "'Inter Variable', Inter, sans-serif" }}>
                      {step.title}
                    </p>
                    <p className="text-[11px] leading-relaxed mt-0.5" style={{ color: 'rgba(255,255,255,0.68)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
                      {step.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="glass-card p-4">
            <div className="flex items-center gap-2 mb-3">
              <Layers3 className="w-4 h-4 text-[#FFD166]" />
              <h4 className="text-sm font-semibold text-white" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
                关键设计点
              </h4>
            </div>
            <div className="space-y-2.5">
              {highlights.map((item) => (
                <div key={item} className="flex gap-2">
                  <div className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0" style={{ background: '#8ECAE6' }} />
                  <p className="text-xs leading-relaxed" style={{ color: '#EDF6F9', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
                    {item}
                  </p>
                </div>
              ))}
            </div>
          </section>

          <section className="glass-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <Edit3 className="w-4 h-4 text-[#06D6A0]" />
              <h4 className="text-sm font-semibold text-white" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
                面试可替换表述
              </h4>
            </div>
            <div
              className="rounded-xl p-3 text-xs leading-relaxed"
              style={{
                background: 'rgba(255,255,255,0.05)',
                border: '1px dashed rgba(142,202,230,0.35)',
                color: '#EDF6F9',
                fontFamily: "'Inter Variable', Inter, sans-serif",
              }}
            >
              <p className="mb-2">
                【可替换】我把这个项目理解成一个“旅行规划 Agent 平台”：前端负责承接用户输入，后端负责上下文整理、工具调度、结果校验和记忆管理，核心目标是让系统既能自动出方案，也能保持稳定、可控、可追踪。
              </p>
              <p style={{ color: 'rgba(255,255,255,0.55)' }}>
                你后面可以把这段直接改成更像你自己的表达，或者替换成“我们重点做了哪些能力”的版本。
              </p>
            </div>
          </section>

          <section className="glass-card p-4">
            <p className="text-[11px] mb-1" style={{ color: 'rgba(255,255,255,0.45)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
              完整版设计文档
            </p>
            <p className="text-xs leading-relaxed" style={{ color: '#EDF6F9', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
              更完整的设计说明可以继续保留在 `docs/tech-design-final.md`，这个 tab 只展示面试时最容易讲清楚的主线。
            </p>
          </section>
        </div>
      </ScrollArea>
    </div>
  );
}
