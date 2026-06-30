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
from typing import Annotated, Any, Literal

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

class TravelState(dict):
    """
    LangGraph TravelState - 核心状态定义

    使用 dict 子类实现，兼容 LangGraph 的 StateGraph 要求。
    包含完整的旅行规划过程中的所有状态字段。

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
    """

    @classmethod
    def create(
        cls,
        session_id: str,
        user_input: str = "",
        messages: list | None = None,
    ) -> "TravelState":
        """
        创建新的初始状态

        Args:
            session_id: 会话 ID
            user_input: 用户初始输入
            messages: 初始对话历史

        Returns:
            TravelState: 初始状态实例
        """
        return cls({
            "messages": messages or [],
            "user_input": user_input,
            "preference": None,
            "constraints": None,
            "missing_fields": [],
            "poi_list": [],
            "route": [],
            "weather": [],
            "budget": None,
            "total_budget_estimate": None,
            "current_node": "START",
            "next_node": None,
            "iteration_count": 0,
            "itinerary": "",
            "confirmation_required": [],
            "risk_alerts": [],
            "session_id": session_id,
            "trace_id": None,
            "tool_calls": [],
            "needs_clarification": False,
            "safety_approved": False,
        })


# ==================== 节点函数 ====================

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

    # 调用偏好收集工具
    result = collect_preferences.invoke({
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

    # 总是搜索 interesting_places 作为基础
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
                name = p.get("name", "")
                if name and name not in seen_names:
                    seen_names.add(name)
                    all_pois.append(p)
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

    state["weather"] = weather_data.get("daily", [])

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

    # 构建行程 Markdown
    lines = [
        f"# {destination} {duration}天{companions_text}旅行计划",
        "",
        "## 约束摘要",
        constraints.get("constraint_summary", "暂无约束摘要"),
        "",
    ]

    # 行程总览
    lines.extend([
        "## 行程总览",
        "| 日期 | 主题 | 主要活动 |",
        "|:-----|:-----|:---------|",
    ])

    # 每日安排
    lines.extend(["", "## 每日详细计划", ""])

    # 将 POI 分配到每一天
    pois_per_day = max(2, min(4, len(poi_list) // duration if duration > 0 else 3))

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
        themes = [p.get("category", "景点") for p in day_pois[:2]]
        theme = "/".join(set(themes)) if themes else "自由探索"

        lines.append(f"### Day {day}（{date_str}）")
        lines.append(f"**主题**: {theme}")
        lines.append(f"**天气**: {weather_desc} {temp_range}")
        lines.append("")

        # 时间安排
        time_slots = [("09:00", "11:00"), ("11:30", "12:30"), ("14:00", "16:00"), ("16:30", "17:30"), ("18:00", "19:30")]
        activities = []

        for i, poi in enumerate(day_pois):
            if i < len(time_slots):
                start, end = time_slots[i]
                activities.append(f"- {start}-{end}: **{poi.get('name', '景点')}** - [推荐原因: {poi.get('category', '热门景点')}]")

        # 添加用餐
        if len(activities) >= 2:
            activities.insert(1, f"- 12:00-13:00: **午餐** - [品尝当地美食]")
        if len(activities) >= 4:
            activities.append(f"- 19:30-20:30: **晚餐** - [推荐当地特色餐厅]")

        if not activities:
            activities.append("- 自由安排时间，建议探索当地特色街区和美食")

        lines.extend(activities)
        lines.append("")

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

    # 数据来源说明
    lines.extend([
        "## 数据来源说明",
        "",
        "- 景点信息: OpenTripMap API",
        "- 坐标数据: Nominatim (OpenStreetMap)",
        "- 路线规划: OSRM (Open Source Routing Machine)",
        "- 天气预报: Open-Meteo",
        "- 预算估算: 基于历史数据和规则估算",
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

    # 添加助手消息
    state["messages"].append({
        "role": "assistant",
        "content": f"行程规划完成！\n\n{itinerary_md[:500]}...",
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

def build_travel_graph() -> StateGraph:
    """
    构建 LangGraph 旅行规划状态机

    定义完整的节点和边关系，包括条件分支。

    Returns:
        StateGraph: 编译后的状态图
    """
    # 初始化图
    workflow = StateGraph(TravelState)

    # 注册所有节点
    workflow.add_node("preference_collector", preference_collector)
    workflow.add_node("constraint_normalizer", constraint_normalizer)
    workflow.add_node("destination_search", destination_search)
    workflow.add_node("route_planner", route_planner)
    workflow.add_node("weather_advisor", weather_advisor)
    workflow.add_node("budget_estimator", budget_estimator)
    workflow.add_node("itinerary_synthesizer", itinerary_synthesizer)
    workflow.add_node("safety_reviewer", safety_reviewer)
    workflow.add_node("output_formatter", output_formatter)

    # 设置入口点
    workflow.set_entry_point("preference_collector")

    # preference_collector -> 条件分支
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

    # 输出格式化 -> 结束
    workflow.add_edge("output_formatter", END)

    return workflow.compile()


# 全局图实例（单例）
travel_graph = build_travel_graph()
