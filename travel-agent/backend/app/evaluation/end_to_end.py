"""
端到端评估模块 - RACE框架

借鉴 DeepResearch-Bench 的 RACE (Report Quality Evaluation) 框架，
对Travel Agent生成的完整行程进行4维度质量评估。

参考论文: "RACE: Benchmarking Retrieval-Augmented Classification Evaluation"
"""

import os
import json
import asyncio
from typing import Any
from dataclasses import dataclass, field

try:
    from backend.app.evaluation.base import BaseEvaluator, EvalResult, DimensionWeight
except ModuleNotFoundError:
    from evaluation.base import BaseEvaluator, EvalResult, DimensionWeight
try:
    from backend.app.evaluation.judge import TravelLLMJudge
except ModuleNotFoundError:
    from evaluation.judge import TravelLLMJudge


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
# RACE 维度定义
# ---------------------------------------------------------------------------
RACE_DIMENSIONS: dict[str, DimensionWeight] = {
    "COMP": DimensionWeight(
        name="Comprehensiveness",
        weight=0.30,
        description="信息覆盖广度 - 是否覆盖了用户所有约束和需求",
    ),
    "DEPTH": DimensionWeight(
        name="Insight/Depth",
        weight=0.25,
        description="分析深度 - 推荐是否有深度，是否提供了有价值的见解",
    ),
    "INST": DimensionWeight(
        name="Instruction-Following",
        weight=0.25,
        description="指令遵循 - 是否严格遵循了用户的指令和约束",
    ),
    "READ": DimensionWeight(
        name="Readability",
        weight=0.20,
        description="可读性 - 输出是否清晰易读，格式是否规范",
    ),
}


# ---------------------------------------------------------------------------
# 维度关键词映射（用于启发式评分）
# ---------------------------------------------------------------------------
DEPTH_INDICATORS = {
    "reason": ["因为", "原因是", "推荐", "之所以", "考虑到", "due to", "because", "recommend"],
    "tradeoff": ["备选", "或者", "不过", "但是", "权衡", "alternative", "however", "trade-off"],
    "culture": ["历史", "文化", "特色", "当地", "传统", "history", "culture", "local", "traditional"],
}

READ_INDICATORS = {
    "heading": ["# ", "## "],
    "table": ["|", "---"],
    "list": ["- ", "* ", "1. ", "2. "],
}


class RACEEndToEndEvaluator(BaseEvaluator):
    """
    RACE框架：端到端行程质量评估

    4个评估维度：
    - COMP (Comprehensiveness): 信息覆盖广度
    - DEPTH (Insight/Depth): 分析深度
    - INST (Instruction-Following): 指令遵循
    - READ (Readability): 可读性

    特点：
    - 动态权重生成：根据任务特征调整各维度权重
    - Reference-based评分：与参考行程对比
    - Adaptive criteria：自适应评估标准
    - LLM-as-a-Judge：使用LLM进行深度质量判断

    Usage:
        evaluator = RACEEndToEndEvaluator()
        result = await evaluator.evaluate(
            input_data={"task": "...", "user_request": "..."},
            output_data={"itinerary": "...", "constraints": {...}},
            context={"reference": {...}},
        )
    """

    def __init__(self, use_llm_judge: bool = True, model: str | None = None) -> None:
        """
        初始化RACE评估器

        Args:
            use_llm_judge: 是否启用LLM-as-a-Judge模式
            model: 使用的LLM模型名称
        """
        self.use_llm_judge = use_llm_judge
        self.model = model
        self._judge = TravelLLMJudge(model=model)
        self._judge_results: dict[str, dict[str, Any]] = {}
        # 缓存维度权重，避免同一任务重复计算
        self._weight_cache: dict[str, dict[str, float]] = {}

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
        执行RACE端到端评估

        Args:
            input_data: 必须包含 user_request (str) 和 constraints (dict)
            output_data: 必须包含 itinerary (str|dict)
            context: 可选 reference_itinerary (dict)

        Returns:
            EvalResult: 包含overall_score和4个维度分数的评估结果
        """
        task = input_data.get("user_request", "")
        constraints = input_data.get("constraints", {})
        generated = output_data.get("itinerary", "")
        reference = (context or {}).get("reference_itinerary")
        self._judge_results = {}

        # 统一将 itinerary 转为字符串
        if isinstance(generated, dict):
            generated_str = json.dumps(generated, ensure_ascii=False, indent=2)
        else:
            generated_str = str(generated)

        # 1. 动态生成维度权重
        weights = await self._generate_dimension_weights(task)

        # 2. 逐维度评分
        comp_score = await self._score_comprehensiveness(
            generated_str, reference, constraints
        )
        depth_score = await self._score_depth(generated_str, reference)
        inst_score = await self._score_instruction_following(
            generated_str, constraints
        )
        read_score = await self._score_readability(generated_str)

        dimension_scores: dict[str, float] = {
            "COMP": comp_score,
            "DEPTH": depth_score,
            "INST": inst_score,
            "READ": read_score,
        }

        # 3. 加权计算总分
        overall = await self._calculate_overall_score(dimension_scores, weights)

        details = {
            "dimension_scores": {k: round(v, 4) for k, v in dimension_scores.items()},
            "weights": {k: round(v, 4) for k, v in weights.items()},
            "task_preview": task[:200] if task else "",
            "judge": self._judge_results,
        }
        hard_failures: list[str] = []
        if constraints.get("destination") and constraints["destination"] not in generated_str:
            hard_failures.append("destination_missing")
        # 预算和天数是否真正满足需要结合结构化预算、每日安排和语义上下文，
        # 交给 RACE Judge；这里只保留目的地完全缺失这种明确失败。
        details["hard_failures"] = hard_failures

        score_formula = " + ".join(
            f"{dimension_scores[k]:.2f}*{weights[k]:.2f}" for k in dimension_scores
        )
        reasoning_parts = [
            f"COMP({comp_score:.2f}): 覆盖了 {comp_score*100:.0f}% 的关键要素",
            f"DEPTH({depth_score:.2f}): 洞察深度评分",
            f"INST({inst_score:.2f}): 指令遵循评分",
            f"READ({read_score:.2f}): 可读性评分",
            f"综合评分 = {score_formula} = {overall:.4f}",
        ]

        return EvalResult(
            metric_name="RACE_end_to_end",
            score=overall,
            details=details,
            reasoning="; ".join(reasoning_parts),
            passed=self._pass_check(overall, threshold=0.6) and not hard_failures,
            hard_failures=hard_failures,
        )

    def get_metric_names(self) -> list[str]:
        """返回RACE框架支持的指标名称列表"""
        return ["RACE_end_to_end", "COMP", "DEPTH", "INST", "READ"]

    # ------------------------------------------------------------------
    #  Step 1: 动态权重生成
    # ------------------------------------------------------------------
    async def _generate_dimension_weights(self, task: str) -> dict[str, float]:
        """
        根据任务描述动态生成维度权重

        策略：
        - 预算敏感请求 → 增加INST权重
        - 探索性/深度请求 → 增加DEPTH权重
        - 快速/简洁请求 → 增加READ权重
        - 复杂多约束请求 → 增加COMP权重

        Args:
            task: 用户原始请求文本

        Returns:
            dict[str, float]: 4个维度的归一化权重
        """
        # 使用缓存
        cache_key = task[:100] if task else "default"
        if cache_key in self._weight_cache:
            return self._weight_cache[cache_key]

        weights = {k: v.weight for k, v in RACE_DIMENSIONS.items()}

        if not task:
            self._weight_cache[cache_key] = weights
            return weights

        # 预算敏感
        if any(kw in task for kw in ["预算", "不能超过", "省钱", "便宜", "划算", "优惠"]):
            weights["INST"] += 0.10
            weights["DEPTH"] -= 0.05
            weights["READ"] -= 0.05

        # 探索性/深度需求
        if any(kw in task for kw in ["深度", "详细", "了解", "文化", "历史", "体验", "特色"]):
            weights["DEPTH"] += 0.10
            weights["COMP"] -= 0.05
            weights["READ"] -= 0.05

        # 快速/简洁需求
        if any(kw in task for kw in ["快速", "简单", "大概", "粗略", "大致"]):
            weights["READ"] += 0.10
            weights["COMP"] -= 0.05
            weights["DEPTH"] -= 0.05

        # 复杂多约束
        constraint_keywords = ["而且", "并且", "还要", "同时", "必须", "一定要"]
        if sum(1 for kw in constraint_keywords if kw in task) >= 2:
            weights["COMP"] += 0.08
            weights["READ"] -= 0.04
            weights["DEPTH"] -= 0.04

        # 归一化
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}

        self._weight_cache[cache_key] = weights
        return weights

    # ------------------------------------------------------------------
    #  Step 2: 逐维度评分
    # ------------------------------------------------------------------
    async def _score_comprehensiveness(
        self,
        generated: str,
        reference: dict | None,
        constraints: dict,
    ) -> float:
        """
        COMP维度: 评估信息覆盖广度

        检查输出是否覆盖了约束中的所有关键要素：
        - 目的地覆盖
        - 预算提及
        - 天数规划
        - 兴趣偏好
        - 同行人需求

        Args:
            generated: 生成的行程文本
            reference: 参考行程（可选）
            constraints: 用户约束条件

        Returns:
            float: 0-1 分数
        """
        score = 0.0
        checks = 0

        # 检查目的地
        destination = constraints.get("destination", "")
        if destination and destination in generated:
            score += 1.0
        checks += 1

        # 检查预算
        budget = constraints.get("budget_cny")
        if budget is not None:
            checks += 1
            if any(kw in generated for kw in ["预算", "费用", "花费", "价格", "元"]):
                score += 1.0

        # 检查天数
        days = constraints.get("duration_days")
        if days is not None:
            checks += 1
            day_mentions = (
                generated.count("Day")
                + generated.count("第")
                + generated.count("天")
            )
            if day_mentions >= days or f"{days}天" in generated:
                score += 1.0
            elif day_mentions > 0:
                score += 0.5

        # 检查兴趣偏好
        interests = constraints.get("interests", [])
        if interests:
            checks += 1
            covered = sum(1 for interest in interests if interest in generated)
            score += covered / len(interests)

        # 检查同行人
        companions = constraints.get("companions")
        if companions:
            checks += 1
            companion_keywords = {
                "solo": ["独自", "一个人", "单人"],
                "couple": ["情侣", "夫妻", "两人"],
                "family": ["家庭", "亲子", "孩子", "家人"],
                "friends": ["朋友", "同伴", "伙伴"],
                "group": ["团队", "集体", "多人"],
            }
            keywords = companion_keywords.get(companions, [companions])
            if any(kw in generated for kw in keywords):
                score += 1.0

        # 参考行程对比
        if reference:
            ref_elements = reference.get("required_elements", [])
            if ref_elements:
                checks += 1
                covered = sum(
                    1 for elem in ref_elements if elem.lower() in generated.lower()
                )
                score += covered / len(ref_elements)

        # LLM-as-a-Judge 深度评估
        if self.use_llm_judge and checks > 0:
            heuristic_score = score / checks if checks > 0 else 0.5
            llm_score = await self._llm_judge_comp(generated, constraints)
            score = heuristic_score if llm_score is None else heuristic_score * 0.4 + llm_score * 0.6
        else:
            score = score / checks if checks > 0 else 0.5

        return self._normalize_score(score)

    async def _score_depth(
        self,
        generated: str,
        reference: dict | None,
    ) -> float:
        """
        DEPTH维度: 评估分析深度

        评估输出的洞察深度：
        - 是否有推荐理由
        - 是否有取舍解释
        - 是否有文化/历史背景
        - 是否有实用建议

        Args:
            generated: 生成的行程文本
            reference: 参考行程（可选）

        Returns:
            float: 0-1 分数
        """
        score = 0.3  # 基础分

        # 检查推荐理由
        reason_hits = sum(
            1 for ind in DEPTH_INDICATORS["reason"] if ind in generated
        )
        score += min(0.25, reason_hits * 0.04)

        # 检查取舍解释
        tradeoff_hits = sum(
            1 for ind in DEPTH_INDICATORS["tradeoff"] if ind in generated
        )
        score += min(0.20, tradeoff_hits * 0.04)

        # 检查文化/历史背景
        culture_hits = sum(
            1 for ind in DEPTH_INDICATORS["culture"] if ind in generated
        )
        score += min(0.15, culture_hits * 0.03)

        # LLM-as-a-Judge
        if self.use_llm_judge:
            llm_score = await self._llm_judge_depth(generated)
            score = score if llm_score is None else score * 0.4 + llm_score * 0.6

        return self._normalize_score(score)

    async def _score_instruction_following(
        self,
        generated: str,
        constraints: dict,
    ) -> float:
        """
        INST维度: 评估指令遵循度

        检查输出是否满足所有约束条件：
        - 预算约束
        - 天数约束
        - 兴趣偏好覆盖
        - 特殊需求（饮食/无障碍）

        Args:
            generated: 生成的行程文本
            constraints: 用户约束条件

        Returns:
            float: 0-1 分数
        """
        score = 1.0

        # 预算约束
        budget = constraints.get("budget_cny")
        if budget:
            if not any(kw in generated for kw in ["预算", "费用", "花费", "元"]):
                score -= 0.2

        # 天数约束
        days = constraints.get("duration_days")
        if days:
            if not any(kw in generated for kw in ["天", "Day", "日程", "行程"]):
                score -= 0.2

        # 兴趣偏好
        interests = constraints.get("interests", [])
        if interests:
            covered = sum(1 for i in interests if i in generated)
            if covered < len(interests) * 0.5:
                score -= 0.15

        # 饮食限制
        dietary = constraints.get("dietary_restrictions", [])
        if dietary and not any(d in generated for d in dietary):
            score -= 0.1

        # 无障碍需求
        if constraints.get("accessibility_needs") and "无障碍" not in generated:
            score -= 0.1

        return self._normalize_score(max(score, 0.0))

    async def _score_readability(
        self,
        generated: str,
    ) -> float:
        """
        READ维度: 评估可读性

        评估输出的清晰度和格式规范：
        - 标题结构
        - 表格使用
        - 段落长度
        - 列表格式

        Args:
            generated: 生成的行程文本

        Returns:
            float: 0-1 分数
        """
        score = 0.5  # 基础分

        # 标题结构
        if "# " in generated:
            score += 0.1
        if "## " in generated:
            score += 0.1

        # 表格
        if "|" in generated:
            score += 0.1

        # 列表
        list_hits = sum(
            1 for ind in READ_INDICATORS["list"] if ind in generated
        )
        score += min(0.1, list_hits * 0.02)

        # 段落长度检查（避免超长段落）
        paragraphs = [p for p in generated.split("\n\n") if p.strip()]
        long_paragraphs = sum(1 for p in paragraphs if len(p) > 500)
        if long_paragraphs == 0:
            score += 0.1
        else:
            score -= min(0.1, long_paragraphs * 0.02)

        return self._normalize_score(score)

    # ------------------------------------------------------------------
    #  Step 3: 加权总分计算
    # ------------------------------------------------------------------
    async def _calculate_overall_score(
        self,
        dimension_scores: dict[str, float],
        weights: dict[str, float],
    ) -> float:
        """
        加权计算总分

        Args:
            dimension_scores: 4个维度的分数
            weights: 4个维度的权重

        Returns:
            float: 加权总分 (0-1)
        """
        overall = sum(dimension_scores[k] * weights[k] for k in dimension_scores)
        return self._normalize_score(overall)

    # ------------------------------------------------------------------
    #  LLM-as-a-Judge
    # ------------------------------------------------------------------
    async def _llm_judge_comp(self, generated: str, constraints: dict) -> float | None:
        """使用结构化 Judge 评估旅行需求覆盖度。"""
        if not self.use_llm_judge:
            return None
        result = await self._judge.evaluate(
            "RACE.COMP",
            "判断行程是否覆盖目的地、天数、预算、兴趣、同行人和天气备选等需求。",
            {"constraints": constraints, "itinerary": generated[:5000]},
            "硬约束缺失直接判 fail；只覆盖部分约束为 soft_pass；所有关键约束均有对应安排和说明才可 pass。",
        )
        self._judge_results["COMP"] = result
        return result.get("score")

    async def _llm_judge_depth(self, generated: str) -> float | None:
        """使用结构化 Judge 评估推荐理由、取舍和备选方案质量。"""
        if not self.use_llm_judge:
            return None
        result = await self._judge.evaluate(
            "RACE.DEPTH",
            "判断旅行行程是否解释了为什么这样安排，以及在天气、体力、预算变化时如何调整。",
            {"itinerary": generated[:5000]},
            "只出现景点清单而没有理由、相邻景点衔接和备选方案时不得超过 0.5；有可执行取舍和个性化解释才可达到 0.8 以上。",
        )
        self._judge_results["DEPTH"] = result
        return result.get("score")
