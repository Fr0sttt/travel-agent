"""
短期记忆管理模块

管理对话上下文和工作记忆，借鉴MemGPT的分层管理思想。
使用双缓冲结构：
- conversation_history: 循环队列存储最近对话
- working_memory: 字典存储当前任务相关的临时信息
"""

from collections import deque
from typing import Any, Optional
import time
import json


class ShortTermMemory:
    """短期记忆管理 - 对话上下文和工作记忆

    核心职责：
    1. 维护最近N轮对话历史（循环队列，自动淘汰旧消息）
    2. 管理工作记忆（当前任务相关的临时信息，如目的地、日期、预算等）
    3. 估算上下文token使用量
    4. 自动压缩旧消息以节省空间

    Attributes:
        max_turns: 最大保留对话轮数
        max_tokens: 最大token预算
        conversation_history: 对话历史循环队列
        working_memory: 当前任务相关临时信息
        context_window_usage: 当前token使用量
    """

    # 估算因子：每个字符约0.5个token（中文字符约1个token）
    TOKEN_ESTIMATE_FACTOR = 0.6

    def __init__(self, max_turns: int = 10, max_tokens: int = 4000):
        """初始化短期记忆

        Args:
            max_turns: 最大保留对话轮数，默认10轮
            max_tokens: 最大token预算，默认4000
        """
        self.max_turns: int = max_turns
        self.max_tokens: int = max_tokens
        self.conversation_history: deque = deque(maxlen=max_turns)
        self.working_memory: dict = {}  # 当前任务相关临时信息
        self.context_window_usage: int = 0
        self._compression_threshold: float = 0.8  # 超过80%时触发压缩
        self._summaries: list[str] = []  # 压缩后的摘要列表

    def add_message(self, role: str, content: str, metadata: dict = None) -> None:
        """添加对话消息到历史记录

        Args:
            role: 消息角色（user/assistant/system）
            content: 消息内容
            metadata: 可选元数据（如节点名称、时间戳等）

        Example:
            >>> stm = ShortTermMemory()
            >>> stm.add_message("user", "我想去杭州旅游")
            >>> stm.add_message("assistant", "好的，请问您计划去几天？")
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": metadata.get("timestamp", time.time()) if metadata else time.time(),
            "metadata": metadata or {}
        }
        self.conversation_history.append(message)
        self._update_token_usage()

        # 检查是否需要压缩
        if self.context_window_usage > self.max_tokens * self._compression_threshold:
            self.compress_old_messages()

    def get_recent_context(self, n_turns: int = 5) -> list[dict]:
        """获取最近n轮对话

        Args:
            n_turns: 获取的对话轮数，默认5轮

        Returns:
            最近n轮对话列表，每条包含role、content、timestamp

        Example:
            >>> recent = stm.get_recent_context(3)
            >>> for msg in recent:
            ...     print(f"{msg['role']}: {msg['content']}")
        """
        recent = list(self.conversation_history)[-n_turns:]
        return [
            {
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg.get("timestamp", 0)
            }
            for msg in recent
        ]

    def get_full_history(self) -> list[dict]:
        """获取完整对话历史（包括摘要和原始消息）

        Returns:
            完整对话上下文列表，按时间顺序排列
        """
        context = []

        # 先添加摘要
        if self._summaries:
            context.append({
                "role": "system",
                "content": f"[历史对话摘要] {'; '.join(self._summaries)}",
                "is_summary": True
            })

        # 添加原始消息
        context.extend([
            {
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg.get("timestamp", 0)
            }
            for msg in self.conversation_history
        ])

        return context

    def update_working_memory(self, key: str, value: Any) -> None:
        """更新工作记忆

        工作记忆存储当前任务相关的关键信息，如目的地、日期、预算等。
        这些信息会被频繁访问，需要快速读取。

        Args:
            key: 信息键名
            value: 信息值

        Example:
            >>> stm.update_working_memory("destination", "杭州")
            >>> stm.update_working_memory("budget", 5000)
            >>> stm.update_working_memory("travel_dates", {"start": "2025-08-01", "end": "2025-08-05"})
        """
        self.working_memory[key] = {
            "value": value,
            "updated_at": time.time()
        }

    def get_working_memory(self) -> dict:
        """获取当前工作记忆内容

        Returns:
            工作记忆字典，仅返回键值对（不含时间戳）

        Example:
            >>> wm = stm.get_working_memory()
            >>> print(wm.get("destination"))
        """
        return {
            key: item["value"]
            for key, item in self.working_memory.items()
        }

    def get_working_memory_with_meta(self) -> dict:
        """获取带元数据的完整工作记忆

        Returns:
            包含值和更新时间的完整工作记忆
        """
        return self.working_memory.copy()

    def remove_from_working_memory(self, key: str) -> bool:
        """从工作记忆中移除指定键

        Args:
            key: 要移除的键名

        Returns:
            是否成功移除
        """
        if key in self.working_memory:
            del self.working_memory[key]
            return True
        return False

    def clear_working_memory(self) -> None:
        """清除工作记忆（任务完成时调用）

        当当前旅行规划任务完成时，调用此方法清空工作记忆，
        为下一个任务做准备。
        """
        self.working_memory.clear()

    def estimate_token_count(self) -> int:
        """估算当前上下文的token数量

        使用字符数 * 估算因子来快速估算token数量。
        中文文本约为1 token/字符，英文约为0.25 token/字符。

        Returns:
            估算的token总数
        """
        total_chars = 0

        # 对话历史的字符数
        for msg in self.conversation_history:
            total_chars += len(msg.get("content", ""))

        # 工作记忆的字符数
        for key, item in self.working_memory.items():
            value = item["value"]
            if isinstance(value, str):
                total_chars += len(value)
            else:
                total_chars += len(json.dumps(value, ensure_ascii=False))

        # 摘要的字符数
        for summary in self._summaries:
            total_chars += len(summary)

        return int(total_chars * self.TOKEN_ESTIMATE_FACTOR)

    def _update_token_usage(self) -> None:
        """更新token使用量统计"""
        self.context_window_usage = self.estimate_token_count()

    def compress_old_messages(self, summary: str = None) -> str:
        """压缩旧消息，生成摘要替代原始内容

        当上下文超过压缩阈值时，将最旧的一半对话压缩为摘要。
        借鉴上下文工程指南的"上下文总结"策略。

        Args:
            summary: 可选的外部提供的摘要，如果为None则自动生成简单摘要

        Returns:
            生成的摘要文本

        Example:
            >>> summary = stm.compress_old_messages()
            >>> print(f"已压缩历史对话: {summary}")
        """
        if len(self.conversation_history) <= 3:
            # 消息太少，不压缩
            return ""

        # 取最旧的一半消息进行压缩
        history_list = list(self.conversation_history)
        compress_count = len(history_list) // 2
        old_messages = history_list[:compress_count]

        if summary:
            generated_summary = summary
        else:
            # 自动生成简单摘要：提取关键信息
            user_contents = [
                msg["content"][:50] for msg in old_messages
                if msg["role"] == "user"
            ]
            generated_summary = " | ".join(user_contents)
            if len(generated_summary) > 200:
                generated_summary = generated_summary[:200] + "..."

        # 保存摘要
        self._summaries.append(generated_summary)

        # 保留最近的消息，移除旧消息
        keep_messages = history_list[compress_count:]
        self.conversation_history.clear()
        for msg in keep_messages:
            self.conversation_history.append(msg)

        self._update_token_usage()
        return generated_summary

    def get_token_usage_report(self) -> dict:
        """获取详细的token使用报告

        Returns:
            包含各类token使用量的字典
        """
        history_tokens = sum(
            int(len(msg.get("content", "")) * self.TOKEN_ESTIMATE_FACTOR)
            for msg in self.conversation_history
        )

        working_memory_tokens = 0
        for key, item in self.working_memory.items():
            value = item["value"]
            if isinstance(value, str):
                working_memory_tokens += int(len(value) * self.TOKEN_ESTIMATE_FACTOR)
            else:
                working_memory_tokens += int(
                    len(json.dumps(value, ensure_ascii=False)) * self.TOKEN_ESTIMATE_FACTOR
                )

        summary_tokens = sum(
            int(len(s) * self.TOKEN_ESTIMATE_FACTOR)
            for s in self._summaries
        )

        return {
            "total": self.context_window_usage,
            "history": history_tokens,
            "working_memory": working_memory_tokens,
            "summaries": summary_tokens,
            "max_budget": self.max_tokens,
            "usage_ratio": round(self.context_window_usage / self.max_tokens, 2) if self.max_tokens > 0 else 0,
            "message_count": len(self.conversation_history),
            "summary_count": len(self._summaries)
        }

    def clear(self) -> None:
        """完全清空短期记忆

        重置所有状态，包括对话历史、工作记忆和摘要。
        """
        self.conversation_history.clear()
        self.working_memory.clear()
        self._summaries.clear()
        self.context_window_usage = 0

    def __repr__(self) -> str:
        return (
            f"ShortTermMemory("
            f"messages={len(self.conversation_history)}, "
            f"working_keys={list(self.working_memory.keys())}, "
            f"tokens={self.context_window_usage}/{self.max_tokens}"
            f")"
        )
