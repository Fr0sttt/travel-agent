"""统一记忆入口。

这一层把短期记忆、长期记忆、会话历史和 mem0 统一包装成一个门面，
Agent 侧只需要依赖这里，不需要关心底层存储细节。
"""

from __future__ import annotations

from typing import Any
import time

from .context_manager import ContextManager
from .long_term import LongTermMemory
from .mem0_adapter import Mem0Adapter
from .session_history import SessionHistoryStore
from .short_term import ShortTermMemory


class MemoryManager:
    """统一记忆门面。"""

    def __init__(
        self,
        use_mem0: bool = True,
        max_context_tokens: int = 8000,
        embedding_provider: str = "hash",
        persist_dir: str = "./data/chroma_db",
        memory_backend: str = "chromadb",
        elasticsearch_url: str = "http://127.0.0.1:9200",
        elasticsearch_username: str = "",
        elasticsearch_password: str = "",
        elasticsearch_index_prefix: str = "travel_memory",
        elasticsearch_vector_dims: int = 384,
        session_history_db_url: str = "postgresql+psycopg2://travel:travel@127.0.0.1:5432/travel_agent",
    ):
        self.memory_backend = memory_backend
        self.short_term = ShortTermMemory(max_turns=10, max_tokens=4000)
        self.long_term = LongTermMemory(
            collection_name=elasticsearch_index_prefix
            if memory_backend == "elasticsearch"
            else "travel_memory",
            persist_dir=persist_dir,
            embedding_provider=embedding_provider,
            backend=memory_backend,
            elasticsearch_url=elasticsearch_url,
            elasticsearch_username=elasticsearch_username,
            elasticsearch_password=elasticsearch_password,
            elasticsearch_index_prefix=elasticsearch_index_prefix,
            elasticsearch_vector_dims=elasticsearch_vector_dims,
        )
        self.context_manager = ContextManager(
            short_term=self.short_term,
            long_term=self.long_term,
            max_context_tokens=max_context_tokens,
        )
        self.history_store = SessionHistoryStore(session_history_db_url)

        if use_mem0:
            self.mem0 = Mem0Adapter(
                user_id="default",
                fallback_long_term=self.long_term,
            )
        else:
            self.mem0 = None

    async def process_interaction(
        self,
        user_input: str,
        agent_response: str,
        state: dict,
    ) -> None:
        """处理一次完整交互。"""
        session_id = state.get("session_id", "default")
        node = state.get("current_node", "unknown")

        # 1. 更新短期记忆
        self.short_term.add_message(
            role="user",
            content=user_input,
            metadata={"timestamp": time.time(), "session_id": session_id},
        )
        self.short_term.add_message(
            role="assistant",
            content=agent_response,
            metadata={
                "timestamp": time.time(),
                "session_id": session_id,
                "node": node,
            },
        )

        # 2. 同步工作记忆
        self._update_working_memory_from_state(state)

        # 3. 落库会话历史
        try:
            self.history_store.append_turn(
                session_id=session_id,
                user_input=user_input,
                assistant_output=agent_response,
                metadata={
                    "node": node,
                    "destination": state.get("destination", ""),
                    "state": state,
                },
            )
        except Exception as exc:
            print(f"[MemoryManager] 保存会话历史失败: {exc}")

        # 3.1 保存会话快照，前端切换会话时可以恢复面板状态
        try:
            self.save_session_snapshot(
                session_id=session_id,
                state=state,
                title_hint=user_input,
                preview_hint=agent_response,
            )
        except Exception as exc:
            print(f"[MemoryManager] 保存会话快照失败: {exc}")

        # 4. 写入长期记忆
        try:
            await self.long_term.add_interaction(
                session_id=session_id,
                query=user_input,
                response=agent_response,
                metadata={
                    "node": node,
                    "destination": state.get("destination", ""),
                    "timestamp": time.time(),
                },
            )
        except Exception as exc:
            print(f"[MemoryManager] 长期记忆保存失败: {exc}")

        # 5. 同步 mem0
        if self.mem0 and self.mem0.enabled:
            try:
                await self.mem0.add(
                    messages=[
                        {"role": "user", "content": user_input},
                        {"role": "assistant", "content": agent_response},
                    ],
                    metadata={"session_id": session_id, "node": node},
                )
            except Exception as exc:
                print(f"[MemoryManager] mem0 同步失败: {exc}")

    async def get_enhanced_context(
        self,
        user_input: str,
        state: dict,
    ) -> dict:
        """构建增强上下文。"""
        context = await self.context_manager.build_context(
            user_input=user_input,
            current_state=state,
        )

        session_id = state.get("session_id", "default")
        try:
            recent_history = self.history_store.get_recent_messages(session_id, limit=20)
            if recent_history:
                context["session_history"] = recent_history
                context["conversation_history"] = recent_history
        except Exception as exc:
            print(f"[MemoryManager] 读取会话历史失败: {exc}")

        if self.mem0:
            try:
                mem0_memories = await self.mem0.search(
                    query=user_input,
                    user_id=session_id,
                    limit=3,
                )
                if mem0_memories:
                    mem0_context = self.mem0.convert_to_context(mem0_memories)
                    if mem0_context:
                        existing = context.get("retrieved_memories", [])
                        existing.append(f"[mem0记忆] {mem0_context}")
                        context["retrieved_memories"] = existing
            except Exception as exc:
                print(f"[MemoryManager] mem0 检索失败: {exc}")

        return context

    async def get_relevant_history(self, query: str, k: int = 5) -> list[dict]:
        """从长期记忆中检索相关历史。"""
        try:
            return await self.long_term.retrieve_relevant(
                query=query,
                k=k,
                memory_type="episodic",
            )
        except Exception as exc:
            print(f"[MemoryManager] 历史检索失败: {exc}")
            return []

    def get_recent_session_history(self, session_id: str, limit: int = 10) -> list[dict]:
        """获取指定会话最近消息。"""
        return self.history_store.get_recent_messages(session_id, limit=limit)

    def get_session_snapshot(self, session_id: str) -> dict[str, Any] | None:
        """读取持久化会话快照。"""
        return self.history_store.get_session_snapshot(session_id)

    def list_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        """列出最近活跃的会话摘要。"""
        sessions = self.history_store.list_sessions(limit=limit)
        return [
            {
                "session_id": item.session_id,
                "title": item.title,
                "preview": item.preview,
                "message_count": item.message_count,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "last_message_at": item.last_message_at,
            }
            for item in sessions
        ]

    def save_session_snapshot(
        self,
        session_id: str,
        state: dict,
        title_hint: str | None = None,
        preview_hint: str | None = None,
    ) -> None:
        """保存会话快照。"""
        self.history_store.save_session_snapshot(
            session_id=session_id,
            state=state,
            title_hint=title_hint,
            preview_hint=preview_hint,
        )

    def delete_session(self, session_id: str) -> None:
        """彻底删除一个会话。"""
        self.history_store.clear_session(session_id)

    def clear_session_history(self, session_id: str) -> None:
        """清空指定会话的历史。"""
        self.history_store.clear_session(session_id)

    def get_working_memory(self) -> dict:
        """获取工作记忆。"""
        return self.short_term.get_working_memory()

    def update_working_memory(self, key: str, value: Any) -> None:
        """更新工作记忆。"""
        self.short_term.update_working_memory(key, value)

    def _update_working_memory_from_state(self, state: dict) -> None:
        """把 Agent 状态同步到工作记忆。"""
        key_mapping = {
            "destination": "destination",
            "duration_days": "duration_days",
            "budget": "budget",
            "travel_dates": "travel_dates",
            "companions": "companions",
            "interests": "interests",
            "accommodation_type": "accommodation_type",
            "transportation_preference": "transportation_preference",
            "pace_preference": "pace_preference",
        }

        for state_key, wm_key in key_mapping.items():
            if state_key in state and state[state_key] is not None:
                self.short_term.update_working_memory(wm_key, state[state_key])

    async def add_episode(self, episode: dict) -> str:
        """新增情节记忆。"""
        try:
            return await self.long_term.add_episode(
                session_id=episode.get("session_id", "default"),
                episode=episode,
            )
        except Exception as exc:
            print(f"[MemoryManager] 添加情节记忆失败: {exc}")
            return ""

    async def add_fact(self, fact: str, metadata: dict | None = None) -> str:
        """新增知识记忆。"""
        try:
            topic = (metadata or {}).get("topic", "general")
            return await self.long_term.add_travel_knowledge(
                topic=topic,
                content=fact,
                source=(metadata or {}).get("source"),
                metadata=metadata,
            )
        except Exception as exc:
            print(f"[MemoryManager] 添加知识记忆失败: {exc}")
            return ""

    async def update_user_profile(self, user_id: str, new_info: dict) -> str:
        """更新用户画像。"""
        try:
            return await self.long_term.update_user_profile(
                user_id=user_id,
                new_info=new_info,
            )
        except Exception as exc:
            print(f"[MemoryManager] 更新用户画像失败: {exc}")
            return ""

    async def get_user_preferences(self, user_id: str) -> dict:
        """获取用户偏好。"""
        try:
            return await self.long_term.get_user_preferences(user_id)
        except Exception as exc:
            print(f"[MemoryManager] 获取用户偏好失败: {exc}")
            return {}

    def get_stats(self) -> dict:
        """获取记忆系统统计信息。"""
        return {
            "short_term": self.short_term.get_token_usage_report(),
            "long_term": self.long_term.get_collection_stats(),
            "context_manager": self.context_manager.get_context_stats(),
            "history_store": {
                "total_messages": self.history_store.count(),
                "session_count": len(self.history_store.list_sessions()),
            },
            "mem0": {
                "enabled": self.mem0 is not None,
                "available": self.mem0.enabled if self.mem0 else False,
            },
        }

    def clear_short_term(self) -> None:
        """清空短期记忆。"""
        self.short_term.clear()

    def clear_long_term(self, collection_type: str = "all") -> None:
        """清空长期记忆。"""
        self.long_term.clear_collection(collection_type)

    def clear_all(self) -> None:
        """清空所有记忆层。"""
        self.clear_short_term()
        self.clear_long_term("all")
        self.history_store.clear_all()

    async def compress_conversation(self) -> str:
        """压缩对话历史。"""
        return self.short_term.compress_old_messages()

    def get_token_usage(self) -> dict:
        """获取 token 使用情况。"""
        return self.short_term.get_token_usage_report()

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            "MemoryManager("
            f"short_term_messages={stats['short_term']['message_count']}, "
            f"mem0_enabled={stats['mem0']['enabled']}, "
            f"history_messages={stats['history_store']['total_messages']}"
            ")"
        )

