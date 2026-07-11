"""旅行规划专用的结构化 LLM Judge。"""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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

    score: float | None = Field(default=None, ge=0.0, le=1.0)
    label: Literal["pass", "soft_pass", "fail"] = "fail"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""
    evidence: list[str] = Field(default_factory=list)
    failure_category: str = ""
    failed_checks: list[str] = Field(default_factory=list)


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
    start = 0
    while True:
        start = text.find("{", start)
        if start < 0:
            break
        try:
            result, _ = decoder.raw_decode(text[start:])
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError as exc:
            last_error = exc
        start += 1
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
    result = JudgeOutput.model_validate(value).model_dump()
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
                "禁止输出思考过程、分析过程、<think>标签或 Markdown。只输出符合给定结构的合法 JSON。\n"
                + json.dumps(payload, ensure_ascii=False)
            )
            started = time.perf_counter()

            def call(mode: str) -> Any:
                kwargs: dict[str, Any] = {
                    "model": self.model or settings.openai_model,
                    "messages": [
                        {"role": "system", "content": "你是可审计的旅行 Agent 评测器。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0,
                    "max_tokens": 700,
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
                elif mode == "json_object":
                    kwargs["response_format"] = {"type": "json_object"}
                return client.chat.completions.create(**kwargs)

            result: dict[str, Any] | None = None
            last_parse_error: Exception | None = None
            async with self._get_semaphore():
                # 优先使用结构化输出；兼容不支持 JSON Schema/JSON mode 的中转站。
                modes = ("json_schema", "json_object", "plain")
                for attempt, mode in enumerate(modes):
                    try:
                        response = await asyncio.wait_for(
                            asyncio.to_thread(call, mode), timeout=self.timeout_seconds + 5
                        )
                        message = response.choices[0].message
                        contents = []
                        for field in ("content", "reasoning_content"):
                            content = _message_to_text(getattr(message, field, None))
                            if content and content not in contents:
                                contents.append(content)
                        if not contents:
                            raise ValueError("Judge 返回空内容")
                        last_content_error: Exception | None = None
                        for content in contents:
                            try:
                                result = _validate_judge_output(_extract_json_object(content))
                                break
                            except Exception as content_exc:
                                last_content_error = content_exc
                        if result is None:
                            raise last_content_error or ValueError("Judge 未返回可解析结果")
                        break
                    except Exception as exc:
                        # 结构化协议不被中转站支持时，继续尝试兼容模式。
                        last_parse_error = exc
                    if attempt < len(modes) - 1:
                        await asyncio.sleep(1)
            if result is None:
                raise last_parse_error or ValueError("Judge 未返回可解析结果")
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
            # 前端只展示稳定的协议错误，不展示模型原始思考文本或响应片段。
            if isinstance(exc, ValueError) and (
                "JSON" in str(exc) or "结构化" in str(exc) or "空内容" in str(exc)
            ):
                return _default_result(
                    "Judge 返回格式不符合结构化输出契约，已拒绝本次结果",
                )
            return _default_result(f"Judge 调用失败: {type(exc).__name__}: {exc}")
