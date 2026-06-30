"""
Travel Agent 记忆管理系统

提供短期记忆、长期记忆、上下文管理和mem0集成功能。

主要组件:
- ShortTermMemory: 短期记忆管理（对话历史 + 工作记忆）
- LongTermMemory: 长期记忆管理（ChromaDB向量数据库 + RAG）
- ContextManager: 上下文管理器（MemGPT风格分层管理）
- Mem0Adapter: mem0框架适配器
- MemoryManager: 统一记忆管理器（Facade接口）
"""

from .memory_manager import MemoryManager

__all__ = ["MemoryManager"]
