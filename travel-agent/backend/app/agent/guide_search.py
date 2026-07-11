from __future__ import annotations

import hashlib
import asyncio
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from openai import AsyncOpenAI

from config import settings


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _find_first_list(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("items", "notes", "list", "records", "data", "result", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _find_first_list(value)
            if nested:
                return nested
    return []


def _get_deepseek_client() -> AsyncOpenAI | None:
    if not settings.deepseek_enabled:
        return None
    # 优先复用项目里已经在用的 OpenAI 兼容中转站；
    # 只有当你显式填写了 DeepSeek 独立配置时，才切到 deepseek_base_url。
    api_key = settings.deepseek_api_key.strip() or settings.openai_api_key.strip()
    if not api_key:
        return None
    if settings.deepseek_api_key.strip() and settings.deepseek_base_url.strip():
        base_url = settings.deepseek_base_url.strip()
    else:
        base_url = settings.openai_base_url.strip() or settings.deepseek_base_url.strip()
    return AsyncOpenAI(
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        timeout=settings.deepseek_timeout,
    )


def _note_text(note: Any) -> str:
    if not isinstance(note, dict):
        return _clean_text(note)
    parts: list[str] = []
    for key in (
        "title",
        "desc",
        "description",
        "content",
        "display_title",
        "note_card",
        "noteCard",
        "summary",
    ):
        value = note.get(key)
        if isinstance(value, dict):
            parts.append(_note_text(value))
        elif isinstance(value, list):
            parts.extend(_note_text(item) for item in value)
        else:
            parts.append(_clean_text(value))
    return " ".join(part for part in parts if part)


def _compact_note_payload(notes: list[Any]) -> list[dict[str, str]]:
    """把笔记压缩成适合发给模型的短文本，减少 token 消耗。"""
    compact: list[dict[str, str]] = []
    for note in notes[: settings.deepseek_max_notes_per_request]:
        if not isinstance(note, dict):
            continue
        title = _clean_text(note.get("title") or note.get("display_title") or note.get("desc") or "")
        desc = _clean_text(note.get("desc") or note.get("description") or note.get("content") or "")
        text = f"{title} {desc}".strip()
        if not text:
            continue
        compact.append({
            "title": title[:120],
            "text": text[:1200],
        })
    return compact


def _candidate_score(name: str, full_text: str, city: str) -> int:
    score = 0
    if city and city in name:
        score += 3
    if name in full_text:
        score += min(full_text.count(name), 5)
    if re.search(r"(博物馆|纪念馆|遗址|古镇|老街|公园|寺|祠|宫|观|山|湖|塔|楼|巷子|景区|基地|宽窄巷子|太古里)", name):
        score += 4
    if re.search(r"(酒店|宾馆|地铁|公交|机场|车站|写字楼|停车场|售楼部|公司|店铺|商场|广场店)$", name):
        score -= 5
    return score


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


def _normalize_candidate_name(raw_name: str) -> str:
    name = _clean_text(raw_name).strip("《》【】[]（）()，,。.!！:：;；")
    name = re.sub(r"^(第[一二三四五六七八九十\d]+天|上午|下午|晚上|早上|中午|白天|夜游|打卡)", "", name)
    for prefix in ("成都", "重庆", "北京", "上海", "广州", "深圳", "杭州", "武汉", "西安", "南京", "天津", "苏州", "长沙", "郑州"):
        if name.startswith(prefix):
            name = name[len(prefix):].lstrip()
            break
    suffix_pattern = (
        r"([\u4e00-\u9fffA-Za-z0-9·]{2,18}?"
        r"(?:博物馆|纪念馆|遗址|古镇|古街|老街|公园|寺|祠|宫|观|山|湖|塔|楼|巷子|景区|基地|街区|广场|园|桥|岛|湾|谷|湿地|湿地公园|自然保护区|动物园|植物园|美术馆|艺术馆|图书馆|步行街|商业街|太古里|草堂|春熙路|锦里))"
    )
    match = re.search(suffix_pattern, name)
    if match:
        name = match.group(1)
    if re.match(r"^(住进|可以|真的|避暑|雪山|傍晚|晚上|白天|第一|第二|第三|推荐|保姆|精华|直观|打卡|逛|去|看|吃|拍|玩|慢慢|感觉|后劲|攻略|路线|行程|旅游|旅行|种草|探店|分享|合集|必去|避雷|出片|Vlog|vlog|citywalk)", name):
        return ""
    # 只保留“像真实景点名”的候选，避免把攻略标签、拍摄词、情绪词当成 POI。
    if re.fullmatch(r"[A-Za-z]{2,12}", name):
        return ""
    if "的" in name and not re.search(r"(博物馆|纪念馆|遗址|古镇|古街|老街|公园|寺|祠|宫|观|山|湖|塔|楼|巷子|景区|基地|街区|广场|园|桥|岛|湾|谷|湿地|美术馆|艺术馆|图书馆|步行街|商业街|太古里|草堂|春熙路|锦里)$", name):
        return ""
    return name.strip()


def _looks_like_poi_name(name: str) -> bool:
    """判断候选是否像一个真实景点名。

    这里用比较保守的规则，只保留明显的景点/场所后缀，尽量把
    vlog、citywalk、租车、洗浴中心、周边游这类内容词挡掉。
    """
    if not name:
        return False

    if re.search(r"(攻略|路线|行程|旅游|旅行|打卡|收藏|评论|点赞|笔记|主页|全文|推荐|必去|避雷|超全|保姆|种草|探店|分享|合集|拍照|出片|美食|住宿|交通|Vlog|vlog|citywalk|租车|洗浴|周边游)", name):
        return False

    if re.fullmatch(r"[A-Za-z]{2,12}", name):
        return False

    poi_suffixes = (
        "博物馆", "纪念馆", "遗址", "古镇", "古街", "老街", "公园", "景区", "街区", "广场",
        "园", "桥", "岛", "湾", "谷", "湿地", "湿地公园", "自然保护区", "动物园", "植物园",
        "美术馆", "艺术馆", "图书馆", "步行街", "商业街", "乐园", "基地", "锦里", "太古里",
        "春熙路", "宽窄巷子", "寺", "祠", "宫", "观", "山", "湖", "塔", "楼", "巷子", "堰",
        "城", "门", "花园", "路",
    )
    return any(name.endswith(suffix) for suffix in poi_suffixes)


def extract_poi_candidates_from_notes(
    notes: list[Any],
    city: str,
    limit: int = 12,
    source_label: str = "JustOneAPI 攻略搜索",
) -> list[dict[str, Any]]:
    """从小红书搜索结果中抽取可能的地点名，先做候选，不直接当作真实 POI 使用。"""
    full_text = "\n".join(_note_text(note) for note in notes[: settings.justoneapi_max_notes_per_plan])
    if not full_text:
        return []

    patterns = [
        r"#([\u4e00-\u9fffA-Za-z0-9·]{2,18})",
        r"([\u4e00-\u9fffA-Za-z0-9·]{2,18}(?:博物馆|纪念馆|遗址|古镇|古街|老街|公园|寺|祠|宫|观|山|湖|塔|楼|巷子|景区|基地|街区|广场|园|桥|岛|湾|谷|湿地|湿地公园|自然保护区|动物园|植物园|美术馆|艺术馆|图书馆|步行街|商业街|太古里|草堂|春熙路|锦里))",
    ]

    counts: dict[str, int] = {}

    def add_candidate(raw_name: str) -> None:
        name = _normalize_candidate_name(raw_name)
        if not name or len(name) < 2 or len(name) > 18:
            return
        if city and name == city:
            return
        if not _looks_like_poi_name(name):
            return
        counts[name] = counts.get(name, 0) + 1

    # 先按常见分隔符切词，只保留“看起来像景点名”的片段。
    for chunk in re.split(r"[#\s,，、。.!！:：;；/｜|]+", full_text):
        if re.search(r"(博物馆|纪念馆|遗址|古镇|古街|老街|公园|寺|祠|宫|观|山|湖|塔|楼|巷子|景区|基地|街区|广场|园|桥|岛|湾|谷|湿地|湿地公园|自然保护区|动物园|植物园|美术馆|艺术馆|图书馆|步行街|商业街|太古里|草堂|春熙路|锦里|乐园|花园|路)", chunk):
            add_candidate(chunk)

    for pattern in patterns:
        for match in re.findall(pattern, full_text):
            add_candidate(match)

    ranked = sorted(
        counts.items(),
        key=lambda item: (_candidate_score(item[0], full_text, city), item[1], len(item[0])),
        reverse=True,
    )
    return [
        {"name": name, "guide_mentions": count, "guide_source": source_label}
        for name, count in ranked[:limit]
    ]


async def extract_poi_candidates_from_notes_with_ai(notes: list[Any], city: str, limit: int = 12) -> list[dict[str, Any]]:
    """优先用 DeepSeek 清洗候选地点，再回退到规则抽取。"""
    client = _get_deepseek_client()
    if client is None:
        return []

    compact_notes = _compact_note_payload(notes)
    if not compact_notes:
        return []

    prompt = (
        "你是旅行攻略地点抽取器。"
        "你的任务只有一个：从攻略笔记中提取真实存在、适合行程安排的景点名称。"
        "只保留景点/景区/公园/博物馆/古镇/古街/寺庙/山/湖/塔/楼/广场/街区/步行街等明确地点名。"
        "不要输出 vlog、citywalk、打卡、攻略、路线、旅行方式、情绪词、句子残片、标签词或任何泛化表达。"
        "如果不是明确地点名，就不要提取。"
        "只返回 JSON，不要解释。"
    )
    user_payload = {
        "city": city,
        "limit": limit,
        "notes": compact_notes,
        "output_schema": {
            "candidates": [
                {
                    "name": "地点名",
                    "mentions": 1,
                }
            ]
        },
    }

    try:
        response = await client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            temperature=0.0,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        payload = json.loads(content)
        raw_candidates = payload.get("candidates")
        if not isinstance(raw_candidates, list):
            return []

        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in raw_candidates:
            if not isinstance(item, dict):
                continue
            name = _normalize_candidate_name(item.get("name") or "")
            if not name or name in seen:
                continue
            if city and name == city:
                continue
            if not _looks_like_poi_name(name):
                continue
            seen.add(name)
            results.append(
                {
                    "name": name,
                    "guide_mentions": int(item.get("mentions") or 1),
                    "guide_source": "DeepSeek 攻略抽取",
                    "reason": _clean_text(item.get("reason") or ""),
                }
            )
            if len(results) >= limit:
                break

        return results
    except Exception as exc:
        print(f"[guide_search] LLM 景点提取失败 city={city!r}: {exc}", flush=True)
        return []


class JustOneGuideSearch:
    """JustOneAPI 小红书攻略搜索技能，负责低成本拿攻略信号并交给高德校验。"""

    endpoint = "/api/xiaohongshu/search-note/v4"
    fallback_endpoints = {
        "douyin": "/api/douyin/search-video/v4",
        "bilibili": "/api/bilibili/search-video/v2",
        "weibo": "/api/weibo/search-all/v2",
    }

    def __init__(self) -> None:
        self.cache_dir = Path(settings.justoneapi_cache_dir)

    def enabled(self) -> bool:
        return bool(settings.justoneapi_enabled and settings.justoneapi_key.strip())

    def _cache_path(self, keyword: str) -> Path:
        digest = hashlib.sha256(keyword.encode("utf-8")).hexdigest()[:24]
        return self.cache_dir / f"{digest}.json"

    def _read_cache(self, keyword: str) -> dict[str, Any] | None:
        path = self._cache_path(keyword)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            fetched_at = datetime.fromisoformat(data.get("fetched_at", ""))
            if datetime.now() - fetched_at > timedelta(hours=settings.justoneapi_cache_ttl_hours):
                return None
            payload = data.get("payload") or {}
            # 失败响应不能进入长期缓存，否则一次临时失败会阻断后续一周的搜索。
            if isinstance(payload, dict) and (
                str(payload.get("code", "0")) not in ("0", "200")
                or payload.get("data") is None
            ):
                return None
            return data
        except Exception:
            return None

    def _write_cache(self, keyword: str, payload: dict[str, Any]) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "keyword": keyword,
                "fetched_at": datetime.now().isoformat(timespec="seconds"),
                "payload": payload,
            }
            self._cache_path(keyword).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            # 缓存失败不能影响主链路，最多多花一次外部 API 调用成本。
            return

    async def _request_endpoint(
        self,
        base_url: str,
        endpoint: str,
        params: dict[str, Any],
        retries: int = 2,
    ) -> dict[str, Any]:
        """请求指定版本的小红书接口，供 V4 失败后的 V2 降级使用。"""
        last_error = ""
        payload: dict[str, Any] = {}
        request_id = ""
        http_status: int | None = None
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=settings.justoneapi_timeout) as client:
                    response = await client.get(f"{base_url}{endpoint}", params=params)
                    http_status = response.status_code
                    response.raise_for_status()
                    payload = response.json()
                code = str(payload.get("code", "0")) if isinstance(payload, dict) else "0"
                request_id = str(payload.get("requestId") or "") if isinstance(payload, dict) else ""
                if code in ("0", "200") and payload.get("data") is not None:
                    return {
                        "success": True,
                        "payload": payload,
                        "code": code,
                        "request_id": request_id,
                        "http_status": http_status,
                        "attempts": attempt + 1,
                        "endpoint": endpoint,
                    }
                last_error = f"JustOneAPI code={code}: {payload.get('message', 'data为空')}"
            except Exception as exc:
                last_error = str(exc)
            if attempt < retries - 1:
                await asyncio.sleep(1)
        return {
            "success": False,
            "payload": payload,
            "code": str(payload.get("code", "0")) if payload else "0",
            "request_id": request_id,
            "http_status": http_status,
            "attempts": retries,
            "endpoint": endpoint,
            "error": last_error or "JustOneAPI 返回空数据",
        }

    async def search_notes(self, city: str, days: int | None = None, interests: list[str] | None = None) -> dict[str, Any]:
        if not self.enabled():
            return {"enabled": False, "notes": [], "source": "JustOneAPI disabled"}

        # 这里刻意只搜“城市 + 景点”这类强指向词，避免把预算、天数、
        # 玩法、心情词一起混进来，后面的抽取结果会干净很多。
        keyword_parts = [city, "景点", "热门景点"]
        keyword = " ".join(part for part in keyword_parts if part)

        cached = self._read_cache(keyword)
        if cached is not None:
            return {"enabled": True, "cached": True, "keyword": keyword, "notes": _find_first_list(cached.get("payload"))}

        base_url = settings.justoneapi_base_url.rstrip("/")
        params = {
            "token": settings.justoneapi_key,
            "keyword": keyword,
            "page": 1,
            "sortType": "popularity_descending",
            "noteType": "ALL",
            "timeFilter": "ALL",
        }
        payload: dict[str, Any] = {}
        last_error = ""
        request_id = ""
        attempts = 0
        http_status: int | None = None
        for attempt in range(3):
            attempts = attempt + 1
            try:
                async with httpx.AsyncClient(timeout=settings.justoneapi_timeout) as client:
                    response = await client.get(f"{base_url}{self.endpoint}", params=params)
                    http_status = response.status_code
                    response.raise_for_status()
                    payload = response.json()
                code = str(payload.get("code", "0")) if isinstance(payload, dict) else "0"
                data = payload.get("data") if isinstance(payload, dict) else None
                request_id = str(payload.get("requestId") or "") if isinstance(payload, dict) else ""
                if code in ("0", "200") and data is not None:
                    break
                last_error = f"JustOneAPI code={code}: {payload.get('message', 'data为空')}"
            except Exception as exc:
                last_error = str(exc)
            if attempt < 2:
                await asyncio.sleep(1 + attempt)

        print(
            f"[guide_search] endpoint={self.endpoint} keyword={keyword!r} "
            f"attempts={attempts} http_status={http_status} code={payload.get('code') if payload else None} "
            f"request_id={request_id or '-'} notes={len(_find_first_list(payload)) if payload else 0} "
            f"error={last_error or '-'}",
            flush=True,
        )

        code = str(payload.get("code", "0")) if isinstance(payload, dict) else "0"
        if code not in ("0", "200") or payload.get("data") is None:
            # V4 采集失败时尝试 V2；只有 V2 也失败才让上层看到小红书不可用。
            v2 = await self._request_endpoint(
                base_url,
                "/api/xiaohongshu/search-note/v2",
                params,
                retries=2,
            )
            print(
                f"[guide_search] fallback endpoint={v2.get('endpoint')} keyword={keyword!r} "
                f"http_status={v2.get('http_status')} code={v2.get('code')} "
                f"request_id={v2.get('request_id') or '-'} notes={len(_find_first_list(v2.get('payload') or {}))} "
                f"error={v2.get('error') or '-'}",
                flush=True,
            )
            if v2.get("success"):
                v2_payload = v2.get("payload") or {}
                self._write_cache(keyword, v2_payload)
                return {
                    "enabled": True,
                    "cached": False,
                    "keyword": keyword,
                    "notes": _find_first_list(v2_payload),
                    "api_code": v2.get("code"),
                    "http_status": v2.get("http_status"),
                    "request_id": v2.get("request_id"),
                    "attempts": attempts + int(v2.get("attempts", 0)),
                    "endpoint": v2.get("endpoint"),
                    "attempted_endpoints": [self.endpoint, v2.get("endpoint")],
                }
            return {
                "enabled": True,
                "cached": False,
                "keyword": keyword,
                "notes": [],
                "error": last_error or "JustOneAPI 返回空数据",
                "source": "JustOneAPI 小红书搜索",
                "api_code": code,
                "http_status": http_status,
                "request_id": request_id,
                "attempts": attempts,
                "endpoint": self.endpoint,
            }

        self._write_cache(keyword, payload)
        return {
            "enabled": True,
            "cached": False,
            "keyword": keyword,
            "notes": _find_first_list(payload),
            "api_code": code,
            "http_status": http_status,
            "request_id": request_id,
            "attempts": attempts,
            "endpoint": self.endpoint,
        }

    @staticmethod
    def _fallback_records(payload: Any, source: str) -> list[dict[str, Any]]:
        """把抖音/B站/微博的异构结果压成地点抽取器可消费的攻略文本。"""
        records: list[dict[str, Any]] = []
        seen: set[str] = set()

        def visit(value: Any) -> None:
            if isinstance(value, list):
                for item in value:
                    visit(item)
                return
            if not isinstance(value, dict):
                return

            aweme = value.get("aweme_info")
            if isinstance(aweme, dict):
                visit(aweme)
                return

            title = _clean_text(
                value.get("title")
                or value.get("desc")
                or value.get("description")
                or value.get("text")
                or value.get("content")
                or ""
            )
            description = _clean_text(
                value.get("description")
                or value.get("desc")
                or value.get("text")
                or value.get("content")
                or value.get("tag")
                or ""
            )
            url = _clean_text(
                value.get("arcurl")
                or value.get("url")
                or value.get("share_url")
                or value.get("shareUrl")
                or ""
            )
            # 只把带有正文/标题的内容对象作为候选，避免把响应中的配置字典
            # 误当成攻略；随后仍由规则/LLM 和高德 POI 校验共同过滤。
            if title or description:
                key = f"{title}|{url}"
                if key not in seen:
                    seen.add(key)
                    records.append({
                        "title": title[:160],
                        "desc": description[:1600],
                        "content": description[:1600],
                        "url": url,
                        "source": source,
                    })

            for nested_key in ("result", "data", "business_data", "items", "list", "cards"):
                nested = value.get(nested_key)
                if isinstance(nested, (dict, list)):
                    visit(nested)

        visit(payload)
        return records

    async def search_fallback_notes(self, city: str) -> dict[str, Any]:
        """小红书失败时并行搜索抖音、B站、微博，保持同一 JustOneAPI 账号。"""
        if not self.enabled():
            return {"enabled": False, "notes": [], "source": "JustOneAPI disabled"}

        base_url = settings.justoneapi_base_url.rstrip("/")
        keyword = f"{city} 旅游 景点"
        now = datetime.now()
        start_day = (now - timedelta(days=180)).strftime("%Y-%m-%d")
        end_day = now.strftime("%Y-%m-%d")
        requests = {
            "douyin": {
                "token": settings.justoneapi_key,
                "keyword": keyword,
                "sortType": "_1",
                "publishTime": "_180",
                "page": 1,
            },
            "bilibili": {
                "token": settings.justoneapi_key,
                "keyword": keyword,
                "order": "click",
                "page": 1,
            },
            "weibo": {
                "token": settings.justoneapi_key,
                "q": keyword,
                "startDay": start_day,
                "startHour": 0,
                "endDay": end_day,
                "endHour": 23,
                "hotSort": "true",
                "page": 1,
            },
        }

        async def request_one(source: str) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
            endpoint = self.fallback_endpoints[source]
            try:
                async with httpx.AsyncClient(timeout=settings.justoneapi_timeout) as client:
                    response = await client.get(f"{base_url}{endpoint}", params=requests[source])
                    payload = response.json()
                code = str(payload.get("code", "0")) if isinstance(payload, dict) else "0"
                records = self._fallback_records(payload, f"JustOneAPI {source} 攻略搜索") if code in ("0", "200") else []
                meta = {
                    "endpoint": endpoint,
                    "http_status": response.status_code,
                    "api_code": code,
                    "request_id": str(payload.get("requestId") or "") if isinstance(payload, dict) else "",
                    "error": None if records else str(payload.get("message") or "返回空数据"),
                }
                return source, meta, records
            except Exception as exc:
                return source, {
                    "endpoint": endpoint,
                    "http_status": None,
                    "api_code": None,
                    "request_id": "",
                    "error": str(exc),
                }, []

        results = await asyncio.gather(*(request_one(source) for source in requests))
        notes: list[dict[str, Any]] = []
        metadata: list[dict[str, Any]] = []
        for source, meta, records in results:
            metadata.append({"source": source, **meta, "record_count": len(records)})
            notes.extend(records)

        # 以标题/URL 去重，避免同一视频在多个响应层级重复出现。
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for note in notes:
            key = f"{note.get('title', '')}|{note.get('url', '')}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(note)

        return {
            "enabled": True,
            "cached": False,
            "keyword": keyword,
            "notes": deduped[: settings.justoneapi_max_notes_per_plan * 3],
            "source": "JustOneAPI 抖音+B站+微博降级搜索",
            "fallback_platforms": metadata,
            "attempted_endpoints": [item["endpoint"] for item in metadata],
        }

    async def validate_with_amap(
        self,
        candidates: list[dict[str, Any]],
        city: str,
        center_lat: float | None = None,
        center_lon: float | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """候选地点先经过地理编码校验，再按城市中心距离过滤，避免把攻略文本里的泛词直接放进行程。"""
        from agent.tools import geocode_location, search_places

        validated: list[dict[str, Any]] = []
        seen: set[str] = set()
        max_items = limit or settings.justoneapi_max_pois_per_plan

        for candidate in candidates[: max_items * 2]:
            name = str(candidate.get("name") or "").strip()
            if not name or name in seen:
                continue
            query = f"{name} {city}".strip()
            try:
                geo_result = await geocode_location.ainvoke({"query": query})
                if isinstance(geo_result, str):
                    geo_result = json.loads(geo_result)
            except Exception:
                continue
            if not isinstance(geo_result, dict) or not geo_result.get("success"):
                continue

            lat = _coerce_float(geo_result.get("lat"))
            lon = _coerce_float(geo_result.get("lon"))
            if lat is None or lon is None:
                continue
            if center_lat is not None and center_lon is not None:
                if _haversine_km(center_lat, center_lon, lat, lon) > 120:
                    continue

            # 先用高德地理编码确认候选名称，再用高德 POI 搜索确认它确实
            # 是地图中的地点，而不是攻略文本里的 vlog/活动描述或泛化词。
            try:
                amap_results = await search_places.ainvoke({
                    "lat": lat,
                    "lon": lon,
                    "radius": 3000,
                    "kinds": "interesting_places",
                    "rate": "3",
                    "keyword": name,
                })
                if isinstance(amap_results, str):
                    amap_results = json.loads(amap_results)
            except Exception:
                continue
            if not isinstance(amap_results, list) or not amap_results:
                continue
            if not any(
                isinstance(item, dict)
                and any(
                    marker in str(item.get("source") or "")
                    for marker in ("高德", "MCP")
                )
                for item in amap_results
            ):
                continue

            matched = next(
                (
                    item for item in amap_results
                    if isinstance(item, dict)
                    and name in str(item.get("name") or "")
                ),
                None,
            )
            if not matched:
                continue
            matched_coordinates = matched.get("coordinates") or {}
            matched_lat = _coerce_float(matched_coordinates.get("lat"))
            matched_lon = _coerce_float(matched_coordinates.get("lon"))
            if matched_lat is not None and matched_lon is not None:
                lat, lon = matched_lat, matched_lon

            guide_source = str(candidate.get("guide_source") or "JustOneAPI 攻略搜索")
            poi = {
                "name": name,
                "category": "guide_recommended",
                "coordinates": {"lat": lat, "lon": lon},
                "rating": None,
                "description": f"{guide_source}提及 {candidate.get('guide_mentions', 1)} 次，坐标已通过地理编码校验",
                "source": f"{guide_source} + 高德地图校验",
                "uncertainty_flags": ["来源于攻略提名，开放时间和门票需出发前确认"],
                "guide_mentions": candidate.get("guide_mentions", 1),
            }
            seen.add(poi["name"])
            validated.append(poi)
            if len(validated) >= max_items:
                break
        return validated


async def search_guide_pois(
    city: str,
    days: int | None = None,
    interests: list[str] | None = None,
    center_lat: float | None = None,
    center_lon: float | None = None,
) -> dict[str, Any]:
    skill = JustOneGuideSearch()
    try:
        note_result = await skill.search_notes(city=city, days=days, interests=interests)
        # V4/V2 小红书均失败，或返回空结果时，降级到同一 JustOneAPI
        # 账号下的抖音、B站、微博搜索；这些结果只作为“候选来源”，
        # 最终仍必须经过高德地理编码和 POI 校验。
        if note_result.get("error") or not note_result.get("notes"):
            fallback_result = await skill.search_fallback_notes(city)
            if fallback_result.get("notes"):
                note_result = fallback_result
            elif note_result.get("error"):
                note_result["fallback_platforms"] = fallback_result.get("fallback_platforms", [])

        if note_result.get("error") and not note_result.get("notes"):
            return {
                "enabled": note_result.get("enabled", False),
                "cached": False,
                "keyword": note_result.get("keyword"),
                "candidate_count": 0,
                "poi_list": [],
                "error": note_result["error"],
                "api_code": note_result.get("api_code"),
                "http_status": note_result.get("http_status"),
                "request_id": note_result.get("request_id"),
                "attempts": note_result.get("attempts", 0),
                "endpoint": note_result.get("endpoint", JustOneGuideSearch.endpoint),
                "source": "JustOneAPI 小红书搜索",
            }
        notes = note_result.get("notes") or []
        candidates = await extract_poi_candidates_from_notes_with_ai(
            notes,
            city,
            limit=settings.justoneapi_max_pois_per_plan * 2,
        )
        guide_source = str(note_result.get("source") or "JustOneAPI 攻略搜索")
        for candidate in candidates:
            candidate["guide_source"] = guide_source
        pois = await skill.validate_with_amap(
            candidates,
            city,
            center_lat=center_lat,
            center_lon=center_lon,
            limit=settings.justoneapi_max_pois_per_plan,
        )
        return {
            "enabled": note_result.get("enabled", False),
            "cached": note_result.get("cached", False),
            "keyword": note_result.get("keyword"),
            "note_count": len(notes),
            "candidate_count": len(candidates),
            "poi_list": pois,
            "api_code": note_result.get("api_code"),
            "http_status": note_result.get("http_status"),
            "request_id": note_result.get("request_id"),
            "attempts": note_result.get("attempts", 0),
            "endpoint": note_result.get("endpoint", JustOneGuideSearch.endpoint),
            "source": guide_source + " + 高德地图 MCP 校验",
            "fallback_platforms": note_result.get("fallback_platforms", []),
            "attempted_endpoints": note_result.get("attempted_endpoints", []),
        }
    except httpx.HTTPStatusError as exc:
        return {
            "enabled": True,
            "error": f"JustOneAPI HTTP {exc.response.status_code}",
            "poi_list": [],
            "source": "JustOneAPI 小红书搜索",
        }
    except Exception as exc:
        return {
            "enabled": bool(settings.justoneapi_enabled),
            "error": f"JustOneAPI 搜索失败: {exc}",
            "poi_list": [],
            "source": "JustOneAPI 小红书搜索",
        }
