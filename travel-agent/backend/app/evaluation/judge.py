"""旅行规划专用的结构化 LLM Judge。"""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any


def _clip(value: Any, limit: int = 6000) -> Any:
    """限制 Judge 输入大小，避免一次评测消耗过多上下文。"""
    if isinstance(value, str):
        return value[:limit]
    if isinstance(value, dict):
        return {str(k): _clip(v, limit) for k, v in list(value.items())[:80]}
    if isinstance(value, list):
        return [_clip(v, limit) for v in value[:80]]
    return value


def _default_result(reason: str, status: str = "unavailable") -> dict[str, Any]:
    return {
        "score": None,
        "label": "unavailable",
        "confidence": 0.0,
        "reason": reason,
        "evidence": [],
        "failure_category": "judge_unavailable" if status != "ok" else "",
        "failed_checks": [],
        "status": status,
    }


class TravelLLMJudge:
    """统一的 LLM-as-a-Judge 入口，所有维度使用同一输出契约。"""

    def __init__(self, model: str | None = None, timeout_seconds: int = 45) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def evaluate(
        self,
        rubric_name: str,
        task: str,
        evidence: dict[str, Any],
        rubric: str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """根据明确 Rubric 输出分数、证据、置信度和失败分类。"""
        try:
            from config import settings

            if not settings.openai_api_key:
                return _default_result("未配置评测模型，保留规则评测结果", "unavailable")
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                timeout=min(self.timeout_seconds, settings.openai_timeout),
            )
            payload = {
                "rubric_name": rubric_name,
                "task": _clip(task),
                "evidence": _clip(evidence),
                "rubric": rubric,
                "output_schema": {
                    "score": "0到1之间的小数",
                    "label": "pass|soft_pass|fail",
                    "confidence": "0到1之间的小数",
                    "reason": "一句话说明判定原因",
                    "evidence": "最多5条来自输入证据的具体依据",
                    "failure_category": "失败分类，没有则为空字符串",
                    "failed_checks": "未通过的硬检查名称列表",
                },
            }
            prompt = (
                "你是旅行规划 Agent 的严格评测器。只能依据给定证据判定，不能补造事实。"
                "先检查硬约束，再判断语义质量；硬约束失败时不得用文案质量抵消。"
                "只输出合法 JSON，不要 Markdown，不要额外解释。\n"
                + json.dumps(payload, ensure_ascii=False)
            )
            started = time.perf_counter()

            def call() -> Any:
                try:
                    return client.chat.completions.create(
                        model=self.model or settings.openai_model,
                        messages=[
                            {"role": "system", "content": "你是可审计的旅行 Agent 评测器。"},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0,
                        max_tokens=700,
                        response_format={"type": "json_object"},
                    )
                except Exception:
                    return client.chat.completions.create(
                        model=self.model or settings.openai_model,
                        messages=[
                            {"role": "system", "content": "你是可审计的旅行 Agent 评测器。"},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0,
                        max_tokens=700,
                    )

            response = await asyncio.wait_for(
                asyncio.to_thread(call), timeout=self.timeout_seconds + 5
            )
            content = (response.choices[0].message.content or "").strip()
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content).strip()
            result = json.loads(content)
            score = result.get("score")
            result["score"] = max(0.0, min(1.0, float(score))) if score is not None else None
            result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.0))))
            result["label"] = result.get("label") or ("pass" if (result["score"] or 0) >= 0.6 else "fail")
            result["evidence"] = list(result.get("evidence") or [])[:5]
            result["failed_checks"] = list(result.get("failed_checks") or [])[:10]
            result["status"] = "ok"
            result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)

            if trace_id:
                try:
                    from observability.langfuse_client import get_langfuse
                    get_langfuse().log_llm_call(
                        trace_id,
                        None,
                        self.model or settings.openai_model,
                        prompt,
                        json.dumps(result, ensure_ascii=False),
                        latency_ms=result["latency_ms"],
                    )
                except Exception:
                    pass
            return result
        except Exception as exc:
            return _default_result(f"Judge 调用失败: {type(exc).__name__}: {exc}")

