"""
mem0集成适配器模块

mem0是一个开源的记忆框架，提供：
- 自动记忆提取和存储
- 上下文感知的记忆检索
- 用户画像管理

本适配器封装mem0的API调用，提供与Travel Agent记忆系统
一致的接口。当mem0不可用时，自动降级到本地ChromaDB方案。
"""

from typing import Any, Optional
import time
import json
import os

# 尝试导入mem0
try:
    from mem0 import MemoryClient
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False


class Mem0Adapter:
    """mem0框架的适配器

    封装mem0 MemoryClient的API调用，提供统一的记忆管理接口。
    当mem0不可用时，自动降级为本地ChromaDB方案。

    Attributes:
        client: mem0 MemoryClient实例（如果可用）
        user_id: 默认用户ID
        enabled: 是否启用mem0
    """

    def __init__(self, api_key: str = None, user_id: str = "default",
                 fallback_long_term=None):
        """初始化mem0适配器

        Args:
            api_key: mem0 API密钥，默认从环境变量MEM0_API_KEY读取
            user_id: 默认用户ID
            fallback_long_term: 降级时使用的本地长期记忆实例
        """
        self.user_id = user_id
        self.enabled = False
        self.client = None
        self._fallback = fallback_long_term

        # 尝试初始化mem0客户端
        if MEM0_AVAILABLE:
            _api_key = api_key or os.getenv("MEM0_API_KEY")
            if _api_key:
                try:
                    self.client = MemoryClient(api_key=_api_key)
                    self.enabled = True
                except Exception as e:
                    print(f"[Mem0Adapter] 初始化mem0客户端失败: {e}")
            else:
                print("[Mem0Adapter] 未找到MEM0_API_KEY，mem0未启用")
        else:
            print("[Mem0Adapter] mem0包未安装，使用降级方案")

    async def add(self, messages: list[dict], metadata: dict = None) -> dict:
        """添加对话到mem0记忆

        将对话记录添加到mem0记忆系统中，自动提取关键信息。

        Args:
            messages: 对话消息列表，每条包含role和content
            metadata: 附加元数据（如session_id、节点名称等）

        Returns:
            添加结果，包含memory_id和提取的信息

        Example:
            >>> result = await adapter.add([
            ...     {"role": "user", "content": "我想去杭州旅游"},
            ...     {"role": "assistant", "content": "好的，请问您计划去几天？"}
            ... ], metadata={"session_id": "abc123"})
        """
        if not messages:
            return {"status": "skipped", "reason": "empty_messages"}

        # 构建元数据
        meta = {
            "timestamp": time.time(),
            "user_id": self.user_id,
            **(metadata or {})
        }

        if self.enabled and self.client:
            try:
                # 使用mem0 API添加记忆
                result = self.client.add(
                    messages=messages,
                    user_id=self.user_id,
                    metadata=meta
                )
                return {
                    "status": "success",
                    "mem0_result": result,
                    "message_count": len(messages)
                }
            except Exception as e:
                # mem0调用失败，降级到本地存储
                print(f"[Mem0Adapter] mem0添加失败，降级到本地存储: {e}")
                return await self._fallback_add(messages, meta)
        else:
            # mem0未启用，使用本地存储
            return await self._fallback_add(messages, meta)

    async def _fallback_add(self, messages: list[dict], metadata: dict) -> dict:
        """降级方案：使用本地长期记忆存储

        Args:
            messages: 对话消息列表
            metadata: 元数据

        Returns:
            存储结果
        """
        if self._fallback:
            try:
                # 提取用户查询和助手回复
                user_msg = next((m for m in messages if m.get("role") == "user"), None)
                assistant_msg = next((m for m in messages if m.get("role") == "assistant"), None)

                if user_msg and assistant_msg:
                    memory_id = await self._fallback.add_interaction(
                        session_id=metadata.get("session_id", self.user_id),
                        query=user_msg.get("content", ""),
                        response=assistant_msg.get("content", ""),
                        metadata=metadata
                    )
                    return {
                        "status": "success_fallback",
                        "memory_id": memory_id,
                        "storage": "local_chromadb"
                    }

                # 存储为情节记忆
                session_id = metadata.get("session_id", self.user_id)
                for msg in messages:
                    if msg.get("role") == "user":
                        memory_id = await self._fallback.add_interaction(
                            session_id=session_id,
                            query=msg.get("content", ""),
                            response="",
                            metadata=metadata
                        )

                return {
                    "status": "success_fallback",
                    "storage": "local_chromadb",
                    "message_count": len(messages)
                }
            except Exception as e:
                return {"status": "error", "reason": str(e)}

        return {"status": "failed", "reason": "no_fallback_available"}

    async def search(self, query: str, user_id: str = None,
                      limit: int = 5) -> list[dict]:
        """搜索相关记忆

        从mem0记忆系统中检索与查询相关的记忆。

        Args:
            query: 搜索查询
            user_id: 用户ID（覆盖默认）
            limit: 返回的最大结果数

        Returns:
            相关记忆列表

        Example:
            >>> memories = await adapter.search("杭州旅游推荐")
            >>> for mem in memories:
            ...     print(mem["content"])
        """
        target_user = user_id or self.user_id

        if self.enabled and self.client:
            try:
                results = self.client.search(
                    query=query,
                    user_id=target_user,
                    limit=limit
                )
                return [
                    {
                        "content": r.get("memory", ""),
                        "metadata": r.get("metadata", {}),
                        "score": r.get("score", 0),
                        "source": "mem0"
                    }
                    for r in results
                ]
            except Exception as e:
                print(f"[Mem0Adapter] mem0搜索失败，降级到本地搜索: {e}")
                return await self._fallback_search(query, target_user, limit)
        else:
            return await self._fallback_search(query, target_user, limit)

    async def _fallback_search(self, query: str, user_id: str,
                                limit: int) -> list[dict]:
        """降级方案：使用本地长期记忆搜索

        Args:
            query: 搜索查询
            user_id: 用户ID
            limit: 最大结果数

        Returns:
            相关记忆列表
        """
        if self._fallback:
            try:
                results = await self._fallback.retrieve_relevant(
                    query=query,
                    k=limit
                )
                return [
                    {
                        "content": r.get("content", ""),
                        "metadata": r.get("metadata", {}),
                        "distance": r.get("distance", 0),
                        "source": "local_chromadb"
                    }
                    for r in results
                ]
            except Exception as e:
                return [{"content": "", "error": str(e), "source": "error"}]

        return []

    async def get_user_memory(self, user_id: str = None) -> dict:
        """获取用户完整记忆画像

        检索指定用户的所有相关记忆，构建完整的用户画像。

        Args:
            user_id: 用户ID（覆盖默认）

        Returns:
            用户记忆画像字典
        """
        target_user = user_id or self.user_id

        if self.enabled and self.client:
            try:
                # mem0 API获取用户所有记忆
                memories = self.client.get_all(user_id=target_user)
                return {
                    "user_id": target_user,
                    "memories": memories,
                    "count": len(memories),
                    "source": "mem0"
                }
            except Exception as e:
                print(f"[Mem0Adapter] mem0获取用户记忆失败: {e}")
                return await self._fallback_get_user(target_user)
        else:
            return await self._fallback_get_user(target_user)

    async def _fallback_get_user(self, user_id: str) -> dict:
        """降级方案：从本地存储获取用户记忆

        Args:
            user_id: 用户ID

        Returns:
            用户记忆画像
        """
        if self._fallback:
            try:
                prefs = await self._fallback.get_user_preferences(user_id)
                return {
                    "user_id": user_id,
                    "preferences": prefs,
                    "source": "local_chromadb"
                }
            except Exception as e:
                return {"user_id": user_id, "error": str(e)}

        return {"user_id": user_id, "memories": []}

    def convert_to_context(self, memories: list[dict]) -> str:
        """将mem0记忆转换为LLM上下文格式

        将检索到的记忆格式化为适合注入LLM上下文的字符串。

        Args:
            memories: mem0记忆列表

        Returns:
            格式化后的上下文字符串

        Example:
            >>> memories = await adapter.search("杭州美食")
            >>> context = adapter.convert_to_context(memories)
            >>> # 可以将context注入到LLM的系统提示中
        """
        if not memories:
            return ""

        parts = []
        parts.append("## 相关历史记忆")

        for i, mem in enumerate(memories, 1):
            content = mem.get("content", "")
            if not content:
                continue

            # 添加记忆来源和分数
            source_info = ""
            score = mem.get("score")
            if score is not None:
                source_info = f" (相关度: {score:.2f})"

            parts.append(f"{i}. {content}{source_info}")

        return "\n\n".join(parts)

    def format_memories_for_prompt(self, memories: list[dict],
                                    max_length: int = 1000) -> str:
        """将记忆格式化为提示词友好的格式（带长度限制）

        Args:
            memories: 记忆列表
            max_length: 最大长度限制

        Returns:
            格式化并截断的记忆字符串
        """
        context = self.convert_to_context(memories)

        if len(context) > max_length:
            # 截断并添加提示
            context = context[:max_length] + "\n\n[记忆内容已截断...]"

        return context

    async def delete_user_memory(self, user_id: str = None) -> dict:
        """删除用户的所有记忆

        Args:
            user_id: 用户ID

        Returns:
            删除结果
        """
        target_user = user_id or self.user_id

        if self.enabled and self.client:
            try:
                result = self.client.delete_all(user_id=target_user)
                return {"status": "success", "mem0_result": result}
            except Exception as e:
                return {"status": "error", "reason": str(e)}

        # 本地存储的删除
        if self._fallback:
            try:
                self._fallback.clear_collection("all")
                return {"status": "success", "storage": "local"}
            except Exception as e:
                return {"status": "error", "reason": str(e)}

        return {"status": "failed", "reason": "no_storage_available"}

    def __repr__(self) -> str:
        return (
            f"Mem0Adapter("
            f"enabled={self.enabled}, "
            f"user_id={self.user_id}, "
            f"fallback={'available' if self._fallback else 'none'}"
            f")"
        )
