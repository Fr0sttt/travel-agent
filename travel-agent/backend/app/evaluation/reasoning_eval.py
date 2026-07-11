"""
推理评估模块 - DoVer框架

借鉴 DoVer (Intervention-Driven Debugging Evaluation) 框架，
对Travel Agent的推理过程进行深度评估。

核心思想：
- Trial Segmentation: 将执行轨迹按re-plan点分段
- Failure Attribution: 对失败进行归因分析
- Intervention: 干预验证

参考论文: "DoVer: Debugging with Intervention-Driven Evaluation"
"""

import os
import json
from enum import Enum
from typing import Any
from dataclasses import dataclass, field
from collections import Counter

try:
    from backend.app.evaluation.base import BaseEvaluator, EvalResult, TrialSegment
except ModuleNotFoundError:
    from evaluation.base import BaseEvaluator, EvalResult, TrialSegment
try:
    from backend.app.evaluation.judge import TravelLLMJudge
except ModuleNotFoundError:
    from evaluation.judge import TravelLLMJudge


# ---------------------------------------------------------------------------
# 失败类型枚举
# ---------------------------------------------------------------------------
class FailureType(str, Enum):
    """推理失败类型"""
    WRONG_TOOL = "wrong_tool"          # 选择了错误的工具
    WRONG_PARAMETER = "wrong_parameter"  # 参数错误
    MISSING_TOOL = "missing_tool"      # 遗漏必要工具
    REDUNDANT_TOOL = "redundant_tool"  # 冗余工具调用
    WRONG_ORDER = "wrong_order"        # 工具调用顺序错误
    HALLUCINATION = "hallucination"    # 幻觉/虚构信息
    TIMEOUT = "timeout"                # 超时
    UNKNOWN = "unknown"                # 未知原因


# ---------------------------------------------------------------------------
# 干预验证结果
# ---------------------------------------------------------------------------
class InterventionResult(str, Enum):
    """干预假设验证结果"""
    VALIDATED = "Validated"                  # 假设完全验证
    PARTIALLY_VALIDATED = "PartiallyValidated"  # 部分验证
    REFUTED = "Refuted"                      # 假设被推翻
    INCONCLUSIVE = "Inconclusive"            # 无法确定


# 期望的LangGraph节点执行顺序
EXPECTED_NODES = [
    "preference_collector",
    "constraint_normalizer",
    "destination_search",
    "route_planner",
    "weather_advisor",
    "budget_estimator",
    "itinerary_synthesizer",
    "safety_reviewer",
    "output_formatter",
]

# 每个节点期望的里程碑
NODE_MILESTONES = {
    "preference_collector": ["extract_preferences", "identify_missing_fields"],
    "constraint_normalizer": ["normalize_constraints", "derive_implicit_needs"],
    "destination_search": ["geocode_destination", "search_pois", "deduplicate_results"],
    "route_planner": ["calculate_distances", "sort_pois", "build_route_segments"],
    "weather_advisor": ["fetch_weather", "identify_rainy_days", "suggest_alternatives"],
    "budget_estimator": ["estimate_categories", "calculate_total_range", "check_budget_fit"],
    "itinerary_synthesizer": ["arrange_daily_schedule", "generate_explanations", "format_markdown"],
    "safety_reviewer": ["scan_risk_keywords", "flag_confirmations", "add_disclaimer"],
    "output_formatter": ["assemble_final_output", "attach_risk_alerts"],
}


class DoVerReasoningEvaluator(BaseEvaluator):
    """
    DoVer框架：推理过程评估

    核心能力：
    1. Trial Segmentation: 将执行轨迹按re-plan节点分段
    2. Failure Attribution: 对失败进行根因归因
    3. Intervention Generation: 生成修复干预建议
    4. Metrics: Trial Success Rate, Progress Made

    Usage:
        evaluator = DoVerReasoningEvaluator()
        result = await evaluator.evaluate(
            input_data={"expected_milestones": [...]},
            output_data={"trajectory": [...]},
            context={"interventions": [...]},
        )
    """

    def __init__(self) -> None:
        """初始化DoVer评估器"""
        self._judge = TravelLLMJudge()

    # ------------------------------------------------------------------
    #  核心评估接口
    # ------------------------------------------------------------------
    async def evaluate(
        self,
        input_data: dict,
        output_data: dict,
        context: dict | None = None,
    ) -> EvalResult:
        """
        执行DoVer推理评估

        Args:
            input_data: 必须包含 expected_milestones (list[str])
            output_data: 必须包含 trajectory (list[dict])
            context: 可选 interventions (list[dict])

        Returns:
            EvalResult: 包含trial_success_rate和progress_made的评估结果
        """
        trajectory = output_data.get("trajectory", [])
        expected_milestones = input_data.get("expected_milestones", [])
        interventions = (context or {}).get("interventions", [])

        if not trajectory:
            return EvalResult(
                metric_name="DoVer_reasoning",
                score=0.0,
                details={"error": "Empty trajectory"},
                reasoning="执行轨迹为空，无法评估",
                passed=False,
            )

        # 1. 分段 trial
        trials = self.segment_trials(trajectory)

        # 2. 检查每个trial的里程碑完成情况
        milestone_progress = []
        for trial in trials:
            progress = self.check_milestones(trial, expected_milestones)
            milestone_progress.append(progress)

        # 一个完整规划默认就是一个 trial，进展应按该 trial 已完成的里程碑占比计算。
        progress_scores = [
            sum(1 for completed in progress.values() if completed) / max(len(progress), 1)
            for progress in milestone_progress
        ]
        avg_progress = sum(progress_scores) / len(progress_scores) if progress_scores else 0.0

        # 4. 失败归因
        failures = self._attribute_failures(trials)

        # 5. 干预验证
        intervention_results = []
        for intervention in interventions:
            for trial in trials:
                result = self.validate_hypothesis(trial, intervention)
                intervention_results.append(result)

        # 6. 计算综合指标
        metrics = self._calculate_metrics(trials)

        # 综合分数：trial_success_rate * 0.5 + progress_made * 0.5
        overall = metrics.get("trial_success_rate", 0) * 0.5 + avg_progress * 0.5

        judge = await self._judge.evaluate(
            "DoVer.travel_execution",
            "判断旅行规划执行轨迹是否按正确顺序推进，失败后是否基于新证据恢复，是否存在重复调用或无效步骤。",
            {
                "expected_milestones": expected_milestones,
                "trajectory": trajectory,
                "rule_metrics": metrics,
                "failures": failures,
            },
            "只看可观测轨迹，不推测隐藏思维；缺少地理编码就直接搜索、天气失败后没有备选、重复失败且未恢复都应降低分数。成功完成关键里程碑且每次失败后有有效恢复才可 pass。",
        )
        if judge.get("score") is not None:
            overall = overall * 0.5 + float(judge["score"]) * 0.5

        details = {
            "metrics": metrics,
            "trial_count": len(trials),
            "failure_count": len(failures),
            "intervention_results": [
                r.value for r in intervention_results
            ] if intervention_results else [],
            "progress_scores": progress_scores,
            "judge": judge,
        }
        hard_failures = []
        completed_milestones = {
            name for progress in milestone_progress for name, completed in progress.items() if completed
        }
        missing_milestones = [m for m in expected_milestones if m not in completed_milestones]
        if missing_milestones:
            hard_failures.append("missing_milestones:" + ",".join(missing_milestones[:8]))
        if failures and not any(item.get("root_cause") for item in failures):
            hard_failures.append("failure_without_root_cause")
        details["hard_failures"] = hard_failures

        reasoning_parts = [
            f"Trial数量: {len(trials)}, 成功率: {metrics.get('trial_success_rate', 0):.2f}",
            f"平均进展: {avg_progress:.2f}",
            f"失败数: {len(failures)}",
            f"工具效率: {metrics.get('tool_efficiency', 0):.2f}",
        ]

        return EvalResult(
            metric_name="DoVer_reasoning",
            score=self._normalize_score(overall),
            details=details,
            reasoning="; ".join(reasoning_parts),
            passed=self._pass_check(overall, threshold=0.5) and not hard_failures,
            hard_failures=hard_failures,
        )

    def get_metric_names(self) -> list[str]:
        """返回DoVer框架支持的指标名称列表"""
        return [
            "DoVer_reasoning",
            "trial_success_rate",
            "progress_made",
            "tool_efficiency",
        ]

    # ------------------------------------------------------------------
    #  Step 1: Trial 分段
    # ------------------------------------------------------------------
    def segment_trials(self, trajectory: list[dict]) -> list[list[dict]]:
        """
        将执行轨迹分割为trials（以re-plan或节点切换为分割点）

        分割策略：
        - 当节点名称发生变化时创建新trial
        - 当检测到retry/re-plan标记时创建新trial

        Args:
            trajectory: 执行日志列表，每个元素包含 node, type, tool_name 等

        Returns:
            list[list[dict]]: 分段后的trials
        """
        trials: list[list[dict]] = []
        current_trial: list[dict] = []
        current_trial_id: str | None = None

        for entry in trajectory:
            entry_type = entry.get("type", "")
            trial_id = entry.get("trial_id")

            # re-plan标记检测
            is_replan = entry.get("replan", False) or entry_type in [
                "replan",
                "retry",
                "recover",
            ]

            # 节点切换不代表新的 trial，只有显式重试/重规划才切段。
            if is_replan or (trial_id and current_trial_id and trial_id != current_trial_id):
                if current_trial:
                    trials.append(current_trial)
                current_trial = [entry]
                current_trial_id = trial_id
            else:
                current_trial.append(entry)
                if current_trial_id is None:
                    current_trial_id = trial_id

        if current_trial:
            trials.append(current_trial)

        # 如果没有有效分段，将整个轨迹作为一个trial
        if not trials and trajectory:
            trials = [trajectory]

        return trials

    # ------------------------------------------------------------------
    #  Step 2: 里程碑检查
    # ------------------------------------------------------------------
    def check_milestones(
        self,
        trial: list[dict],
        milestones: list[str],
    ) -> dict[str, bool]:
        """
        检查trial完成了哪些里程碑

        通过分析trial中的工具调用和节点完成状态，
        判断每个期望里程碑是否已完成。

        Args:
            trial: 单个trial的日志列表
            milestones: 期望的里程碑列表

        Returns:
            dict[str, bool]: 每个里程碑的完成状态
        """
        result: dict[str, bool] = {}

        # 提取trial中的工具名称和节点名称
        tool_names = [
            e.get("tool_name", "") for e in trial if e.get("type") == "tool_call"
        ]
        node_names = [e.get("node", "") for e in trial]

        for milestone in milestones:
            completed = False

            # 基于里程碑关键词匹配
            milestone_lower = milestone.lower()

            # 工具调用匹配
            if any(milestone_lower in t.lower() for t in tool_names if t):
                completed = True

            # 节点名称匹配
            if any(milestone_lower in n.lower() for n in node_names if n):
                completed = True

            # 特定里程碑逻辑
            if milestone == "geocode_destination" and "geocode_location" in tool_names:
                completed = True
            elif milestone == "search_pois" and "search_places" in tool_names:
                completed = True
            elif milestone == "calculate_distances" and "estimate_route" in tool_names:
                completed = True
            elif milestone == "fetch_weather" and "get_weather" in tool_names:
                completed = True
            elif milestone == "estimate_categories" and "estimate_budget" in tool_names:
                completed = True

            result[milestone] = completed

        return result

    # ------------------------------------------------------------------
    #  Step 3: 进展计算
    # ------------------------------------------------------------------
    def calculate_progress(
        self,
        before_milestones: dict[str, bool],
        after_milestones: dict[str, bool],
    ) -> float:
        """
        计算干预前后的进展增量

        返回值范围: [-1, 1]
        - 正值: 有进展（完成了更多里程碑）
        - 负值: 退步（丢失了已完成的里程碑）
        - 0: 无变化

        Args:
            before_milestones: 干预前的里程碑状态
            after_milestones: 干预后的里程碑状态

        Returns:
            float: 进展增量 [-1, 1]
        """
        all_milestones = set(before_milestones.keys()) | set(
            after_milestones.keys()
        )
        if not all_milestones:
            return 0.0

        before_completed = sum(1 for v in before_milestones.values() if v)
        after_completed = sum(1 for v in after_milestones.values() if v)

        progress = (after_completed - before_completed) / len(all_milestones)

        # 限制在 [-1, 1] 区间
        return max(-1.0, min(1.0, progress))

    # ------------------------------------------------------------------
    #  Step 4: 失败归因
    # ------------------------------------------------------------------
    def _attribute_failures(
        self, trials: list[list[dict]]
    ) -> list[dict]:
        """
        分析失败trial的根因

        Args:
            trials: 分段后的trials

        Returns:
            list[dict]: 每个失败的归因结果
        """
        failures = []

        for trial in trials:
            # 判断trial是否失败
            has_error = any(
                e.get("error") or e.get("status") == "failed" or e.get("success") is False
                for e in trial
            )

            if has_error:
                failure = self._analyze_failure(trial)
                failures.append(failure)

        return failures

    def _analyze_failure(self, trial: list[dict]) -> dict:
        """
        分析单个失败trial的根因

        Args:
            trial: 失败的trial日志

        Returns:
            dict: 失败分析结果
        """
        tool_calls = [e for e in trial if e.get("type") == "tool_call"]
        tool_names = [t.get("tool_name", "") for t in tool_calls]
        node_name = trial[0].get("node", "unknown") if trial else "unknown"

        failure = {
            "node": node_name,
            "type": FailureType.UNKNOWN,
            "description": "",
            "root_cause": "",
            "tools_used": tool_names,
        }

        # 检查错误类型
        for entry in tool_calls:
            error = entry.get("error", "")
            if error:
                if "parameter" in error.lower() or "argument" in error.lower():
                    failure["type"] = FailureType.WRONG_PARAMETER
                    failure["description"] = f"参数错误: {error}"
                    failure["root_cause"] = "参数格式或值不正确"
                    return failure
                elif "timeout" in error.lower() or "timed out" in error.lower():
                    failure["type"] = FailureType.TIMEOUT
                    failure["description"] = f"超时: {error}"
                    failure["root_cause"] = "工具调用超时"
                    return failure

        # 检查是否缺少必要工具
        expected_tools = NODE_MILESTONES.get(node_name, [])
        if expected_tools:
            missing = []
            for milestone in expected_tools:
                if milestone in ["geocode_destination"] and "geocode_location" not in tool_names:
                    missing.append("geocode_location")
                elif milestone in ["search_pois"] and "search_places" not in tool_names:
                    missing.append("search_places")
                elif milestone in ["calculate_distances"] and "estimate_route" not in tool_names:
                    missing.append("estimate_route")

            if missing:
                failure["type"] = FailureType.MISSING_TOOL
                failure["description"] = f"缺少必要工具: {missing}"
                failure["root_cause"] = "工具调用链不完整"
                return failure

        # 检查重复调用
        tool_counts = Counter(tool_names)
        redundant = {k: v for k, v in tool_counts.items() if v > 3}
        if redundant:
            failure["type"] = FailureType.REDUNDANT_TOOL
            failure["description"] = f"工具重复调用: {redundant}"
            failure["root_cause"] = "可能存在循环或无效重试"
            return failure

        # 默认
        failure["type"] = FailureType.HALLUCINATION
        failure["description"] = "未知的执行失败"
        failure["root_cause"] = "可能需要检查LLM推理逻辑"

        return failure

    # ------------------------------------------------------------------
    #  Step 5: 干预假设验证
    # ------------------------------------------------------------------
    def validate_hypothesis(
        self,
        trial: list[dict],
        intervention: dict,
    ) -> InterventionResult:
        """
        验证失败假设

        通过对比干预预期和实际trial结果，判断假设是否成立。

        Args:
            trial: 被验证的trial
            intervention: 干预配置，包含 expected_fix, target_node 等

        Returns:
            InterventionResult: 验证结果
        """
        if not trial or not intervention:
            return InterventionResult.INCONCLUSIVE

        expected_fix = intervention.get("expected_fix", "")
        target_node = intervention.get("target_node", "")

        trial_nodes = [e.get("node", "") for e in trial]

        # 如果trial不包含目标节点，无法验证
        if target_node and target_node not in trial_nodes:
            return InterventionResult.INCONCLUSIVE

        # 检查trial是否成功（没有错误）
        has_error = any(
            e.get("error") or e.get("status") == "failed" or e.get("success") is False for e in trial
        )

        if has_error:
            # 仍有错误，检查是否是不同错误
            error_messages = [
                e.get("error", "") for e in trial if e.get("error")
            ]
            if error_messages and expected_fix not in str(error_messages):
                # 错误改变了，说明干预有部分效果
                return InterventionResult.PARTIALLY_VALIDATED
            return InterventionResult.REFUTED

        # 没有错误，假设验证成功
        return InterventionResult.VALIDATED

    # ------------------------------------------------------------------
    #  综合指标计算
    # ------------------------------------------------------------------
    def _calculate_metrics(self, trials: list[list[dict]]) -> dict[str, Any]:
        """
        计算推理评估指标

        Metrics:
        - trial_success_rate: 成功trial数 / 总trial数
        - progress_made: 完成的节点数 / 期望节点数
        - tool_efficiency: 成功工具调用 / 总工具调用
        - failure_rate: 失败trial数 / 总trial数

        Args:
            trials: 分段后的trials

        Returns:
            dict: 各项指标
        """
        total_trials = len(trials)
        if total_trials == 0:
            return {
                "trial_success_rate": 0.0,
                "progress_made": 0.0,
                "tool_efficiency": 0.0,
                "failure_rate": 0.0,
            }

        successful_trials = 0
        failed_trials = 0
        total_tool_calls = 0
        successful_tool_calls = 0
        completed_nodes: set[str] = set()

        for trial in trials:
            has_error = any(
                e.get("error") or e.get("status") == "failed" or e.get("success") is False
                for e in trial
            )

            if has_error:
                failed_trials += 1
            else:
                successful_trials += 1

            for entry in trial:
                if entry.get("type") == "tool_call":
                    total_tool_calls += 1
                    if not entry.get("error") and entry.get("success", True) is not False:
                        successful_tool_calls += 1

                node = entry.get("node")
                if node:
                    completed_nodes.add(node)

        trial_success_rate = successful_trials / total_trials
        failure_rate = failed_trials / total_trials

        # 进度 = 完成的节点数 / 期望节点数
        progress_made = len(completed_nodes) / len(EXPECTED_NODES) if EXPECTED_NODES else 0

        # 工具效率
        tool_efficiency = (
            successful_tool_calls / total_tool_calls if total_tool_calls > 0 else 0
        )

        return {
            "trial_success_rate": round(trial_success_rate, 4),
            "progress_made": round(progress_made, 4),
            "tool_efficiency": round(tool_efficiency, 4),
            "failure_rate": round(failure_rate, 4),
            "total_trials": total_trials,
            "successful_trials": successful_trials,
            "failed_trials": failed_trials,
            "total_tool_calls": total_tool_calls,
            "successful_tool_calls": successful_tool_calls,
            "completed_nodes": list(completed_nodes),
        }
