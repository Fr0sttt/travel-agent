"""
工具调用评估模块 - Agent-World框架

借鉴 Agent-World 框架的 Tool Use Evaluation 方法，
对Travel Agent的工具调用行为进行多维评估。

评估维度：
1. 工具选择正确性: 是否选择了正确的工具
2. 参数准确性: 参数是否符合schema
3. 多步工具链执行: 工具链是否合理
4. Structured Verifiable Reward: 可验证的结构化奖励

参考论文: "Agent-World: Benchmarking Tool-Using Agents"
"""

import os
import json
from typing import Any
from dataclasses import dataclass, field
from collections import Counter

try:
    from backend.app.evaluation.base import BaseEvaluator, EvalResult, ToolCallRecord
except ModuleNotFoundError:
    from evaluation.base import BaseEvaluator, EvalResult, ToolCallRecord
try:
    from backend.app.evaluation.judge import TravelLLMJudge
except ModuleNotFoundError:
    from evaluation.judge import TravelLLMJudge


# ---------------------------------------------------------------------------
# 节点-工具期望映射
# ---------------------------------------------------------------------------
TOOL_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "preference_collector": {
        "required_tools": [],
        "optional_tools": [],
        "description": "纯LLM推理，无需工具",
        "forbidden_tools": [],
    },
    "constraint_normalizer": {
        "required_tools": [],
        "optional_tools": [],
        "description": "纯LLM推理，无需工具",
        "forbidden_tools": [],
    },
    "destination_search": {
        "required_tools": ["geocode_location", "search_places"],
        "optional_tools": ["guide_search", "destination_search"],
        "description": "必须先地理编码，再搜索POI",
        "forbidden_tools": [],
    },
    "route_planner": {
        "required_tools": ["estimate_route"],
        "optional_tools": [],
        "description": "使用OSRM估算路线",
        "forbidden_tools": [],
    },
    "weather_advisor": {
        "required_tools": ["get_weather"],
        "optional_tools": [],
        "description": "查询天气",
        "forbidden_tools": [],
    },
    "budget_estimator": {
        "required_tools": ["estimate_budget"],
        "optional_tools": [],
        "description": "估算预算",
        "forbidden_tools": [],
    },
    "itinerary_synthesizer": {
        "required_tools": [],
        "optional_tools": [],
        "description": "纯LLM推理",
        "forbidden_tools": [],
    },
    "safety_reviewer": {
        "required_tools": [],
        "optional_tools": [],
        "description": "纯LLM安全检查",
        "forbidden_tools": [],
    },
    "output_formatter": {
        "required_tools": [],
        "optional_tools": [],
        "description": "纯LLM格式化",
        "forbidden_tools": [],
    },
}

# 工具参数schema定义
TOOL_PARAMETER_SCHEMA: dict[str, dict[str, Any]] = {
    "geocode_location": {
        "required": ["query"],
        "types": {"query": str},
        "constraints": {
            "query": lambda v: len(str(v)) > 0,
        },
    },
    "search_places": {
        "required": ["lat", "lon"],
        "types": {"lat": (int, float), "lon": (int, float), "radius": (int, float), "kinds": str, "rate": str},
        "constraints": {
            "lat": lambda v: -90 <= float(v) <= 90,
            "lon": lambda v: -180 <= float(v) <= 180,
            "radius": lambda v: 0 < float(v) <= 50000,
        },
    },
    "estimate_route": {
        "required": ["start_lat", "start_lon", "end_lat", "end_lon"],
        "types": {
            "start_lat": (int, float), "start_lon": (int, float),
            "end_lat": (int, float), "end_lon": (int, float),
        },
        "constraints": {
            "start_lat": lambda v: -90 <= float(v) <= 90,
            "start_lon": lambda v: -180 <= float(v) <= 180,
            "end_lat": lambda v: -90 <= float(v) <= 90,
            "end_lon": lambda v: -180 <= float(v) <= 180,
        },
    },
    "get_weather": {
        "required": ["lat", "lon"],
        "types": {"lat": (int, float), "lon": (int, float)},
        "constraints": {
            "lat": lambda v: -90 <= float(v) <= 90,
            "lon": lambda v: -180 <= float(v) <= 180,
        },
    },
    "estimate_budget": {
        "required": ["destination", "duration_days"],
        "types": {"destination": str, "duration_days": int},
        "constraints": {
            "destination": lambda v: len(str(v)) > 0,
            "duration_days": lambda v: 0 < int(v) <= 365,
        },
    },
}

# 工具调用顺序约束（前置依赖）
TOOL_ORDER_CONSTRAINTS: list[tuple[str, str]] = [
    ("geocode_location", "search_places"),  # 先地理编码再搜索POI
    ("search_places", "estimate_route"),    # 先搜索再规划路线
]


class AgentWorldToolEvaluator(BaseEvaluator):
    """
    Agent-World框架：工具调用评估

    评估维度：
    - 工具选择正确性: 是否正确选择了工具
    - 参数准确性: 参数是否符合schema和约束
    - 多步工具链执行: 工具链顺序是否合理
    - 可验证奖励: 基于工具调用结果的奖励分数

    Usage:
        evaluator = AgentWorldToolEvaluator()
        result = await evaluator.evaluate(
            input_data={"task": "...", "expected_tools": [...]},
            output_data={"tool_calls": [...]},
        )
    """

    def __init__(self) -> None:
        """初始化Agent-World工具评估器"""
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
        执行Agent-World工具调用评估

        Args:
            input_data: 必须包含 task_description (str)
            output_data: 必须包含 tool_calls (list[dict])
            context: 可选 expected_tools (list[str])

        Returns:
            EvalResult: 包含correctness/parameters/chain分数的评估结果
        """
        tool_calls = output_data.get("tool_calls", [])
        task = input_data.get("task_description", "")
        expected_tools = (context or {}).get("expected_tools", [])

        if not tool_calls:
            return EvalResult(
                metric_name="AgentWorld_tool",
                score=0.0,
                details={"error": "No tool calls"},
                reasoning="没有工具调用记录",
                passed=False,
            )

        # 1. 检查工具选择正确性
        correctness_scores = self._evaluate_tool_correctness(tool_calls)
        correctness_avg = (
            sum(s["score"] for s in correctness_scores.values())
            / len(correctness_scores)
            if correctness_scores else 0
        )

        # 2. 验证参数准确性
        param_result = self._evaluate_parameter_accuracy(tool_calls)

        # 3. 评估工具链执行顺序
        chain_result = self._evaluate_tool_chain(tool_calls, task)

        # 4. 计算可验证奖励
        reward = self._calculate_verifiable_reward(tool_calls, task)

        # 综合分数
        overall = (
            correctness_avg * 0.35
            + param_result["average_score"] * 0.30
            + chain_result["score"] * 0.20
            + reward * 0.15
        )

        judge = await self._judge.evaluate(
            "AgentWorld.travel_tools",
            "判断旅行规划 Agent 的工具选择、参数、调用顺序和失败处理是否合理。",
            {
                "task": task,
                "tool_calls": tool_calls,
                "rule_checks": {
                    "correctness": correctness_scores,
                    "parameters": param_result,
                    "chain": chain_result,
                    "reward": reward,
                },
            },
            "规则检查负责硬性 schema、必需工具和顺序；Judge 只补充语义策略判断。没有坐标时调用路线工具、没有天气结果却声称天气确定、工具失败后重复同样参数，都应判为策略失败。",
        )
        if judge.get("score") is not None:
            overall = overall * 0.6 + float(judge["score"]) * 0.4

        details = {
            "correctness": {
                k: {"score": round(v["score"], 4), "missing": v.get("missing", []),
                    "unexpected": v.get("unexpected", [])}
                for k, v in correctness_scores.items()
            },
            "parameters": param_result,
            "tool_chain": chain_result,
            "verifiable_reward": round(reward, 4),
            "judge": judge,
        }
        hard_failures: list[str] = []
        missing_tools = [
            f"{node}:{tool}"
            for node, item in correctness_scores.items()
            for tool in item.get("missing", [])
        ]
        if missing_tools:
            hard_failures.append("missing_required_tools:" + ",".join(missing_tools[:8]))
        if any(item.get("issues") for item in param_result.get("details", [])):
            hard_failures.append("invalid_tool_parameters")
        # 单次工具失败不直接判死：旅行规划允许在高德/天气失败后换策略，
        # 是否恢复、是否继续编造结论交给 Judge 结合后续轨迹判断。
        details["hard_failures"] = hard_failures

        reasoning_parts = [
            f"工具正确性: {correctness_avg:.2f}",
            f"参数准确性: {param_result['average_score']:.2f}",
            f"工具链合理性: {chain_result['score']:.2f}",
            f"可验证奖励: {reward:.2f}",
        ]

        return EvalResult(
            metric_name="AgentWorld_tool",
            score=self._normalize_score(overall),
            details=details,
            reasoning="; ".join(reasoning_parts),
            passed=self._pass_check(overall, threshold=0.6) and not hard_failures,
            hard_failures=hard_failures,
        )

    def get_metric_names(self) -> list[str]:
        """返回Agent-World框架支持的指标名称列表"""
        return [
            "AgentWorld_tool",
            "tool_correctness",
            "parameter_accuracy",
            "tool_chain",
            "verifiable_reward",
        ]

    # ------------------------------------------------------------------
    #  工具选择正确性
    # ------------------------------------------------------------------
    def _evaluate_tool_correctness(
        self, tool_calls: list[dict]
    ) -> dict[str, dict[str, Any]]:
        """
        评估每个节点是否正确使用了工具

        检查：
        - 必需工具是否被调用
        - 是否有不应使用的工具
        - 节点-工具映射是否匹配

        Args:
            tool_calls: 工具调用记录列表

        Returns:
            dict: 每个节点的评分详情
        """
        scores: dict[str, dict[str, Any]] = {}

        for node_name, expectation in TOOL_EXPECTATIONS.items():
            node_calls = [
                c for c in tool_calls if c.get("node") == node_name
            ]
            # 当前会话没有执行到该节点时，不把“未调用工具”误判成缺失工具。
            if not node_calls:
                continue
            tools_used = [
                c.get("tool_name", "") for c in node_calls if c.get("tool_name")
            ]

            required = expectation["required_tools"]
            optional = expectation["optional_tools"]
            all_allowed = required + optional

            missing = [t for t in required if t not in tools_used]
            unexpected = [t for t in tools_used if t not in all_allowed]

            if not required:
                # 不需要工具的节点
                if not tools_used:
                    score = 1.0
                else:
                    score = 0.5  # 用了不需要的工具
            else:
                score = 1.0
                if missing:
                    score -= 0.3 * len(missing) / len(required)
                if unexpected:
                    score -= 0.2 * len(unexpected) / max(len(tools_used), 1)

            scores[node_name] = {
                "score": max(score, 0.0),
                "tools_used": tools_used,
                "required": required,
                "missing": missing,
                "unexpected": unexpected,
            }

        return scores

    # ------------------------------------------------------------------
    #  参数准确性
    # ------------------------------------------------------------------
    def _evaluate_parameter_accuracy(
        self, tool_calls: list[dict]
    ) -> dict[str, Any]:
        """
        评估工具参数的准确性

        检查：
        - 必需参数是否存在
        - 参数类型是否正确
        - 参数值是否在约束范围内

        Args:
            tool_calls: 工具调用记录列表

        Returns:
            dict: 参数评估结果
        """
        param_scores = []

        for call in tool_calls:
            tool_name = call.get("tool_name", "")
            params = call.get("arguments", call.get("input", {}))

            if tool_name not in TOOL_PARAMETER_SCHEMA:
                continue

            schema = TOOL_PARAMETER_SCHEMA[tool_name]
            score = 1.0
            issues = []

            # 检查必需参数
            for required_param in schema.get("required", []):
                if required_param not in params or params[required_param] is None:
                    score -= 0.3
                    issues.append(f"缺少必需参数: {required_param}")

            # 检查参数类型和约束
            for param_name, param_value in params.items():
                if param_value is None:
                    continue

                # 类型检查
                expected_types = schema.get("types", {}).get(param_name)
                if expected_types and not isinstance(param_value, expected_types):
                    score -= 0.15
                    issues.append(f"参数类型错误: {param_name}")

                # 约束检查
                constraints = schema.get("constraints", {})
                if param_name in constraints:
                    try:
                        if not constraints[param_name](param_value):
                            score -= 0.15
                            issues.append(f"参数值超出范围: {param_name}={param_value}")
                    except Exception:
                        score -= 0.1
                        issues.append(f"参数验证异常: {param_name}")

            param_scores.append({
                "tool": tool_name,
                "score": max(score, 0.0),
                "issues": issues,
                "params": params,
            })

        avg_score = (
            sum(p["score"] for p in param_scores) / len(param_scores)
            if param_scores else 0.0
        )

        return {
            "average_score": round(avg_score, 4),
            "details": param_scores,
            "total_checked": len(param_scores),
        }

    # ------------------------------------------------------------------
    #  工具链执行评估
    # ------------------------------------------------------------------
    def _evaluate_tool_chain(
        self, tool_calls: list[dict], task: str
    ) -> dict[str, Any]:
        """
        评估多步工具链执行顺序

        检查：
        - 前置依赖是否满足（如先geocode再search）
        - 工具调用顺序是否合理
        - 是否有重复调用

        Args:
            tool_calls: 工具调用记录列表
            task: 任务描述

        Returns:
            dict: 工具链评估结果
        """
        tool_sequence = [
            c.get("tool_name", "") for c in tool_calls if c.get("tool_name")
        ]

        score = 1.0
        issues = []

        # 检查顺序约束
        for prerequisite, dependent in TOOL_ORDER_CONSTRAINTS:
            if prerequisite in tool_sequence and dependent in tool_sequence:
                prereq_idx = tool_sequence.index(prerequisite)
                depend_idx = tool_sequence.index(dependent)
                if prereq_idx > depend_idx:
                    score -= 0.3
                    issues.append(
                        f"{prerequisite} 应在 {dependent} 之前调用"
                    )

        # 检查是否有重复调用（超过3次视为异常）
        call_counts = Counter(tool_sequence)
        for tool_name, count in call_counts.items():
            if count > 3:
                score -= min(0.15, (count - 3) * 0.03)
                issues.append(f"{tool_name} 重复调用 {count} 次")

        # 根据任务复杂度调整分数
        complexity_bonus = 0.0
        if len(tool_sequence) >= 5:
            complexity_bonus = 0.05  # 复杂任务的奖励

        score = min(1.0, max(0.0, score + complexity_bonus))

        return {
            "score": round(score, 4),
            "tool_sequence": tool_sequence,
            "issues": issues,
            "tool_count": len(tool_sequence),
            "unique_tools": len(set(tool_sequence)),
        }

    # ------------------------------------------------------------------
    #  可验证奖励计算
    # ------------------------------------------------------------------
    def _calculate_verifiable_reward(
        self, tool_calls: list[dict], task: str
    ) -> float:
        """
        计算Structured Verifiable Reward

        基于工具调用的实际结果计算奖励：
        - 成功调用的比例
        - 结果数据的丰富度
        - 与任务的相关性

        Args:
            tool_calls: 工具调用记录列表
            task: 任务描述

        Returns:
            float: 奖励分数 (0-1)
        """
        if not tool_calls:
            return 0.0

        success_count = 0
        richness_scores = []

        for call in tool_calls:
            result = call.get("result", {})

            # 成功检查
            if not call.get("error") and result:
                success_count += 1

                # 结果丰富度
                if isinstance(result, dict):
                    # 基于结果字段数量评估丰富度
                    field_count = len(result)
                    if field_count >= 5:
                        richness_scores.append(1.0)
                    elif field_count >= 3:
                        richness_scores.append(0.7)
                    else:
                        richness_scores.append(0.4)
                elif isinstance(result, list):
                    item_count = len(result)
                    if item_count >= 10:
                        richness_scores.append(1.0)
                    elif item_count >= 5:
                        richness_scores.append(0.7)
                    else:
                        richness_scores.append(0.4)
                else:
                    richness_scores.append(0.5)

        # 成功率
        success_rate = success_count / len(tool_calls)

        # 平均丰富度
        avg_richness = (
            sum(richness_scores) / len(richness_scores)
            if richness_scores else 0.0
        )

        # 奖励 = 成功率 * 0.6 + 丰富度 * 0.4
        reward = success_rate * 0.6 + avg_richness * 0.4

        return round(reward, 4)

    # ------------------------------------------------------------------
    #  公开辅助方法
    # ------------------------------------------------------------------
    def check_tool_selection(
        self, actual: str, expected: str, context: str
    ) -> tuple[bool, str]:
        """
        检查工具选择是否正确

        Args:
            actual: 实际选择的工具
            expected: 期望的工具
            context: 任务上下文

        Returns:
            tuple[bool, str]: (是否正确, 原因)
        """
        if actual == expected:
            return True, f"工具选择正确: {actual}"

        # 检查是否有前置依赖问题
        for prereq, dependent in TOOL_ORDER_CONSTRAINTS:
            if expected == dependent and actual == prereq:
                return True, f"工具选择合理: {actual} 是 {dependent} 的前置步骤"

        return False, f"期望 {expected}，实际选择了 {actual}"

    def check_parameters(
        self, actual_args: dict, expected_schema: dict
    ) -> dict[str, bool]:
        """
        检查参数是否符合schema

        Args:
            actual_args: 实际参数
            expected_schema: 期望的schema定义

        Returns:
            dict[str, bool]: 每个参数的校验结果
        """
        results = {}
        required = expected_schema.get("required", [])
        types = expected_schema.get("types", {})

        for param in required:
            if param not in actual_args or actual_args[param] is None:
                results[param] = False
                continue

            value = actual_args[param]
            expected_type = types.get(param)
            if expected_type and not isinstance(value, expected_type):
                results[param] = False
                continue

            results[param] = True

        # 检查可选参数
        for param, value in actual_args.items():
            if param not in results:
                results[param] = value is not None

        return results

    def evaluate_tool_chain(
        self, tool_sequence: list[str], task: str
    ) -> float:
        """
        评估工具链合理性（公开接口）

        Args:
            tool_sequence: 工具调用顺序列表
            task: 任务描述

        Returns:
            float: 工具链合理性分数 (0-1)
        """
        if not tool_sequence:
            return 0.0

        score = 1.0

        # 检查顺序约束
        for prereq, dependent in TOOL_ORDER_CONSTRAINTS:
            if prereq in tool_sequence and dependent in tool_sequence:
                if tool_sequence.index(prereq) > tool_sequence.index(dependent):
                    score -= 0.3

        # 检查重复
        counts = Counter(tool_sequence)
        for count in counts.values():
            if count > 3:
                score -= 0.1

        return max(0.0, score)
