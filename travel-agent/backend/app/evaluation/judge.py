"""旅行规划专用的结构化 LLM Judge。"""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


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


class JudgeOutput(BaseModel):
    """Judge 的统一输出契约，避免把任意模型文本直接当成评分结果。"""

    model_config = ConfigDict(extra="ignore")

    score: float = Field(..., ge=0.0, le=1.0)
    label: Literal["pass", "soft_pass", "fail"] = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(..., min_length=1)
    evidence: list[str] = Field(...)
    failure_category: str = Field(...)
    failed_checks: list[str] = Field(...)


_JUDGE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "score": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        "label": {"type": "string", "enum": ["pass", "soft_pass", "fail"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reason": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "failure_category": {"type": "string"},
        "failed_checks": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "score",
        "label",
        "confidence",
        "reason",
        "evidence",
        "failure_category",
        "failed_checks",
    ],
}


def _extract_json_object(content: str) -> dict[str, Any]:
    """兼容中转模型返回的 Markdown、前后缀说明和思考标签。"""
    text = (content or "").strip()
    if not text:
        raise ValueError("Judge 返回空内容")
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    decoder = json.JSONDecoder()
    last_error: json.JSONDecodeError | None = None
    first_object: dict[str, Any] | None = None
    start = 0
    while True:
        start = text.find("{", start)
        if start < 0:
            break
        try:
            result, _ = decoder.raw_decode(text[start:])
            if isinstance(result, dict):
                # 模型偶尔会复述输入 payload；优先选真正含有评分字段的对象。
                if first_object is None:
                    first_object = result
                if "score" in result and any(
                    key in result for key in ("label", "confidence", "reason")
                ):
                    return result
        except json.JSONDecodeError as exc:
            last_error = exc
        start += 1
    if first_object is not None:
        return first_object
    if last_error:
        raise ValueError(f"Judge 返回内容无法解析为 JSON: {last_error.msg}") from last_error
    # 不把模型的思考文本写入评测报告，避免内部推理内容泄漏到前端。
    raise ValueError("Judge 未返回 JSON 对象，可能返回了未结构化的思考文本")


def _message_to_text(value: Any) -> str:
    """兼容 OpenAI 兼容接口返回字符串或内容分片。"""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
        return "".join(parts).strip()
    return ""


def _validate_judge_output(value: dict[str, Any]) -> dict[str, Any]:
    """用同一份 Pydantic 契约校验三种传输模式的返回值。"""
    normalized = dict(value)
    label_aliases = {
        "success": "pass",
        "passed": "pass",
        "positive": "pass",
        "通过": "pass",
        "部分通过": "soft_pass",
        "neutral": "soft_pass",
        "failure": "fail",
        "failed": "fail",
        "negative": "fail",
        "失败": "fail",
    }
    if isinstance(normalized.get("label"), str):
        normalized["label"] = label_aliases.get(
            normalized["label"].strip().lower(), normalized["label"].strip().lower()
        )
    if normalized.get("evidence") is None:
        normalized["evidence"] = []
    elif isinstance(normalized.get("evidence"), str):
        normalized["evidence"] = [normalized["evidence"]]
    if normalized.get("failed_checks") is None:
        normalized["failed_checks"] = []
    elif isinstance(normalized.get("failed_checks"), str):
        normalized["failed_checks"] = [normalized["failed_checks"]]
    if normalized.get("failure_category") is None:
        normalized["failure_category"] = ""
    result = JudgeOutput.model_validate(normalized).model_dump()
    result["evidence"] = result["evidence"][:5]
    result["failed_checks"] = result["failed_checks"][:10]
    return result


class TravelLLMJudge:
    """统一的 LLM-as-a-Judge 入口，所有维度使用同一输出契约。"""

    _semaphore: asyncio.Semaphore | None = None

    def __init__(self, model: str | None = None, timeout_seconds: int = 45) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds

    @classmethod
    def _get_semaphore(cls) -> asyncio.Semaphore:
        if cls._semaphore is None:
            # 评测一次会触发多个维度，限制并发避免中转站返回空内容或触发限流。
            cls._semaphore = asyncio.Semaphore(2)
        return cls._semaphore

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
                    "score": "必须是0到1之间的小数，不能为null",
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
                "即使证据不足也必须给出0到1之间的数值分数，不能返回null。"
                "不要复述输入 payload，不要输出 rubric_name、task、output_schema 等输入包装字段。"
                "禁止输出思考过程、分析过程、<think>标签或 Markdown。只输出符合给定结构的合法 JSON。\n"
                + json.dumps(payload, ensure_ascii=False)
            )
            started = time.perf_counter()

            def call(mode: str) -> Any:
                kwargs: dict[str, Any] = {
                    "model": self.model or settings.openai_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "你是可审计的旅行 Agent 评测器。"
                                "只输出评分结果 JSON，不复述输入，不输出思考过程。"
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0,
                    # DeepSeek 思考模型会消耗一部分输出额度，700 容易只返回
                    # reasoning_content 而没有最终 JSON，因此给 Judge 独立留出额度。
                    "max_tokens": max(1600, min(settings.openai_max_tokens, 2400)),
                    # DeepSeek v4 flash 的 thinking 模式会把最终答案留在
                    # reasoning_content，关闭后才会稳定返回 content JSON。
                    "extra_body": {"thinking": {"type": "disabled"}},
                }
                if mode == "json_schema":
                    kwargs["response_format"] = {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "travel_agent_judge_result",
                            "strict": True,
                            "schema": _JUDGE_JSON_SCHEMA,
                        },
                    }
                elif mode in ("json_object", "json_object_retry"):
                    kwargs["response_format"] = {"type": "json_object"}
                return client.chat.completions.create(**kwargs)

            result: dict[str, Any] | None = None
            last_parse_error: Exception | None = None
            async with self._get_semaphore():
                # 当前中转站不支持 JSON Schema，但支持 JSON Object；不再把普通
                # 思考文本当作正式降级协议，避免“解析成功但不可审计”。
                modes = ("json_schema", "json_object", "json_object_retry")
                for attempt, mode in enumerate(modes):
                    try:
                        response = await asyncio.wait_for(
                            asyncio.to_thread(call, mode), timeout=self.timeout_seconds + 5
                        )
                        message = response.choices[0].message
                        # reasoning_content 永远是内部思考，不参与评测结果解析。
                        content = _message_to_text(getattr(message, "content", None))
                        if not content:
                            raise ValueError("Judge 返回空内容")
                        result = _validate_judge_output(_extract_json_object(content))
                        break
                    except Exception as exc:
                        # 结构化协议不被中转站支持时，继续尝试兼容模式。
                        last_parse_error = exc
                    if attempt < len(modes) - 1:
                        await asyncio.sleep(1)
            if result is None:
                raise last_parse_error or ValueError("Judge 未返回可解析结果")
            result["status"] = "ok"
            result["judge_transport"] = mode
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
            # 前端只展示稳定的协议错误，不展示模型原始思考文本或响应片段。
            if isinstance(exc, ValidationError) or (
                isinstance(exc, ValueError)
                and ("JSON" in str(exc) or "结构化" in str(exc) or "空内容" in str(exc))
            ):
                return _default_result(
                    "Judge 返回格式不符合结构化输出契约，已拒绝本次结果",
                )
            return _default_result(f"Judge 调用失败: {type(exc).__name__}: {exc}")
