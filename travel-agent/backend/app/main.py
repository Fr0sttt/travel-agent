"""
Travel Agent FastAPI 入口模块

提供 REST API 和 WebSocket 端点：
- POST /api/plan - 创建行程规划
- GET /api/plan/{session_id} - 获取规划结果
- POST /api/chat - 聊天接口
- WS /ws/chat/{session_id} - WebSocket 流式对话
- GET /health - 健康检查
- GET /api/tools - 获取可用工具列表
"""

from __future__ import annotations

import atexit
import asyncio
import os
import json
import sys
import uuid
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agent.graph import build_travel_graph
from agent.tools import TOOLS, get_tools
from agent.mcp_bridge import close_mcp_bridge, get_mcp_health_text
from agent.travel_agent import TravelAgent
from config import settings
from memory.memory_manager import MemoryManager
from infrastructure.remote_middleware_tunnel import RemoteMiddlewareTunnels, _TunnelSpec
from models.schemas import (
    AgentResponse,
    ChatRequest,
    HealthResponse,
    PlanRequest,
)

# psycopg 的异步模式（LangGraph checkpointer 依赖）在 Windows 上不兼容默认的
# ProactorEventLoop，必须在事件循环创建之前切换成 SelectorEventLoop。
# 已用独立脚本验证过这个修复是必需的（报错：
# "Psycopg cannot use the 'ProactorEventLoop' to run in async mode"）。
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _running_in_pycharm() -> bool:
    """判断是否运行在 PyCharm 调试环境，便于关闭重载子进程。

    新版 PyCharm 不再注入 PYCHARM_HOSTED 等环境变量,改成检测
    命令行里带的 pycharm helper 脚本或 IDE 特有的调试参数。
    """
    if os.getenv("PYCHARM_HOSTED") or os.getenv("PYCHARM_DISPLAY_PORT") or os.getenv("PYCHARM_MATPLOTLIB_PORT"):
        return True
    # 新版 PyCharm 会把 pydevd/pycharm helper 路径塞进 sys.argv 或 sys.path
    import sys
    joined = " ".join(sys.argv) + " " + " ".join(sys.path)
    return "pycharm" in joined.lower() or "pydevd" in joined.lower()


def _cleanup_runtime() -> None:
    """进程退出时兜底清理已创建的运行时资源。"""
    app_obj = globals().get("app")
    if app_obj is None:
        return

    state = getattr(app_obj, "state", None)
    tunnel_manager = getattr(state, "tunnel_manager", None)
    if tunnel_manager is not None:
        try:
            tunnel_manager.close()
        except Exception:
            pass

    try:
        asyncio.run(close_mcp_bridge())
    except Exception:
        pass


atexit.register(_cleanup_runtime)


def _kill_port_occupants(port: int) -> None:
    """启动前把占用指定端口的残留进程干掉。

    PyCharm 点红色停止按钮走 TerminateProcess,atexit 不会跑,
    paramiko SSH 隧道线程和 uvicorn socket 可能留着占端口。
    下次启动前主动清理,避免 [WinError 10048]。
    """
    import subprocess

    current_pid = os.getpid()
    killed = []

    if os.name == "nt":
        # Windows:netstat 找 PID,taskkill 杀
        try:
            result = subprocess.run(
                ["netstat", "-ano", "-p", "TCP"],
                capture_output=True, text=True, timeout=5,
            )
        except Exception as exc:
            print(f"[startup] netstat 查询失败,跳过端口清理: {exc}", flush=True)
            return

        for line in result.stdout.splitlines():
            parts = line.split()
            # 格式: TCP 0.0.0.0:8000 0.0.0.0:0 LISTENING <pid>
            if len(parts) < 5:
                continue
            local = parts[1]
            state = parts[3] if len(parts) >= 5 else ""
            if not local.endswith(f":{port}"):
                continue
            if state != "LISTENING":
                continue
            try:
                pid = int(parts[-1])
            except ValueError:
                continue
            if pid == current_pid or pid == 0:
                continue
            try:
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True, timeout=5,
                )
                killed.append(pid)
            except Exception as exc:
                print(f"[startup] 杀掉 PID {pid} 失败: {exc}", flush=True)
    else:
        # Linux/Mac:lsof
        try:
            result = subprocess.run(
                ["lsof", "-ti", f"tcp:{port}"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                try:
                    pid = int(line.strip())
                except ValueError:
                    continue
                if pid == current_pid:
                    continue
                try:
                    os.kill(pid, 9)
                    killed.append(pid)
                except Exception:
                    pass
        except FileNotFoundError:
            return

    if killed:
        print(f"[startup] 清理了占用 {port} 端口的残留进程: {killed}", flush=True)
        # 给系统一点时间释放 socket
        import time as _time
        _time.sleep(0.5)


# ==================== 生命周期管理 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期管理

    启动时初始化 Agent，关闭时清理资源。
    """
    # 启动
    print("[startup] begin", flush=True)
    tunnel_manager = None
    if settings.remote_middleware_ssh_enabled:
        print("[startup] preparing remote tunnels", flush=True)
        tunnel_manager = RemoteMiddlewareTunnels(
            ssh_host=settings.remote_middleware_ssh_host,
            ssh_port=settings.remote_middleware_ssh_port,
            ssh_username=settings.remote_middleware_ssh_username,
            ssh_password=settings.remote_middleware_ssh_password,
            auto_start_remote_services=settings.remote_middleware_auto_start,
            tunnel_specs=[
                _TunnelSpec(
                    name="postgres",
                    local_host="127.0.0.1",
                    local_port=settings.local_postgres_port,
                    remote_host=settings.remote_postgres_host,
                    remote_port=settings.remote_postgres_port,
                ),
                _TunnelSpec(
                    name="elasticsearch",
                    local_host="127.0.0.1",
                    local_port=settings.local_elasticsearch_port,
                    remote_host=settings.remote_elasticsearch_host,
                    remote_port=settings.remote_elasticsearch_port,
                ),
            ],
        )
        tunnel_manager.start()
        print("[startup] remote tunnels ready", flush=True)
        app.state.tunnel_manager = tunnel_manager

    print("[startup] initializing memory manager", flush=True)
    memory_manager = MemoryManager(
        use_mem0=bool(settings.mem0_api_key),
        max_context_tokens=8000,
        embedding_provider="hash",
        persist_dir=settings.mem0_chroma_path,
        memory_backend=settings.memory_backend,
        elasticsearch_url=settings.elasticsearch_url,
        elasticsearch_username=settings.elasticsearch_username,
        elasticsearch_password=settings.elasticsearch_password,
        elasticsearch_index_prefix=settings.elasticsearch_index_prefix,
        elasticsearch_vector_dims=settings.elasticsearch_vector_dims,
        session_history_db_url=settings.session_history_db_url,
    )
    print("[startup] memory manager ready", flush=True)
    app.state.memory_manager = memory_manager

    # LangGraph checkpointer 用于持久化图执行状态，支持断点续传。
    # psycopg v3 原生连接不认 SQLAlchemy 专用的 +psycopg2/+psycopg 前缀。
    pg_conn_str = (
        settings.session_history_db_url
        .replace("postgresql+psycopg2://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
    )
    print("[startup] initializing LangGraph checkpointer", flush=True)
    async with AsyncPostgresSaver.from_conn_string(pg_conn_str) as checkpointer:
        await checkpointer.setup()  # 幂等，首次建表，之后调用不会重复建
        graph = build_travel_graph(checkpointer=checkpointer)
        app.state.agent = TravelAgent(graph=graph, memory_manager=memory_manager)
        print("[startup] agent ready (with checkpointer)", flush=True)
        app.state.start_time = asyncio.get_event_loop().time()

        yield

        # 关闭（必须在 async with 内部，否则 checkpointer 连接会在请求
        # 处理期间被提前关闭）
        if hasattr(app.state, "agent"):
            del app.state.agent
        if hasattr(app.state, "memory_manager"):
            del app.state.memory_manager
        if hasattr(app.state, "tunnel_manager"):
            app.state.tunnel_manager.close()
            del app.state.tunnel_manager
        await close_mcp_bridge()


# ==================== FastAPI 应用 ====================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Travel Agent - 可解释旅行规划 Agent API\n\n"
                "基于 LangGraph + LLM 的智能旅行规划系统，提供可解释的行程推荐。",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

frontend_dist_dir = Path(settings.frontend_dist_dir).expanduser().resolve() if settings.frontend_dist_dir else None
frontend_index_file = frontend_dist_dir / "index.html" if frontend_dist_dir else None
frontend_assets_dir = frontend_dist_dir / "assets" if frontend_dist_dir else None

if frontend_assets_dir and frontend_assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_assets_dir)), name="frontend_assets")

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 依赖注入 ====================

def get_agent(request: Request) -> TravelAgent:
    """
    获取 Agent 实例

    Args:
        request: FastAPI 请求对象

    Returns:
        TravelAgent: Agent 实例
    """
    return request.app.state.agent


def get_memory_manager(request: Request) -> MemoryManager:
    """获取记忆管理器实例。"""
    return request.app.state.memory_manager


# ==================== 健康检查 ====================

@app.get("/health", response_model=HealthResponse, tags=["系统"])
async def health() -> HealthResponse:
    """
    健康检查端点

    返回服务状态、版本号和依赖项状态。
    """
    deps: dict[str, str] = {
        "langgraph": "ok",
        "tools": f"{len(TOOLS)} tools loaded",
    }

    # 检查 OpenAI
    if settings.openai_api_key:
        deps["openai"] = "configured"
    else:
        deps["openai"] = "not configured"

    # 检查 OpenTripMap
    if settings.opentripmap_api_key:
        deps["opentripmap"] = "configured"
    else:
        deps["opentripmap"] = "not configured (using demo data)"

    # 检查 Langfuse
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        deps["langfuse"] = "configured"
    else:
        deps["langfuse"] = "not configured"

    deps["amap_mcp"] = get_mcp_health_text()

    return HealthResponse(
        status="ok",
        version=settings.app_version,
        dependencies=deps,
    )


@app.get("/", tags=["系统"])
async def root():
    """
    根路径 - 优先返回前端页面，没有静态文件时返回 API 信息
    """
    if frontend_index_file and frontend_index_file.exists():
        return FileResponse(frontend_index_file)
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理

    捕获未处理的异常，返回标准化的错误响应。
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": str(exc),
            "path": str(request.url),
        },
    )



# ==================== 行程规划 API ====================

@app.post("/api/plan", response_model=AgentResponse, tags=["行程规划"])
async def create_plan(
    request: PlanRequest,
    agent: TravelAgent = Depends(get_agent),
) -> AgentResponse:
    """
    创建行程规划（同步版本）

    接收用户输入，执行完整的旅行规划流程，返回最终结果。
    如需流式输出，请使用 WebSocket 接口。

    Args:
        request: 规划请求，包含用户输入和可选的会话 ID

    Returns:
        AgentResponse: 规划结果

    Raises:
        HTTPException: 规划失败时返回 500 错误
    """
    session_id = request.session_id or f"sess_{uuid.uuid4().hex[:8]}"

    try:
        # 收集所有流式输出
        chunks: list[str] = []
        async for chunk in agent.plan_travel(request.user_input, session_id):
            chunks.append(chunk)

        # 从最后一个 chunk 解析结果
        if chunks:
            last_chunk = chunks[-1]
            try:
                data = json.loads(last_chunk.replace("data: ", "").strip())
                event_type = data.get("type", "")

                if event_type == "complete":
                    itinerary = data.get("itinerary", "")
                    risk_alerts = data.get("risk_alerts", [])
                    session_state = await agent.get_session_state(session_id)

                    return AgentResponse(
                        session_id=session_id,
                        status="complete",
                        current_step="output_formatter",
                        message="行程规划完成！",
                        tool_calls=session_state.get("tool_calls", []) if session_state else [],
                        risk_alerts=risk_alerts,
                        needs_clarification=False,
                        trace_id=session_state.get("trace_id") if session_state else None,
                    )
                elif event_type == "clarify":
                    return AgentResponse(
                        session_id=session_id,
                        status="clarifying",
                        current_step="preference_collector",
                        message=data.get("message", "请补充更多信息"),
                        risk_alerts=[],
                        needs_clarification=True,
                        clarification_question=data.get("message"),
                    )
                elif event_type == "error":
                    raise HTTPException(
                        status_code=500,
                        detail=data.get("message", "规划失败"),
                    )

            except json.JSONDecodeError:
                pass

        # 兜底返回
        return AgentResponse(
            session_id=session_id,
            status="complete",
            message="规划完成",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"规划失败: {str(e)}")


@app.get("/api/plan/{session_id}", response_model=AgentResponse, tags=["行程规划"])
async def get_plan(
    session_id: str,
    agent: TravelAgent = Depends(get_agent),
) -> AgentResponse:
    """
    获取已有规划结果

    根据会话 ID 获取已生成的行程规划。

    Args:
        session_id: 会话 ID

    Returns:
        AgentResponse: 规划结果

    Raises:
        HTTPException: 会话不存在时返回 404
    """
    state = await agent.get_session_state(session_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

    return AgentResponse(
        session_id=session_id,
        status="complete" if state.get("itinerary") else "processing",
        current_step=state.get("current_node", "unknown"),
        message="规划结果" if state.get("itinerary") else "规划中...",
        tool_calls=state.get("tool_calls", []),
        risk_alerts=state.get("risk_alerts", []),
        needs_clarification=state.get("needs_clarification", False),
    )


@app.delete("/api/plan/{session_id}", tags=["行程规划"])
async def delete_plan(
    session_id: str,
    agent: TravelAgent = Depends(get_agent),
) -> dict[str, str]:
    """
    删除行程规划

    清除指定会话的规划状态。

    Args:
        session_id: 会话 ID

    Returns:
        操作结果
    """
    cleared = agent.clear_session(session_id)
    if cleared:
        return {"status": "ok", "message": f"会话 {session_id} 已清除"}
    return {"status": "not_found", "message": f"会话 {session_id} 不存在"}


@app.get("/api/session/{session_id}", tags=["行程规划"])
async def get_session_state(
    session_id: str,
    agent: TravelAgent = Depends(get_agent),
    memory_manager: MemoryManager = Depends(get_memory_manager),
) -> JSONResponse:
    """
    获取会话完整状态

    返回指定会话的内部状态（POI、路线、天气、预算、工具调用等），
    供前端将结构化数据渲染到地图、时间线、日历等面板。

    Args:
        session_id: 会话 ID

    Returns:
        JSONResponse: 会话状态字典

    Raises:
        HTTPException: 会话不存在时返回 404
    """
    state = await agent.get_session_state(session_id)
    if not state:
        state = memory_manager.get_session_snapshot(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

    # 确保内容可 JSON 序列化，并补上最近消息，方便前端恢复聊天窗口
    serializable_state = json.loads(json.dumps(state, default=str))
    if not serializable_state.get("messages"):
        serializable_state["messages"] = memory_manager.get_recent_session_history(
            session_id,
            limit=200,
        )
    return JSONResponse(content=serializable_state)


@app.get("/api/sessions", tags=["行程规划"])
async def list_sessions(
    memory_manager: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """列出最近活跃的会话。"""
    sessions = memory_manager.list_sessions(limit=100)
    return {
        "count": len(sessions),
        "sessions": sessions,
    }


@app.delete("/api/sessions/{session_id}", tags=["行程规划"])
async def delete_session(
    session_id: str,
    agent: TravelAgent = Depends(get_agent),
    memory_manager: MemoryManager = Depends(get_memory_manager),
) -> dict[str, str]:
    """
    彻底删除一个会话

    同时清除：PG 中的会话历史/消息记录、LangGraph 的内存规划状态。
    与 /api/plan/{session_id} 不同，后者只清规划状态，不删会话记录。

    Args:
        session_id: 会话 ID

    Returns:
        操作结果
    """
    memory_manager.delete_session(session_id)
    agent.clear_session(session_id)
    return {"status": "ok", "message": f"会话 {session_id} 已删除"}


# ==================== 聊天 API ====================

@app.post("/api/chat", response_model=AgentResponse, tags=["聊天"])
async def chat(
    request: ChatRequest,
    agent: TravelAgent = Depends(get_agent),
) -> AgentResponse:
    """
    聊天接口（同步版本）

    接收用户消息，返回答复或规划结果。

    Args:
        request: 聊天请求

    Returns:
        AgentResponse: 响应结果
    """
    try:
        chunks: list[str] = []
        async for chunk in agent.plan_travel(request.message, request.session_id):
            chunks.append(chunk)

        if chunks:
            last_chunk = chunks[-1]
            try:
                data = json.loads(last_chunk.replace("data: ", "").strip())
                return AgentResponse(
                    session_id=request.session_id,
                    status="complete",
                    message=data.get("message", ""),
                    risk_alerts=[],
                    needs_clarification=False,
                )
            except json.JSONDecodeError:
                pass

        return AgentResponse(
            session_id=request.session_id,
            status="complete",
            message="处理完成",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天处理失败: {str(e)}")


# ==================== 流式 API (SSE) ====================


async def _stream_with_keepalive(
    source: AsyncGenerator[str, None],
    *,
    session_id: str,
    heartbeat_seconds: int = 15,
) -> AsyncGenerator[str, None]:
    """给 SSE 流加一个轻量保活，避免长任务被中间层误断开。"""

    queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def producer() -> None:
        try:
            async for chunk in source:
                await queue.put(chunk)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[stream] session_id={session_id} SSE 生产者异常: {exc}", flush=True)
            error_event = json.dumps(
                {
                    "type": "error",
                    "message": f"流式输出异常: {exc}",
                    "session_id": session_id,
                },
                ensure_ascii=False,
            )
            await queue.put(f"data: {error_event}\n\n")
        finally:
            await queue.put(None)

    task = asyncio.create_task(producer())
    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=heartbeat_seconds)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue

            if item is None:
                break
            yield item
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await task

@app.post("/api/plan/stream", tags=["行程规划"])
async def create_plan_stream(request: PlanRequest) -> StreamingResponse:
    """
    创建行程规划（SSE 流式版本）

    通过 Server-Sent Events 流式返回规划过程中的每一步状态。

    Args:
        request: 规划请求

    Returns:
        StreamingResponse: SSE 流
    """
    session_id = request.session_id or f"sess_{uuid.uuid4().hex[:8]}"
    agent: TravelAgent = app.state.agent

    async def event_generator() -> AsyncGenerator[str, None]:
        async for chunk in _stream_with_keepalive(
            agent.plan_travel(request.user_input, session_id),
            session_id=session_id,
        ):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/chat/stream", tags=["聊天"])
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    聊天接口（SSE 流式版本）

    通过 Server-Sent Events 流式返回聊天响应。

    Args:
        request: 聊天请求

    Returns:
        StreamingResponse: SSE 流
    """
    agent: TravelAgent = app.state.agent

    async def event_generator() -> AsyncGenerator[str, None]:
        async for chunk in _stream_with_keepalive(
            agent.plan_travel(request.message, request.session_id),
            session_id=request.session_id,
        ):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== WebSocket API ====================

@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket 聊天端点

    支持双向实时通信，流式返回规划过程和结果。

    Args:
        websocket: WebSocket 连接
        session_id: 会话 ID
    """
    await websocket.accept()
    agent: TravelAgent = app.state.agent

    try:
        while True:
            # 接收客户端消息
            raw_data = await websocket.receive_text()

            try:
                data = json.loads(raw_data)
                message = data.get("message", "")
                # plan_travel 内部走 intent_router 判断是规划/续问/问答/闲聊，
                # 不再需要在这里区分 message_type 走不同方法
                async for chunk in agent.plan_travel(message, session_id):
                    await websocket.send_text(chunk)

                # 发送结束标记
                await websocket.send_text(
                    json.dumps({
                        "type": "done",
                        "session_id": session_id,
                    }, ensure_ascii=False)
                )

            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({
                        "type": "error",
                        "message": "无效的 JSON 格式",
                    }, ensure_ascii=False)
                )

    except WebSocketDisconnect:
        print(f"WebSocket 断开: {session_id}")
    except Exception as e:
        try:
            await websocket.send_text(
                json.dumps({
                    "type": "error",
                    "message": f"服务器错误: {str(e)}",
                }, ensure_ascii=False)
            )
        except Exception:
            pass


# ==================== 工具管理 API ====================

@app.get("/api/tools", tags=["工具"])
async def list_tools() -> dict[str, Any]:
    """
    获取可用工具列表

    返回所有注册的工具及其描述信息。

    Returns:
        工具列表
    """
    tools_info = []
    for tool in TOOLS:
        tool_info = {
            "name": tool.name,
            "description": tool.description,
        }
        # 尝试获取参数信息
        if hasattr(tool, "args_schema"):
            try:
                schema = tool.args_schema.model_json_schema()
                tool_info["parameters"] = schema.get("properties", {})
                tool_info["required"] = schema.get("required", [])
            except Exception:
                pass
        tools_info.append(tool_info)

    return {
        "count": len(tools_info),
        "tools": tools_info,
    }


# ==================== 全局异常处理 ====================


# ==================== 主入口 ====================


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    """
    前端单页应用兜底路由。
    """
    if full_path.startswith(("api", "ws", "docs", "redoc", "openapi.json", "health")):
        raise HTTPException(status_code=404, detail="Not Found")

    if frontend_dist_dir and full_path:
        candidate = (frontend_dist_dir / full_path).resolve()
        if candidate.is_file() and frontend_dist_dir in candidate.parents:
            return FileResponse(candidate)

    if frontend_index_file and frontend_index_file.exists():
        return FileResponse(frontend_index_file)

    raise HTTPException(status_code=404, detail="Not Found")


if __name__ == "__main__":
    import uvicorn

    # 启动前先清掉占用目标端口的残留进程
    # (PyCharm 红色停止不走 atexit,paramiko/uvicorn socket 会残留)
    _kill_port_occupants(settings.api_port)

    # 不用 uvicorn.run(...)：它内部的 Server.run() 会调用
    # config.setup_event_loop()，这个方法在 Windows 上会强制
    # asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy())，
    # 把我们设置的 SelectorEventLoop 策略覆盖回去（已实测确认）。
    # psycopg 的异步模式（LangGraph checkpointer 依赖）不支持 Proactor，
    # 所以改用更底层的 Server(...).serve()，跳过 setup_event_loop()，
    # 自己用 asyncio.run() 控制事件循环创建时机。
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    config = uvicorn.Config(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=False,  # PyCharm 有自己的热重载,uvicorn reload 会导致双进程 bind 冲突
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())
