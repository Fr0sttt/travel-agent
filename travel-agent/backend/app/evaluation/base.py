"""
评估系统基类模块

定义所有评估器共享的数据结构和抽象基类，
包括评估结果(EvalResult)、评估报告(EvalReport)和评估器基类(BaseEvaluator)。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime


@dataclass
class EvalResult:
    """
    单个评估维度的结果

    Attributes:
        metric_name: 评估指标名称
        score: 评分 (0-1 浮点数)
        details: 详细评分数据字典
        reasoning: 评分依据和推理过程
        passed: 是否通过预设阈值
    """
    metric_name: str
    score: float
    details: dict
    reasoning: str
    passed: bool
    judge: dict[str, Any] | None = None
    hard_failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "metric_name": self.metric_name,
            "score": round(self.score, 4),
            "details": self.details,
            "reasoning": self.reasoning,
            "passed": self.passed,
            "judge": self.judge,
            "hard_failures": self.hard_failures,
        }


@dataclass
class EvalReport:
    """
    完整评估报告

    Attributes:
        session_id: 被评估的会话ID
        overall_score: 综合评分 (0-1)
        dimension_scores: 各维度评分字典
        results: 所有EvalResult列表
        recommendations: 改进建议列表
        timestamp: 评估时间戳
    """
    session_id: str
    overall_score: float
    dimension_scores: dict[str, float]
    results: list[EvalResult]
    recommendations: list[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "session_id": self.session_id,
            "overall_score": round(self.overall_score, 4),
            "dimension_scores": {k: round(v, 4) for k, v in self.dimension_scores.items()},
            "results": [r.to_dict() for r in self.results],
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
        }


@dataclass
class DimensionWeight:
    """
    评估维度权重配置

    Attributes:
        name: 维度名称
        weight: 权重值 (0-1)
        description: 维度描述
    """
    name: str
    weight: float
    description: str


@dataclass
class ToolCallRecord:
    """
    工具调用记录

    Attributes:
        tool_name: 工具名称
        arguments: 调用参数
        result: 调用结果
        timestamp: 调用时间戳
        latency_ms: 调用延迟(毫秒)
        success: 是否成功
    """
    tool_name: str
    arguments: dict
    result: Any
    timestamp: str
    latency_ms: float
    success: bool

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "timestamp": self.timestamp,
            "latency_ms": self.latency_ms,
            "success": self.success,
        }


@dataclass
class TrialSegment:
    """
    DoVer框架: 试次段 - 一次规划尝试的某个阶段

    Attributes:
        segment_id: 段唯一标识
        node_name: 对应LangGraph节点名称
        tool_calls: 该段的工具调用列表
        outcome: 执行结果 (success/partial/failure)
        duration_ms: 执行耗时(毫秒)
        errors: 错误信息列表
    """
    segment_id: str
    node_name: str
    tool_calls: list[dict] = field(default_factory=list)
    outcome: str = ""
    duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "segment_id": self.segment_id,
            "node_name": self.node_name,
            "tool_calls": self.tool_calls,
            "outcome": self.outcome,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
        }


class BaseEvaluator(ABC):
    """
    评估器抽象基类

    所有具体评估器必须继承此类，实现 evaluate 和 get_metric_names 方法。

    Usage:
        class MyEvaluator(BaseEvaluator):
            async def evaluate(self, input_data, output_data, context=None):
                # 评估逻辑
                return EvalResult(...)

            def get_metric_names(self):
                return ["my_metric"]
    """

    # 默认评分阈值，低于此值视为未通过
    DEFAULT_THRESHOLD: float = 0.6

    @abstractmethod
    async def evaluate(
        self,
        input_data: dict,
        output_data: dict,
        context: dict | None = None,
    ) -> EvalResult:
        """
        执行评估

        Args:
            input_data: 输入数据（如用户请求、任务描述）
            output_data: 输出数据（如生成的行程、工具调用记录）
            context: 可选的上下文信息

        Returns:
            EvalResult: 评估结果
        """
        pass

    @abstractmethod
    def get_metric_names(self) -> list[str]:
        """
        获取该评估器支持的所有指标名称

        Returns:
            list[str]: 指标名称列表
        """
        pass

    def _pass_check(self, score: float, threshold: float | None = None) -> bool:
        """
        检查分数是否通过阈值

        Args:
            score: 评分数值 (0-1)
            threshold: 自定义阈值，None则使用默认阈值

        Returns:
            bool: 是否通过
        """
        th = threshold if threshold is not None else self.DEFAULT_THRESHOLD
        return score >= th

    def _normalize_score(self, score: float) -> float:
        """
        将分数归一化到 [0, 1] 区间

        Args:
            score: 原始分数

        Returns:
            float: 归一化后的分数
        """
        return max(0.0, min(1.0, float(score)))

    async def batch_evaluate(
        self,
        cases: list[dict],
    ) -> list[EvalResult]:
        """
        批量评估多个案例

        Args:
            cases: 每个案例为包含 input_data, output_data, context 的字典

        Returns:
            list[EvalResult]: 所有案例的评估结果
        """
        results: list[EvalResult] = []
        for case in cases:
            result = await self.evaluate(
                input_data=case.get("input_data", {}),
                output_data=case.get("output_data", {}),
                context=case.get("context"),
            )
            results.append(result)
        return results
