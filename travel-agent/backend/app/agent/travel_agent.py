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
import time
import traceback
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from agent.graph import create_initial_state
from agent.prompts import FOLLOW_UP_PROMPT
from agent.tools import TOOLS
from models.schemas import AgentResponse, Itinerary, ToolCallRecord

# 节点名 -> 用户可读的进度提示，astream 拿到某个节点的输出时用这个映射
# 生成 progress 事件的文案。
_NODE_STATUS_MESSAGES = {
    "intent_router": "正在理解您的意图...",
    "preference_collector": "正在收集您的旅行偏好...",
    "constraint_normalizer": "正在分析您的需求...",
    "destination_search": "正在搜索目的地景点...",
    "route_planner": "正在规划最佳路线...",
    "weather_advisor": "正在查询天气预报...",
    "budget_estimator": "正在估算旅行费用...",
    "itinerary_synthesizer": "正在合成行程计划...",
    "safety_reviewer": "正在进行安全审查...",
    "output_formatter": "正在格式化输出...",
    "qa_responder": "正在回答您的问题...",
    "chitchat_responder": "正在回应...",
}

# 用于计算 progress 百分比的节点总数（跟 _NODE_STATUS_MESSAGES 数量一致即可，
# 只是个大致进度展示，不要求精确）
_TOTAL_NODE_COUNT = len(_NODE_STATUS_MESSAGES)


class TravelAgent:
    """
    Travel Agent 主类

    提供完整的旅行规划服务，包括：
    - 意图路由（新规划/继续澄清/行程问答/闲聊）
    - 偏好收集和澄清
    - 目的地搜索和 POI 发现
    - 路线规划和天气查询
    - 预算估算和行程合成
    - 安全审查和输出格式化

    执行引擎是真正的 LangGraph StateGraph（通过 self.graph.astream 驱动），
    状态持久化交给传入的 checkpointer（比如 AsyncPostgresSaver），
    支持进程重启后用同一个 session_id 继续未完成的对话。

    Attributes:
        graph: 编译好的 LangGraph 状态图（已绑定 checkpointer）
    """

    def __init__(
        self,
        graph: Any,
        memory_manager: Any | None = None,
        safety_guard: Any | None = None,
        langfuse_client: Any | None = None,
        evaluation_service: Any | None = None,
    ):
        """
        初始化 Travel Agent

        Args:
            graph: 编译好的 LangGraph 状态图（由 main.py 的 lifespan 传入，
                已经在编译时绑定了 checkpointer）
            memory_manager: 记忆管理器（会话历史持久化、长期记忆检索）
            safety_guard: 安全审查器
            langfuse_client: Langfuse 观测客户端
        """
        self.graph = graph
        self.memory = memory_manager
        self.safety = safety_guard
        self.langfuse = langfuse_client
        self.evaluation_service = evaluation_service

    async def plan_travel(
        self,
        user_input: str,
        session_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        主入口 - 流式输出

        接收用户输入，交给 LangGraph 图执行（意图路由 -> 对应分支），
        通过异步生成器流式返回结果。原来 chat() 方法的职责（判断"是继续
        规划还是行程问答还是闲聊"）现在由图入口的 intent_router 节点承担，
        不再需要在 TravelAgent 层单独维护一套判断逻辑，所以 plan_travel
        是唯一入口，chat() 已删除。

        断点续传：session_id 直接当作 LangGraph 的 thread_id 使用。
        checkpointer（绑定在 self.graph 编译时）会自动持久化每个节点执行后
        的状态，进程重启后用同一个 session_id 调用，图会从上次停下的地方
        （比如等待用户澄清）继续，而不是从头重新跑。

        Args:
            user_input: 用户的自然语言输入
            session_id: 会话 ID（可选，首次调用自动生成，之后必须复用同一个
                ID 才能续上之前的对话）

        Yields:
            str: SSE 格式的事件字符串（status/progress/clarify/reply/complete/error）
        """
        session_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"
        call_id = uuid.uuid4().hex[:6]
        config = {"configurable": {"thread_id": session_id}}
        trace_id: str | None = None

        print(
            f"[TravelAgent][{call_id}] plan_travel 被调用: "
            f"session_id={session_id}, user_input={user_input[:60]!r}",
            flush=True,
        )

        # 查一下 checkpointer 里有没有这个 thread 的历史状态，
        # 用来判断这是全新对话还是接着上次未完成的继续。
        try:
            existing_snapshot = await self.graph.aget_state(config)
            existing_values = existing_snapshot.values if existing_snapshot else {}
        except Exception as exc:
            print(f"[TravelAgent][{call_id}] 读取 checkpoint 状态失败（视为全新会话）: {exc}", flush=True)
            existing_values = {}

        has_existing_state = bool(existing_values)
        print(
            f"[TravelAgent][{call_id}] checkpoint 状态: has_existing_state={has_existing_state} "
            f"needs_clarification={existing_values.get('needs_clarification')}",
            flush=True,
        )

        if has_existing_state:
            yield self._format_event(
                "status",
                {"message": "收到补充信息，继续规划...", "session_id": session_id},
            )
            # 把新一轮用户输入合并进去，图会从 intent_router 重新判断意图
            # （比如上次在等澄清，这次用户补充了信息，intent_router 会分到
            # continue_clarify 分支；如果用户改口说了完全不相关的新目的地，
            # 也能被正确识别为 new_plan）。
            input_state = {
                "user_input": user_input,
                "messages": (existing_values.get("messages") or []) + [
                    {"role": "user", "content": user_input}
                ],
            }
        else:
            yield self._format_event(
                "status",
                {"message": "开始处理您的请求...", "session_id": session_id},
            )
            input_state = create_initial_state(session_id, user_input)
            input_state["messages"] = [{"role": "user", "content": user_input}]

        # 一次用户请求对应一个 Langfuse Trace；同一 session 继续对话时复用已有 Trace。
        trace_id = existing_values.get("trace_id") if has_existing_state else None
        if not trace_id and self.langfuse:
            trace_id = self.langfuse.start_trace(
                session_id=session_id,
                user_input=user_input,
                metadata={"call_id": call_id, "has_existing_state": has_existing_state},
            )
        if trace_id:
            input_state["trace_id"] = trace_id
            try:
                from observability.langfuse_client import set_trace_id
                set_trace_id(trace_id)
            except Exception:
                pass

        try:
            # final_state 的起点必须是完整的初始状态（input_state），不能只是
            # existing_values——全新对话时 existing_values 是空字典，如果不
            # 从 input_state 起步，后续 messages/preference 等字段会缺失，
            # 第一个节点（intent_router 只改 user_intent/current_node 两个字段）
            # 跑完后 final_state 里就没有 messages，preference_collector 一读
            # state["messages"] 就会 KeyError。
            final_state: dict[str, Any] = dict(existing_values)
            final_state.update(input_state)
            node_index = 0
            previous_node = "START"
            previous_completed_at = time.perf_counter()

            async for step in self.graph.astream(input_state, config=config, stream_mode="updates"):
                # stream_mode="updates" 每次迭代给一个 {节点名: 该节点输出的状态更新}
                for node_name, node_output in step.items():
                    node_index += 1
                    node_started_at = time.perf_counter()
                    before_snapshot = self._trace_snapshot(final_state)
                    before_tool_calls = list(final_state.get("tool_calls") or [])
                    final_state.update(node_output)
                    duration_ms = (node_started_at - previous_completed_at) * 1000
                    previous_completed_at = time.perf_counter()
                    after_snapshot = self._trace_snapshot(final_state)
                    trajectory_entry = {
                        "type": "node",
                        "node": node_name,
                        "from_node": previous_node,
                        "timestamp": datetime.now().isoformat(),
                        "duration_ms": round(duration_ms, 2),
                        "input": before_snapshot,
                        "output": after_snapshot,
                        "success": True,
                    }
                    final_state.setdefault("trajectory", []).append(trajectory_entry)
                    final_state.setdefault("node_snapshots", []).append({
                        "node": node_name,
                        "timestamp": trajectory_entry["timestamp"],
                        "duration_ms": trajectory_entry["duration_ms"],
                        "state": after_snapshot,
                    })
                    # 将节点内新增的工具调用展开成独立轨迹事件，供 AgentWorld 和 DoVer 评测。
                    current_tool_calls = list(final_state.get("tool_calls") or [])
                    for tool_call in current_tool_calls[len(before_tool_calls):]:
                        final_state.setdefault("trajectory", []).append({
                            "type": "tool_call",
                            "node": tool_call.get("node", node_name) if isinstance(tool_call, dict) else node_name,
                            "tool_name": tool_call.get("tool_name", "") if isinstance(tool_call, dict) else "",
                            "arguments": (tool_call.get("arguments") or tool_call.get("input") or {}) if isinstance(tool_call, dict) else {},
                            "result": tool_call.get("result") if isinstance(tool_call, dict) else None,
                            "success": tool_call.get("success", True) if isinstance(tool_call, dict) else True,
                            "error": tool_call.get("error") if isinstance(tool_call, dict) else None,
                            "timestamp": tool_call.get("timestamp", datetime.now().isoformat()) if isinstance(tool_call, dict) else datetime.now().isoformat(),
                        })
                    if self.langfuse and trace_id:
                        self.langfuse.log_state_transition(
                            trace_id, previous_node, node_name, after_snapshot
                        )
                        self.langfuse.log_node_execution(
                            trace_id,
                            node_name,
                            before_snapshot,
                            after_snapshot,
                            duration_ms,
                        )
                    previous_node = node_name

                    status_msg = _NODE_STATUS_MESSAGES.get(node_name, f"执行 {node_name}...")
                    print(
                        f"[TravelAgent][{call_id}] 节点 {node_name} 完成 "
                        f"poi_list数={len(final_state.get('poi_list') or [])} "
                        f"itinerary长度={len(final_state.get('itinerary') or '')} "
                        f"needs_clarification={final_state.get('needs_clarification')} "
                        f"user_intent={final_state.get('user_intent')}",
                        flush=True,
                    )

                    yield self._format_event(
                        "progress",
                        {
                            "step": node_name,
                            "message": status_msg,
                            "progress": min(95, int((node_index / _TOTAL_NODE_COUNT) * 100)),
                            "session_id": session_id,
                        },
                    )

            # ===== 图执行完毕（或在 preference_collector 之后停在 END 等待澄清）=====
            intent = final_state.get("user_intent")
            needs_clarification = bool(final_state.get("needs_clarification"))
            itinerary_md = final_state.get("itinerary") or ""
            qa_response = final_state.get("qa_response")
            chitchat_response = final_state.get("chitchat_response")
            risk_alerts = final_state.get("risk_alerts") or []
            tool_calls = final_state.get("tool_calls") or []

            if needs_clarification:
                # 还缺关键信息，等待用户继续补充（图已经在 END 停住，
                # checkpointer 记住了这个状态，下次同 session_id 调用会续上）
                follow_up = ""
                messages = final_state.get("messages") or []
                if messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg, dict) and last_msg.get("role") == "assistant":
                        follow_up = last_msg.get("content", "")

                if self.memory:
                    try:
                        await self.memory.process_interaction(
                            user_input, follow_up or "请补充更多信息", final_state,
                        )
                    except Exception as exc:
                        print(f"[TravelAgent][{call_id}] 保存澄清会话历史失败: {exc}")

                yield self._format_event(
                    "clarify",
                    {
                        "message": follow_up or "请补充更多信息",
                        "missing_fields": final_state.get("missing_fields", []),
                        "session_id": session_id,
                    },
                )
                if self.langfuse:
                    self.langfuse.end_trace(trace_id, final_output=follow_up, status="clarify")
                return

            if intent == "faq_about_itinerary" and qa_response:
                if self.memory:
                    try:
                        await self.memory.process_interaction(user_input, qa_response, final_state)
                    except Exception as exc:
                        print(f"[TravelAgent][{call_id}] 保存问答记忆失败: {exc}")
                yield self._format_event(
                    "reply",
                    {"message": qa_response, "session_id": session_id},
                )
                if self.langfuse:
                    self.langfuse.end_trace(trace_id, final_output=qa_response, status="success")
                return

            if intent == "chitchat" and chitchat_response:
                if self.memory:
                    try:
                        await self.memory.process_interaction(user_input, chitchat_response, final_state)
                    except Exception as exc:
                        print(f"[TravelAgent][{call_id}] 保存闲聊记忆失败: {exc}")
                yield self._format_event(
                    "reply",
                    {"message": chitchat_response, "session_id": session_id},
                )
                if self.langfuse:
                    self.langfuse.end_trace(trace_id, final_output=chitchat_response, status="success")
                return

            # 走到这里说明完整规划流程跑完了，itinerary_md 应该有内容
            print(
                f"[TravelAgent][{call_id}] 即将发出 complete 事件: "
                f"itinerary长度={len(itinerary_md)} tool_calls数={len(tool_calls)} "
                f"risk_alerts数={len(risk_alerts)}",
                flush=True,
            )

            if self.memory:
                try:
                    final_reply = itinerary_md or "行程已生成"
                    await self.memory.process_interaction(user_input, final_reply, final_state)
                except Exception as e:
                    print(f"[TravelAgent][{call_id}] 写入记忆失败: {e}")

            evaluation_run_id = None
            if self.evaluation_service:
                evaluation_run_id = self.evaluation_service.submit(
                    self._build_evaluation_data(final_state, user_input, session_id)
                )
                final_state["evaluation_meta"] = {
                    "run_id": evaluation_run_id,
                    "status": "queued",
                    "queued_at": datetime.now().isoformat(),
                }

            # 将本轮可观测轨迹和评测任务 ID 写回 LangGraph checkpoint，支持后续复盘。
            try:
                await self.graph.aupdate_state(
                    config,
                    {
                        "trace_id": trace_id,
                        "trajectory": final_state.get("trajectory", []),
                        "node_snapshots": final_state.get("node_snapshots", []),
                        "evaluation_meta": final_state.get("evaluation_meta"),
                    },
                )
            except Exception as exc:
                print(f"[TravelAgent][{call_id}] 保存评测轨迹失败: {exc}", flush=True)

            if self.langfuse:
                self.langfuse.end_trace(
                    trace_id,
                    final_output=itinerary_md,
                    status="success",
                )

            response = AgentResponse(
                session_id=session_id,
                status="complete",
                current_step="output_formatter",
                message="行程规划完成！",
                itinerary=None,  # 简化处理，实际应构建 Itinerary 对象
                tool_calls=[ToolCallRecord(**tc) for tc in tool_calls if isinstance(tc, dict)],
                risk_alerts=risk_alerts,
                needs_clarification=False,
                trace_id=final_state.get("trace_id"),
            )

            yield self._format_event(
                "complete",
                {
                    "message": "行程规划完成！",
                    "itinerary": itinerary_md,
                    "risk_alerts": risk_alerts,
                    "session_id": session_id,
                    "evaluation_run_id": evaluation_run_id,
                    "response": response.model_dump(),
                },
            )

        except Exception as e:
            error_detail = traceback.format_exc()
            # 之前这个异常只发进了 SSE error 事件给前端，后端终端完全没有
            # 任何输出——看起来像是"卡住了"，实际是异常被这里默默吞掉了。
            # 必须打印到后端终端，否则排查时看不到真实的报错位置。
            print(
                f"[TravelAgent][{call_id}] plan_travel 内部异常，完整堆栈如下:\n{error_detail}",
                flush=True,
            )
            if self.langfuse:
                self.langfuse.end_trace(trace_id, status="error")
            yield self._format_event(
                "error",
                {
                    "message": f"规划过程中发生错误: {str(e)}",
                    "detail": error_detail if __debug__ else None,
                    "session_id": session_id,
                },
            )

    @staticmethod
    def _trace_snapshot(state: dict[str, Any]) -> dict[str, Any]:
        """生成用于 Trace 和评测的轻量状态快照，不上传完整消息和大文本。"""
        return {
            "current_node": state.get("current_node"),
            "user_intent": state.get("user_intent"),
            "needs_clarification": state.get("needs_clarification", False),
            "poi_count": len(state.get("poi_list") or []),
            "route_count": len(state.get("route") or []),
            "weather_count": len(state.get("weather") or []),
            "tool_call_count": len(state.get("tool_calls") or []),
            "itinerary_length": len(state.get("itinerary") or ""),
            "risk_alert_count": len(state.get("risk_alerts") or []),
        }

    @staticmethod
    def _build_evaluation_data(
        state: dict[str, Any], user_input: str, session_id: str
    ) -> dict[str, Any]:
        """把 LangGraph 最终状态转换成四层评测统一输入契约。"""
        poi_list = state.get("poi_list") or []
        route = state.get("route") or []
        weather = state.get("weather") or []
        budget = state.get("budget") or []
        tool_calls = state.get("tool_calls") or []

        # 评测需要“事实 -> 证据”的结构化输入。正文里的“数据来源说明”只是
        # 展示文案，不能代替证据；这里把真实工具返回结果和状态中的来源字段
        # 统一整理给 FACT 与综合评测使用。
        cited_sources: list[dict[str, Any]] = []

        def add_source(source_type: str, source: Any, content: Any, metadata: dict[str, Any] | None = None) -> None:
            if not source and not content:
                return
            cited_sources.append({
                "source_type": source_type,
                "source": str(source or source_type),
                "url": str(source or source_type),
                "content": content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, default=str)[:6000],
                "metadata": metadata or {},
            })

        for poi in poi_list:
            if isinstance(poi, dict):
                add_source("poi", poi.get("source"), poi, {"name": poi.get("name"), "category": poi.get("category")})
        for item in weather:
            if isinstance(item, dict):
                add_source("weather", item.get("source"), item, {"date": item.get("date")})
        for segment in route:
            if isinstance(segment, dict):
                add_source("route", segment.get("source"), segment, {"from": segment.get("from_poi"), "to": segment.get("to_poi")})
        for item in (budget if isinstance(budget, list) else []):
            if isinstance(item, dict):
                add_source("budget", item.get("source") or "规则估算", item, {"category": item.get("category")})

        # 工具调用是最底层的可审计证据。只加入成功且确实有结果的调用，
        # 避免把异常文本当成事实来源。
        for call in tool_calls:
            if not isinstance(call, dict) or not call.get("success", True) or not call.get("result"):
                continue
            add_source(
                "tool_result",
                call.get("tool_name"),
                call.get("result"),
                {"node": call.get("node"), "arguments": call.get("arguments") or call.get("input") or {}},
            )

        return {
            "session_id": session_id,
            "trace_id": state.get("trace_id"),
            "user_request": user_input,
            "constraints": state.get("constraints") or {},
            "preferences": state.get("preference") or {},
            "itinerary": state.get("itinerary") or "",
            "route_plan": state.get("route") or [],
            "weather": state.get("weather") or [],
            "budget": state.get("budget") or {},
            "trajectory": state.get("trajectory") or [],
            "node_snapshots": state.get("node_snapshots") or [],
            "tool_calls": tool_calls,
            "cited_sources": cited_sources,
            "actions": state.get("confirmation_required") or [],
            "risk_alerts": state.get("risk_alerts") or [],
            "replan_events": state.get("replan_events") or [],
        }

    async def get_session_state(self, session_id: str) -> dict[str, Any] | None:
        """
        获取会话状态

        直接从 checkpointer 读取图执行的最新状态快照，不再依赖内存字典。

        Args:
            session_id: 会话 ID

        Returns:
            会话状态字典或 None
        """
        try:
            snapshot = await self.graph.aget_state({"configurable": {"thread_id": session_id}})
            if snapshot and snapshot.values:
                return dict(snapshot.values)
        except Exception as exc:
            print(f"[TravelAgent] 读取 checkpoint 状态失败: {exc}")

        if self.memory:
            try:
                persisted = self.memory.get_session_snapshot(session_id)
                if persisted:
                    return persisted
            except Exception as exc:
                print(f"[TravelAgent] 读取持久化快照失败: {exc}")
        return None

    def clear_session(self, session_id: str) -> bool:
        """
        清除会话的持久化记录（chat_sessions/chat_messages）。

        注意：这里只清 self.memory 管理的会话历史表，不清 LangGraph
        checkpointer 里的图执行状态——checkpointer 的清理需要按 thread_id
        删除对应的 checkpoint 记录，如果后续需要“彻底删除会话”包含图状态，
        再补充调用 checkpointer 的删除接口。

        Args:
            session_id: 会话 ID

        Returns:
            是否成功清除
        """
        cleared = False
        if self.memory:
            try:
                self.memory.delete_session(session_id)
                cleared = True
            except Exception as exc:
                print(f"[TravelAgent] 删除持久化会话失败: {exc}")
        return cleared

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
