"""
记忆管理器 - 统一接口模块

协调短期记忆、长期记忆和mem0三个记忆层，提供统一的记忆管理接口。
这是Travel Agent记忆系统的门面（Facade）类，其他模块通过此类与记忆系统交互。

架构设计借鉴上下文工程指南的混合记忆策略：
- 短期记忆：对话上下文和工作记忆（本地deque + dict）
- 长期记忆：向量数据库 + RAG（ChromaDB）
- mem0层：自动记忆提取和上下文感知检索（可选）

使用示例:
    >>> manager = MemoryManager(use_mem0=True)
    >>> await manager.process_interaction(
    ...     user_input="我想去杭州旅游",
    ...     agent_response="好的，请问您计划去几天？",
    ...     state={"session_id": "abc123"}
    ... )
    >>> context = await manager.get_enhanced_context("杭州有什么景点？", {})
"""

from __future__ import annotations

from typing import Any
import time
import json

from .short_term import ShortTermMemory
from .long_term import LongTermMemory
from .context_manager import ContextManager
from .mem0_adapter import Mem0Adapter


class MemoryManager:
    """
    统一记忆管理器，协调短期记忆、长期记忆和mem0

    提供以下核心能力：
    1. 处理交互：将每次用户-Agent交互更新到所有记忆层
    2. 获取增强上下文：综合所有记忆层构建LLM上下文
    3. 管理用户画像：偏好存储和检索
    4. 记忆维护：压缩、清理和统计

    Attributes:
        short_term: 短期记忆实例（对话历史 + 工作记忆）
        long_term: 长期记忆实例（ChromaDB向量数据库）
        context_manager: 上下文管理器（MemGPT风格）
        mem0: mem0适配器（可选）
    """

    def __init__(self, use_mem0: bool = True,
                 max_context_tokens: int = 8000,
                 embedding_provider: str = "hash",
                 persist_dir: str = "./data/chroma_db"):
        """初始化记忆管理器

        Args:
            use_mem0: 是否启用mem0
            max_context_tokens: 最大上下文token数
            embedding_provider: Embedding提供者 (openai/sentence-transformers/hash)
            persist_dir: ChromaDB持久化目录
        """
        # 1. 短期记忆
        self.short_term = ShortTermMemory(
            max_turns=10,
            max_tokens=4000
        )

        # 2. 长期记忆
        self.long_term = LongTermMemory(
            collection_name="travel_memory",
            persist_dir=persist_dir,
            embedding_provider=embedding_provider
        )

        # 3. 上下文管理器
        self.context_manager = ContextManager(
            short_term=self.short_term,
            long_term=self.long_term,
            max_context_tokens=max_context_tokens
        )

        # 4. mem0适配器（可选）
        if use_mem0:
            self.mem0 = Mem0Adapter(
                user_id="default",
                fallback_long_term=self.long_term
            )
        else:
            self.mem0 = None

    # ==================== 核心接口 ====================

    async def process_interaction(self, user_input: str,
                                   agent_response: str,
                                   state: dict) -> None:
        """处理交互，更新所有记忆层

        每次用户-Agent交互后调用此函数，将信息同步到所有记忆层。

        更新流程：
        1. 添加消息到短期记忆（对话历史）
        2. 存储交互到长期记忆（Episodic Memory）
        3. 同步到mem0（如果启用）

        Args:
            user_input: 用户输入
            agent_response: Agent回复
            state: 当前状态字典，包含session_id等

        Example:
            >>> await manager.process_interaction(
            ...     user_input="我想去杭州旅游",
            ...     agent_response="好的，请问您计划去几天？",
            ...     state={"session_id": "abc123", "destination": "杭州"}
            ... )
        """
        session_id = state.get("session_id", "default")
        node = state.get("current_node", "unknown")

        # 1. 更新短期记忆 - 对话历史
        self.short_term.add_message(
            role="user",
            content=user_input,
            metadata={
                "timestamp": time.time(),
                "session_id": session_id
            }
        )
        self.short_term.add_message(
            role="assistant",
            content=agent_response,
            metadata={
                "timestamp": time.time(),
                "session_id": session_id,
                "node": node
            }
        )

        # 2. 更新工作记忆（从状态中提取关键信息）
        self._update_working_memory_from_state(state)

        # 3. 存储到长期记忆 - Episodic Memory
        try:
            await self.long_term.add_interaction(
                session_id=session_id,
                query=user_input,
                response=agent_response,
                metadata={
                    "node": node,
                    "destination": state.get("destination", ""),
                    "timestamp": time.time()
                }
            )
        except Exception as e:
            print(f"[MemoryManager] 长期记忆存储失败: {e}")

        # 4. 同步到mem0（如果启用）
        if self.mem0 and self.mem0.enabled:
            try:
                await self.mem0.add(
                    messages=[
                        {"role": "user", "content": user_input},
                        {"role": "assistant", "content": agent_response}
                    ],
                    metadata={
                        "session_id": session_id,
                        "node": node
                    }
                )
            except Exception as e:
                print(f"[MemoryManager] mem0同步失败: {e}")

    async def get_enhanced_context(self, user_input: str,
                                    state: dict) -> dict:
        """获取增强的上下文（所有记忆层的综合）

        构建MemGPT风格的分层上下文，综合短期记忆、长期记忆和mem0的记忆。

        Args:
            user_input: 当前用户输入
            state: 当前Agent状态

        Returns:
            完整的上下文字典，包含：
            - system_prompt: 系统提示
            - conversation_history: 对话历史
            - working_memory: 工作记忆
            - user_input: 用户输入
            - retrieved_memories: 检索到的相关记忆
            - token_usage: token使用统计

        Example:
            >>> context = await manager.get_enhanced_context(
            ...     "杭州有什么好玩的？",
            ...     {"session_id": "abc123", "destination": "杭州"}
            ... )
            >>> print(context["system_prompt"])
            >>> print(context["retrieved_memories"])
        """
        # 使用上下文管理器构建完整上下文
        context = await self.context_manager.build_context(
            user_input=user_input,
            current_state=state
        )

        # 如果mem0可用，补充mem0记忆
        if self.mem0:
            try:
                mem0_memories = await self.mem0.search(
                    query=user_input,
                    user_id=state.get("session_id", "default"),
                    limit=3
                )
                if mem0_memories:
                    mem0_context = self.mem0.convert_to_context(mem0_memories)
                    if mem0_context:
                        # 将mem0记忆添加到检索结果中
                        existing = context.get("retrieved_memories", [])
                        existing.append(f"[mem0记忆] {mem0_context}")
                        context["retrieved_memories"] = existing
            except Exception as e:
                print(f"[MemoryManager] mem0检索失败: {e}")

        return context

    async def get_relevant_history(self, query: str, k: int = 5) -> list[dict]:
        """获取相关历史交互

        从长期记忆中检索与查询最相关的历史交互。

        Args:
            query: 查询文本
            k: 返回的最大结果数

        Returns:
            相关历史交互列表

        Example:
            >>> history = await manager.get_relevant_history("杭州景点推荐", k=3)
            >>> for item in history:
            ...     print(item["content"])
        """
        try:
            results = await self.long_term.retrieve_relevant(
                query=query,
                k=k,
                memory_type="episodic"
            )
            return results
        except Exception as e:
            print(f"[MemoryManager] 检索历史失败: {e}")
            return []

    # ==================== 工作记忆管理 ====================

    def get_working_memory(self) -> dict:
        """获取工作记忆

        Returns:
            工作记忆字典
        """
        return self.short_term.get_working_memory()

    def update_working_memory(self, key: str, value: Any) -> None:
        """更新工作记忆

        Args:
            key: 键名
            value: 值

        Example:
            >>> manager.update_working_memory("destination", "杭州")
            >>> manager.update_working_memory("budget", 5000)
        """
        self.short_term.update_working_memory(key, value)

    def _update_working_memory_from_state(self, state: dict) -> None:
        """从Agent状态更新工作记忆

        将状态中的关键字段同步到工作记忆。

        Args:
            state: Agent状态字典
        """
        # 从状态中同步关键字段到工作记忆
        key_mapping = {
            "destination": "destination",
            "duration_days": "duration_days",
            "budget": "budget",
            "travel_dates": "travel_dates",
            "companions": "companions",
            "interests": "interests",
            "accommodation_type": "accommodation_type",
            "transportation_preference": "transportation_preference",
            "pace_preference": "pace_preference"
        }

        for state_key, wm_key in key_mapping.items():
            if state_key in state and state[state_key] is not None:
                self.short_term.update_working_memory(wm_key, state[state_key])

    # ==================== 长期记忆管理 ====================

    async def add_episode(self, episode: dict) -> str:
        """添加情节记忆

        Args:
            episode: 情节字典，包含：
                - event: 事件描述
                - outcome: 结果
                - satisfaction: 满意度 (0-1)
                - destination: 目的地
                - tags: 标签列表

        Returns:
            记忆ID

        Example:
            >>> memory_id = await manager.add_episode({
            ...     "event": "用户完成了杭州3日游规划",
            ...     "outcome": "生成了满意的行程",
            ...     "satisfaction": 0.9,
            ...     "destination": "杭州",
            ...     "tags": ["成功", "家庭游"]
            ... })
        """
        try:
            memory_id = await self.long_term.add_episode(
                session_id=episode.get("session_id", "default"),
                episode=episode
            )
            return memory_id
        except Exception as e:
            print(f"[MemoryManager] 添加情节记忆失败: {e}")
            return ""

    async def add_fact(self, fact: str, metadata: dict = None) -> str:
        """添加事实记忆（旅行知识）

        Args:
            fact: 事实/知识内容
            metadata: 附加元数据（如topic、source等）

        Returns:
            知识ID

        Example:
            >>> knowledge_id = await manager.add_fact(
            ...     "杭州西湖是中国十大名胜之一，最佳游览时间为春季",
            ...     metadata={"topic": "杭州西湖", "source": "旅游指南"}
            ... )
        """
        try:
            topic = (metadata or {}).get("topic", "general")
            knowledge_id = await self.long_term.add_travel_knowledge(
                topic=topic,
                content=fact,
                source=(metadata or {}).get("source"),
                metadata=metadata
            )
            return knowledge_id
        except Exception as e:
            print(f"[MemoryManager] 添加事实记忆失败: {e}")
            return ""

    async def update_user_profile(self, user_id: str, new_info: dict) -> str:
        """更新用户画像

        Args:
            user_id: 用户ID
            new_info: 新的偏好信息

        Returns:
            偏好记录ID
        """
        try:
            pref_id = await self.long_term.update_user_profile(
                user_id=user_id,
                new_info=new_info
            )
            return pref_id
        except Exception as e:
            print(f"[MemoryManager] 更新用户画像失败: {e}")
            return ""

    async def get_user_preferences(self, user_id: str) -> dict:
        """获取用户偏好

        Args:
            user_id: 用户ID

        Returns:
            用户偏好字典
        """
        try:
            return await self.long_term.get_user_preferences(user_id)
        except Exception as e:
            print(f"[MemoryManager] 获取用户偏好失败: {e}")
            return {}

    # ==================== 工具方法 ====================

    def get_stats(self) -> dict:
        """获取记忆系统统计信息

        Returns:
            各记忆层的统计信息
        """
        return {
            "short_term": self.short_term.get_token_usage_report(),
            "long_term": self.long_term.get_collection_stats(),
            "context_manager": self.context_manager.get_context_stats(),
            "mem0": {
                "enabled": self.mem0 is not None,
                "available": self.mem0.enabled if self.mem0 else False
            }
        }

    def clear_short_term(self) -> None:
        """清空短期记忆"""
        self.short_term.clear()

    def clear_long_term(self, collection_type: str = "all") -> None:
        """清空长期记忆

        Args:
            collection_type: 要清空的集合类型 (episodic/semantic/preference/all)
        """
        self.long_term.clear_collection(collection_type)

    def clear_all(self) -> None:
        """清空所有记忆层"""
        self.clear_short_term()
        self.clear_long_term("all")

    async def compress_conversation(self) -> str:
        """压缩对话历史

        将旧的对话消息压缩为摘要。

        Returns:
            生成的摘要
        """
        summary = self.short_term.compress_old_messages()
        return summary

    def get_token_usage(self) -> dict:
        """获取token使用报告

        Returns:
            token使用统计
        """
        return self.short_term.get_token_usage_report()

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"MemoryManager("
            f"short_term_messages={stats['short_term']['message_count']}, "
            f"mem0_enabled={stats['mem0']['enabled']}"
            f")"
        )
