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

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from agent.tools import TOOLS, get_tools
from agent.travel_agent import TravelAgent
from config import get_settings, settings
from models.schemas import (
    AgentResponse,
    ChatRequest,
    HealthResponse,
    PlanRequest,
)


# ==================== 生命周期管理 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期管理

    启动时初始化 Agent，关闭时清理资源。
    """
    # 启动
    app.state.agent = TravelAgent()
    app.state.start_time = asyncio.get_event_loop().time()

    yield

    # 关闭
    if hasattr(app.state, "agent"):
        del app.state.agent


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

    return HealthResponse(
        status="ok",
        version=settings.app_version,
        dependencies=deps,
    )


@app.get("/", tags=["系统"])
async def root() -> dict[str, str]:
    """
    根路径 - API 信息
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


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
                    session_state = agent.get_session_state(session_id)

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
    state = agent.get_session_state(session_id)

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
    state = agent.get_session_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

    # 确保内容可 JSON 序列化
    serializable_state = json.loads(json.dumps(state, default=str))
    return JSONResponse(content=serializable_state)


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
        async for chunk in agent.chat(request.message, request.session_id):
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
        async for chunk in agent.plan_travel(request.user_input, session_id):
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
        async for chunk in agent.chat(request.message, request.session_id):
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
                message_type = data.get("type", "chat")

                if message_type == "plan":
                    # 行程规划模式
                    async for chunk in agent.plan_travel(message, session_id):
                        await websocket.send_text(chunk)
                else:
                    # 聊天模式
                    async for chunk in agent.chat(message, session_id):
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


# ==================== 主入口 ====================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
