from __future__ import annotations

import asyncio
import json
import os
from contextlib import AsyncExitStack
from collections import deque
from datetime import datetime, timedelta
from typing import Any
from time import monotonic

from config import settings

try:  # 可选依赖：没有安装 mcp 时，应用仍然可以正常启动
    from mcp import ClientSession, StdioServerParameters, stdio_client
except Exception:  # pragma: no cover - 某些环境里可能没有安装 MCP 依赖
    ClientSession = None  # type: ignore[assignment]
    StdioServerParameters = None  # type: ignore[assignment]
    stdio_client = None  # type: ignore[assignment]


AMAP_MCP_DEFAULT_COMMAND = "npx"
AMAP_MCP_DEFAULT_ARGS = ["-y", "@amap/amap-maps-mcp-server"]


def _short_error(value: Exception | str | None, limit: int = 160) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _parse_mcp_payload(result: Any) -> Any | None:
    """把 MCP 返回结果整理成普通 Python 数据。"""
    if result is None:
        return None

    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured

    pieces: list[str] = []
    for content in getattr(result, "content", []) or []:
        if getattr(content, "type", None) != "text":
            continue
        text = getattr(content, "text", "")
        if not text:
            continue
        try:
            return json.loads(text)
        except Exception:
            pieces.append(text)

    if not pieces:
        return None

    joined = "\n".join(pieces).strip()
    if not joined:
        return None

    try:
        return json.loads(joined)
    except Exception:
        return joined


class AMapMCPBridge:
    """
    高德 MCP 连接桥。

    这里不做“多供应商抽象”，只保留当前项目真正需要的高德接入能力。
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._rate_lock = asyncio.Lock()
        self._call_lock = asyncio.Lock()
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._tool_names: set[str] = set()
        self._last_error: str | None = None
        self._last_connected_at: str | None = None
        # 高德开放平台这里按 3 次/秒做全局限流，避免把 MCP 入口打超
        self._max_calls_per_second = 3
        self._recent_calls: deque[float] = deque()

    def is_available(self) -> bool:
        return all((ClientSession is not None, StdioServerParameters is not None, stdio_client is not None))

    def is_enabled(self) -> bool:
        return bool(settings.amap_mcp_enabled)

    def is_configured(self) -> bool:
        return self.is_available() and self.is_enabled() and bool(settings.amap_maps_api_key.strip())

    def missing_configuration(self) -> list[str]:
        missing: list[str] = []
        if not self.is_available():
            missing.append("mcp library missing")
            return missing
        if not settings.amap_mcp_enabled:
            missing.append("amap_mcp_enabled=false")
        if not settings.amap_maps_api_key.strip():
            missing.append("amap_maps_api_key")
        if not settings.amap_mcp_command.strip():
            missing.append("amap_mcp_command")
        return missing

    def status_text(self) -> str:
        if not self.is_available():
            return "MCP 依赖未安装"
        if not self.is_enabled():
            return "已关闭"
        if not self.is_configured():
            return "已启用但缺少 " + ", ".join(self.missing_configuration())

        parts = [f"已启用，通过 {settings.amap_mcp_command} 启动高德 MCP"]
        if self._session is None:
            parts.append("尚未建立连接")
        else:
            parts.append(f"已连接（缓存 {len(self._tool_names)} 个工具）")
        if self._last_connected_at:
            parts.append(f"最近连接={self._last_connected_at}")
        if self._last_error:
            parts.append(f"最近错误={self._last_error}")
        return "; ".join(parts)

    async def close(self) -> None:
        async with self._lock:
            if self._stack is None:
                return
            try:
                await self._stack.aclose()
            finally:
                self._stack = None
                self._session = None
                self._tool_names = set()

    async def _create_session(self) -> ClientSession | None:
        if not self.is_configured():
            return None

        stack = AsyncExitStack()
        try:
            env = os.environ.copy()
            env["AMAP_MAPS_API_KEY"] = settings.amap_maps_api_key
            env.update(settings.amap_mcp_env)

            server = StdioServerParameters(
                command=settings.amap_mcp_command.strip() or AMAP_MCP_DEFAULT_COMMAND,
                args=list(settings.amap_mcp_args) or list(AMAP_MCP_DEFAULT_ARGS),
                env=env,
                cwd=settings.amap_mcp_cwd or None,
            )
            read_stream, write_stream = await stack.enter_async_context(stdio_client(server))

            session = ClientSession(
                read_stream,
                write_stream,
                read_timeout_seconds=timedelta(seconds=settings.amap_mcp_request_timeout_seconds),
            )
            await stack.enter_async_context(session)
            await session.initialize()

            try:
                tool_result = await session.list_tools()
                self._tool_names = {tool.name for tool in tool_result.tools}
            except Exception:
                self._tool_names = set()

            self._stack = stack
            self._session = session
            self._last_error = None
            self._last_connected_at = datetime.now().isoformat(timespec="seconds")
            return session
        except Exception as exc:
            self._last_error = _short_error(exc)
            await stack.aclose()
            return None

    async def _ensure_session(self) -> ClientSession | None:
        if self._session is not None:
            return self._session

        async with self._lock:
            if self._session is not None:
                return self._session
            return await self._create_session()

    async def _acquire_rate_slot(self) -> None:
        """按滑动窗口限制高德 MCP 的调用频率。"""
        while True:
            async with self._rate_lock:
                now = monotonic()
                window_start = now - 1.0

                while self._recent_calls and self._recent_calls[0] <= window_start:
                    self._recent_calls.popleft()

                if len(self._recent_calls) < self._max_calls_per_second:
                    self._recent_calls.append(now)
                    return

                wait_for = 1.0 - (now - self._recent_calls[0])

            await asyncio.sleep(max(wait_for, 0.01))

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any | None:
        if not self.is_configured():
            return None

        session = await self._ensure_session()
        if session is None:
            return None

        payload = arguments or {}
        # 限流令牌 + 实际调用必须用同一把锁串行化：
        # session 是单条 stdio 管道，多个协程同时调用容易导致响应错位，
        # 触发 except 分支把整个连接关掉，后续所有 MCP 调用都会返回 None，
        # 表现为“搜不到任何 POI，行程全变成自由探索”。
        async with self._call_lock:
            try:
                await self._acquire_rate_slot()
                result = await session.call_tool(tool_name, payload)
                self._last_error = None
                return _parse_mcp_payload(result)
            except Exception as exc:
                self._last_error = _short_error(exc)
                await self.close()
                return None


_MCP_BRIDGE = AMapMCPBridge()


def get_mcp_bridge() -> AMapMCPBridge:
    return _MCP_BRIDGE


async def maybe_call_mcp_tool(tool_name: str, arguments: dict[str, Any] | None = None) -> Any | None:
    """优先走高德 MCP；失败时由上层自行决定是否使用本地兜底。"""
    return await _MCP_BRIDGE.call_tool(tool_name, arguments)


def get_mcp_health_text() -> str:
    return _MCP_BRIDGE.status_text()


async def close_mcp_bridge() -> None:
    await _MCP_BRIDGE.close()
