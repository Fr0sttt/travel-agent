"""
RAG评估模块 - FACT框架

借鉴 DeepResearch-Bench 的 FACT (Factual Abundance and Citation Trustworthiness) 框架，
对Travel Agent的RAG效果进行评估。

评估维度：
1. Citation Accuracy (C.Acc.): 引用准确性
2. Average Effective Citations (E.Cit.): 有效引用数量
3. Statement-URL Pair质量
4. Source Grounding: 来源接地性

参考论文: "DeepResearch-Bench: Evaluating Deep Research Capabilities"
"""

import os
import re
import json
import asyncio
from typing import Any
from dataclasses import dataclass, field

from backend.app.evaluation.base import BaseEvaluator, EvalResult


# ---------------------------------------------------------------------------
# OpenAI client (lazy init)
# ---------------------------------------------------------------------------
_oa_client = None


def _get_openai_client():
    """获取OpenAI异步客户端（延迟初始化）"""
    global _oa_client
    if _oa_client is None:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("请安装 openai 库: pip install openai")
        _oa_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", "sk-test"))
    return _oa_client


# ---------------------------------------------------------------------------
# 已知的可信数据源
# ---------------------------------------------------------------------------
TRUSTED_SOURCES = [
    "OpenTripMap",
    "Nominatim",
    "OSRM",
    "Open-Meteo",
    "OpenStreetMap",
    "Wikidata",
    "opentripmap.com",
    "openstreetmap.org",
    "open-meteo.com",
    "router.project-osrm.org",
]

# 引用提取正则模式
CITATION_PATTERNS = [
    r'[\[\(]来源[:：]\s*([^\]\)]+)[\]\)]',
    r'数据来源[:：]\s*([^\n\s]+)',
    r'(?:来自|来源于|source[:：])\s*([^\n,，。]+)',
    r'_source["\']?\s*[:=]\s*["\']?([^"\'}\n]+)',
    r'(?:参考|参见|资料|出处)[:：]\s*([^\n,，。]+)',
]


@dataclass
class StatementUrlPair:
    """
    Statement-URL 对

    Attributes:
        statement: 事实性陈述
        url: 引用的URL/来源
        position: 在原文中的位置
        confidence: 置信度
    """
    statement: str
    url: str
    position: int = 0
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "statement": self.statement,
            "url": self.url,
            "position": self.position,
            "confidence": self.confidence,
        }


class FACTRAGEvaluator(BaseEvaluator):
    """
    FACT框架：RAG效果评估

    评估维度：
    - Citation Accuracy (C.Acc.): 引用准确性
    - Average Effective Citations (E.Cit.): 平均有效引用数
    - Statement-URL Pair: 陈述-来源对质量
    - Source Grounding: 来源接地性

    Usage:
        evaluator = FACTRAGEvaluator()
        result = await evaluator.evaluate(
            input_data={"response": "..."},
            output_data={"cited_sources": [...]},
            context={"retrieved_contexts": [...]},
        )
    """

    def __init__(self, use_llm_judge: bool = True, model: str = "gpt-4o-mini") -> None:
        """
        初始化FACT评估器

        Args:
            use_llm_judge: 是否启用LLM-as-a-Judge
            model: 使用的LLM模型
        """
        self.use_llm_judge = use_llm_judge
        self.model = model
        # 缓存support judgment结果
        self._support_cache: dict[str, bool] = {}

    # ------------------------------------------------------------------
    #  核心评估接口
    # ------------------------------------------------------------------
    async def evaluate(
        self,
        input_data: dict,
        output_data: dict,
        context: dict | None = None,
    ) -> EvalResult:
        """
        执行FACT RAG评估

        Args:
            input_data: 必须包含 response (str)
            output_data: 必须包含 cited_sources (list[dict])
            context: 可选 retrieved_contexts (list[str])

        Returns:
            EvalResult: 包含citation_accuracy和e_cit的评估结果
        """
        response = input_data.get("response", "")
        cited_sources = output_data.get("cited_sources", [])
        retrieved_contexts = (context or {}).get("retrieved_contexts", [])

        if not response:
            return EvalResult(
                metric_name="FACT_rag",
                score=0.0,
                details={"error": "Empty response"},
                reasoning="响应内容为空，无法评估",
                passed=False,
            )

        # 1. 提取 Statement-URL 对
        pairs = await self.extract_statement_url_pairs(response)

        # 2. 去重
        deduped_pairs = await self.deduplicate_pairs(pairs)

        # 3. Support Judgment (判断来源是否支持陈述)
        judgments = []
        supported_pairs = []

        for pair in deduped_pairs:
            # 查找对应来源内容
            source_content = self._find_source_content(
                pair.url, cited_sources, retrieved_contexts
            )
            judgment = await self.support_judgment(
                pair.statement, pair.url, source_content
            )
            judgments.append(judgment)
            if judgment:
                supported_pairs.append(pair)

        # 4. 计算 Citation Accuracy
        c_acc = self.calculate_citation_accuracy(judgments)

        # 5. 计算 E.Cit.
        e_cit = self.calculate_effective_citations(supported_pairs)

        # 6. Source Grounding
        grounding = self._evaluate_source_grounding(response, cited_sources)

        # 综合FACT分数
        fact_score = (
            c_acc * 0.40
            + min(e_cit / 2.0, 0.5) * 0.30  # 归一化到0-0.5
            + grounding["score"] * 0.30
        )

        details = {
            "citation_accuracy": round(c_acc, 4),
            "effective_citations": round(e_cit, 4),
            "statement_count": len(pairs),
            "deduplicated_count": len(deduped_pairs),
            "supported_count": len(supported_pairs),
            "source_grounding": grounding,
            "pairs_sample": [p.to_dict() for p in supported_pairs[:10]],
        }

        reasoning_parts = [
            f"引用准确率(C.Acc.): {c_acc:.2f}",
            f"平均有效引用(E.Cit.): {e_cit:.2f}",
            f"陈述-引用对: {len(deduped_pairs)} 对, {len(supported_pairs)} 被支持",
            f"来源接地性: {grounding['score']:.2f}",
        ]

        return EvalResult(
            metric_name="FACT_rag",
            score=self._normalize_score(fact_score),
            details=details,
            reasoning="; ".join(reasoning_parts),
            passed=self._pass_check(fact_score, threshold=0.5),
        )

    def get_metric_names(self) -> list[str]:
        """返回FACT框架支持的指标名称列表"""
        return [
            "FACT_rag",
            "citation_accuracy",
            "effective_citations",
            "source_grounding",
        ]

    # ------------------------------------------------------------------
    #  Step 1: 提取 Statement-URL 对
    # ------------------------------------------------------------------
    async def extract_statement_url_pairs(
        self, response: str
    ) -> list[StatementUrlPair]:
        """
        从响应中提取Statement-URL对

        策略：
        1. 按句子分割
        2. 提取包含数字/日期/价格的事实性陈述
        3. 在陈述附近查找引用标记

        Args:
            response: Agent的响应文本

        Returns:
            list[StatementUrlPair]: 提取的陈述-来源对
        """
        pairs = []

        # 先提取所有引用
        all_citations = []
        for pattern in CITATION_PATTERNS:
            for match in re.finditer(pattern, response, re.IGNORECASE):
                all_citations.append({
                    "text": match.group(0),
                    "source": match.group(1).strip(),
                    "position": match.start(),
                })

        # 按句子分割并提取事实性陈述
        sentences = re.split(r'[。！？\n]+', response)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue

            # 事实性陈述：包含数字、日期、价格等
            if re.search(r'\d+', sentence):
                sentence_pos = response.find(sentence)

                # 在句子附近查找引用（200字符范围内）
                nearby_citation = None
                min_distance = float('inf')

                for citation in all_citations:
                    distance = abs(citation["position"] - sentence_pos)
                    if distance < 200 and distance < min_distance:
                        min_distance = distance
                        nearby_citation = citation

                if nearby_citation:
                    pairs.append(StatementUrlPair(
                        statement=sentence,
                        url=nearby_citation["source"],
                        position=sentence_pos,
                    ))

        return pairs

    # ------------------------------------------------------------------
    #  Step 2: 去重
    # ------------------------------------------------------------------
    async def deduplicate_pairs(
        self, pairs: list[StatementUrlPair]
    ) -> list[StatementUrlPair]:
        """
        去重：相同URL + 相同/相似事实只保留一个

        策略：
        - 基于URL和statement的精确匹配去重
        - 对相似statement使用简单启发式合并

        Args:
            pairs: 原始Statement-URL对列表

        Returns:
            list[StatementUrlPair]: 去重后的列表
        """
        seen: dict[str, StatementUrlPair] = {}

        for pair in pairs:
            # 创建去重键（URL + statement前30字符）
            key = f"{pair.url.lower()}::{pair.statement[:30].lower()}"

            if key not in seen:
                seen[key] = pair

        return list(seen.values())

    # ------------------------------------------------------------------
    #  Step 3: Support Judgment
    # ------------------------------------------------------------------
    async def support_judgment(
        self,
        statement: str,
        url: str,
        source_content: str,
    ) -> bool:
        """
        判断来源是否支持陈述

        策略：
        1. 启发式匹配：检查关键词重叠
        2. LLM-as-a-Judge：使用LLM判断支持关系

        Args:
            statement: 事实性陈述
            url: 引用来源
            source_content: 来源的实际内容

        Returns:
            bool: 来源是否支持陈述
        """
        # 缓存检查
        cache_key = f"{statement[:50]}::{url}"
        if cache_key in self._support_cache:
            return self._support_cache[cache_key]

        # 启发式匹配
        heuristic_score = self._heuristic_support(statement, url, source_content)

        # 如果启发式结果很确定，直接返回
        if heuristic_score > 0.8:
            self._support_cache[cache_key] = True
            return True
        if heuristic_score < 0.2:
            self._support_cache[cache_key] = False
            return False

        # LLM-as-a-Judge
        if self.use_llm_judge and source_content:
            llm_result = await self._llm_support_judgment(
                statement, url, source_content
            )
            result = llm_result
        else:
            # 无LLM时，使用启发式分数
            result = heuristic_score >= 0.5

        self._support_cache[cache_key] = result
        return result

    def _heuristic_support(
        self, statement: str, url: str, source_content: str
    ) -> float:
        """
        启发式支持判断

        基于关键词重叠和来源可信度进行判断。

        Returns:
            float: 支持度 (0-1)
        """
        score = 0.0

        # 来源可信度
        url_lower = url.lower()
        for trusted in TRUSTED_SOURCES:
            if trusted.lower() in url_lower:
                score += 0.3
                break

        # 关键词重叠
        if source_content:
            # 提取statement中的关键词（数字、地名等）
            statement_keywords = set(re.findall(r'\b\w{2,}\b', statement.lower()))
            source_keywords = set(re.findall(r'\b\w{2,}\b', source_content.lower()))

            if statement_keywords and source_keywords:
                overlap = len(statement_keywords & source_keywords)
                union = len(statement_keywords | source_keywords)
                if union > 0:
                    jaccard = overlap / union
                    score += min(0.5, jaccard)

        # 数字匹配
        statement_numbers = re.findall(r'\d+\.?\d*', statement)
        if source_content and statement_numbers:
            source_numbers = re.findall(r'\d+\.?\d*', source_content)
            matched = sum(1 for n in statement_numbers if n in source_numbers)
            score += min(0.2, matched * 0.05)

        return min(score, 1.0)

    async def _llm_support_judgment(
        self, statement: str, url: str, source_content: str
    ) -> bool:
        """使用LLM判断来源是否支持陈述"""
        try:
            client = _get_openai_client()
            prompt = f"""
判断以下来源内容是否支持该陈述。

陈述: {statement}
来源URL: {url}
来源内容(前1500字):
{source_content[:1500]}

请只回答 "支持" 或 "不支持"，不要其他解释。
"""
            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=10,
            )
            content = response.choices[0].message.content.strip()
            return "支持" in content and "不支持" not in content
        except Exception:
            return False

    # ------------------------------------------------------------------
    #  Step 4: 计算 Citation Accuracy
    # ------------------------------------------------------------------
    def calculate_citation_accuracy(self, judgments: list[bool]) -> float:
        """
        计算引用准确率 (C.Acc.)

        C.Acc. = 被支持的引用数 / 总引用数

        Args:
            judgments: support_judgment结果列表

        Returns:
            float: C.Acc. (0-1)
        """
        if not judgments:
            return 0.0
        supported = sum(1 for j in judgments if j)
        return supported / len(judgments)

    # ------------------------------------------------------------------
    #  Step 5: 计算 E.Cit.
    # ------------------------------------------------------------------
    def calculate_effective_citations(
        self,
        supported_pairs: list[StatementUrlPair],
        total_tasks: int = 1,
    ) -> float:
        """
        计算平均有效引用数 (E.Cit.)

        E.Cit. = 有效引用总数 / 任务数

        Args:
            supported_pairs: 被支持的Statement-URL对
            total_tasks: 任务数量（默认1）

        Returns:
            float: E.Cit.
        """
        if total_tasks <= 0:
            total_tasks = 1
        return len(supported_pairs) / total_tasks

    # ------------------------------------------------------------------
    #  Source Grounding 评估
    # ------------------------------------------------------------------
    def _evaluate_source_grounding(
        self, response: str, cited_sources: list[dict]
    ) -> dict[str, Any]:
        """
        评估来源接地性

        检查Agent是否使用了外部数据源而非仅依赖LLM知识。

        Args:
            response: 响应文本
            cited_sources: 引用的来源列表

        Returns:
            dict: 来源接地性评估结果
        """
        found_sources = []
        for source in TRUSTED_SOURCES:
            if source.lower() in response.lower():
                found_sources.append(source)

        # 不确定性披露
        uncertainty_keywords = [
            "不确定", "可能", "仅供参考", "估算", "约",
            "大概", "左右", "approximately", "estimated",
        ]
        has_uncertainty = any(kw in response for kw in uncertainty_keywords)

        # 日期标注
        has_dates = bool(re.search(r'\d{4}-\d{2}-\d{2}', response))

        # 来源多样性评分
        source_diversity = min(0.5, len(found_sources) * 0.125)

        # 综合接地性分数
        score = source_diversity
        score += 0.25 if has_uncertainty else 0
        score += 0.25 if has_dates else 0

        return {
            "score": round(score, 4),
            "found_sources": found_sources,
            "source_count": len(found_sources),
            "has_uncertainty_disclosure": has_uncertainty,
            "has_date_annotations": has_dates,
        }

    # ------------------------------------------------------------------
    #  辅助方法
    # ------------------------------------------------------------------
    def _find_source_content(
        self,
        url: str,
        cited_sources: list[dict],
        retrieved_contexts: list[str],
    ) -> str:
        """
        查找来源对应的实际内容

        Args:
            url: 引用URL
            cited_sources: 引用的来源列表
            retrieved_contexts: 检索到的上下文

        Returns:
            str: 来源内容，找不到则返回空字符串
        """
        # 在cited_sources中查找
        for source in cited_sources:
            source_url = source.get("url", source.get("source", ""))
            if url.lower() in source_url.lower() or source_url.lower() in url.lower():
                return source.get("content", source.get("text", ""))

        # 如果找不到，拼接所有retrieved_contexts
        if retrieved_contexts:
            return "\n".join(retrieved_contexts[:3])

        return ""
