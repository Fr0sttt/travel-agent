"""
Langfuse 观测客户端模块

提供全链路追踪功能，包括：
- Trace 创建和管理
- Span 记录（LangGraph 节点级别）
- LLM 调用记录（Generation）
- 工具调用记录（Event）
- 状态转换记录
- 评估分数上报

Langfuse 配置通过环境变量：
- LANGFUSE_PUBLIC_KEY: 公钥
- LANGFUSE_SECRET_KEY: 私钥
- LANGFUSE_HOST: 服务器地址
"""

from __future__ import annotations

import time
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Optional

# 上下文变量（用于在线程/协程间传递追踪 ID）
current_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
current_span_id: ContextVar[str | None] = ContextVar("span_id", default=None)


def get_current_trace_id() -> str | None:
    """获取当前 Trace ID"""
    return current_trace_id.get()


def get_current_span_id() -> str | None:
    """获取当前 Span ID"""
    return current_span_id.get()


def set_trace_id(trace_id: str) -> None:
    """设置当前 Trace ID"""
    current_trace_id.set(trace_id)


def set_span_id(span_id: str) -> None:
    """设置当前 Span ID"""
    current_span_id.set(span_id)


class LangfuseClient:
    """
    Langfuse 集成客户端 - 全链路观测

    每个旅行规划 session 作为一个 Trace，
    Trace 包含多个 Span（对应 LangGraph 节点）。

    Trace 层次结构:
    Trace (session_id)
    ├── Span: preference_collector
    │   ├── Event: 偏好提取
    │   └── Event: 追问输出
    ├── Span: destination_search
    │   ├── Span: geocode_location
    │   │   └── Event: Nominatim API 调用
    │   └── Span: search_places
    │       └── Event: OpenTripMap API 调用
    ├── Span: route_planner
    │   └── Event: OSRM 路线计算
    ├── Span: weather_advisor
    │   └── Event: Open-Meteo API 调用
    ├── Span: budget_estimator
    │   └── Event: 预算计算
    ├── Span: itinerary_synthesizer
    │   └── Event: 行程生成
    ├── Span: safety_reviewer
    │   └── Event: 安全审查
    └── Score: 多维评估分数
    """

    def __init__(self) -> None:
        """初始化 Langfuse 客户端"""
        self._langfuse: Any = None
        self._enabled = False
        self._init_client()

    def _init_client(self) -> None:
        """
        初始化底层 Langfuse 客户端

        如果环境变量未配置或导入失败，则禁用追踪。
        """
        try:
            from config import settings

            if not settings.langfuse_enabled:
                return

            if not settings.langfuse_public_key or not settings.langfuse_secret_key:
                self._enabled = False
                return

            from langfuse import Langfuse

            self._langfuse = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
            self._enabled = True

        except ImportError:
            self._enabled = False
        except Exception:
            self._enabled = False

    @property
    def is_enabled(self) -> bool:
        """检查 Langfuse 是否可用"""
        return self._enabled and self._langfuse is not None

    def start_trace(
        self,
        session_id: str,
        user_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """
        开始一个新的 Trace

        Args:
            session_id: 会话 ID
            user_input: 用户初始输入
            metadata: 附加元数据

        Returns:
            Trace ID 或 None（如果 Langfuse 未启用）
        """
        if not self.is_enabled:
            return None

        try:
            trace = self._langfuse.trace(
                id=session_id,
                name="travel_planning",
                user_id=metadata.get("user_id", "anonymous") if metadata else "anonymous",
                metadata={
                    "session_id": session_id,
                    "user_input": user_input,
                    "timestamp": datetime.now().isoformat(),
                    **(metadata or {}),
                },
                tags=["travel_agent", "v1.0"],
            )
            return trace.id
        except Exception:
            return None

    def start_span(
        self,
        trace_id: str,
        node_name: str,
        parent_span_id: str | None = None,
    ) -> str | None:
        """
        开始一个 Span

        Args:
            trace_id: 父 Trace ID
            node_name: 节点名称
            parent_span_id: 父 Span ID

        Returns:
            Span ID 或 None
        """
        if not self.is_enabled:
            return None

        try:
            span = self._langfuse.span(
                trace_id=trace_id,
                parent_observation_id=parent_span_id,
                name=node_name,
                metadata={"node_type": "langgraph_node"},
            )
            return span.id
        except Exception:
            return None

    def log_llm_call(
        self,
        trace_id: str | None,
        span_id: str | None,
        model: str,
        prompt: str,
        completion: str,
        tokens_used: dict[str, int] | None = None,
        latency_ms: float | None = None,
    ) -> None:
        """
        记录 LLM 调用（Generation）

        Args:
            trace_id: Trace ID
            span_id: 父 Span ID
            model: 模型名称
            prompt: 输入提示词
            completion: 模型输出
            tokens_used: Token 使用量
            latency_ms: 延迟（毫秒）
        """
        if not self.is_enabled or not trace_id:
            return

        try:
            self._langfuse.generation(
                trace_id=trace_id,
                parent_observation_id=span_id,
                name="llm_generation",
                model=model,
                input=prompt,
                output=completion,
                usage={
                    "input": tokens_used.get("prompt", 0) if tokens_used else 0,
                    "output": tokens_used.get("completion", 0) if tokens_used else 0,
                    "total": tokens_used.get("total", 0) if tokens_used else 0,
                },
                metadata={"latency_ms": latency_ms},
            )
        except Exception:
            pass

    def log_tool_call(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: dict[str, Any] | str,
        latency_ms: float | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
    ) -> None:
        """
        记录工具调用（Event）

        Args:
            tool_name: 工具名称
            tool_input: 工具输入参数
            tool_output: 工具输出结果
            latency_ms: 执行耗时（毫秒）
            trace_id: Trace ID（可选，默认使用当前上下文）
            span_id: Span ID（可选）
        """
        if not self.is_enabled:
            return

        tid = trace_id or get_current_trace_id()
        if not tid:
            return

        try:
            output_dict = tool_output if isinstance(tool_output, dict) else {"result": str(tool_output)}

            self._langfuse.event(
                trace_id=tid,
                parent_observation_id=span_id,
                name=f"tool_{tool_name}",
                input=tool_input,
                output=output_dict,
                metadata={
                    "tool_name": tool_name,
                    "latency_ms": round(latency_ms, 2) if latency_ms else None,
                    "source": output_dict.get("_source", "unknown"),
                },
            )
        except Exception:
            pass

    def log_state_transition(
        self,
        trace_id: str | None,
        from_node: str,
        to_node: str,
        state_snapshot: dict[str, Any] | None = None,
    ) -> None:
        """
        记录状态转换

        Args:
            trace_id: Trace ID
            from_node: 源节点
            to_node: 目标节点
            state_snapshot: 状态快照
        """
        if not self.is_enabled or not trace_id:
            return

        try:
            self._langfuse.event(
                trace_id=trace_id,
                name="state_transition",
                input={"from": from_node},
                output={"to": to_node},
                metadata={
                    "state_keys": list(state_snapshot.keys()) if state_snapshot else [],
                    "poi_count": len(state_snapshot.get("poi_list", [])) if state_snapshot else 0,
                },
            )
        except Exception:
            pass

    def add_score(
        self,
        trace_id: str | None,
        name: str,
        value: float,
        comment: str | None = None,
    ) -> None:
        """
        添加评估分数

        评分维度:
        - constraint_satisfaction: 约束满足率 (0-1)
        - route_reasonableness: 路线合理性 (0-1)
        - source_grounding: 来源引用 (0-1)
        - uncertainty_disclosure: 不确定性披露 (0-1)
        - safety_compliance: 安全合规率 (0-1)
        - total_latency_ms: 总响应时间

        Args:
            trace_id: Trace ID
            name: 分数名称
            value: 分数值
            comment: 备注
        """
        if not self.is_enabled or not trace_id:
            return

        try:
            self._langfuse.score(
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment,
            )
        except Exception:
            pass

    def end_trace(
        self,
        trace_id: str | None,
        final_output: str | None = None,
        status: str = "success",
    ) -> None:
        """
        结束 Trace

        Args:
            trace_id: Trace ID
            final_output: 最终输出
            status: 状态
        """
        # Langfuse 自动处理 trace 结束
        pass


# 全局客户端实例（单例）
_langfuse_client: LangfuseClient | None = None


def get_langfuse() -> LangfuseClient:
    """
    获取 Langfuse 客户端单例

    Returns:
        LangfuseClient: 全局客户端实例
    """
    global _langfuse_client
    if _langfuse_client is None:
        _langfuse_client = LangfuseClient()
    return _langfuse_client
