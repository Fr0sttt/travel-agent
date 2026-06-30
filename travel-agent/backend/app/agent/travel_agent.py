"""
Travel Agent 主类模块

TravelAgent 类是整个旅行规划系统的核心入口，负责：
1. 管理 LangGraph 状态机的执行
2. 协调 LLM 调用、工具调用和安全审查
3. 提供流式输出支持（通过异步生成器）
4. 集成 Langfuse 观测和记忆管理
"""

from __future__ import annotations

import asyncio
import json
import traceback
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from agent.graph import TravelState, travel_graph
from agent.prompts import FOLLOW_UP_PROMPT
from agent.tools import TOOLS
from models.schemas import AgentResponse, Itinerary, ToolCallRecord


class TravelAgent:
    """
    Travel Agent 主类

    提供完整的旅行规划服务，包括：
    - 偏好收集和澄清
    - 目的地搜索和 POI 发现
    - 路线规划和天气查询
    - 预算估算和行程合成
    - 安全审查和输出格式化

    Attributes:
        graph: LangGraph 编译后的状态图
        sessions: 会话状态缓存（简单内存实现）
    """

    def __init__(
        self,
        llm_client: Any | None = None,
        memory_manager: Any | None = None,
        safety_guard: Any | None = None,
        langfuse_client: Any | None = None,
    ):
        """
        初始化 Travel Agent

        Args:
            llm_client: LLM 客户端（如 OpenAI 客户端）
            memory_manager: 记忆管理器（如 mem0 实例）
            safety_guard: 安全审查器
            langfuse_client: Langfuse 观测客户端
        """
        self.graph = travel_graph
        self.llm = llm_client
        self.memory = memory_manager
        self.safety = safety_guard
        self.langfuse = langfuse_client
        # 简单的内存会话缓存
        self.sessions: dict[str, dict[str, Any]] = {}

    async def plan_travel(
        self,
        user_input: str,
        session_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        主规划流程 - 流式输出

        接收用户输入，执行完整的旅行规划流程，通过异步生成器流式返回结果。

        Args:
            user_input: 用户的自然语言输入
            session_id: 会话 ID（可选，首次调用自动生成）

        Yields:
            str: JSON 格式的状态更新，包含当前步骤、消息和最终结果

        Examples:
            >>> async for update in agent.plan_travel("我想去杭州玩3天", "sess_001"):
            ...     print(update)
        """
        # 生成或获取会话 ID
        session_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"

        # 检查是否是追问回复（已有会话）
        existing_state = self.sessions.get(session_id)

        if existing_state and existing_state.get("needs_clarification"):
            # 追问模式：合并用户输入到现有会话
            yield self._format_event(
                "status",
                {"message": "收到补充信息，继续规划...", "session_id": session_id},
            )

            # 合并新的输入
            prev_input = existing_state.get("user_input", "")
            combined_input = f"{prev_input}\n用户补充: {user_input}"

            # 获取当前偏好并更新
            current_pref = existing_state.get("preference", {})

            # 重新创建状态
            state = TravelState.create(session_id, combined_input)
            state["preference"] = current_pref
            state["messages"] = existing_state.get("messages", [])
            state["messages"].append({"role": "user", "content": user_input})
        else:
            # 新建规划流程
            state = TravelState.create(session_id, user_input)
            state["messages"] = [{"role": "user", "content": user_input}]
            self.sessions[session_id] = state

            yield self._format_event(
                "status",
                {"message": "开始规划您的旅行...", "session_id": session_id},
            )

        # 执行 LangGraph
        try:
            current_state = state
            iteration = 0
            max_iterations = 10

            # 逐步执行图中的每个节点
            node_sequence = [
                ("preference_collector", "正在收集您的旅行偏好..."),
                ("constraint_normalizer", "正在分析您的需求..."),
                ("destination_search", "正在搜索目的地景点..."),
                ("route_planner", "正在规划最佳路线..."),
                ("weather_advisor", "正在查询天气预报..."),
                ("budget_estimator", "正在估算旅行费用..."),
                ("itinerary_synthesizer", "正在合成行程计划..."),
                ("safety_reviewer", "正在进行安全审查..."),
                ("output_formatter", "正在格式化输出..."),
            ]

            for node_name, status_msg in node_sequence:
                if iteration >= max_iterations:
                    yield self._format_event(
                        "error",
                        {"message": "规划流程超出最大迭代次数", "session_id": session_id},
                    )
                    break

                iteration += 1
                current_state["iteration_count"] = iteration

                # 发送状态更新
                yield self._format_event(
                    "progress",
                    {
                        "step": node_name,
                        "message": status_msg,
                        "progress": int((iteration / len(node_sequence)) * 100),
                        "session_id": session_id,
                    },
                )

                # 获取节点函数
                node_func = self._get_node_function(node_name)
                if node_func is None:
                    continue

                # 执行节点
                try:
                    current_state = await node_func(current_state)
                except Exception as e:
                    error_msg = f"节点 {node_name} 执行失败: {str(e)}"
                    current_state["risk_alerts"].append(error_msg)
                    yield self._format_event(
                        "warning",
                        {"message": error_msg, "step": node_name, "session_id": session_id},
                    )
                    # 继续执行后续节点，不要中断

                # 检查是否需要澄清
                if node_name == "preference_collector" and current_state.get("needs_clarification"):
                    self.sessions[session_id] = dict(current_state)
                    follow_up = ""
                    if current_state.get("messages"):
                        last_msg = current_state["messages"][-1]
                        if isinstance(last_msg, dict) and last_msg.get("role") == "assistant":
                            follow_up = last_msg.get("content", "")

                    yield self._format_event(
                        "clarify",
                        {
                            "message": follow_up or "请补充更多信息",
                            "missing_fields": current_state.get("missing_fields", []),
                            "session_id": session_id,
                        },
                    )
                    return  # 等待用户回复

            # 保存最终状态
            self.sessions[session_id] = dict(current_state)

            # 发送最终结果
            itinerary_md = current_state.get("itinerary", "")
            risk_alerts = current_state.get("risk_alerts", [])
            tool_calls = current_state.get("tool_calls", [])

            # 构建响应
            response = AgentResponse(
                session_id=session_id,
                status="complete",
                current_step="output_formatter",
                message="行程规划完成！",
                itinerary=None,  # 简化处理，实际应构建 Itinerary 对象
                tool_calls=[ToolCallRecord(**tc) for tc in tool_calls if isinstance(tc, dict)],
                risk_alerts=risk_alerts,
                needs_clarification=False,
                trace_id=current_state.get("trace_id"),
            )

            yield self._format_event(
                "complete",
                {
                    "message": "行程规划完成！",
                    "itinerary": itinerary_md,
                    "risk_alerts": risk_alerts,
                    "session_id": session_id,
                    "response": response.model_dump(),
                },
            )

        except Exception as e:
            error_detail = traceback.format_exc()
            yield self._format_event(
                "error",
                {
                    "message": f"规划过程中发生错误: {str(e)}",
                    "detail": error_detail if __debug__ else None,
                    "session_id": session_id,
                },
            )

    async def chat(
        self,
        message: str,
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        聊天模式 - 支持自由对话

        接收用户消息，可以是对已有行程的追问或新的规划需求。

        Args:
            message: 用户消息
            session_id: 会话 ID

        Yields:
            str: JSON 格式的响应
        """
        # 检查是否已有行程
        existing = self.sessions.get(session_id)

        if existing and existing.get("itinerary") and not message.startswith("新规划"):
            # 追问模式 - 基于已有行程回答
            yield self._format_event(
                "status",
                {"message": "正在回答您的问题...", "session_id": session_id},
            )

            # 简单的问答回复（实际可由 LLM 生成）
            reply = self._generate_qa_reply(message, existing)
            yield self._format_event(
                "reply",
                {"message": reply, "session_id": session_id},
            )
        else:
            # 新规划需求
            async for update in self.plan_travel(message, session_id):
                yield update

    def get_session_state(self, session_id: str) -> dict[str, Any] | None:
        """
        获取会话状态

        Args:
            session_id: 会话 ID

        Returns:
            会话状态字典或 None
        """
        return self.sessions.get(session_id)

    def clear_session(self, session_id: str) -> bool:
        """
        清除会话

        Args:
            session_id: 会话 ID

        Returns:
            是否成功清除
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def _get_node_function(self, node_name: str):
        """
        根据节点名称获取节点函数

        Args:
            node_name: 节点名称

        Returns:
            节点函数或 None
        """
        from agent.graph import (
            budget_estimator,
            constraint_normalizer,
            destination_search,
            itinerary_synthesizer,
            output_formatter,
            preference_collector,
            route_planner,
            safety_reviewer,
            weather_advisor,
        )

        node_map = {
            "preference_collector": preference_collector,
            "constraint_normalizer": constraint_normalizer,
            "destination_search": destination_search,
            "route_planner": route_planner,
            "weather_advisor": weather_advisor,
            "budget_estimator": budget_estimator,
            "itinerary_synthesizer": itinerary_synthesizer,
            "safety_reviewer": safety_reviewer,
            "output_formatter": output_formatter,
        }
        return node_map.get(node_name)

    def _generate_qa_reply(self, message: str, state: dict) -> str:
        """
        生成问答回复（简化版）

        Args:
            message: 用户问题
            state: 当前会话状态

        Returns:
            回复文本
        """
        message_lower = message.lower()
        itinerary = state.get("itinerary", "")
        preference = state.get("preference") or {}
        pref_dict = preference if isinstance(preference, dict) else {}

        if any(kw in message for kw in ["预算", "多少钱", "费用"]):
            budget = state.get("total_budget_estimate", {})
            return (
                f"根据估算，您的旅行总费用大约在 {budget.get('min', 'N/A')} - {budget.get('max', 'N/A')} 元之间。"
                f"\n\n具体费用明细可以在行程计划中查看。"
            )

        if any(kw in message for kw in ["天气", "下雨", "温度"]):
            weather = state.get("weather", [])
            if weather:
                first_day = weather[0]
                return (
                    f"{first_day.get('date', '')} 的天气是 {first_day.get('description', '未知')}，"
                    f"温度 {first_day.get('temperature_min', 'N/A')}~{first_day.get('temperature_max', 'N/A')}°C，"
                    f"降水概率 {first_day.get('precipitation_probability', 0)}%。"
                )
            return "暂无天气信息。"

        if any(kw in message for kw in ["景点", "去哪", "玩什么"]):
            poi_list = state.get("poi_list", [])
            poi_names = [p.get("name", "") for p in poi_list[:5]]
            return f"推荐景点: {', '.join(poi_names)} 等。详细安排请查看行程计划。"

        if any(kw in message for kw in ["修改", "改", "换", "调整"]):
            return (
                "如果您需要修改行程，请直接告诉我您的新的需求，"
                "例如\"我想换成上海的行程\"或\"预算提高到5000\"。"
            )

        return (
            f"我理解您的问题是关于: {message}\n\n"
            f"您可以查看上方生成的完整行程计划，"
            f"或者告诉我您需要调整的地方，我可以为您重新规划。"
        )

    def _format_event(self, event_type: str, data: dict) -> str:
        """
        格式化 SSE 事件

        Args:
            event_type: 事件类型
            data: 事件数据

        Returns:
            SSE 格式的字符串
        """
        return f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False)}\n\n"


# 全局 Agent 实例
travel_agent = TravelAgent()
