"""
评估运行器模块

协调所有评估器，提供统一的评估入口。
支持完整评估、单项评估、报告生成和导出。

Usage:
    runner = EvaluationRunner()
    report = await runner.run_full_evaluation(session_data)

    # 单项评估
    result = await runner.run_single_eval("end_to_end", data)

    # 导出报告
    json_str = runner.export_report(report, format="json")
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Any

try:
    from backend.app.evaluation.base import BaseEvaluator, EvalResult, EvalReport
    from backend.app.evaluation.end_to_end import RACEEndToEndEvaluator
    from backend.app.evaluation.reasoning_eval import DoVerReasoningEvaluator
    from backend.app.evaluation.tool_eval import AgentWorldToolEvaluator
    from backend.app.evaluation.rag_eval import FACTRAGEvaluator
    from backend.app.evaluation.comprehensive_metrics import ComprehensiveMetricsEvaluator
except ModuleNotFoundError:
    from evaluation.base import BaseEvaluator, EvalResult, EvalReport
    from evaluation.end_to_end import RACEEndToEndEvaluator
    from evaluation.reasoning_eval import DoVerReasoningEvaluator
    from evaluation.tool_eval import AgentWorldToolEvaluator
    from evaluation.rag_eval import FACTRAGEvaluator
    from evaluation.comprehensive_metrics import ComprehensiveMetricsEvaluator


# ---------------------------------------------------------------------------
# 默认评估阈值配置
# ---------------------------------------------------------------------------
DEFAULT_THRESHOLDS = {
    "RACE_end_to_end": 0.60,
    "DoVer_reasoning": 0.50,
    "AgentWorld_tool": 0.60,
    "FACT_rag": 0.50,
    "comprehensive_metrics": 0.60,
}


class EvaluationRunner:
    """
    评估运行器 - 协调所有评估器

    管理5个评估器的生命周期，提供统一的评估接口。

    Attributes:
        evaluators: 评估器字典，key为评估类型，value为评估器实例
        thresholds: 各评估指标的通过阈值

    Usage:
        runner = EvaluationRunner()

        # 完整评估
        report = await runner.run_full_evaluation(session_data)

        # 单项评估
        result = await runner.run_single_eval("end_to_end", data)

        # 批量评估
        reports = await runner.run_batch_evaluation(sessions_data)

        # 导出
        json_report = runner.export_report(report, format="json")
    """

    def __init__(
        self,
        evaluators: dict[str, BaseEvaluator] | None = None,
        thresholds: dict[str, float] | None = None,
    ) -> None:
        """
        初始化评估运行器

        Args:
            evaluators: 自定义评估器字典（None则使用默认）
            thresholds: 自定义阈值字典（None则使用默认）
        """
        self.evaluators = evaluators or {
            "end_to_end": RACEEndToEndEvaluator(),
            "reasoning": DoVerReasoningEvaluator(),
            "tool_use": AgentWorldToolEvaluator(),
            "rag": FACTRAGEvaluator(),
            "comprehensive": ComprehensiveMetricsEvaluator(),
        }
        self.thresholds = thresholds or DEFAULT_THRESHOLDS

    # ------------------------------------------------------------------
    #  完整评估
    # ------------------------------------------------------------------
    async def run_full_evaluation(
        self,
        session_data: dict,
    ) -> EvalReport:
        """
        运行完整评估（所有评估器）

        Args:
            session_data: 会话数据，必须包含 session_id 和各评估器所需字段
                {
                    "session_id": str,
                    "user_request": str,
                    "constraints": dict,
                    "itinerary": str|dict,
                    "trajectory": list[dict],
                    "tool_calls": list[dict],
                    "cited_sources": list[dict],
                    "route_plan": list[dict],
                    "preferences": dict,
                    ...
                }

        Returns:
            EvalReport: 完整评估报告
        """
        session_id = session_data.get("session_id", "unknown")
        results: list[EvalResult] = []
        errors: list[str] = []

        # 并行执行所有评估
        eval_tasks = []
        eval_names = []

        for eval_type, evaluator in self.evaluators.items():
            try:
                task = self._run_evaluator(eval_type, evaluator, session_data)
                eval_tasks.append(task)
                eval_names.append(eval_type)
            except Exception as e:
                errors.append(f"{eval_type} 评估任务创建失败: {str(e)}")

        # 等待所有评估完成
        if eval_tasks:
            eval_results = await asyncio.gather(*eval_tasks, return_exceptions=True)

            for name, result in zip(eval_names, eval_results):
                if isinstance(result, Exception):
                    errors.append(f"{name} 评估失败: {str(result)}")
                    # 创建失败结果
                    results.append(
                        EvalResult(
                            metric_name=name,
                            score=0.0,
                            details={"error": str(result)},
                            reasoning=f"评估异常: {str(result)}",
                            passed=False,
                        )
                    )
                else:
                    results.append(result)

        # 计算综合分数
        dimension_scores = {}
        for r in results:
            dimension_scores[r.metric_name] = r.score

        overall_score = (
            sum(r.score for r in results) / len(results) if results else 0.0
        )

        # 生成改进建议
        recommendations = self._generate_recommendations(results)

        # 如果有错误，添加到建议中
        if errors:
            recommendations.insert(0, f"评估过程中发生 {len(errors)} 个错误")
            for error in errors[:5]:  # 最多显示5个
                recommendations.append(f"  - {error}")

        return EvalReport(
            session_id=session_id,
            overall_score=round(overall_score, 4),
            dimension_scores=dimension_scores,
            results=results,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat(),
        )

    # ------------------------------------------------------------------
    #  单项评估
    # ------------------------------------------------------------------
    async def run_single_eval(
        self,
        eval_type: str,
        data: dict,
    ) -> EvalResult:
        """
        运行单个评估

        Args:
            eval_type: 评估类型 (end_to_end/reasoning/tool_use/rag/comprehensive)
            data: 评估数据，包含 input_data, output_data, context 等

        Returns:
            EvalResult: 单项评估结果

        Raises:
            ValueError: 评估类型不存在
        """
        if eval_type not in self.evaluators:
            raise ValueError(
                f"未知的评估类型: {eval_type}. "
                f"可用类型: {list(self.evaluators.keys())}"
            )

        evaluator = self.evaluators[eval_type]
        return await self._run_evaluator(eval_type, evaluator, data)

    # ------------------------------------------------------------------
    #  批量评估
    # ------------------------------------------------------------------
    async def run_batch_evaluation(
        self,
        sessions_data: list[dict],
        max_concurrent: int = 5,
    ) -> list[EvalReport]:
        """
        批量评估多个会话

        Args:
            sessions_data: 会话数据列表
            max_concurrent: 最大并发数

        Returns:
            list[EvalReport]: 所有会话的评估报告
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def eval_with_limit(session_data: dict) -> EvalReport:
            async with semaphore:
                return await self.run_full_evaluation(session_data)

        tasks = [eval_with_limit(sd) for sd in sessions_data]
        return await asyncio.gather(*tasks, return_exceptions=True)

    # ------------------------------------------------------------------
    #  报告生成
    # ------------------------------------------------------------------
    def generate_report(
        self,
        results: list[EvalResult],
        session_id: str = "unknown",
    ) -> EvalReport:
        """
        从评估结果生成报告

        Args:
            results: 评估结果列表
            session_id: 会话ID

        Returns:
            EvalReport: 评估报告
        """
        dimension_scores = {r.metric_name: r.score for r in results}
        overall_score = (
            sum(r.score for r in results) / len(results) if results else 0.0
        )
        recommendations = self._generate_recommendations(results)

        return EvalReport(
            session_id=session_id,
            overall_score=round(overall_score, 4),
            dimension_scores=dimension_scores,
            results=results,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat(),
        )

    # ------------------------------------------------------------------
    #  报告导出
    # ------------------------------------------------------------------
    def export_report(
        self,
        report: EvalReport,
        format: str = "json",
    ) -> str:
        """
        导出报告为指定格式

        Args:
            report: 评估报告
            format: 导出格式 (json/md/csv)

        Returns:
            str: 格式化后的报告字符串

        Raises:
            ValueError: 不支持的格式
        """
        if format == "json":
            return self._export_json(report)
        elif format == "md":
            return self._export_markdown(report)
        elif format == "csv":
            return self._export_csv(report)
        else:
            raise ValueError(f"不支持的格式: {format}. 可用: json, md, csv")

    def _export_json(self, report: EvalReport) -> str:
        """导出为JSON格式"""
        return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)

    def _export_markdown(self, report: EvalReport) -> str:
        """导出为Markdown格式"""
        lines = [
            f"# 评估报告 - Session {report.session_id}",
            "",
            f"**评估时间**: {report.timestamp}",
            "",
            "## 综合评分",
            "",
            f"| 指标 | 分数 | 状态 |",
            f"|------|------|------|",
        ]

        for name, score in report.dimension_scores.items():
            status = "通过" if score >= self.thresholds.get(name, 0.6) else "未通过"
            lines.append(f"| {name} | {score:.4f} | {status} |")

        lines.extend([
            "",
            f"**综合分数**: {report.overall_score:.4f}",
            "",
            "## 详细结果",
            "",
        ])

        for result in report.results:
            lines.extend([
                f"### {result.metric_name}",
                "",
                f"- **分数**: {result.score:.4f}",
                f"- **状态**: {'通过' if result.passed else '未通过'}",
                f"- **依据**: {result.reasoning}",
                f"- **详情**: `{json.dumps(result.details, ensure_ascii=False, indent=2)[:500]}`",
                "",
            ])

        lines.extend([
            "## 改进建议",
            "",
        ])
        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {rec}")

        return "\n".join(lines)

    def _export_csv(self, report: EvalReport) -> str:
        """导出为CSV格式"""
        lines = ["metric_name,score,passed,reasoning"]
        for result in report.results:
            lines.append(
                f"{result.metric_name},{result.score:.4f},"
                f"{result.passed},\"{result.reasoning[:200]}\""
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    #  内部辅助方法
    # ------------------------------------------------------------------
    async def _run_evaluator(
        self,
        eval_type: str,
        evaluator: BaseEvaluator,
        session_data: dict,
    ) -> EvalResult:
        """
        运行单个评估器

        根据评估类型准备 input_data/output_data/context。

        Args:
            eval_type: 评估类型
            evaluator: 评估器实例
            session_data: 会话数据

        Returns:
            EvalResult: 评估结果
        """
        constraints = self._normalize_constraints(session_data)

        if eval_type == "end_to_end":
            return await evaluator.evaluate(
                input_data={
                    "user_request": session_data.get("user_request", ""),
                    "constraints": constraints,
                },
                output_data={
                    "itinerary": session_data.get("itinerary", {}),
                },
                context={
                    "reference_itinerary": session_data.get("reference_itinerary"),
                },
            )

        elif eval_type == "reasoning":
            return await evaluator.evaluate(
                input_data={
                    "expected_milestones": session_data.get(
                        "expected_milestones",
                        [
                            "preference_collector",
                            "constraint_normalizer",
                            "geocode_location",
                            "search_places",
                            "estimate_route",
                            "get_weather",
                            "estimate_budget",
                            "itinerary_synthesizer",
                            "safety_reviewer",
                            "output_formatter",
                        ],
                    ),
                },
                output_data={
                    "trajectory": session_data.get("trajectory", []),
                },
                context={
                    "interventions": session_data.get("interventions", []),
                },
            )

        elif eval_type == "tool_use":
            return await evaluator.evaluate(
                input_data={
                    "task_description": session_data.get("user_request", ""),
                },
                output_data={
                    "tool_calls": session_data.get("tool_calls", []),
                },
                context={
                    "expected_tools": session_data.get("expected_tools"),
                },
            )

        elif eval_type == "rag":
            return await evaluator.evaluate(
                input_data={
                    "response": (
                        session_data.get("itinerary", "")
                        if isinstance(session_data.get("itinerary"), str)
                        else json.dumps(
                            session_data.get("itinerary", {}), ensure_ascii=False
                        )
                    ),
                },
                output_data={
                    "cited_sources": session_data.get("cited_sources", []),
                },
                context={
                    "retrieved_contexts": session_data.get("retrieved_contexts", []),
                },
            )

        elif eval_type == "comprehensive":
            return await evaluator.evaluate(
                input_data={
                    "preferences": session_data.get("preferences", {}),
                },
                output_data={
                    "itinerary": session_data.get("itinerary", {}),
                    "route_plan": session_data.get("route_plan", []),
                    "actions": session_data.get("actions") or session_data.get("confirmation_required", []),
                },
                context={
                    "constraints": constraints,
                    "cited_sources": session_data.get("cited_sources", []),
                    "weather": session_data.get("weather", []),
                    "risk_alerts": session_data.get("risk_alerts", []),
                },
            )

        else:
            raise ValueError(f"未知的评估类型: {eval_type}")

    @staticmethod
    def _normalize_constraints(session_data: dict[str, Any]) -> dict[str, Any]:
        """把偏好和嵌套约束归一化成评测器统一使用的平面契约。"""
        preference = session_data.get("preferences") or session_data.get("preference") or {}
        preference = dict(preference) if isinstance(preference, dict) else {}
        raw = session_data.get("constraints") or {}
        raw = dict(raw) if isinstance(raw, dict) else {}
        hard = raw.get("hard_constraints") or {}
        soft = raw.get("soft_constraints") or {}

        normalized = dict(preference)
        if normalized.get("budget_cny") is None and hard.get("budget_max") is not None:
            normalized["budget_cny"] = hard.get("budget_max")
        if not normalized.get("dietary_restrictions") and hard.get("dietary"):
            normalized["dietary_restrictions"] = hard.get("dietary")
        if not normalized.get("accessibility_needs") and hard.get("accessibility"):
            normalized["accessibility_needs"] = hard.get("accessibility")
        if not normalized.get("interests") and soft.get("interests"):
            normalized["interests"] = soft.get("interests")
        if not normalized.get("pace_preference") and soft.get("pace"):
            normalized["pace_preference"] = soft.get("pace")
        if not normalized.get("transportation_preference") and soft.get("transportation"):
            normalized["transportation_preference"] = soft.get("transportation")
        normalized["implicit_needs"] = raw.get("implicit_needs") or []
        normalized["constraint_summary"] = raw.get("constraint_summary") or normalized.get("constraint_summary", "")
        return normalized

    def _generate_recommendations(self, results: list[EvalResult]) -> list[str]:
        """
        基于评估结果生成改进建议

        Args:
            results: 评估结果列表

        Returns:
            list[str]: 改进建议列表
        """
        recommendations = []

        for result in results:
            if result.passed:
                continue

            metric = result.metric_name
            score = result.score

            if metric == "RACE_end_to_end":
                if score < 0.4:
                    recommendations.append(
                        "端到端质量较低: 建议优化行程生成逻辑，确保覆盖用户需求"
                    )
                else:
                    recommendations.append(
                        "端到端质量有提升空间: 检查行程的可读性和深度"
                    )

            elif metric == "DoVer_reasoning":
                if score < 0.3:
                    recommendations.append(
                        "推理过程问题较多: 建议优化工具调用链，检查失败节点"
                    )
                else:
                    recommendations.append(
                        "推理过程需要改进: 关注trial成功率和进度指标"
                    )

            elif metric == "AgentWorld_tool":
                if score < 0.4:
                    recommendations.append(
                        "工具调用问题严重: 检查工具选择和参数传递逻辑"
                    )
                else:
                    recommendations.append(
                        "工具调用需要优化: 关注参数准确性和工具链顺序"
                    )

            elif metric == "FACT_rag":
                if score < 0.3:
                    recommendations.append(
                        "RAG效果较差: 检查引用来源的准确性和完整性"
                    )
                else:
                    recommendations.append(
                        "RAG引用质量有提升空间: 增加有效引用数量"
                    )

            elif metric == "comprehensive_metrics":
                details = result.details.get("dimension_scores", {})
                if details.get("constraint_satisfaction", 1) < 0.6:
                    recommendations.append(
                        "约束满足度不足: 确保满足用户的预算/时间/偏好约束"
                    )
                if details.get("route_reasonableness", 1) < 0.6:
                    recommendations.append(
                        "路线合理性不足: 优化路线规划，减少过长行程"
                    )
                if details.get("uncertainty_disclosure", 1) < 0.4:
                    recommendations.append(
                        "不确定性披露不足: 增加价格/营业时间的不确定性标注"
                    )
                if details.get("safety_compliance", 1) < 0.8:
                    recommendations.append(
                        "安全合规需要关注: 确保高风险操作有确认机制"
                    )

        if not recommendations:
            recommendations.append("所有指标均通过，系统运行良好！")

        return recommendations
