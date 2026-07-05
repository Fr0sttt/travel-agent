"""
Travel Agent 核心工具模块

包含 7 个核心工具的完整实现，地点、地理编码、路线、天气优先走高德 MCP，
其余能力继续保留本地规则与公开数据源兜底：
1. collect_preferences - 提取和更新用户偏好
2. search_places - OpenTripMap POI 搜索
3. geocode_location - Nominatim 地理编码
4. estimate_route - OSRM 路线规划
5. get_weather - Open-Meteo 天气查询
6. estimate_budget - 预算估算（静态规则）
7. request_confirmation - 高风险动作确认请求

每个工具都包含：
- 详细的 docstring（Agent 通过它理解工具）
- 健壮的错误处理和重试逻辑
- 结果格式化和不确定性标注
- Langfuse trace 集成
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Literal, Optional

import httpx
from langchain_core.tools import tool

from config import settings
from agent.mcp_bridge import maybe_call_mcp_tool


# ==================== 工具调用追踪装饰器 ====================

def trace_tool_call(tool_name: str):
    """
    工具调用追踪装饰器

    自动记录工具调用的输入、输出、耗时和状态。
    如果 Langfuse 未启用或不可用，静默跳过追踪。

    Args:
        tool_name: 工具名称，用于追踪标识
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            result: dict[str, Any] = {"tool_name": tool_name, "success": False}

            try:
                # 执行工具函数
                output = await func(*args, **kwargs)
                result["success"] = True
                result["output"] = output
                return output

            except Exception as e:
                result["error"] = str(e)
                result["error_type"] = type(e).__name__
                raise

            finally:
                # 记录追踪信息
                latency_ms = (time.time() - start_time) * 1000
                result["latency_ms"] = round(latency_ms, 2)
                result["timestamp"] = datetime.now().isoformat()
                result["input"] = kwargs

                # 尝试发送 Langfuse 追踪（如果启用）
                if settings.langfuse_enabled:
                    try:
                        from observability.langfuse_client import get_langfuse
                        langfuse = get_langfuse()
                        langfuse.log_tool_call(
                            tool_name=tool_name,
                            tool_input=kwargs,
                            tool_output=result,
                            latency_ms=latency_ms,
                        )
                    except Exception:
                        # Langfuse 追踪失败不应影响主流程
                        pass

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            result: dict[str, Any] = {"tool_name": tool_name, "success": False}

            try:
                output = func(*args, **kwargs)
                result["success"] = True
                result["output"] = output
                return output

            except Exception as e:
                result["error"] = str(e)
                result["error_type"] = type(e).__name__
                raise

            finally:
                latency_ms = (time.time() - start_time) * 1000
                result["latency_ms"] = round(latency_ms, 2)
                result["timestamp"] = datetime.now().isoformat()
                result["input"] = kwargs

                if settings.langfuse_enabled:
                    try:
                        from observability.langfuse_client import get_langfuse
                        langfuse = get_langfuse()
                        langfuse.log_tool_call(
                            tool_name=tool_name,
                            tool_input=kwargs,
                            tool_output=result,
                            latency_ms=latency_ms,
                        )
                    except Exception:
                        pass

        # 根据函数类型返回对应的 wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ==================== HTTP 请求辅助函数 ====================

async def _async_http_get(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    max_retries: int = 3,
) -> dict[str, Any]:
    """
    带重试的异步 HTTP GET 请求

    Args:
        url: 请求 URL
        params: URL 查询参数
        headers: 请求头
        timeout: 超时时间（秒）
        max_retries: 最大重试次数

    Returns:
        解析后的 JSON 响应

    Raises:
        httpx.HTTPError: 请求失败且重试耗尽
    """
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()

        except (httpx.HTTPError, httpx.TimeoutException) as e:
            last_error = e
            if attempt < max_retries:
                wait = 2 ** attempt  # 指数退避
                await asyncio.sleep(wait)
            continue

    raise last_error or httpx.HTTPError(f"请求失败: {url}")


def _sync_http_get(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    max_retries: int = 3,
) -> dict[str, Any]:
    """
    带重试的同步 HTTP GET 请求

    用于同步工具函数（如预算估算等不需要外部 API 的工具）。
    """
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()

        except (httpx.HTTPError, httpx.TimeoutException) as e:
            last_error = e
            if attempt < max_retries:
                wait = 2 ** attempt
                time.sleep(wait)
            continue

    raise last_error or httpx.HTTPError(f"请求失败: {url}")


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _mcp_list_payload(payload: Any) -> list[Any] | None:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("results", "places", "pois", "items", "data", "daily"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = _mcp_list_payload(value)
                if nested is not None:
                    return nested
    return None


def _mcp_dict_payload(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                return item
    return None


def _normalize_mcp_pois(payload: Any, lat: float, lon: float, kinds: str, tool_name: str) -> list[dict[str, Any]] | None:
    items = _mcp_list_payload(payload)
    if items is None and isinstance(payload, dict) and any(
        key in payload for key in ("name", "coordinates", "lat", "lon")
    ):
        items = [payload]

    if items is None:
        return None

    results: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        coordinates = item.get("coordinates") if isinstance(item.get("coordinates"), dict) else {}
        poi = {
            "name": str(item.get("name") or item.get("title") or item.get("poi_name") or "").strip(),
            "category": item.get("category") or item.get("type") or item.get("kind") or kinds,
            "coordinates": {
                "lat": _coerce_float(item.get("lat") or coordinates.get("lat")) or lat,
                "lon": _coerce_float(item.get("lon") or coordinates.get("lon")) or lon,
            },
            "rating": _coerce_float(item.get("rating") or item.get("rate")),
            "description": item.get("description") or item.get("summary") or item.get("address") or item.get("note"),
            "source": item.get("source") or f"MCP:{tool_name}",
            "uncertainty_flags": item.get("uncertainty_flags") or ["MCP 数据源返回"],
        }
        if poi["name"]:
            results.append(poi)

    return results


def _normalize_mcp_geocode(payload: Any, query: str, tool_name: str) -> dict[str, Any] | None:
    data = _mcp_dict_payload(payload)
    if data is None:
        return None

    coordinates = data.get("coordinates") if isinstance(data.get("coordinates"), dict) else {}
    lat = _coerce_float(data.get("lat") or coordinates.get("lat"))
    lon = _coerce_float(data.get("lon") or coordinates.get("lon"))
    if lat is None or lon is None:
        return None

    return {
        "lat": lat,
        "lon": lon,
        "display_name": data.get("display_name") or data.get("name") or query,
        "source": data.get("source") or f"MCP:{tool_name}",
        "uncertainty": data.get("uncertainty") or "MCP 地理编码结果",
        "success": bool(data.get("success", True)),
    }


def _normalize_mcp_route(
    payload: Any,
    profile: str,
    tool_name: str,
) -> dict[str, Any] | None:
    data = _mcp_dict_payload(payload)
    if data is None:
        return None

    distance = _coerce_float(
        data.get("distance")
        or data.get("distance_meters")
        or data.get("distance_meter")
        or data.get("distance_m")
    )
    duration = _coerce_float(
        data.get("duration")
        or data.get("duration_seconds")
        or data.get("duration_sec")
        or data.get("duration_s")
    )
    if distance is None or duration is None:
        return None

    route_profile = data.get("profile") or data.get("transportation_mode") or profile
    return {
        "distance": round(distance, 2),
        "duration": round(duration, 2),
        "distance_km": round(distance / 1000, 2),
        "duration_minutes": round(duration / 60, 1),
        "profile": route_profile,
        "source": data.get("source") or f"MCP:{tool_name}",
        "uncertainty": data.get("uncertainty") or "MCP 路线结果",
    }


def _normalize_mcp_weather(payload: Any, tool_name: str) -> dict[str, Any] | None:
    if isinstance(payload, list):
        data = {"daily": payload}
    else:
        data = _mcp_dict_payload(payload)
    if data is None:
        return None

    WEATHER_CODES = {
        0: "晴朗", 1: "大部晴朗", 2: "多云", 3: "阴天",
        45: "雾", 48: "雾凇",
        51: "毛毛雨", 53: "中度毛毛雨", 55: "大毛毛雨",
        61: "小雨", 63: "中雨", 65: "大雨",
        71: "小雪", 73: "中雪", 75: "大雪",
        77: "雪粒", 80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
        85: "小阵雪", 86: "大阵雪",
        95: "雷雨", 96: "雷伴小冰雹", 99: "雷伴大冰雹",
    }

    daily_source = data.get("daily")
    if daily_source is None:
        daily_source = data.get("forecast") or data.get("items") or data.get("data")
    if daily_source is None and any(key in data for key in ("date", "temperature_max", "temperature_min")):
        daily_source = [data]

    if not isinstance(daily_source, list):
        return None

    daily: list[dict[str, Any]] = []
    for item in daily_source:
        if not isinstance(item, dict):
            continue
        code = int(item.get("weather_code", item.get("code", 0)) or 0)
        daily.append({
            "date": item.get("date") or item.get("day") or item.get("time"),
            "temperature_max": _coerce_float(item.get("temperature_max") or item.get("temperature_2m_max") or item.get("max_temp")),
            "temperature_min": _coerce_float(item.get("temperature_min") or item.get("temperature_2m_min") or item.get("min_temp")),
            "precipitation_probability": _coerce_float(
                item.get("precipitation_probability")
                or item.get("precipitation_probability_max")
                or item.get("rain_probability")
            )
            or 0,
            "weather_code": code,
            "description": item.get("description") or WEATHER_CODES.get(code, "未知"),
        })

    return {
        "daily": daily,
        "source": data.get("source") or f"MCP:{tool_name}",
        "uncertainty": data.get("uncertainty") or "MCP 天气结果",
    }


AMAP_KIND_KEYWORDS = {
    "interesting_places": "景点",
    "museums": "博物馆",
    "historic": "古迹",
    "natural": "景点",
    "foods": "美食",
    "shops": "购物",
    "religion": "寺庙",
    "architecture": "建筑",
    "parks": "公园",
}


def _amap_keyword_for_kinds(kinds: str) -> str:
    return AMAP_KIND_KEYWORDS.get(kinds, kinds.replace("_", " ").strip())


def _parse_amap_location(location: Any) -> tuple[float | None, float | None]:
    if isinstance(location, dict):
        lon = _coerce_float(location.get("lng") or location.get("lon") or location.get("longitude"))
        lat = _coerce_float(location.get("lat") or location.get("latitude"))
        return lat, lon

    if not isinstance(location, str):
        return None, None

    text = location.strip()
    if not text or "," not in text:
        return None, None

    lon_text, lat_text = [piece.strip() for piece in text.split(",", 1)]
    lon = _coerce_float(lon_text)
    lat = _coerce_float(lat_text)
    return lat, lon


def _amap_first_record(payload: Any) -> dict[str, Any] | None:
    data = _mcp_dict_payload(payload)
    if data is None:
        return None

    records = data.get("return")
    if isinstance(records, list) and records and isinstance(records[0], dict):
        return records[0]
    if isinstance(records, dict):
        return records

    for key in ("geocodes", "pois", "casts", "forecast", "data"):
        value = data.get(key)
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value[0]
        if isinstance(value, dict):
            return value

    return data


def _normalize_amap_geocode(payload: Any, query: str) -> dict[str, Any] | None:
    record = _amap_first_record(payload)
    if record is None:
        return None

    lat, lon = _parse_amap_location(record.get("location"))
    if lat is None or lon is None:
        lat = _coerce_float(record.get("lat"))
        lon = _coerce_float(record.get("lon") or record.get("lng"))
    if lat is None or lon is None:
        return None

    display_name = (
        record.get("formatted_address")
        or record.get("address")
        or record.get("name")
        or query
    )
    return {
        "lat": lat,
        "lon": lon,
        "display_name": display_name,
        "source": "高德地图 MCP",
        "uncertainty": "高德地理编码结果",
        "success": True,
    }


def _normalize_amap_route(payload: Any, profile: str) -> dict[str, Any] | None:
    data = _mcp_dict_payload(payload)
    if data is None:
        return None

    route = data.get("route") if isinstance(data.get("route"), dict) else data
    if route is None:
        return None

    paths = route.get("paths") if isinstance(route.get("paths"), list) else []
    first_path = paths[0] if paths and isinstance(paths[0], dict) else route

    distance = _coerce_float(first_path.get("distance") or route.get("distance"))
    duration = _coerce_float(first_path.get("duration") or route.get("duration"))
    if distance is None or duration is None:
        return None

    steps: list[dict[str, Any]] = []
    polyline_points: list[list[float]] = []
    raw_steps = first_path.get("steps") if isinstance(first_path.get("steps"), list) else []
    for step in raw_steps:
        if not isinstance(step, dict):
            continue
        steps.append(
            {
                "instruction": step.get("instruction"),
                "road": step.get("road"),
                "distance": _coerce_float(step.get("distance")),
                "orientation": step.get("orientation"),
                "duration": _coerce_float(step.get("duration")),
            }
        )
        # 高德每个 step 的 polyline 是 "lon1,lat1;lon2,lat2;..." 格式的实际道路坐标串，
        # 拼接起来才是真实路网路径，而不是 POI 点之间的直线。
        step_polyline = step.get("polyline")
        if isinstance(step_polyline, str) and step_polyline:
            for point in step_polyline.split(";"):
                point = point.strip()
                if not point or "," not in point:
                    continue
                lon_str, lat_str = point.split(",", 1)
                point_lon = _coerce_float(lon_str)
                point_lat = _coerce_float(lat_str)
                if point_lon is not None and point_lat is not None:
                    polyline_points.append([point_lon, point_lat])

    return {
        "distance": round(distance, 2),
        "duration": round(duration, 2),
        "distance_km": round(distance / 1000, 2),
        "duration_minutes": round(duration / 60, 1),
        "profile": route.get("strategy") or route.get("profile") or profile,
        "steps": steps,
        # 实际道路路径坐标点 [[lon, lat], ...]，前端画线应使用这个而非 POI 直连
        "polyline": polyline_points,
        "source": "高德地图 MCP",
        "uncertainty": "高德路线结果",
    }


def _normalize_amap_weather(payload: Any) -> dict[str, Any] | None:
    data = _mcp_dict_payload(payload)
    if data is None:
        return None

    WEATHER_CODES = {
        0: "晴朗", 1: "大部晴朗", 2: "多云", 3: "阴天",
        45: "雾", 48: "雾凇",
        51: "毛毛雨", 53: "中度毛毛雨", 55: "大毛毛雨",
        61: "小雨", 63: "中雨", 65: "大雨",
        71: "小雪", 73: "中雪", 75: "大雪",
        77: "雪粒", 80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
        85: "小阵雪", 86: "大阵雪",
        95: "雷雨", 96: "雷伴小冰雹", 99: "雷伴大冰雹",
    }

    forecasts = data.get("forecasts")
    if not isinstance(forecasts, list):
        forecasts = data.get("casts")
    if not isinstance(forecasts, list):
        forecasts = data.get("daily")
    if not isinstance(forecasts, list):
        return None

    daily: list[dict[str, Any]] = []
    for item in forecasts:
        if not isinstance(item, dict):
            continue
        code = int(item.get("weather_code", item.get("code", 0)) or 0)
        day_weather = item.get("dayweather") or item.get("description")
        night_weather = item.get("nightweather")
        if day_weather and night_weather and night_weather != day_weather:
            description = f"白天{day_weather}，夜间{night_weather}"
        else:
            description = day_weather or night_weather or WEATHER_CODES.get(code, "未知")

        daily.append(
            {
                "date": item.get("date") or item.get("day") or item.get("time"),
                "temperature_max": _coerce_float(
                    item.get("temperature_max")
                    or item.get("daytemp")
                    or item.get("temperature_2m_max")
                    or item.get("max_temp")
                ),
                "temperature_min": _coerce_float(
                    item.get("temperature_min")
                    or item.get("nighttemp")
                    or item.get("temperature_2m_min")
                    or item.get("min_temp")
                ),
                "precipitation_probability": _coerce_float(
                    item.get("precipitation_probability")
                    or item.get("precipitation_probability_max")
                    or item.get("rain_probability")
                )
                or 0,
                "weather_code": code,
                "description": description,
            }
        )

    if not daily:
        return None

    return {
        "daily": daily,
        "source": "高德地图 MCP",
        "uncertainty": "高德天气结果",
    }


async def _enrich_amap_poi_item(item: dict[str, Any], lat: float, lon: float, kinds: str) -> dict[str, Any] | None:
    name = str(item.get("name") or "").strip()
    if not name:
        return None

    poi: dict[str, Any] = {
        "name": name,
        "category": kinds,
        "coordinates": {"lat": lat, "lon": lon},
        "rating": None,
        "description": item.get("address") or item.get("typecode"),
        "source": "高德地图 MCP",
        "uncertainty_flags": ["高德周边搜索结果"],
    }

    parsed_lat, parsed_lon = _parse_amap_location(item.get("location"))
    if parsed_lat is not None and parsed_lon is not None:
        poi["coordinates"] = {"lat": parsed_lat, "lon": parsed_lon}
        poi["uncertainty_flags"] = []
    elif item.get("id"):
        detail_payload = await maybe_call_mcp_tool("maps_search_detail", {"id": str(item["id"])})
        detail = _mcp_dict_payload(detail_payload)
        if detail:
            detail_lat, detail_lon = _parse_amap_location(detail.get("location"))
            if detail_lat is not None and detail_lon is not None:
                poi["coordinates"] = {"lat": detail_lat, "lon": detail_lon}
                poi["uncertainty_flags"] = []
            poi["description"] = detail.get("address") or poi["description"]
            poi["rating"] = _coerce_float(detail.get("rating"))
            poi["source"] = "高德地图 MCP（详情）"

    return poi


async def _normalize_amap_pois(payload: Any, lat: float, lon: float, kinds: str) -> list[dict[str, Any]] | None:
    data = _mcp_dict_payload(payload)
    if data is None:
        return None

    items = data.get("pois")
    if not isinstance(items, list):
        items = _mcp_list_payload(data)
    if not isinstance(items, list):
        return None

    results: list[dict[str, Any]] = []
    for item in items[:15]:
        if not isinstance(item, dict):
            continue
        poi = await _enrich_amap_poi_item(item, lat, lon, kinds)
        if poi is not None:
            results.append(poi)

    return results or None


# ==================== 工具 1: 偏好收集 ====================

@tool
async def collect_preferences(user_input: str, current_preferences: dict | None = None) -> dict:
    """
    从用户对话中提取和结构化旅行偏好信息。

    当用户提供了新的旅行需求时使用此工具。优先用 LLM 从自然语言中提取
    关键字段：目的地、天数、预算、兴趣、同行人等，能处理任意表达方式
    （比如"杭州 10000 3天"这种没有"去/预算/元"等关键词的紧凑表达）。
    LLM 调用失败或超时时，降级到关键词正则提取兜底，保证流程不中断。

    Args:
        user_input: 用户的原始自然语言输入，例如"我想去杭州玩3天，预算3000"
        current_preferences: 当前已收集的偏好字典（如有），用于增量更新

    Returns:
        dict: 包含以下字段的字典
            - preference (dict): 提取的结构化偏好
            - missing_critical_fields (list): 缺失的关键字段
            - follow_up_question (str|None): 追问问题
            - updated (bool): 是否有更新

    Examples:
        >>> await collect_preferences.ainvoke({"user_input": "我想去杭州玩3天，预算3000"})
        {
            "preference": {"destination": "杭州", "duration_days": 3, "budget_cny": 3000},
            "missing_critical_fields": [],
            "follow_up_question": None,
            "updated": True
        }
    """
    if current_preferences is None:
        current_preferences = {}

    llm_result = await _extract_preferences_with_llm(user_input, current_preferences)
    rule_result = _extract_preferences_from_text(user_input)

    # LLM 可能只提取出部分字段，不能因为它成功返回就跳过规则兜底。
    # 这里采用“LLM 优先、规则补缺”的策略，保证目的地/天数/预算这类硬字段尽量完整。
    result: dict[str, Any] = {}
    if isinstance(llm_result, dict):
        result.update({key: value for key, value in llm_result.items() if value not in (None, "", [])})
    for key, value in rule_result.items():
        if value not in (None, "", []) and not result.get(key):
            result[key] = value

    # 合并到现有偏好
    merged = dict(current_preferences)
    for key, value in result.items():
        if value is not None and (key not in merged or merged[key] is None):
            merged[key] = value

    # 判断缺失的关键字段
    critical = ["destination", "duration_days", "budget_cny"]
    missing = [f for f in critical if not merged.get(f)]

    return {
        "preference": merged,
        "missing_critical_fields": missing,
        "follow_up_question": _generate_follow_up_question(missing, merged) if missing else None,
        "updated": bool(result),
    }


async def _extract_preferences_with_llm(
    user_input: str, current_preferences: dict
) -> dict[str, Any] | None:
    """
    用 LLM 做结构化偏好提取，失败返回 None（调用方负责降级到正则）。

    Args:
        user_input: 用户输入
        current_preferences: 当前已收集的偏好（用于增量提取的上下文）

    Returns:
        提取出的偏好字段字典，或 None（表示提取失败）
    """
    from agent.prompts import PREFERENCE_COLLECTION_PROMPT

    try:
        client = _get_async_openai_client()
        from config import settings

        prompt = PREFERENCE_COLLECTION_PROMPT.format(
            current_preferences=json.dumps(current_preferences, ensure_ascii=False),
            user_input=user_input,
        )
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
            timeout=10,
        )
        raw_text = response.choices[0].message.content or ""
        import re
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        json_text = match.group(0) if match else raw_text
        parsed = json.loads(json_text)
        preference = parsed.get("preference")
        if not isinstance(preference, dict):
            return None
        return preference
    except Exception:
        return None


def _extract_preferences_from_text(text: str) -> dict[str, Any]:
    """从文本中提取偏好（简化版关键词提取）"""
    import re
    result: dict[str, Any] = {}

    def parse_number(value: str) -> int | None:
        value = value.strip()
        if value.isdigit():
            return int(value)

        chinese_digits = {
            "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
            "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
        }
        if value in chinese_digits:
            return chinese_digits[value]
        if value == "十":
            return 10
        if "十" in value:
            left, right = value.split("十", 1)
            tens = chinese_digits.get(left, 1) if left else 1
            ones = chinese_digits.get(right, 0) if right else 0
            return tens * 10 + ones
        return None

    def parse_budget(amount: str, unit: str | None = None) -> float:
        value = float(amount.replace(",", ""))
        if unit == "万":
            value *= 10000
        return value

    # 目的地提取 - 匹配"去XX"、"到XX"、"XX旅行"
    dest_patterns = [
        r'(?:想)?(?:去|到|飞往|前往)([\u4e00-\u9fffA-Za-z]{2,12}?)(?:市|县|区|省)?(?=玩|旅行|旅游|度假|攻略|[,，。；;、\s]|$)',
        r'([\u4e00-\u9fffA-Za-z]{2,12})\s*(?:旅行|旅游|度假|攻略)',
    ]
    for pattern in dest_patterns:
        match = re.search(pattern, text)
        if match:
            result["destination"] = match.group(1)
            break

    # 天数提取
    day_match = re.search(r'([0-9]+|[零一二两三四五六七八九十]{1,3})\s*(?:天|日)', text)
    if day_match:
        duration_days = parse_number(day_match.group(1))
        if duration_days is not None:
            result["duration_days"] = duration_days

    # 预算提取
    budget_match = re.search(r'预算(?:大概|约|为)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(万)?', text)
    if budget_match:
        result["budget_cny"] = parse_budget(budget_match.group(1), budget_match.group(2))
    else:
        # 匹配"X块钱"、"X元"
        budget_match2 = re.search(r'([0-9][0-9,]*(?:\.\d+)?)\s*(万)?\s*(?:块钱|块|元|人民币)', text)
        if budget_match2:
            result["budget_cny"] = parse_budget(budget_match2.group(1), budget_match2.group(2))

    # 同行人
    companion_map = {
        "一个人": "solo", "独自": "solo", "单人": "solo",
        "两个人": "couple", "情侣": "couple", "夫妻": "couple", "老婆": "couple", "老公": "couple",
        "带孩子": "family", "带小孩": "family", "亲子": "family", "一家人": "family",
        "朋友": "friends", "闺蜜": "friends", "兄弟": "friends",
        "团队": "group", "公司": "group", "同事": "group",
    }
    for keyword, companion_type in companion_map.items():
        if keyword in text:
            result["companions"] = companion_type
            break

    # 兴趣
    interest_keywords = {
        "博物馆": "博物馆", "历史": "历史", "古迹": "历史",
        "美食": "美食", "吃": "美食", "小吃": "美食",
        "自然": "自然", "风景": "自然", "山水": "自然",
        "购物": "购物", "逛街": "购物", "买东西": "购物",
        "艺术": "艺术", "展览": "艺术",
        "科技": "科技", "科学": "科技",
        "宗教": "宗教", "寺庙": "宗教", "佛教": "宗教",
        "公园": "公园", "休闲": "公园",
        "建筑": "建筑", "拍照": "建筑",
    }
    interests = []
    for keyword, interest in interest_keywords.items():
        if keyword in text and interest not in interests:
            interests.append(interest)
    if interests:
        result["interests"] = interests

    # 节奏偏好
    if "休闲" in text or "轻松" in text or "慢" in text:
        result["pace_preference"] = "relaxed"
    elif "紧凑" in text or "多玩" in text or "赶" in text:
        result["pace_preference"] = "intensive"
    else:
        result["pace_preference"] = "moderate"

    return result


def _generate_follow_up_question(missing: list[str], prefs: dict) -> str:
    """生成追问问题"""
    questions = []
    if "destination" in missing:
        questions.append("您想去哪里旅行呢？")
    if "duration_days" in missing:
        questions.append("计划玩几天？")
    if "budget_cny" in missing:
        questions.append("预算大概是多少？")

    if not questions:
        return "还有其他需要补充的信息吗？"

    return " ".join(questions)


# ==================== 工具 2: POI 搜索（OpenTripMap） ====================

@tool
async def search_places(
    lat: float,
    lon: float,
    radius: int = 5000,
    kinds: str = "interesting_places",
    rate: str = "3",
) -> list[dict[str, Any]]:
    """
    搜索目的地附近的景点、餐厅、咖啡馆等 POI。

    优先通过高德 MCP 的周边搜索获取结果；如果 MCP 不可用，再回退到 OpenTripMap。
    需要先调用 geocode_location 获取目的地的经纬度坐标。

    Args:
        lat: 中心点纬度，范围 -90~90
        lon: 中心点经度，范围 -180~180
        radius: 搜索半径（米），默认 5000 米（5公里）
        kinds: POI 类别，支持:
            - interesting_places: 所有类型（默认）
            - museums: 博物馆
            - historic: 历史古迹
            - natural: 自然景观
            - foods: 餐厅美食
            - shops: 购物
            - religion: 宗教场所
            - architecture: 建筑
            - parks: 公园
        rate: 最低评分 1-7，默认 3（只返回评分 >=3 的景点）

    Returns:
        list[dict]: POI 列表，每个元素包含:
            - name (str): POI 名称
            - category (str): 类别
            - coordinates (dict): 坐标 {"lat": float, "lon": float}
            - rating (float|None): 评分
            - description (str|None): 描述
            - source (str): 数据来源
            - uncertainty_flags (list): 不确定性标注

    Examples:
        >>> await search_places(lat=30.25, lon=120.16, radius=10000, kinds="museums")
        [{"name": "浙江省博物馆", "category": "museums", ...}]
    """
    mcp_payload = await maybe_call_mcp_tool(
        "maps_around_search",
        {
            "location": f"{lon},{lat}",
            "radius": str(radius),
            "keywords": _amap_keyword_for_kinds(kinds),
            # weight: 综合权重排序（人气/评分优先），避免默认按距离返回无名 POI
            "sortrule": "weight",
        },
    )
    if mcp_payload is not None:
        mcp_results = await _normalize_amap_pois(mcp_payload, lat, lon, kinds)
        if mcp_results is not None:
            # 高德返回本身已按权重排过序，这里只做兜底：有评分的优先
            mcp_results.sort(key=lambda p: (p.get("rating") or 0), reverse=True)
            return mcp_results

    api_key = settings.opentripmap_api_key
    if not api_key:
        return _get_demo_poi_data(lat, lon, kinds)

    url = "https://api.opentripmap.com/0.1/en/places/radius"
    params = {
        "apikey": api_key,
        "lat": lat,
        "lon": lon,
        "radius": radius,
        "kinds": kinds,
        "rate": rate,
        "format": "json",
        "limit": 20,
    }

    try:
        data = await _async_http_get(
            url,
            params=params,
            timeout=settings.opentripmap_timeout,
            max_retries=settings.opentripmap_max_retries,
        )
    except httpx.HTTPError as e:
        return [{
            "name": "API请求失败",
            "category": "error",
            "coordinates": {"lat": lat, "lon": lon},
            "rating": None,
            "description": f"OpenTripMap API 请求失败: {str(e)}",
            "source": "OpenTripMap (Error)",
            "uncertainty_flags": ["数据获取失败"],
        }]

    # 格式化结果
    results = []
    seen_names: set[str] = set()

    for item in data or []:
        name = item.get("name", "").strip()
        if not name or name in seen_names:
            continue
        seen_names.add(name)

        poi = {
            "name": name,
            "category": item.get("kinds", kinds).split(",")[0],
            "coordinates": {
                "lat": item.get("point", {}).get("lat", lat),
                "lon": item.get("point", {}).get("lon", lon),
            },
            "rating": float(item["rate"]) if item.get("rate") else None,
            "description": item.get("wikidata", ""),
            "source": f"OpenTripMap (kinds={kinds})",
            "uncertainty_flags": [
                "评分基于用户反馈，可能存在偏差",
                "营业时间可能变动，请出发前确认",
            ] if not item.get("rate") else ["营业时间可能变动，请出发前确认"],
        }
        results.append(poi)

    return results[:15]  # 限制返回数量


def _get_demo_poi_data(lat: float, lon: float, kinds: str) -> list[dict[str, Any]]:
    """当没有 API Key 时返回示例数据（以杭州为例）"""
    # 判断是否是杭州附近
    is_hangzhou = 30.0 <= lat <= 30.5 and 120.0 <= lon <= 120.3

    if not is_hangzhou:
        return [{
            "name": "（示例数据）请配置 OPENTRIPMAP_API_KEY 以获取真实数据",
            "category": kinds,
            "coordinates": {"lat": lat, "lon": lon},
            "rating": None,
            "description": "当前使用演示数据，请配置 OpenTripMap API Key",
            "source": "Demo Data",
            "uncertainty_flags": ["示例数据，非真实结果"],
        }]

    demo_data = {
        "interesting_places": [
            {"name": "西湖", "category": "natural", "coordinates": {"lat": 30.2485, "lon": 120.1468}, "rating": 5.0},
            {"name": "灵隐寺", "category": "religion", "coordinates": {"lat": 30.2406, "lon": 120.0984}, "rating": 4.5},
            {"name": "雷峰塔", "category": "historic", "coordinates": {"lat": 30.2311, "lon": 120.1494}, "rating": 4.0},
            {"name": "断桥残雪", "category": "natural", "coordinates": {"lat": 30.2596, "lon": 120.1479}, "rating": 4.5},
            {"name": "三潭印月", "category": "natural", "coordinates": {"lat": 30.2392, "lon": 120.1407}, "rating": 4.5},
            {"name": "宋城", "category": "cultural", "coordinates": {"lat": 30.1889, "lon": 120.1122}, "rating": 4.0},
            {"name": "西溪湿地", "category": "natural", "coordinates": {"lat": 30.2653, "lon": 120.0612}, "rating": 4.5},
            {"name": "龙井村", "category": "cultural", "coordinates": {"lat": 30.2185, "lon": 120.1036}, "rating": 4.0},
        ],
        "museums": [
            {"name": "浙江省博物馆", "category": "museums", "coordinates": {"lat": 30.2485, "lon": 120.1468}, "rating": 4.0},
            {"name": "中国丝绸博物馆", "category": "museums", "coordinates": {"lat": 30.2289, "lon": 120.1498}, "rating": 4.0},
        ],
        "foods": [
            {"name": "楼外楼", "category": "foods", "coordinates": {"lat": 30.2585, "lon": 120.1408}, "rating": 4.0},
            {"name": "知味观", "category": "foods", "coordinates": {"lat": 30.2556, "lon": 120.1608}, "rating": 4.0},
            {"name": "外婆家", "category": "foods", "coordinates": {"lat": 30.2589, "lon": 120.1656}, "rating": 4.0},
        ],
    }

    results = []
    for poi in demo_data.get(kinds, demo_data["interesting_places"]):
        poi_copy = dict(poi)
        poi_copy["description"] = "演示数据"
        poi_copy["source"] = "OpenTripMap (Demo)"
        poi_copy["uncertainty_flags"] = ["示例数据，价格和时间仅供参考"]
        results.append(poi_copy)

    return results


# ==================== 工具 3: 地理编码（Nominatim） ====================

@tool
async def geocode_location(query: str) -> dict[str, Any]:
    """
    将地名转换为经纬度坐标。

    优先通过高德 MCP 完成地理编码；如果 MCP 不可用，再回退到 Nominatim（OpenStreetMap）。
    这是 search_places 的前置步骤，需要先获取坐标才能搜索 POI。

    Args:
        query: 地点名称，例如"杭州市"、"西湖"、"北京天安门"

    Returns:
        dict: 包含以下字段:
            - lat (float): 纬度
            - lon (float): 经度
            - display_name (str): 完整地名
            - source (str): 数据来源
            - uncertainty (str): 不确定性说明
            - success (bool): 是否成功

    Examples:
        >>> await geocode_location("杭州")
        {"lat": 30.2485, "lon": 120.1468, "display_name": "杭州市, 浙江省, 中国", ...}
    """
    mcp_payload = await maybe_call_mcp_tool("maps_geo", {"address": query})
    if mcp_payload is not None:
        mcp_result = _normalize_amap_geocode(mcp_payload, query)
        if mcp_result is not None:
            return mcp_result

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "accept-language": "zh-CN",
    }
    headers = {"User-Agent": settings.nominatim_user_agent}

    try:
        data = await _async_http_get(
            url,
            params=params,
            headers=headers,
            timeout=settings.nominatim_timeout,
            max_retries=settings.nominatim_max_retries,
        )
    except httpx.HTTPError as e:
        # 返回杭州作为兜底
        return {
            "lat": 30.2485,
            "lon": 120.1468,
            "display_name": f"{query}（地理编码失败，使用默认值）",
            "source": "Nominatim (Fallback)",
            "uncertainty": f"地理编码请求失败: {str(e)}，坐标可能不准确",
            "success": False,
        }

    if not data or len(data) == 0:
        return {
            "lat": 30.2485,
            "lon": 120.1468,
            "display_name": f"{query}（未找到，使用默认值）",
            "source": "Nominatim (Not Found)",
            "uncertainty": "未找到该地点的坐标，使用了默认坐标，请确认地名",
            "success": False,
        }

    result = data[0]
    return {
        "lat": float(result["lat"]),
        "lon": float(result["lon"]),
        "display_name": result.get("display_name", query),
        "source": "Nominatim (OpenStreetMap)",
        "uncertainty": "坐标精度取决于地名匹配度，建议出发前二次确认",
        "success": True,
    }


# ==================== 工具 4: 路线估算（OSRM） ====================

@tool
async def estimate_route(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    profile: str = "driving",
) -> dict[str, Any]:
    """
    估算两点之间的路线距离和时间。

    优先通过高德 MCP 规划路线；如果 MCP 不可用，再回退到 OSRM。
    支持步行、驾车、骑行三种交通方式。

    Args:
        start_lat: 起点纬度
        start_lon: 起点经度
        end_lat: 终点纬度
        end_lon: 终点经度
        profile: 交通方式，可选:
            - driving: 驾车（默认）
            - walking: 步行
            - cycling: 骑行

    Returns:
        dict: 包含以下字段:
            - distance (float): 距离（米）
            - duration (float): 预计耗时（秒）
            - distance_km (float): 距离（公里）
            - duration_minutes (float): 耗时（分钟）
            - profile (str): 交通方式
            - source (str): 数据来源
            - uncertainty (str): 不确定性说明

    Examples:
        >>> await estimate_route(30.25, 120.16, 30.24, 120.15, "walking")
        {"distance": 1500.0, "duration": 1200.0, "distance_km": 1.5, ...}
    """
    mcp_tool_name = {
        "walking": "maps_direction_walking",
        "cycling": "maps_bicycling",
    }.get(profile, "maps_direction_driving")
    mcp_payload = await maybe_call_mcp_tool(
        mcp_tool_name,
        {
            "origin": f"{start_lon},{start_lat}",
            "destination": f"{end_lon},{end_lat}",
        },
    )
    if mcp_payload is not None:
        mcp_result = _normalize_amap_route(mcp_payload, profile)
        if mcp_result is not None:
            return mcp_result

    base_url = settings.osrm_base_url
    coords = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    url = f"{base_url}/{coords}"
    params = {"overview": "false"}

    try:
        data = await _async_http_get(
            url,
            params=params,
            timeout=settings.osrm_timeout,
            max_retries=settings.osrm_max_retries,
        )
    except httpx.HTTPError as e:
        # 使用直线距离估算作为兜底
        straight_distance = _haversine_distance(start_lat, start_lon, end_lat, end_lon)
        speed_map = {"driving": 30, "walking": 5, "cycling": 15}
        speed = speed_map.get(profile, 30)  # km/h
        duration_seconds = (straight_distance / 1000 / speed) * 3600

        return {
            "distance": round(straight_distance, 2),
            "duration": round(duration_seconds, 2),
            "distance_km": round(straight_distance / 1000, 2),
            "duration_minutes": round(duration_seconds / 60, 1),
            "profile": profile,
            "source": "Haversine (Fallback)",
            "uncertainty": f"OSRM 请求失败: {str(e)}，使用直线距离估算，实际路线可能更长",
        }

    if data.get("code") != "Ok" or not data.get("routes"):
        return {
            "distance": 0,
            "duration": 0,
            "distance_km": 0,
            "duration_minutes": 0,
            "profile": profile,
            "source": "OSRM (Error)",
            "uncertainty": f"路线计算失败: {data.get('message', 'Unknown error')}",
        }

    route = data["routes"][0]
    distance = route["distance"]
    duration = route["duration"]

    return {
        "distance": round(distance, 2),
        "duration": round(duration, 2),
        "distance_km": round(distance / 1000, 2),
        "duration_minutes": round(duration / 60, 1),
        "profile": profile,
        "source": "OSRM",
        "uncertainty": "估算基于道路网络，不包含实时交通状况，实际时间可能更长",
    }


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    使用 Haversine 公式计算两点间直线距离（米）

    Args:
        lat1, lon1: 起点坐标
        lat2, lon2: 终点坐标

    Returns:
        float: 直线距离（米）
    """
    import math

    R = 6371000  # 地球半径（米）
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


# ==================== 工具 5: 天气查询（Open-Meteo） ====================

@tool
async def get_weather(
    lat: float,
    lon: float,
    days: int = 7,
) -> dict[str, Any]:
    """
    查询指定位置的天气预报。

    优先通过高德 MCP 查询天气；如果 MCP 不可用，再回退到 Open-Meteo。
    提供未来 1-14 天的天气预报，包括温度、降水概率和天气描述。

    Args:
        lat: 纬度
        lon: 经度
        days: 预报天数，默认 7 天，最大 14 天

    Returns:
        dict: 包含以下字段:
            - daily (list): 每日天气预报列表
                - date (str): 日期 YYYY-MM-DD
                - temperature_max (float): 最高温度（摄氏度）
                - temperature_min (float): 最低温度（摄氏度）
                - precipitation_probability (float): 降水概率（%）
                - weather_code (int): WMO 天气代码
                - description (str): 天气描述（中文）
            - source (str): 数据来源
            - uncertainty (str): 不确定性说明

    Examples:
        >>> await get_weather(lat=30.25, lon=120.16, days=3)
        {"daily": [{"date": "2025-08-01", "temperature_max": 35, ...}], ...}
    """
    mcp_city = ""
    mcp_geocode_payload = await maybe_call_mcp_tool("maps_regeocode", {"location": f"{lon},{lat}"})
    if mcp_geocode_payload is not None:
        mcp_geocode = _mcp_dict_payload(mcp_geocode_payload)
        if mcp_geocode:
            mcp_city = str(
                mcp_geocode.get("city")
                or mcp_geocode.get("province")
                or mcp_geocode.get("provice")
                or ""
            ).strip()

    if mcp_city:
        mcp_weather_payload = await maybe_call_mcp_tool("maps_weather", {"city": mcp_city})
        if mcp_weather_payload is not None:
            mcp_result = _normalize_amap_weather(mcp_weather_payload)
            if mcp_result is not None:
                return mcp_result

    # WMO 天气代码映射（中文）
    WEATHER_CODES = {
        0: "晴朗", 1: "大部晴朗", 2: "多云", 3: "阴天",
        45: "雾", 48: "雾凇",
        51: "毛毛雨", 53: "中度毛毛雨", 55: "大毛毛雨",
        61: "小雨", 63: "中雨", 65: "大雨",
        71: "小雪", 73: "中雪", 75: "大雪",
        77: "雪粒", 80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
        85: "小阵雪", 86: "大阵雪",
        95: "雷雨", 96: "雷伴小冰雹", 99: "雷伴大冰雹",
    }

    url = "https://api.open-meteo.com/v1/forecast"

    end_date = (datetime.now() + timedelta(days=min(days, 14))).strftime("%Y-%m-%d")
    start_date = datetime.now().strftime("%Y-%m-%d")

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "weather_code",
        ],
        "timezone": "auto",
    }

    try:
        data = await _async_http_get(
            url,
            params=params,
            timeout=settings.openmeteo_timeout,
            max_retries=settings.openmeteo_max_retries,
        )
    except httpx.HTTPError as e:
        return {
            "daily": [],
            "source": "Open-Meteo (Error)",
            "uncertainty": f"天气查询失败: {str(e)}",
            "error": str(e),
        }

    daily_data = data.get("daily", {})
    dates = daily_data.get("time", [])
    temp_max = daily_data.get("temperature_2m_max", [])
    temp_min = daily_data.get("temperature_2m_min", [])
    precip_prob = daily_data.get("precipitation_probability_max", [])
    weather_codes = daily_data.get("weather_code", [])

    daily_list = []
    for i in range(len(dates)):
        code = weather_codes[i] if i < len(weather_codes) else 0
        daily_list.append({
            "date": dates[i],
            "temperature_max": temp_max[i] if i < len(temp_max) else None,
            "temperature_min": temp_min[i] if i < len(temp_min) else None,
            "precipitation_probability": precip_prob[i] if i < len(precip_prob) else 0,
            "weather_code": code,
            "description": WEATHER_CODES.get(code, "未知"),
        })

    return {
        "daily": daily_list,
        "source": "Open-Meteo",
        "uncertainty": "天气预报基于模型预测，准确率随预报时长降低，建议出发前再次确认",
    }


# ==================== 工具 6: 预算估算 ====================

@tool
def estimate_budget(
    destination: str,
    duration_days: int,
    travelers: int = 1,
    style: str = "moderate",
) -> dict[str, Any]:
    """
    估算旅行各项费用。

    基于目的地、天数、人数和消费风格，使用静态规则和经验数据
    计算住宿、餐饮、交通、门票和购物的估算费用。
    结果为区间估算，不编造精确价格。

    Args:
        destination: 目的地城市名称，如"杭州"、"上海"
        duration_days: 旅行天数
        travelers: 旅行人数，默认 1 人
        style: 消费风格，可选:
            - budget: 经济型
            - moderate: 舒适型（默认）
            - luxury: 豪华型

    Returns:
        dict: 包含以下字段:
            - breakdown (list): 各费用项拆分
                - category (str): 费用类别
                - name_cn (str): 中文名称
                - estimated_min (float): 最低估算（元）
                - estimated_max (float): 最高估算（元）
                - notes (str): 说明
            - total_min (float): 总费用下限
            - total_max (float): 总费用上限
            - source (str): 数据来源说明
            - uncertainty (str): 不确定性说明

    Examples:
        >>> estimate_budget(destination="杭州", duration_days=3, travelers=2, style="moderate")
        {"breakdown": [{"category": "accommodation", "estimated_min": 600, ...}], ...}
    """
    # 城市消费等级系数
    city_tier = settings.budget_city_tiers.get(destination, 1.0)

    # 消费风格系数
    style_multiplier = {"budget": 0.6, "moderate": 1.0, "luxury": 2.5}
    sm = style_multiplier.get(style, 1.0)

    # 住宿基准价格（每晚每间房）
    base_acc_min = 150 * city_tier * sm
    base_acc_max = 400 * city_tier * sm

    # 人数对住宿的影响（标间可以住2人）
    rooms_needed = max(1, (travelers + 1) // 2)

    # 餐饮（每天每人）
    food_per_day_min = 60 * city_tier * sm
    food_per_day_max = 150 * city_tier * sm

    # 交通（市内，每天每人）
    transport_per_day_min = 20 * city_tier
    transport_per_day_max = 80 * city_tier

    # 门票（每天每人估算）
    tickets_per_day_min = 30 * city_tier
    tickets_per_day_max = 100 * city_tier

    # 购物（总费用，可选）
    shopping_min = 0
    shopping_max = 300 * city_tier * sm * travelers

    # 计算各项费用
    accommodation_min = base_acc_min * duration_days * rooms_needed
    accommodation_max = base_acc_max * duration_days * rooms_needed

    food_min = food_per_day_min * duration_days * travelers
    food_max = food_per_day_max * duration_days * travelers

    transport_min = transport_per_day_min * duration_days * travelers
    transport_max = transport_per_day_max * duration_days * travelers

    tickets_min = tickets_per_day_min * duration_days * travelers
    tickets_max = tickets_per_day_max * duration_days * travelers

    breakdown = [
        {
            "category": "accommodation",
            "name_cn": "住宿",
            "estimated_min": round(accommodation_min, 2),
            "estimated_max": round(accommodation_max, 2),
            "notes": f"{style}型住宿，{duration_days}晚，{rooms_needed}间房",
        },
        {
            "category": "food",
            "name_cn": "餐饮",
            "estimated_min": round(food_min, 2),
            "estimated_max": round(food_max, 2),
            "notes": f"每日每人{food_per_day_min:.0f}-{food_per_day_max:.0f}元",
        },
        {
            "category": "transportation",
            "name_cn": "交通",
            "estimated_min": round(transport_min, 2),
            "estimated_max": round(transport_max, 2),
            "notes": "市内交通，含公交/地铁/打车",
        },
        {
            "category": "tickets",
            "name_cn": "门票",
            "estimated_min": round(tickets_min, 2),
            "estimated_max": round(tickets_max, 2),
            "notes": f"景点门票，部分景点可能免费",
        },
        {
            "category": "shopping",
            "name_cn": "购物",
            "estimated_min": round(shopping_min, 2),
            "estimated_max": round(shopping_max, 2),
            "notes": "可选，视个人需求",
        },
    ]

    total_min = sum(item["estimated_min"] for item in breakdown)
    total_max = sum(item["estimated_max"] for item in breakdown)

    return {
        "breakdown": breakdown,
        "total_min": round(total_min, 2),
        "total_max": round(total_max, 2),
        "source": "基于历史数据和规则估算",
        "uncertainty": "价格为估算区间，实际费用可能因季节、供需、个人消费习惯等因素有差异。热门旅游城市旺季价格可能上浮30%-50%。",
    }


# ==================== 工具 7: 高风险操作确认请求 ====================

@tool
def request_confirmation(
    action: str,
    details: dict | None = None,
) -> dict[str, Any]:
    """
    对高风险操作请求用户人工确认。

    用于预订、付款、敏感信息处理等需要用户明确授权的场景。
    此工具不会执行任何实际操作，仅生成确认请求。

    Args:
        action: 需要确认的操作描述，例如"预订酒店"、"确认付款"
        details: 操作详情字典，可包含:
            - risk_level (str): 风险等级 LOW/MEDIUM/HIGH/CRITICAL
            - item (str): 具体项目描述
            - amount (float): 金额（如有）
            - alternatives (list): 备选方案

    Returns:
        dict: 包含以下字段:
            - action (str): 操作描述
            - risk_level (str): 风险等级
            - details (dict): 操作详情
            - status (str): PENDING_CONFIRMATION
            - message (str): 给用户的消息
            - requires_human (bool): 是否需要人工确认（始终为 true）
            - source (str): 来源

    Examples:
        >>> request_confirmation("预订酒店", {"risk_level": "HIGH", "item": "杭州西湖酒店"})
        {"action": "预订酒店", "risk_level": "HIGH", "status": "PENDING_CONFIRMATION", ...}
    """
    if details is None:
        details = {}

    risk_level = details.get("risk_level", "HIGH")
    item = details.get("item", "")
    amount = details.get("amount")
    alternatives = details.get("alternatives", [])

    # 构建消息
    message_parts = [f"操作 '{action}'（风险等级: {risk_level}）需要您的人工确认。"]

    if item:
        message_parts.append(f"项目: {item}")
    if amount:
        message_parts.append(f"金额: {amount} 元")

    message_parts.append("请仔细核对后决定是否继续。")

    if alternatives:
        message_parts.append(f"备选方案: {', '.join(alternatives)}")

    message_parts.append("\n注意: 本系统仅提供旅行建议，不执行任何预订或付款操作。如需预订，请前往官方平台操作。")

    return {
        "action": action,
        "risk_level": risk_level,
        "details": details,
        "status": "PENDING_CONFIRMATION",
        "message": " ".join(message_parts),
        "requires_human": True,
        "source": "Safety Guard",
    }


# ==================== 意图路由 / 行程问答 / 闲聊 辅助函数 ====================
# 注意：这三个函数专供 graph.py 里的 intent_router/qa_responder/chitchat_responder
# 节点内部调用，不注册进下面的 TOOLS 列表——TOOLS 是暴露给主 Agent 做
# function calling 用的业务动作工具集，职责不同，混进去会导致意图分类工具
# 被主 LLM 意外选用。

def _get_async_openai_client():
    """构建异步 OpenAI 客户端，复用项目现有的 DeepSeek 接入配置
    （config.py 里的 openai_base_url/openai_api_key，走 OpenAI SDK 兼容接口）。"""
    from openai import AsyncOpenAI
    from config import settings

    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


@tool
async def classify_intent(
    user_input: str,
    has_existing_itinerary: bool,
    needs_clarification: bool,
) -> dict:
    """
    用 LLM 判断用户这句话属于哪种意图场景。

    Args:
        user_input: 用户原始输入
        has_existing_itinerary: 当前会话是否已经生成过完整行程
        needs_clarification: 系统上一轮是否在等待用户补充缺失信息

    Returns:
        dict: {"intent": "new_plan|continue_clarify|faq_about_itinerary|chitchat", "confidence": float}
        LLM 调用失败时返回 {"intent": "new_plan", "confidence": 0.0}，
        调用方（intent_router 节点）会据此再走启发式规则兜底。
    """
    from agent.prompts import INTENT_CLASSIFICATION_PROMPT
    from config import settings

    client = _get_async_openai_client()
    prompt = INTENT_CLASSIFICATION_PROMPT.format(
        user_input=user_input,
        has_existing_itinerary=has_existing_itinerary,
        needs_clarification=needs_clarification,
    )

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=100,
            timeout=8,
        )
        raw_text = response.choices[0].message.content or ""
        # LLM 偶尔会在 JSON 外加说明文字，兜底提取第一个 {...} 片段
        import re
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        json_text = match.group(0) if match else raw_text
        result = json.loads(json_text)
        if "intent" not in result:
            raise ValueError(f"LLM 输出缺少 intent 字段: {raw_text!r}")
        return result
    except Exception as exc:
        return {"intent": "new_plan", "confidence": 0.0, "error": str(exc)}


@tool
async def answer_itinerary_question(
    question: str,
    itinerary: str,
    weather_summary: str,
    budget_summary: str,
) -> str:
    """
    基于已生成的行程内容，回答用户的追问。

    Args:
        question: 用户问题
        itinerary: 完整行程 Markdown
        weather_summary: 天气摘要文本
        budget_summary: 预算摘要文本

    Returns:
        str: 回答文本
    """
    from agent.prompts import QA_ANSWER_PROMPT
    from config import settings

    client = _get_async_openai_client()
    prompt = QA_ANSWER_PROMPT.format(
        question=question,
        itinerary=itinerary,
        weather_summary=weather_summary,
        budget_summary=budget_summary,
    )

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=400,
        timeout=15,
    )
    return response.choices[0].message.content or "抱歉，暂时无法回答这个问题，请查看上方完整行程。"


@tool
async def generate_chitchat_reply(message: str) -> str:
    """
    生成闲聊回复。

    Args:
        message: 用户消息

    Returns:
        str: 回复文本
    """
    from agent.prompts import CHITCHAT_PROMPT
    from config import settings

    client = _get_async_openai_client()
    prompt = CHITCHAT_PROMPT.format(message=message)

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=150,
        timeout=8,
    )
    return response.choices[0].message.content or "很高兴和您聊天。有什么旅行规划需要帮助的吗？"


# ==================== 工具注册表 ====================

TOOLS: list = [
    collect_preferences,
    search_places,
    geocode_location,
    estimate_route,
    get_weather,
    estimate_budget,
    request_confirmation,
]


def get_tools() -> list:
    """
    获取所有可用工具的列表

    Returns:
        list: 工具函数列表，供 LangChain/LangGraph 使用
    """
    return TOOLS


def get_tool_by_name(name: str) -> Any:
    """
    根据名称获取工具

    Args:
        name: 工具名称

    Returns:
        工具函数或 None
    """
    for tool in TOOLS:
        if tool.name == name:
            return tool
    return None
