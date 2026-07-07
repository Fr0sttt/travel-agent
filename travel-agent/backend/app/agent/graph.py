"""
Travel Agent LangGraph 状态机模块

定义 LangGraph 的状态图，包含以下节点：
1. preference_collector - 偏好收集器
2. constraint_normalizer - 约束标准化
3. destination_search - 目的地/POI搜索
4. route_planner - 路线规划
5. weather_advisor - 天气顾问
6. budget_estimator - 预算估算
7. itinerary_synthesizer - 行程合成
8. safety_reviewer - 安全审查
9. output_formatter - 输出格式化

以及条件边路由函数，实现完整的旅行规划工作流。
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from models.schemas import (
    BudgetBreakdown,
    POI,
    RouteSegment,
    ToolCallRecord,
    TravelConstraints,
    TravelPreference,
    WeatherInfo,
)


# ==================== 状态定义 ====================
#
# 重要：这里必须用 TypedDict，不能用普通 dict 子类。
#
# 之前 TravelState 是 `class TravelState(dict)`，没有任何类型注解字段。
# LangGraph 的 StateGraph(schema) 需要从 schema 里反射出所有字段名才能
# 正确地在节点之间做 state 合并——每个节点函数返回的 dict 只包含它自己
# 改动的键，LangGraph 会拿这个返回值跟 schema 声明的字段做 merge，
# 没在 schema 里声明的字段不会被识别、也不会被保留传递到下一个节点。
#
# 用普通 dict 子类时，LangGraph 反射不出任何字段（dict 子类没有类型注解），
# 导致除了节点自己刚写的那个键，其余字段（包括 messages）在传到下一个
# 节点时全部丢失，实测复现为：
#   KeyError: 'messages'（在 chitchat_responder 里 state["messages"].append(...)）
# 换成 TypedDict 之后，LangGraph 能读到完整字段列表，合并行为才正确。


class TravelState(TypedDict, total=False):
    """
    LangGraph TravelState - 核心状态定义

    total=False 表示所有字段都是可选的（节点函数可以只返回部分字段），
    这跟原来 dict 子类的使用方式保持一致。

    Attributes:
        messages: 对话历史
        user_input: 当前用户输入
        preference: 结构化旅行偏好
        constraints: 标准化约束
        missing_fields: 缺失的关键字段
        poi_list: POI 列表
        route: 路线规划
        weather: 天气预报
        budget: 预算拆分
        total_budget_estimate: 总预算区间
        current_node: 当前节点名称
        next_node: 下一节点
        iteration_count: 迭代计数（防循环）
        itinerary: 最终行程 Markdown
        confirmation_required: 需人工确认的事项
        risk_alerts: 风险提示
        session_id: 会话 ID
        trace_id: Langfuse Trace ID
        tool_calls: 工具调用记录
        needs_clarification: 是否需要澄清
        safety_approved: 安全审查是否通过
        user_intent: 意图路由结果 (new_plan | continue_clarify | faq_about_itinerary | chitchat)
        qa_response: 针对已有行程的问答回复
        chitchat_response: 闲聊回复
    """

    messages: list
    user_input: str
    preference: dict | None
    constraints: dict | None
    missing_fields: list
    poi_list: list
    route: list
    weather: list
    budget: list | dict | None
    total_budget_estimate: dict | None
    current_node: str
    next_node: str | None
    iteration_count: int
    itinerary: str
    confirmation_required: list
    risk_alerts: list
    session_id: str
    trace_id: str | None
    tool_calls: list
    needs_clarification: bool
    safety_approved: bool
    user_intent: str | None
    qa_response: str | None
    chitchat_response: str | None


def create_initial_state(
    session_id: str,
    user_input: str = "",
    messages: list | None = None,
) -> TravelState:
    """
    创建新的初始状态

    原来是 TravelState.create(...) 这个 classmethod，因为 TravelState 现在
    是 TypedDict（不支持 classmethod），改成模块级函数。

    Args:
        session_id: 会话 ID
        user_input: 用户初始输入
        messages: 初始对话历史

    Returns:
        TravelState: 初始状态字典
    """
    return TravelState(
        messages=messages or [],
        user_input=user_input,
        preference=None,
        constraints=None,
        missing_fields=[],
        poi_list=[],
        route=[],
        weather=[],
        budget=None,
        total_budget_estimate=None,
        current_node="START",
        next_node=None,
        iteration_count=0,
        itinerary="",
        confirmation_required=[],
        risk_alerts=[],
        session_id=session_id,
        trace_id=None,
        tool_calls=[],
        needs_clarification=False,
        safety_approved=False,
        user_intent=None,
        qa_response=None,
        chitchat_response=None,
    )


# ==================== 节点函数 ====================

async def intent_router(state: TravelState) -> TravelState:
    """
    意图路由节点

    用 LLM 判断用户这句话属于哪种场景，决定图接下来走哪条分支：
    - new_plan: 新的旅行规划需求
    - continue_clarify: 系统上一轮在追问缺失字段，用户在补充信息
    - faq_about_itinerary: 针对已生成行程的提问（不重新跑完整规划流程）
    - chitchat: 跟旅行规划无关的闲聊

    LLM 调用失败或超时时，降级到启发式规则，不会卡死整个流程。

    Args:
        state: 当前状态

    Returns:
        更新后的状态，state["user_intent"] 被设置
    """
    from agent.tools import classify_intent

    user_input = state.get("user_input", "")
    has_existing_itinerary = bool(state.get("itinerary"))
    needs_clarification = bool(state.get("needs_clarification"))

    try:
        result = await classify_intent.ainvoke({
            "user_input": user_input,
            "has_existing_itinerary": has_existing_itinerary,
            "needs_clarification": needs_clarification,
        })
        if isinstance(result, str):
            result = json.loads(result)
        intent = result.get("intent")
        if intent not in ("new_plan", "continue_clarify", "faq_about_itinerary", "chitchat"):
            raise ValueError(f"LLM 返回了未知意图: {intent!r}")
    except Exception as exc:
        # 降级到启发式规则，保证流程不中断
        if needs_clarification:
            intent = "continue_clarify"
        elif has_existing_itinerary and any(kw in user_input for kw in ("吗", "呢", "怎么", "如何", "为什么", "？", "?")):
            intent = "faq_about_itinerary"
        elif any(kw in user_input for kw in ("去", "想去", "规划", "旅游", "旅行", "出游")):
            intent = "new_plan"
        else:
            intent = "chitchat"
        state["risk_alerts"].append(f"意图分类降级为启发式规则: {intent}（原因: {exc}）")

    state["user_intent"] = intent
    state["current_node"] = "intent_router"
    return state


async def qa_responder(state: TravelState) -> TravelState:
    """
    行程问答节点

    用户针对已生成的行程提问（比如"第二天几点出发"），直接基于现有
    itinerary/weather/budget 数据回答，不重新跑完整规划流程。

    Args:
        state: 当前状态

    Returns:
        更新后的状态，答案写入 state["qa_response"] 并追加到 messages
    """
    from agent.tools import answer_itinerary_question

    user_input = state.get("user_input", "")
    itinerary = state.get("itinerary", "") or ""
    weather = state.get("weather") or []
    total_budget = state.get("total_budget_estimate") or {}

    weather_summary = "；".join(
        f"{w.get('date', '')} {w.get('description', '')} "
        f"{w.get('temperature_min', '')}~{w.get('temperature_max', '')}°C"
        for w in weather[:7]
    ) or "暂无天气数据"
    budget_summary = f"预估 {total_budget.get('min', 0)}~{total_budget.get('max', 0)} 元" if total_budget else "暂无预算数据"

    try:
        answer = await answer_itinerary_question.ainvoke({
            "question": user_input,
            "itinerary": itinerary,
            "weather_summary": weather_summary,
            "budget_summary": budget_summary,
        })
    except Exception as exc:
        answer = f"抱歉，暂时无法回答这个问题，请查看上方完整行程。（{exc}）"

    state["qa_response"] = answer
    state["messages"].append({
        "role": "assistant",
        "content": answer,
        "node": "qa_responder",
    })
    state["current_node"] = "qa_responder"
    return state


async def chitchat_responder(state: TravelState) -> TravelState:
    """
    闲聊响应节点

    处理跟旅行规划无关的对话，不触发规划流程。

    Args:
        state: 当前状态

    Returns:
        更新后的状态，回复写入 state["chitchat_response"] 并追加到 messages
    """
    from agent.tools import generate_chitchat_reply

    user_input = state.get("user_input", "")

    try:
        reply = await generate_chitchat_reply.ainvoke({"message": user_input})
    except Exception:
        reply = "很高兴和您聊天。有什么旅行规划需要帮助的吗？"

    state["chitchat_response"] = reply
    state["messages"].append({
        "role": "assistant",
        "content": reply,
        "node": "chitchat_responder",
    })
    state["current_node"] = "chitchat_responder"
    return state


async def preference_collector(state: TravelState) -> TravelState:
    """
    偏好收集节点

    从用户输入中提取旅行偏好，检查是否有缺失的关键字段。
    如果信息完整，推进到约束标准化；否则返回追问。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    from agent.prompts import PREFERENCE_COLLECTION_PROMPT
    from agent.tools import collect_preferences

    user_input = state.get("user_input", "")
    current_pref = state.get("preference") or {}

    # 调用偏好收集工具（现在内部优先走 LLM 提取，失败降级到正则）
    result = await collect_preferences.ainvoke({
        "user_input": user_input,
        "current_preferences": current_pref if isinstance(current_pref, dict) else {},
    })

    # 解析结果
    if isinstance(result, str):
        result = json.loads(result)

    # 更新偏好
    preference_data = result.get("preference", {})
    missing = result.get("missing_critical_fields", [])

    # 构建 TravelPreference
    try:
        pref = TravelPreference(**preference_data)
        state["preference"] = pref.model_dump()
    except Exception:
        state["preference"] = preference_data

    state["missing_fields"] = missing
    state["current_node"] = "preference_collector"

    # 如果有追问问题，设置需要澄清
    follow_up = result.get("follow_up_question")
    if missing and follow_up:
        state["needs_clarification"] = True
        state["messages"].append({
            "role": "assistant",
            "content": follow_up,
            "node": "preference_collector",
        })
    else:
        state["needs_clarification"] = False

    # 记录工具调用
    state["tool_calls"].append({
        "tool_name": "collect_preferences",
        "input": {"user_input": user_input},
        "output": result,
        "timestamp": datetime.now().isoformat(),
    })

    return state


async def constraint_normalizer(state: TravelState) -> TravelState:
    """
    约束标准化节点

    将用户偏好转换为标准化约束，识别隐性约束。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    preference = state.get("preference")
    if not preference:
        state["next_node"] = "preference_collector"
        return state

    # 构建约束
    pref_dict = preference if isinstance(preference, dict) else preference.model_dump()

    # 硬约束
    hard_constraints: dict[str, Any] = {}
    if pref_dict.get("budget_cny"):
        hard_constraints["budget_max"] = pref_dict["budget_cny"]
    if pref_dict.get("accessibility_needs"):
        hard_constraints["accessibility"] = True
    if pref_dict.get("dietary_restrictions"):
        hard_constraints["dietary"] = pref_dict["dietary_restrictions"]

    # 软约束
    soft_constraints: dict[str, Any] = {}
    if pref_dict.get("interests"):
        soft_constraints["interests"] = pref_dict["interests"]
    if pref_dict.get("accommodation_type"):
        soft_constraints["accommodation_type"] = pref_dict["accommodation_type"]
    if pref_dict.get("pace_preference"):
        soft_constraints["pace"] = pref_dict["pace_preference"]
    if pref_dict.get("transportation_preference"):
        soft_constraints["transportation"] = pref_dict["transportation_preference"]

    # 隐性约束推导
    implicit_needs: list[str] = []
    companions = pref_dict.get("companions")
    companions_map = {
        "family": ["儿童友好设施", "安全区域", "家庭餐厅"],
        "solo": ["安全区域", "社交场所", "单人友好设施"],
        "couple": ["浪漫景点", "双人活动", "安静环境"],
        "friends": ["团体活动", "娱乐场所", "灵活安排"],
        "group": ["团体优惠", "统一行动", "交通便利"],
    }
    if companions in companions_map:
        implicit_needs.extend(companions_map[companions])

    if pref_dict.get("accessibility_needs"):
        implicit_needs.extend(["无障碍交通", "无障碍景点", "无障碍餐厅"])

    # 构建约束摘要
    parts: list[str] = []
    if pref_dict.get("destination") and pref_dict.get("duration_days"):
        parts.append(f"{pref_dict['duration_days']}天{pref_dict['destination']}旅行")
    if pref_dict.get("budget_cny"):
        parts.append(f"预算{pref_dict['budget_cny']}元")
    if pref_dict.get("interests"):
        parts.append(f"偏好{','.join(pref_dict['interests'])}")
    if pref_dict.get("pace_preference"):
        parts.append(f"{pref_dict['pace_preference']}节奏")

    constraint_summary = "，".join(parts) if parts else "暂无具体约束"

    constraints = TravelConstraints(
        hard_constraints=hard_constraints,
        soft_constraints=soft_constraints,
        implicit_needs=implicit_needs,
        constraint_summary=constraint_summary,
    )

    state["constraints"] = constraints.model_dump()
    state["current_node"] = "constraint_normalizer"

    return state


async def destination_search(state: TravelState) -> TravelState:
    """
    目的地搜索节点

    1. 地理编码获取目的地坐标
    2. 搜索各类 POI
    3. 去重和格式化

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    from agent.guide_search import search_guide_pois
    from agent.tools import geocode_location, search_places

    preference = state.get("preference") or {}
    pref_dict = preference if isinstance(preference, dict) else {}

    destination = pref_dict.get("destination")
    if not destination:
        state["risk_alerts"].append("未指定目的地，跳过POI搜索")
        state["current_node"] = "destination_search"
        return state

    # Step 1: 地理编码
    try:
        geo_result = await geocode_location.ainvoke({"query": destination})
        if isinstance(geo_result, str):
            geo_result = json.loads(geo_result)
    except Exception as e:
        state["risk_alerts"].append(f"地理编码失败: {str(e)}")
        state["current_node"] = "destination_search"
        return state

    if not geo_result.get("success"):
        state["risk_alerts"].append(f"无法找到目的地'{destination}'的坐标")
        state["current_node"] = "destination_search"
        return state

    lat = geo_result["lat"]
    lon = geo_result["lon"]

    # Step 2: 基于兴趣搜索 POI
    interests = pref_dict.get("interests") or ["interesting_places"]

    # 兴趣到 OpenTripMap kinds 的映射
    kind_mapping: dict[str, list[str]] = {
        "博物馆": ["museums"],
        "历史": ["historic", "cultural"],
        "自然": ["natural", "parks"],
        "美食": ["foods"],
        "购物": ["shops"],
        "宗教": ["religion"],
        "建筑": ["architecture"],
        "公园": ["parks", "natural"],
        "艺术": ["theatres_and_entertainments", "museums"],
        "科技": ["science_museums"],
    }

    all_pois: list[dict] = []
    seen_names: set[str] = set()
    seen_parents: set[str] = set()

    def _parent_key(poi_name: str) -> str:
        """提取"母地点"标识，用于同园区/同景区子点位去重。

        高德等地图服务会把大公园/景区内的长椅、小径、亭子等标记成
        独立 POI（如"人民公园-相亲角"、"人民公园-西山瀑布"），如果只按
        完整名称去重，一个热门大公园的十几个子点位会挤占整个行程，
        把其他真正该出现的知名景点挤掉。这里按常见分隔符取前缀，
        同一母地点只保留第一个命中的子点位。
        """
        for sep in ("-", "·", "（", "(", " "):
            if sep in poi_name:
                prefix = poi_name.split(sep, 1)[0].strip()
                if prefix:
                    return prefix
        return poi_name

    # 总是搜索 interesting_places 作为基础
    def _add_poi(poi: dict) -> bool:
        name = poi.get("name", "")
        if not name or name in seen_names:
            return False
        parent = _parent_key(name)
        if parent in seen_parents:
            return False
        seen_names.add(name)
        seen_parents.add(parent)
        all_pois.append(poi)
        return True

    try:
        duration_days = pref_dict.get("duration_days")
        guide_result = await search_guide_pois(
            city=destination,
            days=int(duration_days) if duration_days else None,
            interests=interests if isinstance(interests, list) else None,
            center_lat=lat,
            center_lon=lon,
        )
        for p in guide_result.get("poi_list") or []:
            if isinstance(p, dict):
                _add_poi(p)
        if guide_result.get("error"):
            state["risk_alerts"].append(str(guide_result["error"]))
        state["tool_calls"].append({
            "tool_name": "guide_search",
            "input": {"destination": destination, "interests": interests},
            "output": {
                "enabled": guide_result.get("enabled"),
                "cached": guide_result.get("cached"),
                "candidate_count": guide_result.get("candidate_count", 0),
                "poi_count": len(guide_result.get("poi_list") or []),
                "error": guide_result.get("error"),
            },
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        state["risk_alerts"].append(f"攻略搜索增强失败: {str(e)}")

    search_kinds = set()
    for interest in interests:
        for kind in kind_mapping.get(interest, ["interesting_places"]):
            search_kinds.add(kind)

    if not search_kinds:
        search_kinds.add("interesting_places")

    for kind in search_kinds:
        try:
            places = await search_places.ainvoke({
                "lat": lat,
                "lon": lon,
                "radius": 10000,
                "kinds": kind,
                "rate": "3",
            })
            if isinstance(places, str):
                places = json.loads(places)

            for p in places or []:
                _add_poi(p)
        except Exception as e:
            state["risk_alerts"].append(f"搜索 {kind} 失败: {str(e)}")
            continue

    # 限制 POI 数量
    state["poi_list"] = all_pois[:20]
    state["current_node"] = "destination_search"

    # 记录工具调用
    state["tool_calls"].append({
        "tool_name": "destination_search",
        "input": {"destination": destination, "interests": interests},
        "output": {"poi_count": len(all_pois)},
        "timestamp": datetime.now().isoformat(),
    })

    return state


async def route_planner(state: TravelState) -> TravelState:
    """
    路线规划节点

    使用贪心最近邻算法对 POI 进行排序，减少回头路。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    from agent.tools import estimate_route

    poi_list = state.get("poi_list", [])
    preference = state.get("preference") or {}
    pref_dict = preference if isinstance(preference, dict) else {}

    if len(poi_list) < 2:
        state["route"] = []
        state["current_node"] = "route_planner"
        return state

    # 获取交通方式
    profile = pref_dict.get("transportation_preference", "driving")
    if profile == "public":
        profile = "driving"
    elif profile not in ["driving", "walking", "cycling"]:
        profile = "driving"

    # 限制POI数量以控制API调用
    pois = poi_list[:10]

    # Step 1: 计算 POI 对之间的距离矩阵
    distance_matrix: dict[tuple[int, int], dict] = {}
    for i in range(len(pois)):
        for j in range(i + 1, len(pois)):
            try:
                coords_i = pois[i].get("coordinates", {})
                coords_j = pois[j].get("coordinates", {})

                route_result = await estimate_route.ainvoke({
                    "start_lat": coords_i.get("lat", 0),
                    "start_lon": coords_i.get("lon", 0),
                    "end_lat": coords_j.get("lat", 0),
                    "end_lon": coords_j.get("lon", 0),
                    "profile": profile,
                })
                if isinstance(route_result, str):
                    route_result = json.loads(route_result)

                distance_matrix[(i, j)] = route_result
            except Exception:
                # 使用直线距离作为兜底
                from agent.tools import _haversine_distance
                ci = pois[i].get("coordinates", {})
                cj = pois[j].get("coordinates", {})
                dist = _haversine_distance(
                    ci.get("lat", 0), ci.get("lon", 0),
                    cj.get("lat", 0), cj.get("lon", 0),
                )
                duration = (dist / 1000 / 30) * 3600 if profile == "driving" else (dist / 1000 / 5) * 3600
                distance_matrix[(i, j)] = {
                    "distance": dist,
                    "duration": duration,
                    "source": "Haversine (Fallback)",
                }

    # Step 2: 贪心最近邻排序
    sorted_indices = _greedy_tsp_sort(len(pois), distance_matrix)

    # Step 3: 构建路线段
    route_segments = []
    for idx in range(len(sorted_indices) - 1):
        i, j = sorted_indices[idx], sorted_indices[idx + 1]
        key = (min(i, j), max(i, j))
        route_data = distance_matrix.get(key, {})

        segment = {
            "from_poi": pois[i].get("name", f"POI_{i}"),
            "to_poi": pois[j].get("name", f"POI_{j}"),
            "distance_meters": route_data.get("distance", 0),
            "duration_seconds": route_data.get("duration", 0),
            "transportation_mode": profile,
            "source": route_data.get("source", "OSRM"),
            # 实际道路坐标点 [[lon, lat], ...]，前端画线用这个而不是两个 POI 直连
            "polyline": route_data.get("polyline") or [],
        }
        route_segments.append(segment)

    state["route"] = route_segments
    state["current_node"] = "route_planner"

    return state


def _greedy_tsp_sort(n: int, distance_matrix: dict[tuple[int, int], dict]) -> list[int]:
    """
    贪心最近邻 TSP 排序

    从第 0 个点开始，每次选择最近的未访问点。

    Args:
        n: 点的数量
        distance_matrix: 距离矩阵 {(i,j): {"distance": float}}

    Returns:
        list[int]: 排序后的索引列表
    """
    if n <= 1:
        return list(range(n))

    unvisited = set(range(1, n))
    tour = [0]

    while unvisited:
        current = tour[-1]
        nearest = min(
            unvisited,
            key=lambda x: distance_matrix.get(
                (min(current, x), max(current, x)), {"distance": float("inf")}
            ).get("distance", float("inf")),
        )
        tour.append(nearest)
        unvisited.remove(nearest)

    return tour


async def weather_advisor(state: TravelState) -> TravelState:
    """
    天气顾问节点

    查询目的地天气预报，标记雨天备选方案。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    from agent.tools import get_weather

    poi_list = state.get("poi_list", [])

    if not poi_list:
        state["weather"] = []
        state["current_node"] = "weather_advisor"
        return state

    # 使用目的地中心坐标
    center_lat = sum(p.get("coordinates", {}).get("lat", 0) for p in poi_list) / len(poi_list)
    center_lon = sum(p.get("coordinates", {}).get("lon", 0) for p in poi_list) / len(poi_list)

    preference = state.get("preference") or {}
    pref_dict = preference if isinstance(preference, dict) else {}
    duration = pref_dict.get("duration_days", 7)

    try:
        weather_data = await get_weather.ainvoke({
            "lat": center_lat,
            "lon": center_lon,
            "days": min(duration, 14),
        })
        if isinstance(weather_data, str):
            weather_data = json.loads(weather_data)
    except Exception as e:
        state["risk_alerts"].append(f"天气查询失败: {str(e)}")
        state["weather"] = []
        state["current_node"] = "weather_advisor"
        return state

    weather_daily = weather_data.get("daily", [])
    weather_source = weather_data.get("source")
    # get_weather 返回的 source 在外层；行程来源汇总按 daily item 收集，
    # 所以这里把来源补到每条天气记录上，避免正文有天气但来源说明显示“暂无数据”。
    if weather_source and isinstance(weather_daily, list):
        for item in weather_daily:
            if isinstance(item, dict) and not item.get("source"):
                item["source"] = weather_source
    state["weather"] = weather_daily

    # 如果有高降雨概率，添加风险提醒
    rainy_days = [
        w for w in state["weather"]
        if w.get("precipitation_probability", 0) > 50
    ]
    if rainy_days:
        for w in rainy_days:
            state["risk_alerts"].append(
                f"{w['date']} 降雨概率{w['precipitation_probability']}%，建议准备室内备选方案"
            )

    state["current_node"] = "weather_advisor"
    return state


async def budget_estimator(state: TravelState) -> TravelState:
    """
    预算估算节点

    基于行程内容估算各项费用，使用区间估算。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    from agent.tools import estimate_budget

    preference = state.get("preference") or {}
    pref_dict = preference if isinstance(preference, dict) else {}

    destination = pref_dict.get("destination", "")
    duration = pref_dict.get("duration_days", 2)
    travelers = 1
    companions = pref_dict.get("companions", "solo")
    if companions == "couple":
        travelers = 2
    elif companions in ["family", "friends", "group"]:
        travelers = 3

    style = pref_dict.get("accommodation_type", "moderate")
    style_map = {"hostel": "budget", "hotel": "moderate", "resort": "luxury", "homestay": "moderate"}
    mapped_style = style_map.get(style, "moderate")

    try:
        budget_result = estimate_budget.invoke({
            "destination": destination,
            "duration_days": duration,
            "travelers": travelers,
            "style": mapped_style,
        })
        if isinstance(budget_result, str):
            budget_result = json.loads(budget_result)
    except Exception as e:
        state["risk_alerts"].append(f"预算估算失败: {str(e)}")
        state["current_node"] = "budget_estimator"
        return state

    state["budget"] = budget_result.get("breakdown", [])
    state["total_budget_estimate"] = {
        "min": budget_result.get("total_min", 0),
        "max": budget_result.get("total_max", 0),
    }

    # 如果超出预算，添加警告
    user_budget = pref_dict.get("budget_cny")
    if user_budget and budget_result.get("total_max", 0) > user_budget:
        state["risk_alerts"].append(
            f"预估总费用 {budget_result['total_min']}-{budget_result['total_max']} 元 "
            f"可能超出预算 {user_budget} 元，建议调整住宿标准或减少景点数量"
        )

    state["current_node"] = "budget_estimator"

    # 记录工具调用
    state["tool_calls"].append({
        "tool_name": "estimate_budget",
        "input": {"destination": destination, "duration_days": duration},
        "output": budget_result,
        "timestamp": datetime.now().isoformat(),
    })

    return state


async def itinerary_synthesizer(state: TravelState) -> TravelState:
    """
    行程合成节点

    编排每日时间表，生成带解释的 Markdown 行程。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    preference = state.get("preference") or {}
    pref_dict = preference if isinstance(preference, dict) else {}

    poi_list = state.get("poi_list", [])
    route = state.get("route", [])
    weather = state.get("weather", [])
    budget = state.get("budget", {})
    total_budget = state.get("total_budget_estimate", {})
    constraints = state.get("constraints", {})

    destination = pref_dict.get("destination", "目的地")
    duration = pref_dict.get("duration_days", 3)
    companions = pref_dict.get("companions", "")
    companions_text = {
        "solo": "个人", "couple": "情侣", "family": "家庭",
        "friends": "朋友", "group": "团队",
    }.get(companions, "")

    # POI/工具内部分类值 -> 中文展示文案，避免把 interesting_places 这类
    # 英文原始标识直接暴露给用户
    category_label_map = {
        "interesting_places": "热门景点",
        "museums": "博物馆",
        "historic": "历史古迹",
        "cultural": "文化景点",
        "natural": "自然风光",
        "parks": "公园",
        "foods": "美食",
        "shops": "购物",
        "religion": "宗教场所",
        "architecture": "建筑",
        "theatres_and_entertainments": "娱乐场所",
        "science_museums": "科技馆",
    }

    def _category_label(raw: str) -> str:
        return category_label_map.get(raw, raw if raw else "热门景点")

    # 构建行程 Markdown
    lines = [
        f"# {destination} {duration}天{companions_text}旅行计划",
        "",
        "## 约束摘要",
        constraints.get("constraint_summary", "暂无约束摘要"),
        "",
    ]

    # 每日安排（先算出每天的数据，用于填充行程总览表格和详细计划两处）
    pois_per_day = max(2, min(4, len(poi_list) // duration if duration > 0 else 3))
    time_slots = [("09:00", "11:00"), ("11:30", "13:00"), ("14:00", "16:00"), ("16:30", "17:30"), ("18:00", "19:30")]

    day_summaries: list[dict[str, str]] = []
    daily_sections: list[str] = []

    for day in range(1, duration + 1):
        day_weather = weather[day - 1] if day - 1 < len(weather) else None
        date_str = day_weather["date"] if day_weather else f"Day {day}"
        weather_desc = day_weather["description"] if day_weather else "未知"
        temp_range = f"{day_weather['temperature_min']:.0f}~{day_weather['temperature_max']:.0f}°C" if day_weather else ""

        # 选择当天的 POI
        start_idx = (day - 1) * pois_per_day
        end_idx = min(start_idx + pois_per_day, len(poi_list))
        day_pois = poi_list[start_idx:end_idx]

        # 主题
        themes = [_category_label(p.get("category", "")) for p in day_pois[:2]]
        theme = "/".join(dict.fromkeys(themes)) if themes else "自由探索"

        section_lines = [
            f"### Day {day}（{date_str}）",
            f"**主题**: {theme}",
            f"**天气**: {weather_desc} {temp_range}",
            "",
        ]

        # 时间安排：先排定景点时段，用餐固定插在对应时段之间，
        # 避免用餐时段与景点时段重叠。
        visit_slots = [time_slots[0], time_slots[2], time_slots[3]]  # 上午/下午两段/傍晚
        activities: list[str] = []
        poi_names_for_summary: list[str] = []

        for i, poi in enumerate(day_pois[:len(visit_slots)]):
            start, end = visit_slots[i]
            poi_name = poi.get("name", "景点")
            poi_names_for_summary.append(poi_name)
            activities.append(f"- {start}-{end}: **{poi_name}** - [推荐: {_category_label(poi.get('category', ''))}]")

        # 按时间顺序插入用餐（不与景点时段重叠）
        if activities:
            activities.insert(1 if len(activities) > 1 else len(activities), "- 12:00-13:30: **午餐** - [品尝当地美食]")
        # pois_per_day 上限为 4、visit_slots 只占 3 段，最多还剩 1 个 POI，
        # 安排在傍晚时段（不与其他时段重叠）
        extra_pois = day_pois[len(visit_slots):]
        for extra_poi in extra_pois:
            extra_name = extra_poi.get("name", "景点")
            poi_names_for_summary.append(extra_name)
            activities.append(f"- 16:30-17:30: **{extra_name}** - [推荐: {_category_label(extra_poi.get('category', ''))}]")
        activities.append("- 19:00-20:00: **晚餐** - [推荐当地特色餐厅]")

        if not day_pois:
            activities = ["- 自由安排时间，建议探索当地特色街区和美食"]
            poi_names_for_summary = []

        section_lines.extend(activities)
        section_lines.append("")
        daily_sections.append("\n".join(section_lines))

        day_summaries.append({
            "date": date_str,
            "theme": theme,
            "activities": "、".join(poi_names_for_summary) if poi_names_for_summary else "自由探索",
        })

    # 行程总览（用上面算好的 day_summaries 填充表格，而不是留空表头）
    lines.extend([
        "## 行程总览",
        "| 日期 | 主题 | 主要活动 |",
        "|:-----|:-----|:---------|",
    ])
    for summary in day_summaries:
        lines.append(f"| {summary['date']} | {summary['theme']} | {summary['activities']} |")
    lines.append("")

    # 每日详细计划
    lines.append("## 每日详细计划")
    lines.append("")
    for section in daily_sections:
        lines.append(section)

    # 预算拆分
    lines.extend([
        "## 预算拆分",
        "",
        "| 类别 | 估算区间（元） | 备注 |",
        "|:-----|:---------------|:-----|",
    ])

    budget_items = budget if isinstance(budget, list) else []
    for item in budget_items:
        cat_name = item.get("name_cn", item.get("category", ""))
        min_val = item.get("estimated_min", 0)
        max_val = item.get("estimated_max", 0)
        notes = item.get("notes", "")
        lines.append(f"| {cat_name} | {min_val:.0f} ~ {max_val:.0f} | {notes} |")

    total_min = total_budget.get("min", 0)
    total_max = total_budget.get("max", 0)
    lines.append(f"| **合计** | **{total_min:.0f} ~ {total_max:.0f}** | |")
    lines.append("")

    # 数据来源说明：按各字段实际返回的 source 动态生成，而不是写死一套
    # OpenTripMap/OSRM/Open-Meteo（那套只是降级兜底方案，实际大多数请求
    # 会先走高德 MCP，写死会导致声明和真实数据来源不一致）。
    def _collect_sources(items: list[dict], key: str = "source") -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            src = item.get(key) if isinstance(item, dict) else None
            if src and src not in seen:
                seen.add(src)
                ordered.append(src)
        return ordered

    poi_sources = _collect_sources(poi_list if isinstance(poi_list, list) else [])
    weather_sources = _collect_sources(weather if isinstance(weather, list) else [])
    route_sources = _collect_sources(route if isinstance(route, list) else [])
    budget_sources = _collect_sources(budget_items)

    lines.extend([
        "## 数据来源说明",
        "",
        f"- 景点信息: {', '.join(poi_sources) if poi_sources else '暂无数据'}",
        f"- 路线规划: {', '.join(route_sources) if route_sources else '暂无数据'}",
        f"- 天气预报: {', '.join(weather_sources) if weather_sources else '暂无数据'}",
        f"- 预算估算: {', '.join(budget_sources) if budget_sources else '基于历史数据和规则估算'}",
        "",
    ])

    # 风险与备选方案
    lines.extend([
        "## 风险与备选方案",
        "",
        "- 景点营业时间和价格可能变动，请出发前再次确认",
        "- 天气预报准确率随预报时长降低，建议出发前查看最新预报",
        "- 预算为估算区间，实际费用因季节、个人消费习惯等因素可能有所不同",
        "",
    ])

    # 安全声明
    lines.extend([
        "## 需要用户确认的事项",
        "",
        "> **安全声明**: 本系统仅提供旅行建议，不执行任何预订或付款操作。如需预订，请前往官方平台操作。",
        "",
        "- [ ] 请确认行程安排是否符合您的预期",
        "- [ ] 请核实景点当前的开放状态和门票价格",
        "- [ ] 如需预订酒店/机票，请通过官方渠道操作",
        "",
    ])

    itinerary_md = "\n".join(lines)
    state["itinerary"] = itinerary_md
    state["current_node"] = "itinerary_synthesizer"

    # 添加助手消息（完整行程，不做截断——这条会被存进会话历史，
    # 之后切换/重新打开会话时前端从这里恢复展示内容，截断会导致
    # 历史记录里的行程显示不全，看起来像是"输出被截断了"）
    state["messages"].append({
        "role": "assistant",
        "content": itinerary_md,
        "node": "itinerary_synthesizer",
    })

    return state


async def safety_reviewer(state: TravelState) -> TravelState:
    """
    安全审查节点

    扫描输出中的高风险操作，标记需要人工确认的事项。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    from config import settings

    itinerary = state.get("itinerary", "")
    confirmation_items = []

    # 扫描高风险关键词
    high_risk_keywords = settings.high_risk_keywords
    found_keywords = []

    for keyword in high_risk_keywords:
        if keyword in itinerary:
            idx = itinerary.find(keyword)
            start = max(0, idx - 30)
            end = min(len(itinerary), idx + 30)
            context = itinerary[start:end]
            found_keywords.append(keyword)
            confirmation_items.append({
                "type": "high_risk_action",
                "keyword": keyword,
                "context": context,
                "message": f"检测到'{keyword}'相关操作，需要您人工确认",
                "risk_level": "HIGH",
                "requires_confirmation": True,
            })

    # 始终添加标准安全声明
    confirmation_items.append({
        "type": "safety_disclaimer",
        "message": "本系统仅提供旅行建议，不执行任何预订或付款操作。如需预订，请前往官方平台操作。",
        "risk_level": "LOW",
        "requires_confirmation": False,
    })

    state["confirmation_required"] = confirmation_items
    state["safety_approved"] = len(found_keywords) == 0
    state["current_node"] = "safety_reviewer"

    return state


async def output_formatter(state: TravelState) -> TravelState:
    """
    输出格式化节点

    组合最终输出，追加约束满足情况说明。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    itinerary = state.get("itinerary", "")
    confirmations = state.get("confirmation_required", [])
    risks = state.get("risk_alerts", [])

    # 组装确认事项
    lines = [itinerary]

    # 风险提醒
    if risks:
        lines.extend(["", "## 系统提醒", ""])
        for risk in risks:
            lines.append(f"-  {risk}")

    # 组装最终输出
    final_output = "\n".join(lines)
    state["itinerary"] = final_output
    state["messages"].append({
        "role": "assistant",
        "content": final_output[:1000] + "..." if len(final_output) > 1000 else final_output,
        "node": "output_formatter",
    })
    state["current_node"] = "output_formatter"

    return state


# ==================== 条件边路由函数 ====================

def should_clarify(state: TravelState) -> str:
    """
    判断是否需要澄清

    如果缺失关键字段，返回 "clarify" 终止流程等待用户输入；
    否则返回 "proceed" 继续执行。

    Args:
        state: 当前状态

    Returns:
        "clarify" 或 "proceed"
    """
    if state.get("needs_clarification") or state.get("missing_fields"):
        return "clarify"
    return "proceed"


def should_continue(state: TravelState) -> str:
    """
    判断是否应该继续执行

    检查迭代计数器，防止无限循环。

    Args:
        state: 当前状态

    Returns:
        "continue" 或 "end"
    """
    from config import settings

    if state.get("iteration_count", 0) > settings.max_iteration_count:
        state["risk_alerts"].append("达到最大迭代次数限制，流程终止")
        return "end"
    return "continue"


def safety_check(state: TravelState) -> str:
    """
    安全检查后的路由

    无论是否通过安全审查，都继续到输出格式化。
    安全审查的结果会体现在输出中。

    Args:
        state: 当前状态

    Returns:
        "format"
    """
    return "format"


# ==================== 构建图 ====================

def build_travel_graph(checkpointer: Any = None) -> Any:
    """
    构建 LangGraph 旅行规划状态机

    定义完整的节点和边关系，包括条件分支。入口是 intent_router，
    根据意图分类结果路由到四条分支：新规划/继续澄清/行程问答/闲聊。

    Args:
        checkpointer: LangGraph checkpointer 实例（如 AsyncPostgresSaver），
            传入后图执行状态会持久化，支持断点续传。不传则不启用持久化
            （比如单测场景）。

    Returns:
        编译后的状态图（CompiledStateGraph）
    """
    # 初始化图
    workflow = StateGraph(TravelState)

    # 注册所有节点
    workflow.add_node("intent_router", intent_router)
    workflow.add_node("qa_responder", qa_responder)
    workflow.add_node("chitchat_responder", chitchat_responder)
    workflow.add_node("preference_collector", preference_collector)
    workflow.add_node("constraint_normalizer", constraint_normalizer)
    workflow.add_node("destination_search", destination_search)
    workflow.add_node("route_planner", route_planner)
    workflow.add_node("weather_advisor", weather_advisor)
    workflow.add_node("budget_estimator", budget_estimator)
    workflow.add_node("itinerary_synthesizer", itinerary_synthesizer)
    workflow.add_node("safety_reviewer", safety_reviewer)
    workflow.add_node("output_formatter", output_formatter)

    # 设置入口点：先经过意图路由
    workflow.set_entry_point("intent_router")

    # intent_router -> 按意图分流
    workflow.add_conditional_edges(
        "intent_router",
        lambda state: state.get("user_intent") or "new_plan",
        {
            "new_plan": "preference_collector",
            "continue_clarify": "preference_collector",
            "faq_about_itinerary": "qa_responder",
            "chitchat": "chitchat_responder",
        },
    )

    # preference_collector -> 条件分支（原有逻辑不变）
    workflow.add_conditional_edges(
        "preference_collector",
        should_clarify,
        {
            "clarify": END,  # 返回追问，等待用户回复
            "proceed": "constraint_normalizer",
        },
    )

    # 线性流程边
    workflow.add_edge("constraint_normalizer", "destination_search")
    workflow.add_edge("destination_search", "route_planner")
    workflow.add_edge("route_planner", "weather_advisor")
    workflow.add_edge("weather_advisor", "budget_estimator")
    workflow.add_edge("budget_estimator", "itinerary_synthesizer")
    workflow.add_edge("itinerary_synthesizer", "safety_reviewer")

    # safety_reviewer -> 条件分支
    workflow.add_conditional_edges(
        "safety_reviewer",
        safety_check,
        {"format": "output_formatter"},
    )

    # 输出格式化 / 行程问答 / 闲聊 -> 结束
    workflow.add_edge("output_formatter", END)
    workflow.add_edge("qa_responder", END)
    workflow.add_edge("chitchat_responder", END)

    return workflow.compile(checkpointer=checkpointer)
