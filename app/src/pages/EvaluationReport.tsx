import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, CheckCircle2, ChevronRight, FileJson, Gauge, Info, Loader2, ShieldAlert, Sparkles, XCircle } from 'lucide-react';
import { Link, useLocation } from 'react-router';
import { getEvaluation, getSession, type EvaluationJob, type EvaluationReport as ApiEvaluationReport, type EvaluationResult, type SessionState } from '@/lib/api';

type JsonRecord = Record<string, unknown>;

const METHOD_META: Record<string, { label: string; focus: string; icon: React.ElementType; color: string }> = {
  RACE_end_to_end: {
    label: 'RACE 端到端质量',
    focus: '检查旅行规划是否覆盖需求、具备执行深度，并且表达清晰可读。',
    icon: Gauge,
    color: '#2EC4B6',
  },
  DoVer_reasoning: {
    label: 'DoVer 执行推理',
    focus: '根据节点轨迹和工具调用，判断执行是否按预期推进、失败是否得到处理。',
    icon: ChevronRight,
    color: '#FF9F1C',
  },
  AgentWorld_tool: {
    label: 'AgentWorld 工具链',
    focus: '检查工具选型、参数、调用顺序和工具失败后的恢复策略。',
    icon: Sparkles,
    color: '#06D6A0',
  },
  FACT_rag: {
    label: 'FACT 来源可信度',
    focus: '检查行程中的事实是否有工具结果或结构化来源支撑，避免把推测写成事实。',
    icon: FileJson,
    color: '#E29578',
  },
  comprehensive_metrics: {
    label: '旅行综合质量',
    focus: '综合判断约束满足、路线合理性、来源支撑、不确定性披露和安全合规。',
    icon: ShieldAlert,
    color: '#8ECAE6',
  },
};

const LABELS: Record<string, string> = {
  COMP: '需求覆盖',
  DEPTH: '规划深度',
  INST: '约束遵循',
  READ: '可读性',
  constraint_satisfaction: '约束满足',
  route_reasonableness: '路线合理性',
  source_grounding: '来源支撑',
  uncertainty_disclosure: '不确定性披露',
  safety_compliance: '安全合规',
  trial_success_rate: 'Trial 成功率',
  average_progress: '平均推进度',
  correctness: '工具正确性',
  parameter_accuracy: '参数准确性',
  chain_reasonableness: '调用链合理性',
  citation_accuracy: '引用准确性',
  evidence_coverage: '证据覆盖率',
};

function asRecord(value: unknown): JsonRecord {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as JsonRecord : {};
}

function asNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim() && Number.isFinite(Number(value))) return Number(value);
  return null;
}

function scorePercent(value: unknown): number {
  const number = asNumber(value) ?? 0;
  return Math.round((number <= 1 ? number * 100 : number));
}

function labelFor(key: string): string {
  return LABELS[key] || key.replaceAll('_', ' ');
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '未提供';
  if (typeof value === 'boolean') return value ? '是' : '否';
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (typeof value === 'string') return value;
  return JSON.stringify(value, null, 2);
}

function statusLabel(status?: EvaluationJob['status']): string {
  if (status === 'completed') return '评测完成';
  if (status === 'running') return '评测进行中';
  if (status === 'queued') return '等待评测';
  if (status === 'failed') return '评测失败';
  return '暂无评测';
}

function ScoreBar({ value, color = '#2EC4B6', label, hint }: { value: unknown; color?: string; label: string; hint?: string }) {
  const percent = scorePercent(value);
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="text-sm text-[#EDF6F9]">{label}</div>
          {hint && <div className="mt-0.5 text-[11px] text-white/40">{hint}</div>}
        </div>
        <span className="font-mono text-sm" style={{ color }}>{percent}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/[0.08]">
        <div className="h-full rounded-full transition-all" style={{ width: `${Math.max(0, Math.min(100, percent))}%`, background: color }} />
      </div>
    </div>
  );
}

function Breakdown({ result, color }: { result: EvaluationResult; color: string }) {
  const details = asRecord(result.details);
  const dimensionScores = asRecord(details.dimension_scores);
  const weights = asRecord(details.weights);
  const metrics = asRecord(details.metrics);
  const values = Object.keys(dimensionScores).length > 0 ? dimensionScores : metrics;
  const entries = Object.entries(values).filter(([, value]) => asNumber(value) !== null);

  if (entries.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-white/10 px-4 py-5 text-sm text-white/45">
        本方法没有返回可拆分的子维度分数，下面的 Judge 证据和原始评测证据仍然是本次判分依据。
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {entries.map(([key, value]) => {
        const weight = asNumber(weights[key]);
        return (
          <ScoreBar
            key={key}
            value={value}
            color={color}
            label={labelFor(key)}
            hint={weight === null ? undefined : `权重 ${(weight * 100).toFixed(0)}% · 子分数参与综合计算`}
          />
        );
      })}
      {Object.keys(weights).length > 0 && (
        <div className="rounded-lg bg-black/10 px-3 py-2 text-xs leading-relaxed text-white/50">
          综合分 = {entries.map(([key]) => `${labelFor(key)}分 × ${(Number(weights[key]) * 100).toFixed(0)}%`).join(' + ')}
        </div>
      )}
    </div>
  );
}

function normalizeJudgeEntries(result: EvaluationResult): Array<[string, JsonRecord]> {
  const details = asRecord(result.details);
  const raw = result.judge || details.judge;
  if (Array.isArray(raw)) {
    return raw.map((item, index) => [`Judge ${index + 1}`, asRecord(item)] as [string, JsonRecord]);
  }
  const record = asRecord(raw);
  const nested = Object.entries(record).filter(([, value]) => value && typeof value === 'object' && !Array.isArray(value));
  return nested.length > 0 ? nested.map(([key, value]) => [key, asRecord(value)]) : (Object.keys(record).length > 0 ? [['LLM Judge', record]] : []);
}

function JudgeEvidence({ result }: { result: EvaluationResult }) {
  const judges = normalizeJudgeEntries(result);
  if (judges.length === 0) {
    return <div className="text-sm text-white/45">本维度没有单独的 LLM Judge 结果，主要依据规则和结构化数据计算。</div>;
  }
  return (
    <div className="space-y-3">
      {judges.map(([name, judge]) => {
        const evidence = Array.isArray(judge.evidence) ? judge.evidence : [];
        const failedChecks = Array.isArray(judge.failed_checks) ? judge.failed_checks : [];
        const score = judge.score === null || judge.score === undefined ? null : scorePercent(judge.score);
        const judgeReason = judge.status === 'unavailable'
          ? 'Judge 没有返回符合结构化输出契约的结果，本次不使用该 Judge 分数。'
          : String(judge.reason || '未返回文字化判定原因。');
        return (
          <div key={name} className="rounded-lg border border-white/[0.08] bg-white/[0.025] p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium text-white">{labelFor(name)}</span>
              <span className="rounded-full bg-white/[0.07] px-2 py-0.5 text-[10px] uppercase tracking-wider text-white/50">
                {String(judge.status || 'judge')}
              </span>
              {score !== null && <span className="ml-auto font-mono text-sm text-[#8ECAE6]">{score}%</span>}
            </div>
            <p className="mt-3 text-sm leading-6 text-white/65">{judgeReason}</p>
            {Boolean(judge.failure_category) && (
              <div className="mt-3 flex items-start gap-2 rounded-md bg-[#EF476F]/10 px-3 py-2 text-xs text-[#FF9FB2]">
                <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                失败分类：{String(judge.failure_category)}
              </div>
            )}
            {evidence.length > 0 && (
              <div className="mt-3">
                <div className="mb-2 text-[10px] uppercase tracking-wider text-white/35">判分证据</div>
                <ul className="space-y-1.5 text-xs leading-5 text-white/55">
                  {evidence.slice(0, 5).map((item, index) => <li key={`${name}-evidence-${index}`} className="flex gap-2"><span className="text-[#2EC4B6]">{index + 1}.</span><span>{String(item)}</span></li>)}
                </ul>
              </div>
            )}
            {failedChecks.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {failedChecks.map((item) => <span key={String(item)} className="rounded bg-[#EF476F]/10 px-2 py-1 text-[11px] text-[#FF9FB2]">{String(item)}</span>)}
              </div>
            )}
            {judge.confidence !== undefined && <div className="mt-3 text-[11px] text-white/35">Judge 置信度：{scorePercent(judge.confidence)}% · 延迟：{formatValue(judge.latency_ms)} ms</div>}
          </div>
        );
      })}
    </div>
  );
}

const MILESTONE_LABELS: Record<string, string> = {
  preference_collector: '收集用户偏好',
  constraint_normalizer: '归一化旅行约束',
  geocode_location: '地理编码目的地',
  search_places: '搜索候选地点',
  estimate_route: '估算地点间路线',
  get_weather: '查询天气预报',
  estimate_budget: '估算旅行预算',
  itinerary_synthesizer: '合成每日行程',
  safety_reviewer: '安全审查',
  output_formatter: '格式化最终输出',
};

function explainHardFailure(value: string): string {
  if (value.startsWith('missing_milestones:')) {
    const names = value.slice('missing_milestones:'.length).split(',').filter(Boolean);
    const labels = names.map((name) => MILESTONE_LABELS[name] || name);
    return `执行链路缺少可观测步骤：${labels.join('、')}`;
  }
  if (value === 'failure_without_root_cause') return '发现失败事件，但没有记录可定位的根因。';
  if (value === 'citation_judge_unavailable') return '引用 Judge 不可用，来源可信度没有完成语义校验。';
  if (value === 'no_citation_support') return '行程事实没有找到对应的结构化来源证据。';
  return value;
}

function RuleChecks({ result }: { result: EvaluationResult }) {
  const details = asRecord(result.details);
  const checks = [
    ...(Array.isArray(result.hard_failures) ? result.hard_failures : []),
    ...(Array.isArray(details.hard_failures) ? details.hard_failures : []),
  ].map(String);
  const unique = [...new Set(checks)];
  return (
    <div className="rounded-lg border border-white/[0.08] bg-white/[0.025] p-4">
      <div className="flex items-center gap-2 text-sm font-medium text-white"><ShieldAlert className="h-4 w-4 text-[#FFD166]" />执行链路硬校验</div>
      <p className="mt-2 text-xs leading-5 text-white/45">这里检查的是 Agent 是否留下必要的节点和工具调用证据，不是对预算、天数等用户约束的重复评分。</p>
      {unique.length === 0 ? (
        <div className="mt-3 flex items-center gap-2 text-sm text-[#06D6A0]"><CheckCircle2 className="h-4 w-4" />本次没有发现硬规则失败项</div>
      ) : (
        <div className="mt-3 space-y-2">{unique.map((item) => <div key={item} className="flex items-start gap-2 text-sm text-[#FF9FB2]"><XCircle className="mt-0.5 h-4 w-4 shrink-0" />{explainHardFailure(item)}</div>)}</div>
      )}
    </div>
  );
}

function ReportContent({ result, color }: { result: EvaluationResult; color: string }) {
  const details = asRecord(result.details);
  const rawDetails = JSON.stringify(details, null, 2);
  return (
    <div className="space-y-5">
      <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <section className="rounded-xl border border-white/[0.08] bg-white/[0.035] p-5">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-white"><Gauge className="h-4 w-4" style={{ color }} />评分构成</div>
          <Breakdown result={result} color={color} />
        </section>
        <section className="rounded-xl border border-white/[0.08] bg-white/[0.035] p-5">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-white"><Info className="h-4 w-4 text-[#8ECAE6]" />本次判定结论</div>
          <p className="text-sm leading-7 text-white/65">{result.reasoning || '暂无文字化结论。'}</p>
          <div className="mt-4 flex items-center gap-2 border-t border-white/[0.07] pt-4 text-sm">
            {result.passed ? <CheckCircle2 className="h-4 w-4 text-[#06D6A0]" /> : <XCircle className="h-4 w-4 text-[#EF476F]" />}
            <span className={result.passed ? 'text-[#06D6A0]' : 'text-[#FF9FB2]'}>{result.passed ? '通过当前维度阈值' : '未通过当前维度阈值'}</span>
          </div>
        </section>
      </div>

      <RuleChecks result={result} />

      <section className="rounded-xl border border-white/[0.08] bg-white/[0.035] p-5">
        <div className="mb-1 flex items-center gap-2 text-sm font-semibold text-white"><Sparkles className="h-4 w-4 text-[#FF9F1C]" />LLM Judge 依据</div>
        <p className="mb-4 text-xs leading-5 text-white/40">LLM 只负责语义质量判断；可计算的约束、工具和来源事实由规则及结构化证据共同校验，最终按方法的融合策略得到本维度分数。</p>
        <JudgeEvidence result={result} />
      </section>

      <details className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-5">
        <summary className="cursor-pointer list-none text-sm font-medium text-[#8ECAE6]">查看原始评测证据</summary>
        <pre className="mt-4 max-h-[420px] overflow-auto whitespace-pre-wrap break-words rounded-lg bg-black/20 p-4 text-[11px] leading-5 text-white/50">{rawDetails}</pre>
      </details>
    </div>
  );
}

export default function EvaluationReport() {
  const location = useLocation();
  const sessionId = new URLSearchParams(location.search).get('session') || '';
  const [session, setSession] = useState<SessionState | null>(null);
  const [job, setJob] = useState<EvaluationJob | null>(null);
  const [selectedMethod, setSelectedMethod] = useState('RACE_end_to_end');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    async function load() {
      if (!sessionId) {
        setLoading(false);
        setError('缺少会话 ID，无法加载评测报告。');
        return;
      }
      try {
        const state = await getSession(sessionId);
        if (!active) return;
        setSession(state);
        if (state.evaluation) {
          setJob(state.evaluation);
          if (state.evaluation.status === 'completed' && state.evaluation.report) setSelectedMethod(state.evaluation.report.results[0]?.metric_name || 'RACE_end_to_end');
        } else {
          setError('该会话还没有生成评测报告。');
        }
      } catch (firstError) {
        if (!active) return;
        setError(firstError instanceof Error ? firstError.message : String(firstError));
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [sessionId]);

  useEffect(() => {
    if (!job?.run_id || job.status === 'completed' || job.status === 'failed') return;
    let active = true;
    const timer = window.setInterval(async () => {
      try {
        const next = await getEvaluation(job.run_id);
        if (active) setJob(next);
        if (next.status === 'completed' || next.status === 'failed') window.clearInterval(timer);
      } catch { /* 保留当前状态，下一次轮询继续尝试 */ }
    }, 1500);
    return () => { active = false; window.clearInterval(timer); };
  }, [job?.run_id, job?.status]);

  const report = job?.report as ApiEvaluationReport | undefined;
  const results = useMemo(() => report?.results || [], [report]);
  const selected = useMemo(() => results.find((item) => item.metric_name === selectedMethod) || results[0], [results, selectedMethod]);
  const meta = selected ? METHOD_META[selected.metric_name] || { label: selected.metric_name, focus: '本次评测方法返回的结构化质量报告。', icon: Info, color: '#8ECAE6' } : null;
  const destination = String((session?.preference as JsonRecord | null)?.destination || '本次旅行规划');

  return (
    <div className="min-h-[calc(100dvh-64px)] bg-[#071B4D] px-4 py-8 text-white sm:px-6 lg:px-10">
      <div className="mx-auto max-w-[1440px]">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <Link to="/app" className="mb-4 inline-flex items-center gap-2 text-sm text-[#8ECAE6] transition-colors hover:text-white"><ArrowLeft className="h-4 w-4" />返回规划工作台</Link>
            <div className="flex items-center gap-3"><h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">评测完整报告</h1><span className="rounded-full border border-[#2EC4B6]/30 bg-[#2EC4B6]/10 px-3 py-1 text-xs text-[#6EE7D7]">{statusLabel(job?.status)}</span></div>
            <p className="mt-2 text-sm text-white/45">{destination} · 从评分结果回溯到规则、证据和 Judge 判定。</p>
          </div>
          {report && <div className="rounded-xl border border-white/[0.08] bg-white/[0.035] px-5 py-4 text-right"><div className="text-[10px] uppercase tracking-[0.2em] text-white/35">Overall</div><div className="mt-1 text-3xl font-semibold text-[#06D6A0]">{scorePercent(report.overall_score)}%</div></div>}
        </div>

        {loading && <div className="flex min-h-[360px] items-center justify-center gap-3 text-white/55"><Loader2 className="h-5 w-5 animate-spin text-[#2EC4B6]" />正在加载评测报告…</div>}
        {!loading && error && <div className="rounded-xl border border-[#FFD166]/20 bg-[#FFD166]/10 p-6 text-sm text-[#FFE3A1]">{error}</div>}
        {!loading && !error && job && !report && <div className="rounded-xl border border-white/[0.08] bg-white/[0.035] p-8 text-center text-white/55">评测尚未完成，当前状态：{statusLabel(job.status)}。</div>}

        {!loading && !error && report && (
          <>
            <section className="mb-6 grid gap-3 sm:grid-cols-3">
              <div className="rounded-lg border border-white/[0.08] bg-white/[0.025] p-4"><div className="text-[10px] uppercase tracking-wider text-white/35">评测任务</div><div className="mt-2 truncate font-mono text-xs text-white/65">{job?.run_id || '-'}</div></div>
              <div className="rounded-lg border border-white/[0.08] bg-white/[0.025] p-4"><div className="text-[10px] uppercase tracking-wider text-white/35">评测时间</div><div className="mt-2 text-xs text-white/65">{report.timestamp ? new Date(report.timestamp).toLocaleString() : '未提供'}</div></div>
              <div className="rounded-lg border border-white/[0.08] bg-white/[0.025] p-4"><div className="text-[10px] uppercase tracking-wider text-white/35">评测流程</div><div className="mt-2 flex items-center gap-1.5 text-xs text-white/65"><CheckCircle2 className="h-3.5 w-3.5 text-[#06D6A0]" />规则校验 · LLM Judge · 分数融合</div></div>
            </section>

            <div className="mb-6 overflow-x-auto border-b border-white/[0.08]">
              <div className="flex min-w-max gap-1">
                {results.map((item) => {
                  const itemMeta = METHOD_META[item.metric_name] || { label: item.metric_name, focus: '', icon: Info, color: '#8ECAE6' };
                  const Icon = itemMeta.icon;
                  const active = item.metric_name === selected?.metric_name;
                  return <button key={item.metric_name} onClick={() => setSelectedMethod(item.metric_name)} className="relative flex items-center gap-2 px-4 py-3 text-sm transition-colors" style={{ color: active ? '#FFFFFF' : 'rgba(255,255,255,0.45)' }}><Icon className="h-4 w-4" style={{ color: itemMeta.color }} />{itemMeta.label}<span className="font-mono text-xs" style={{ color: itemMeta.color }}>{scorePercent(item.score)}%</span>{active && <span className="absolute bottom-0 left-3 right-3 h-0.5 rounded-full" style={{ background: itemMeta.color }} />}</button>;
                })}
              </div>
            </div>

            {selected && meta && (
              <>
                <section className="mb-6 rounded-xl border border-white/[0.08] bg-white/[0.035] p-5 sm:p-6">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div><div className="flex items-center gap-2"><meta.icon className="h-5 w-5" style={{ color: meta.color }} /><h2 className="text-xl font-semibold">{meta.label}</h2></div><p className="mt-3 max-w-3xl text-sm leading-6 text-white/55">{meta.focus}</p></div>
                    <div className="text-right"><div className="font-mono text-4xl font-semibold" style={{ color: meta.color }}>{scorePercent(selected.score)}%</div><div className="mt-1 text-xs text-white/35">{selected.passed ? '通过' : '未通过'} · 当前维度</div></div>
                  </div>
                </section>
                <ReportContent result={selected} color={meta.color} />
              </>
            )}

            {report.recommendations.length > 0 && <section className="mt-6 rounded-xl border border-[#FF9F1C]/20 bg-[#FF9F1C]/[0.06] p-5"><div className="flex items-center gap-2 text-sm font-semibold text-[#FFD166]"><Info className="h-4 w-4" />全局改进建议</div><div className="mt-3 grid gap-2 md:grid-cols-2">{report.recommendations.map((item, index) => <div key={`${item}-${index}`} className="flex gap-2 text-sm leading-6 text-white/65"><span className="font-mono text-[#FFD166]">{index + 1}.</span><span>{item}</span></div>)}</div></section>}
          </>
        )}
      </div>
    </div>
  );
}
