"""
Travel Agent 数据模型定义

所有数据模型使用 Pydantic v2 定义，提供完整的类型验证和序列化支持。
包含旅行偏好、POI、路线、天气、预算、行程等核心数据结构。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==================== 基础模型 ====================

class TravelPreference(BaseModel):
    """用户旅行偏好 - 从用户输入中提取的结构化偏好信息"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "destination": "杭州",
            "duration_days": 3,
            "budget_cny": 3000,
            "travel_dates": {"start": "2025-08-01", "end": "2025-08-03"},
            "companions": "couple",
            "interests": ["自然", "美食", "历史"],
            "dietary_restrictions": [],
            "accessibility_needs": False,
            "pace_preference": "moderate",
            "accommodation_type": "hotel",
            "transportation_preference": "public",
        }
    })

    destination: Optional[str] = Field(default=None, description="目的地（城市/地区名称）")
    duration_days: Optional[int] = Field(default=None, ge=1, le=30, description="旅行天数")
    budget_cny: Optional[float] = Field(default=None, ge=0, description="预算（人民币）")
    travel_dates: Optional[dict[str, str]] = Field(
        default=None, description="旅行日期范围 {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}"
    )
    companions: Optional[str] = Field(
        default=None, description="同行人类型: solo/couple/family/friends/group"
    )
    interests: list[str] = Field(default_factory=list, description="兴趣标签列表")
    dietary_restrictions: list[str] = Field(
        default_factory=list, description="饮食限制（如素食、清真、过敏等）"
    )
    accessibility_needs: bool = Field(
        default=False, description="是否需要无障碍设施"
    )
    pace_preference: Literal["relaxed", "moderate", "intensive"] = Field(
        default="moderate", description="旅行节奏偏好"
    )
    accommodation_type: Optional[str] = Field(
        default=None, description="住宿类型: hotel/hostel/homestay/resort"
    )
    transportation_preference: Optional[str] = Field(
        default=None, description="交通偏好: public/walk/drive/transit"
    )

    @field_validator("companions")
    @classmethod
    def validate_companions(cls, v: Optional[str]) -> Optional[str]:
        """验证同行人类型值"""
        if v is None:
            return v
        allowed = {"solo", "couple", "family", "friends", "group"}
        if v not in allowed:
            raise ValueError(f"同行人类型必须是其中之一: {allowed}")
        return v

    @field_validator("accommodation_type")
    @classmethod
    def validate_accommodation(cls, v: Optional[str]) -> Optional[str]:
        """验证住宿类型值"""
        if v is None:
            return v
        allowed = {"hotel", "hostel", "homestay", "resort"}
        if v not in allowed:
            raise ValueError(f"住宿类型必须是其中之一: {allowed}")
        return v

    def get_critical_missing_fields(self) -> list[str]:
        """
        获取缺失的关键字段列表

        关键字段定义为: destination, duration_days, budget_cny

        Returns:
            list[str]: 缺失的关键字段名称列表
        """
        missing: list[str] = []
        if not self.destination:
            missing.append("destination")
        if not self.duration_days:
            missing.append("duration_days")
        if not self.budget_cny:
            missing.append("budget_cny")
        return missing

    def is_complete(self) -> bool:
        """检查所有关键字段是否已填写"""
        return len(self.get_critical_missing_fields()) == 0


class TravelConstraints(BaseModel):
    """标准化旅行约束 - 由约束标准化节点生成"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "hard_constraints": {"budget_max": 3000, "accessibility": True},
            "soft_constraints": {"interests": ["自然", "美食"], "pace": "moderate"},
            "implicit_needs": ["儿童友好设施", "安全区域"],
            "constraint_summary": "3天杭州旅行，预算3000元，偏好自然和美食",
        }
    })

    hard_constraints: dict[str, Any] = Field(
        default_factory=dict, description="硬约束（必须满足）"
    )
    soft_constraints: dict[str, Any] = Field(
        default_factory=dict, description="软约束（尽量满足）"
    )
    implicit_needs: list[str] = Field(
        default_factory=list, description="隐性需求推导结果"
    )
    constraint_summary: str = Field(
        default="", description="人类可读的一行约束摘要"
    )


class POI(BaseModel):
    """兴趣点（Point of Interest）- 景点、餐厅、咖啡馆等"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "西湖",
            "category": "natural",
            "coordinates": {"lat": 30.2485, "lon": 120.1468},
            "rating": 5.0,
            "description": "杭州著名自然景点",
            "opening_hours": "全天开放",
            "price_level": "free",
            "source_url": "https://opentripmap.com/...",
            "uncertainty_flags": ["营业时间可能变动"],
        }
    })

    name: str = Field(..., min_length=1, description="POI 名称")
    category: str = Field(..., description="类别: attraction/restaurant/cafe/museum/natural/historic 等")
    coordinates: dict[str, float] = Field(..., description="坐标 {'lat': float, 'lon': float}")
    rating: Optional[float] = Field(default=None, ge=0, le=7, description="评分（1-7）")
    description: Optional[str] = Field(default=None, description="描述信息")
    opening_hours: Optional[str] = Field(default=None, description="营业时间")
    price_level: Optional[str] = Field(default=None, description="价格等级: free/low/moderate/high")
    source_url: Optional[str] = Field(default=None, description="数据来源 URL")
    uncertainty_flags: list[str] = Field(
        default_factory=list, description="不确定性标注"
    )

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v: dict[str, float]) -> dict[str, float]:
        """验证坐标值范围"""
        lat = v.get("lat")
        lon = v.get("lon")
        if lat is None or lon is None:
            raise ValueError("坐标必须包含 lat 和 lon")
        if not (-90 <= lat <= 90):
            raise ValueError(f"纬度必须在 -90 到 90 之间，当前: {lat}")
        if not (-180 <= lon <= 180):
            raise ValueError(f"经度必须在 -180 到 180 之间，当前: {lon}")
        return v


class RouteSegment(BaseModel):
    """路线段 - 两个 POI 之间的交通信息"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "from_poi": "西湖",
            "to_poi": "灵隐寺",
            "distance_meters": 5200.0,
            "duration_seconds": 1800.0,
            "transportation_mode": "driving",
            "source": "OSRM",
        }
    })

    from_poi: str = Field(..., description="起点 POI 名称")
    to_poi: str = Field(..., description="终点 POI 名称")
    distance_meters: float = Field(..., ge=0, description="距离（米）")
    duration_seconds: float = Field(..., ge=0, description="预计耗时（秒）")
    transportation_mode: str = Field(
        ..., description="交通方式: walking/driving/cycling/transit"
    )
    source: str = Field(default="OSRM", description="数据来源")

    @property
    def distance_km(self) -> float:
        """获取距离（公里）"""
        return round(self.distance_meters / 1000, 2)

    @property
    def duration_minutes(self) -> float:
        """获取耗时（分钟）"""
        return round(self.duration_seconds / 60, 1)

    @property
    def duration_human(self) -> str:
        """获取人类可读的耗时描述"""
        total_minutes = self.duration_minutes
        hours = int(total_minutes // 60)
        minutes = int(total_minutes % 60)
        if hours > 0:
            return f"{hours}小时{minutes}分钟"
        return f"{minutes}分钟"


class BudgetBreakdown(BaseModel):
    """预算拆分项 - 某一类别的费用估算"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "category": "accommodation",
            "name_cn": "住宿",
            "estimated_min": 600.0,
            "estimated_max": 1500.0,
            "notes": "基于 hotel 类型，每晚200-500元",
            "uncertainty": "价格为估算区间，实际费用可能因季节、供需等因素有差异",
            "source": "基于历史数据和规则估算",
        }
    })

    category: str = Field(..., description="类别标识")
    name_cn: str = Field(..., description="中文名称")
    estimated_min: float = Field(..., ge=0, description="最低估算（元）")
    estimated_max: float = Field(..., ge=0, description="最高估算（元）")
    notes: Optional[str] = Field(default=None, description="备注说明")
    uncertainty: str = Field(
        default="价格为估算区间，实际费用可能因季节、供需等因素有差异",
        description="不确定性说明"
    )
    source: str = Field(default="基于历史数据和规则估算", description="数据来源")

    @property
    def average(self) -> float:
        """获取平均估算值"""
        return round((self.estimated_min + self.estimated_max) / 2, 2)


class WeatherInfo(BaseModel):
    """天气信息 - 单日的天气预报"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "date": "2025-08-01",
            "temperature_max": 35.0,
            "temperature_min": 26.0,
            "precipitation_probability": 30.0,
            "weather_code": 1,
            "description": "大部晴朗",
            "source": "Open-Meteo",
        }
    })

    date: str = Field(..., description="日期 YYYY-MM-DD")
    temperature_max: float = Field(..., description="最高温度（摄氏度）")
    temperature_min: float = Field(..., description="最低温度（摄氏度）")
    precipitation_probability: float = Field(
        default=0.0, ge=0, le=100, description="降水概率（%）"
    )
    weather_code: int = Field(..., description="WMO 天气代码")
    description: str = Field(..., description="天气描述")
    source: str = Field(default="Open-Meteo", description="数据来源")

    @property
    def is_rainy(self) -> bool:
        """判断是否为雨天（降水概率 > 50%）"""
        return self.precipitation_probability > 50

    @property
    def temperature_range(self) -> str:
        """获取温度范围描述"""
        return f"{self.temperature_min:.0f}°C ~ {self.temperature_max:.0f}°C"

    @property
    def weather_icon_hint(self) -> str:
        """获取天气图标提示"""
        code_map = {
            0: "sun", 1: "sun-cloud", 2: "cloud", 3: "cloud",
            45: "fog", 48: "fog",
            51: "drizzle", 53: "drizzle", 55: "drizzle",
            61: "rain", 63: "rain", 65: "rain",
            71: "snow", 73: "snow", 75: "snow",
            95: "thunder", 96: "thunder",
        }
        return code_map.get(self.weather_code, "unknown")


class DayPlan(BaseModel):
    """单日行程安排"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "day_number": 1,
            "date": "2025-08-01",
            "theme": "西湖自然风光",
            "schedule": [
                {"time": "09:00-11:00", "activity": "游览西湖", "reason": "早晨光线好，适合拍照"},
                {"time": "11:30-12:30", "activity": "楼外楼午餐", "reason": "品尝西湖醋鱼"},
            ],
            "weather": "大部晴朗，26~35°C",
            "transportation": "步行+公交",
            "budget_estimate": "500-800元",
        }
    })

    day_number: int = Field(..., ge=1, description="第几天")
    date: Optional[str] = Field(default=None, description="日期 YYYY-MM-DD")
    theme: str = Field(default="", description="当日主题")
    schedule: list[dict[str, Any]] = Field(
        default_factory=list, description="时间安排列表"
    )
    weather: Optional[str] = Field(default=None, description="当日天气描述")
    transportation: Optional[str] = Field(default=None, description="当日交通方式")
    budget_estimate: Optional[str] = Field(default=None, description="当日预算估算")


class Itinerary(BaseModel):
    """完整行程计划"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "杭州 3天情侣旅行计划",
            "summary": "西湖自然风光 + 美食文化之旅",
            "constraint_summary": "预算3000元，偏好自然和美食",
            "total_days": 3,
            "daily_plans": [],
            "total_budget_min": 2000,
            "total_budget_max": 3500,
            "budget_breakdown": [],
            "risk_alerts": [],
            "confirmation_items": [],
        }
    })

    title: str = Field(..., description="行程标题")
    summary: str = Field(default="", description="行程摘要")
    constraint_summary: str = Field(default="", description="约束条件摘要")
    total_days: int = Field(..., ge=1, description="总天数")
    daily_plans: list[DayPlan] = Field(default_factory=list, description="每日计划列表")
    total_budget_min: float = Field(default=0, ge=0, description="总预算下限")
    total_budget_max: float = Field(default=0, ge=0, description="总预算上限")
    budget_breakdown: list[BudgetBreakdown] = Field(
        default_factory=list, description="预算拆分详情"
    )
    risk_alerts: list[str] = Field(default_factory=list, description="风险提醒")
    confirmation_items: list[dict[str, Any]] = Field(
        default_factory=list, description="需人工确认的事项"
    )
    markdown_content: str = Field(default="", description="完整 Markdown 格式行程")


class ToolCallRecord(BaseModel):
    """工具调用记录 - 用于 Langfuse 追踪和调试"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "tool_name": "search_places",
            "input": {"lat": 30.25, "lon": 120.16, "radius": 5000},
            "output": {"places_count": 10},
            "latency_ms": 1200,
            "timestamp": "2025-07-01T10:00:00",
            "success": True,
            "error_message": None,
        }
    })

    tool_name: str = Field(..., description="工具名称")
    input: dict[str, Any] = Field(default_factory=dict, description="输入参数")
    output: dict[str, Any] = Field(default_factory=dict, description="输出结果")
    latency_ms: float = Field(default=0.0, ge=0, description="执行耗时（毫秒）")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(), description="调用时间"
    )
    success: bool = Field(default=True, description="是否成功")
    error_message: Optional[str] = Field(default=None, description="错误信息（如有）")


class AgentResponse(BaseModel):
    """Agent 响应结构 - API 返回的标准格式"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "session_id": "sess_abc123",
            "status": "complete",
            "current_step": "output_formatter",
            "message": "行程规划完成！",
            "itinerary": None,
            "tool_calls": [],
            "risk_alerts": [],
            "needs_clarification": False,
            "clarification_question": None,
            "trace_id": "trace_xyz789",
        }
    })

    session_id: str = Field(..., description="会话 ID")
    status: Literal["processing", "complete", "error", "clarifying"] = Field(
        default="processing", description="当前状态"
    )
    current_step: str = Field(default="", description="当前执行的步骤")
    message: str = Field(default="", description="给用户的消息")
    itinerary: Optional[Itinerary] = Field(default=None, description="行程结果（如已完成）")
    tool_calls: list[ToolCallRecord] = Field(
        default_factory=list, description="本次调用的工具记录"
    )
    risk_alerts: list[str] = Field(default_factory=list, description="风险提示")
    needs_clarification: bool = Field(default=False, description="是否需要澄清")
    clarification_question: Optional[str] = Field(
        default=None, description="追问问题（如需要澄清）"
    )
    trace_id: Optional[str] = Field(default=None, description="Langfuse Trace ID")


class PlanRequest(BaseModel):
    """创建行程规划的请求体"""

    user_input: str = Field(..., min_length=1, description="用户的自然语言输入")
    session_id: Optional[str] = Field(default=None, description="会话 ID（可选，首次调用自动生成）")


class ChatRequest(BaseModel):
    """聊天请求体"""

    message: str = Field(..., min_length=1, description="用户消息")
    session_id: str = Field(..., description="会话 ID")


class ChatMessage(BaseModel):
    """聊天消息"""

    role: Literal["user", "assistant", "system"] = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    node: Optional[str] = Field(default=None, description="来源节点（Agent 消息）")
    timestamp: Optional[str] = Field(
        default_factory=lambda: datetime.now().isoformat(), description="时间戳"
    )


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(default="ok", description="服务状态")
    version: str = Field(default="1.0.0", description="版本号")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(), description="检查时间"
    )
    dependencies: dict[str, str] = Field(
        default_factory=dict, description="依赖服务状态"
    )
