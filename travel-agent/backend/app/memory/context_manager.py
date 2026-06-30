"""
上下文管理器模块（MemGPT风格）

借鉴MemGPT的分层上下文管理思想，实现：
1. 分层上下文管理（系统提示 + 对话历史 + 工作记忆 + 检索内容）
2. 上下文压缩和修剪
3. 智能检索策略
4. 查询工程（重写/扩展/分解）

参考上下文工程指南的查询增强策略和MemGPT的内存管理架构。
"""

from __future__ import annotations

from typing import Any, Optional
from dataclasses import dataclass, field
import time
import json
import re


@dataclass
class ContextBlock:
    """上下文块 - 带优先级和元数据的内容块

    Attributes:
        content: 块内容
        block_type: 块类型 (system/user/assistant/tool/memory/knowledge)
        priority: 优先级 1-10，越高越重要
        timestamp: 创建时间戳
        tokens: token数量
        source: 来源标识
    """
    content: str
    block_type: str  # system/user/assistant/tool/memory/knowledge
    priority: int = 5  # 1-10, 越高越重要
    timestamp: float = field(default_factory=time.time)
    tokens: int = 0
    source: str | None = None


class ContextManager:
    """
    MemGPT风格的上下文管理系统

    核心功能：
    1. 分层上下文管理（系统提示 + 对话历史 + 工作记忆 + 检索内容）
    2. 上下文压缩和修剪
    3. 智能检索策略
    4. 查询工程（重写/扩展/分解）

    Token预算分配（借鉴MemGPT策略）：
    - 系统提示: ~20% (最高优先级，始终保留)
    - 工作记忆: ~10% (任务相关信息)
    - 检索结果: ~30% (相关记忆和知识)
    - 对话历史: ~40% (最近对话，可压缩)

    Attributes:
        short_term: 短期记忆实例
        long_term: 长期记忆实例
        max_tokens: 最大上下文token数
        blocks: 上下文块列表
    """

    # Token预算分配比例
    BUDGET_SYSTEM = 0.20      # 系统提示
    BUDGET_WORKING = 0.10     # 工作记忆
    BUDGET_RETRIEVAL = 0.30   # 检索结果
    BUDGET_HISTORY = 0.40     # 对话历史

    # 估算因子
    TOKEN_FACTOR = 0.6

    def __init__(self, short_term: Any, long_term: Any,
                 max_context_tokens: int = 8000):
        """初始化上下文管理器

        Args:
            short_term: ShortTermMemory实例
            long_term: LongTermMemory实例
            max_context_tokens: 最大上下文token数，默认8000
        """
        self.short_term = short_term
        self.long_term = long_term
        self.max_tokens = max_context_tokens
        self.blocks: list[ContextBlock] = []

        # 系统提示模板（将在build_context中填充）
        self.system_prompt_template = """你是一个专业的旅行规划助手。你的任务是根据用户的需求，帮助规划旅行行程。

## 能力
- 根据用户偏好推荐目的地和景点
- 规划合理的路线和日程安排
- 提供预算估算和天气建议
- 推荐当地美食和住宿

## 原则
- 所有推荐必须基于可靠数据源
- 标注不确定性和风险
- 不编造具体的实时价格
- 尊重用户的预算和偏好约束
- 对高风险操作（预订/付款）需人工确认

## 可用工具
{tools_description}

## 相关记忆
{retrieved_memories}

## 当前任务信息
{working_memory}
"""

    # ==================== 查询工程 ====================

    async def rewrite_query(self, original_query: str,
                            conversation_context: list = None) -> str:
        """查询重写 - 将模糊查询转换为精确查询

        借鉴上下文工程指南的查询重写策略：
        1. 重构不清楚的问题
        2. 上下文移除（消除无关信息）
        3. 关键词增强

        Args:
            original_query: 原始用户查询
            conversation_context: 对话上下文（可选）

        Returns:
            重写后的精确查询

        Example:
            >>> rewritten = await ctx.rewrite_query("我想去玩")
            >>> # 可能返回: "用户想去旅行，需要推荐目的地和景点"
        """
        # 基于规则的查询重写（无需LLM调用，快速执行）
        rewritten = original_query.strip()

        # 1. 消除常见模糊表达
        vague_patterns = {
            r"^(?:我想|我要|我想去|我要去)(?:玩|旅游|旅行|走走|看看)?$":
                "用户想要旅行，需要推荐目的地和行程",
            r"(?:推荐|介绍).*(?:好|不错).*(?:地方|景点|去处)":
                self._enhance_recommendation_query,
            r"(?:多少|什么).*?(?:钱|价格|费用|预算)":
                self._enhance_budget_query,
            r"(?:天气|气候|温度|下雨)":
                self._enhance_weather_query,
        }

        for pattern, replacement in vague_patterns.items():
            if re.search(pattern, rewritten):
                if callable(replacement):
                    rewritten = replacement(rewritten, conversation_context)
                else:
                    rewritten = replacement
                break

        # 2. 添加上下文信息
        if conversation_context:
            # 从对话上下文中提取关键实体
            context_text = " ".join([
                msg.get("content", "") for msg in conversation_context[-3:]
            ])

            # 如果查询中包含指代词，尝试解析
            referential_words = ["这", "那", "它", "那里", "这里"]
            if any(w in rewritten for w in referential_words):
                # 从工作记忆中获取当前上下文
                working = self.short_term.get_working_memory()
                if working:
                    context_str = ", ".join([
                        f"{k}={v}" for k, v in working.items()
                        if v is not None
                    ])
                    rewritten = rewritten + f" (上下文: {context_str})"

        return rewritten if rewritten else original_query

    def _enhance_recommendation_query(self, query: str,
                                       context: list | None) -> str:
        """增强推荐类查询"""
        # 从工作记忆获取已知信息
        working = self.short_term.get_working_memory()
        destination = working.get("destination", "")
        interests = working.get("interests", "")

        parts = ["旅行推荐"]
        if destination:
            parts.append(f"目的地: {destination}")
        if interests:
            parts.append(f"兴趣: {interests}")
        parts.append(f"原始需求: {query}")

        return ", ".join(parts)

    def _enhance_budget_query(self, query: str,
                               context: list | None) -> str:
        """增强预算类查询"""
        working = self.short_term.get_working_memory()
        destination = working.get("destination", "")
        duration = working.get("duration_days", "")

        parts = ["旅行预算估算"]
        if destination:
            parts.append(f"目的地: {destination}")
        if duration:
            parts.append(f"天数: {duration}")
        parts.append(f"原始需求: {query}")

        return ", ".join(parts)

    def _enhance_weather_query(self, query: str,
                                context: list | None) -> str:
        """增强天气类查询"""
        working = self.short_term.get_working_memory()
        destination = working.get("destination", "")
        travel_dates = working.get("travel_dates", "")

        parts = ["天气预报查询"]
        if destination:
            parts.append(f"目的地: {destination}")
        if travel_dates:
            parts.append(f"日期: {travel_dates}")
        parts.append(f"原始需求: {query}")

        return ", ".join(parts)

    async def expand_query(self, query: str) -> list[str]:
        """查询扩展 - 生成多个相关查询

        借鉴上下文工程指南的查询扩展策略：
        1. 生成语义相关的变体查询
        2. 从不同角度表述同一需求

        注意挑战：
        - 避免查询漂移
        - 控制计算开销

        Args:
            query: 原始查询

        Returns:
            扩展查询列表（包含原始查询）

        Example:
            >>> expanded = await ctx.expand_query("杭州三日游")
            >>> # 可能返回: ["杭州三日游", "杭州3天旅游攻略", "杭州三天行程安排"]
        """
        expansions = [query]

        # 基于规则的扩展策略
        # 1. 数字变体（中文数字<->阿拉伯数字）
        cn_nums = {"一": "1", "二": "2", "三": "3", "四": "4",
                    "五": "5", "六": "6", "七": "7", "八": "8"}
        for cn, ar in cn_nums.items():
            if cn in query and ar not in query:
                expansions.append(query.replace(cn, ar))
            elif ar in query and cn not in query:
                expansions.append(query.replace(ar, cn))

        # 2. 同义词扩展
        synonyms = {
            "旅游": ["旅行", "游玩", "度假"],
            "推荐": ["介绍", "攻略", "指南"],
            "景点": ["景区", "名胜", "打卡地"],
            "美食": ["餐厅", "小吃", "特色菜"],
            "住宿": ["酒店", "民宿", "旅馆"],
        }

        for keyword, alts in synonyms.items():
            if keyword in query:
                for alt in alts:
                    expanded = query.replace(keyword, alt)
                    if expanded not in expansions:
                        expansions.append(expanded)

        # 3. 添加限定词
        qualifiers = ["攻略", "推荐", "指南", "行程安排"]
        for q in qualifiers:
            if q not in query:
                expanded = f"{query} {q}"
                if expanded not in expansions:
                    expansions.append(expanded)

        # 去重并限制数量
        seen = set()
        unique = []
        for e in expansions:
            if e not in seen:
                seen.add(e)
                unique.append(e)

        return unique[:6]  # 最多返回6个扩展查询

    async def decompose_query(self, complex_query: str) -> list[str]:
        """查询分解 - 将复杂查询拆分为子查询

        借鉴上下文工程指南的查询分解策略：
        1. 分析查询的多个方面
        2. 分解为独立子查询
        3. 每个子查询聚焦一个主题

        适用场景：
        - 多日多目的地行程
        - 包含多个兴趣点的需求
        - 有特殊约束的复杂需求

        Args:
            complex_query: 复杂查询

        Returns:
            子查询列表

        Example:
            >>> sub_queries = await ctx.decompose_query("杭州3日游，预算5000，带父母")
            >>> # 可能返回: ["杭州三日游攻略", "杭州旅行预算5000", "带父母杭州旅游注意事项"]
        """
        sub_queries = []

        # 1. 按目的地分解
        destinations = self._extract_destinations(complex_query)
        if len(destinations) > 1:
            for dest in destinations:
                sub_queries.append(f"{dest}旅游攻略")

        # 2. 按主题分解
        themes = self._extract_themes(complex_query)
        for theme in themes:
            sub_queries.append(f"{theme} {' '.join(destinations) if destinations else ''}")

        # 3. 按约束分解
        constraints = self._extract_constraints(complex_query)
        if constraints.get("budget"):
            dest_str = destinations[0] if destinations else "目的地"
            sub_queries.append(f"{dest_str}旅行预算{constraints['budget']}")
        if constraints.get("companions"):
            dest_str = destinations[0] if destinations else "目的地"
            sub_queries.append(
                f"{constraints['companions']}旅行{dest_str}注意事项"
            )

        # 4. 如果没有分解出子查询，返回原始查询
        if not sub_queries:
            sub_queries = [complex_query]

        # 去重
        seen = set()
        unique = []
        for sq in sub_queries:
            sq = sq.strip()
            if sq and sq not in seen:
                seen.add(sq)
                unique.append(sq)

        return unique

    def _extract_destinations(self, query: str) -> list[str]:
        """从查询中提取目的地"""
        # 常见中国城市列表
        cities = [
            "北京", "上海", "杭州", "苏州", "南京", "西安", "成都",
            "重庆", "武汉", "长沙", "厦门", "青岛", "大连", "桂林",
            "丽江", "大理", "拉萨", "乌鲁木齐", "哈尔滨", "三亚",
            "昆明", "贵阳", "郑州", "济南", "合肥", "南昌", "福州",
            "广州", "深圳", "珠海", "香港", "澳门", "台北"
        ]
        found = [c for c in cities if c in query]
        return found

    def _extract_themes(self, query: str) -> list[str]:
        """从查询中提取主题"""
        theme_keywords = {
            "美食": "美食",
            "风景": "风景",
            "历史": "历史文化",
            "文化": "文化体验",
            "自然": "自然风光",
            "购物": "购物",
            "亲子": "亲子游",
            "情侣": "情侣旅行",
            "独自": "独自旅行",
            "户外": "户外活动",
            "博物馆": "博物馆",
            "寺庙": "宗教文化",
            "海滩": "海滨度假",
            "山区": "山地旅游",
        }
        return [theme for kw, theme in theme_keywords.items() if kw in query]

    def _extract_constraints(self, query: str) -> dict:
        """从查询中提取约束条件"""
        constraints = {}

        # 预算
        budget_match = re.search(r"预算\s*(\d+)", query)
        if budget_match:
            constraints["budget"] = budget_match.group(1)

        # 天数
        day_match = re.search(r"(\d+)\s*[天日]", query)
        if day_match:
            constraints["days"] = day_match.group(1)

        # 同行人
        companion_patterns = {
            r"[带和]父母": "带父母",
            r"[带和]孩子": "带孩子",
            r"亲子": "亲子",
            r"情侣": "情侣",
            r"独自|一个人|单身": "独自",
            r"朋友|闺蜜|兄弟": "朋友",
        }
        for pattern, companion in companion_patterns.items():
            if re.search(pattern, query):
                constraints["companions"] = companion
                break

        return constraints

    def _assess_complexity(self, query: str) -> float:
        """评估查询复杂度 (0-1)

        借鉴上下文工程指南的复杂度评估：
        - 查询长度
        - 目的地数量
        - 约束条件数量
        """
        score = 0.0

        # 长度
        if len(query) > 50:
            score += 0.2
        if len(query) > 100:
            score += 0.2

        # 多个目的地
        destinations = self._extract_destinations(query)
        if len(destinations) > 1:
            score += 0.2

        # 约束条件
        constraints = self._extract_constraints(query)
        score += len(constraints) * 0.1

        # 多日
        if any(w in query for w in ["天", "晚", "第", "Day"]):
            score += 0.1

        # 多个主题
        themes = self._extract_themes(query)
        if len(themes) > 1:
            score += 0.1

        return min(score, 1.0)

    # ==================== 上下文构建 ====================

    async def build_context(self, user_input: str,
                            current_state: dict) -> dict:
        """构建完整的上下文包

        构建MemGPT风格的分层上下文，包括：
        1. 系统提示
        2. 相关长期记忆
        3. 近期对话历史
        4. 工作记忆
        5. 工具描述

        Args:
            user_input: 当前用户输入
            current_state: 当前Agent状态

        Returns:
            完整的上下文字典
        """
        # 1. 查询处理
        complexity = self._assess_complexity(user_input)

        if complexity > 0.7:
            # 复杂查询：分解 + 检索
            sub_queries = await self.decompose_query(user_input)
            all_queries = []
            for sq in sub_queries:
                expanded = await self.expand_query(sq)
                all_queries.extend(expanded)
        elif complexity > 0.3:
            # 中等复杂度：重写 + 扩展
            rewritten = await self.rewrite_query(user_input)
            all_queries = await self.expand_query(rewritten)
        else:
            # 简单查询：仅重写
            all_queries = [await self.rewrite_query(user_input)]

        # 2. 检索相关记忆
        retrieved_memories = await self._retrieve_memories(
            queries=all_queries,
            state=current_state
        )

        # 3. 获取工具描述
        tools_description = current_state.get("tools_description",
                                                "可用的工具将在此处描述")

        # 4. 构建系统提示
        system_prompt = self._compose_system_prompt(
            tools_description=tools_description,
            retrieved_memories=retrieved_memories
        )

        # 5. 获取对话历史
        conversation = self._format_conversation(
            self.short_term.get_full_history()
        )

        # 6. 获取工作记忆
        working_memory = self.short_term.get_working_memory()
        working_memory_str = self._format_working_memory(working_memory)

        # 7. 构建最终上下文包
        context_package = {
            "system_prompt": system_prompt,
            "conversation_history": conversation,
            "working_memory": working_memory_str,
            "user_input": user_input,
            "retrieved_memories": retrieved_memories,
            "queries_used": all_queries,
            "complexity_score": complexity
        }

        # 8. Token预算管理
        context_package = self.manage_token_budget(context_package)

        return context_package

    def _compose_system_prompt(self, tools_description: str,
                                retrieved_memories: list[str] = None) -> str:
        """组合系统提示

        将系统提示模板与工具描述和检索到的记忆组合。

        Args:
            tools_description: 工具描述字符串
            retrieved_memories: 检索到的记忆列表

        Returns:
            完整的系统提示
        """
        memories_str = "\n".join(
            retrieved_memories[:10] if retrieved_memories else []
        )

        working_memory = self.short_term.get_working_memory()
        working_str = json.dumps(working_memory, ensure_ascii=False, indent=2) \
            if working_memory else "无"

        return self.system_prompt_template.format(
            tools_description=tools_description,
            retrieved_memories=memories_str or "暂无相关记忆",
            working_memory=working_str
        )

    async def _retrieve_memories(self, queries: list[str],
                                  state: dict) -> list[str]:
        """多策略记忆检索

        对多个查询进行检索，合并结果，去重排序。

        Args:
            queries: 查询列表
            state: 当前状态

        Returns:
            检索结果字符串列表
        """
        all_results = []
        seen_contents = set()

        # 获取目的地信息用于过滤
        destination = state.get("destination", "")
        user_id = state.get("session_id", "default")

        for query in queries:
            try:
                results = await self.long_term.retrieve_relevant(
                    query=query,
                    k=3,
                    memory_type=None  # 混合检索
                )

                for r in results:
                    content = r.get("content", "")
                    if content and content not in seen_contents:
                        seen_contents.add(content)
                        all_results.append({
                            "content": content,
                            "distance": r.get("distance", 0),
                            "type": r.get("memory_type", "unknown")
                        })
            except Exception as e:
                # 单个查询失败不影响其他查询
                print(f"[ContextManager] 检索查询失败 '{query}': {e}")
                continue

        # 按距离排序（升序）
        all_results.sort(key=lambda x: x["distance"])

        # 格式化结果
        formatted = []
        for r in all_results[:10]:  # 最多10条
            prefix = {
                "episodic": "[历史交互]",
                "semantic": "[旅行知识]",
                "preference": "[用户偏好]"
            }.get(r["type"], "[记忆]")
            formatted.append(f"{prefix} {r['content']}")

        return formatted

    def _format_conversation(self, messages: list[dict]) -> str:
        """格式化对话历史

        将消息列表格式化为LLM友好的对话字符串。

        Args:
            messages: 消息列表

        Returns:
            格式化后的对话字符串
        """
        if not messages:
            return ""

        parts = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "system" and msg.get("is_summary"):
                parts.append(f"[摘要] {content}")
            elif role == "user":
                parts.append(f"用户: {content}")
            elif role == "assistant":
                parts.append(f"助手: {content}")
            elif role == "system":
                parts.append(f"[系统] {content}")

        return "\n\n".join(parts)

    def _format_working_memory(self, working_memory: dict) -> str:
        """格式化工作记忆

        Args:
            working_memory: 工作记忆字典

        Returns:
            格式化后的工作记忆字符串
        """
        if not working_memory:
            return "当前无任务信息"

        parts = []
        key_labels = {
            "destination": "目的地",
            "duration_days": "旅行天数",
            "budget": "预算",
            "travel_dates": "旅行日期",
            "companions": "同行人",
            "interests": "兴趣爱好",
            "accommodation_type": "住宿类型",
            "transportation_preference": "交通偏好",
            "pace_preference": "节奏偏好"
        }

        for key, value in working_memory.items():
            label = key_labels.get(key, key)
            if value is not None:
                parts.append(f"{label}: {value}")

        return "\n".join(parts) if parts else "当前无任务信息"

    # ==================== 上下文优化 ====================

    def compress_context(self, context: str, target_tokens: int) -> str:
        """上下文压缩 - 保留关键信息

        当上下文超过token预算时，压缩内容以保留关键信息。
        借鉴上下文工程指南的"上下文总结"策略。

        Args:
            context: 要压缩的上下文字符串
            target_tokens: 目标token数

        Returns:
            压缩后的上下文
        """
        current_tokens = self._estimate_tokens(context)

        if current_tokens <= target_tokens:
            return context

        # 策略1: 如果过长，保留前半部分的关键信息
        if len(context) > 1000:
            # 提取关键句子（包含重要信息的句子）
            sentences = re.split(r'[。！？\n]', context)
            important_markers = [
                "目的地", "预算", "天数", "日期", "酒店", "景点",
                "推荐", "注意", "重要", "必须", "不要", "建议"
            ]

            important_sentences = []
            other_sentences = []

            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                if any(m in s for m in important_markers):
                    important_sentences.append(s)
                else:
                    other_sentences.append(s)

            # 优先保留重要句子
            result_parts = important_sentences[:]

            # 补充其他句子直到接近目标
            for s in other_sentences:
                candidate = "。".join(result_parts + [s])
                if self._estimate_tokens(candidate) < target_tokens:
                    result_parts.append(s)
                else:
                    break

            compressed = "。".join(result_parts)
            if len(compressed) < len(context):
                compressed += "\n...[内容已压缩]"
            return compressed

        # 策略2: 简单截断
        target_chars = int(target_tokens / self.TOKEN_FACTOR)
        if len(context) > target_chars:
            return context[:target_chars] + "\n...[已截断]"

        return context

    def prune_irrelevant(self, messages: list[dict],
                         current_task: str) -> list[dict]:
        """修剪不相关的历史消息

        根据当前任务主题，过滤掉不相关的历史消息。
        借鉴上下文工程指南的"上下文修剪"策略。

        Args:
            messages: 消息列表
            current_task: 当前任务描述

        Returns:
            修剪后的消息列表
        """
        if not messages or not current_task:
            return messages

        # 提取当前任务的关键词
        task_keywords = set(
            self._extract_destinations(current_task) +
            self._extract_themes(current_task)
        )

        if not task_keywords:
            return messages

        pruned = []
        for msg in messages:
            content = msg.get("content", "")

            # 系统消息和摘要始终保留
            if msg.get("role") == "system" or msg.get("is_summary"):
                pruned.append(msg)
                continue

            # 检查消息是否与当前任务相关
            msg_keywords = set(
                self._extract_destinations(content) +
                self._extract_themes(content)
            )

            # 如果消息与任务有关键词重叠，或消息太重要不能删
            if msg_keywords & task_keywords:
                pruned.append(msg)
            elif len(content) < 100:
                # 短消息通常很重要（如确认、回答等），保留
                pruned.append(msg)
            # 其他不相关消息被过滤

        return pruned

    def summarize_history(self, messages: list[dict]) -> str:
        """生成对话摘要

        将多轮对话压缩为简洁的摘要。
        借鉴MemGPT的自动摘要策略。

        Args:
            messages: 要摘要的消息列表

        Returns:
            摘要字符串
        """
        if not messages:
            return ""

        # 提取关键信息点
        key_points = []
        user_inputs = []
        assistant_responses = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                user_inputs.append(content[:80])
            elif role == "assistant":
                assistant_responses.append(content[:80])

        # 构建简单摘要
        summary_parts = []

        if user_inputs:
            summary_parts.append(f"用户说了 {len(user_inputs)} 句话")
            # 提取最后一次用户输入的主题
            last_input = user_inputs[-1]
            summary_parts.append(f"最新需求: {last_input}")

        if assistant_responses:
            summary_parts.append(f"助手回复了 {len(assistant_responses)} 次")

        # 从工作记忆中提取关键决策
        working = self.short_term.get_working_memory()
        if working:
            decisions = []
            if working.get("destination"):
                decisions.append(f"目的地已确定为{working['destination']}")
            if working.get("duration_days"):
                decisions.append(f"行程{working['duration_days']}天")
            if working.get("budget"):
                decisions.append(f"预算{working['budget']}元")
            if decisions:
                summary_parts.append("已确认: " + ", ".join(decisions))

        return "; ".join(summary_parts)

    def manage_token_budget(self, context_parts: dict) -> dict:
        """
        Token预算管理

        按照MemGPT的预算分配策略管理token使用：
        - 系统提示: ~20% (最高优先级)
        - 工作记忆: ~10%
        - 检索结果: ~30%
        - 对话历史: ~40%

        当超出预算时，按优先级压缩内容。

        Args:
            context_parts: 上下文各部分字典

        Returns:
            经过预算管理的上下文字典
        """
        # 计算各部分预算
        system_budget = int(self.max_tokens * self.BUDGET_SYSTEM)
        working_budget = int(self.max_tokens * self.BUDGET_WORKING)
        retrieval_budget = int(self.max_tokens * self.BUDGET_RETRIEVAL)
        history_budget = int(self.max_tokens * self.BUDGET_HISTORY)

        # 估算各部分token
        system_tokens = self._estimate_tokens(
            context_parts.get("system_prompt", "")
        )
        working_tokens = self._estimate_tokens(
            context_parts.get("working_memory", "")
        )
        history_tokens = self._estimate_tokens(
            context_parts.get("conversation_history", "")
        )

        # 检索结果需要特殊处理（列表）
        retrieval_memories = context_parts.get("retrieved_memories", [])
        retrieval_text = "\n".join(retrieval_memories)
        retrieval_tokens = self._estimate_tokens(retrieval_text)

        # 检查是否超出预算
        total_tokens = system_tokens + working_tokens + history_tokens + retrieval_tokens

        # 按优先级压缩（优先级：系统提示 > 工作记忆 > 检索结果 > 对话历史）
        if total_tokens > self.max_tokens:
            # 1. 压缩对话历史（优先级最低）
            if history_tokens > history_budget:
                context_parts["conversation_history"] = self.compress_context(
                    context_parts.get("conversation_history", ""),
                    history_budget
                )

            # 2. 压缩检索结果
            retrieval_text = "\n".join(retrieval_memories)
            if retrieval_tokens > retrieval_budget:
                compressed_retrieval = self.compress_context(
                    retrieval_text, retrieval_budget
                )
                context_parts["retrieved_memories"] = [compressed_retrieval]

            # 3. 如果还超出，压缩工作记忆
            working_tokens = self._estimate_tokens(
                context_parts.get("working_memory", "")
            )
            if working_tokens > working_budget:
                context_parts["working_memory"] = self.compress_context(
                    context_parts.get("working_memory", ""),
                    working_budget
                )

            # 4. 最后手段：压缩系统提示
            system_tokens = self._estimate_tokens(
                context_parts.get("system_prompt", "")
            )
            if system_tokens > system_budget:
                context_parts["system_prompt"] = self.compress_context(
                    context_parts.get("system_prompt", ""),
                    system_budget
                )

        # 重新计算总token
        total = (
            self._estimate_tokens(context_parts.get("system_prompt", "")) +
            self._estimate_tokens(context_parts.get("working_memory", "")) +
            self._estimate_tokens(context_parts.get("conversation_history", "")) +
            self._estimate_tokens("\n".join(
                context_parts.get("retrieved_memories", [])
            ))
        )

        context_parts["token_usage"] = {
            "total": total,
            "max_budget": self.max_tokens,
            "usage_ratio": round(total / self.max_tokens, 2) if self.max_tokens else 0,
            "allocations": {
                "system": system_budget,
                "working_memory": working_budget,
                "retrieval": retrieval_budget,
                "history": history_budget
            }
        }

        return context_parts

    def _estimate_tokens(self, text: str) -> int:
        """估算文本的token数量

        Args:
            text: 要估算的文本

        Returns:
            估算的token数
        """
        if not text:
            return 0
        return int(len(text) * self.TOKEN_FACTOR)

    def get_context_stats(self) -> dict:
        """获取上下文统计信息

        Returns:
            上下文使用统计
        """
        return {
            "blocks_count": len(self.blocks),
            "max_tokens": self.max_tokens,
            "budget_allocation": {
                "system": f"{self.BUDGET_SYSTEM * 100:.0f}%",
                "working_memory": f"{self.BUDGET_WORKING * 100:.0f}%",
                "retrieval": f"{self.BUDGET_RETRIEVAL * 100:.0f}%",
                "history": f"{self.BUDGET_HISTORY * 100:.0f}%"
            }
        }

    def __repr__(self) -> str:
        return (
            f"ContextManager("
            f"blocks={len(self.blocks)}, "
            f"max_tokens={self.max_tokens}"
            f")"
        )
