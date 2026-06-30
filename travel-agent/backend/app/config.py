"""
Travel Agent 配置管理模块

使用 pydantic-settings 管理所有环境变量和配置项，
支持 .env 文件加载和类型验证。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 配置文件所在目录，用于定位 .env 文件
_CONFIG_DIR = Path(__file__).resolve().parent
_ENV_FILE = _CONFIG_DIR.parent / ".env"


class Settings(BaseSettings):
    """
    Travel Agent 全局配置类

    所有配置项均可通过环境变量或 .env 文件设置。
    环境变量名自动转换为大写。
    """

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==================== 应用基础配置 ====================
    app_name: str = Field(default="Travel Agent API", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    app_env: Literal["development", "testing", "production"] = Field(
        default="development", description="运行环境"
    )
    debug: bool = Field(default=False, description="调试模式")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="日志级别"
    )

    # ==================== OpenAI 配置 ====================
    openai_api_key: str = Field(default="", description="OpenAI API 密钥")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1", description="OpenAI API 基础 URL"
    )
    openai_model: str = Field(default="gpt-4o-mini", description="默认使用的大模型")
    openai_temperature: float = Field(default=0.3, description="LLM 温度参数", ge=0.0, le=2.0)
    openai_max_tokens: int = Field(default=4096, description="最大输出 token 数", gt=0)
    openai_timeout: int = Field(default=60, description="OpenAI API 超时时间（秒）", gt=0)

    # ==================== Langfuse 配置 ====================
    langfuse_public_key: str = Field(default="", description="Langfuse 公钥")
    langfuse_secret_key: str = Field(default="", description="Langfuse 私钥")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com", description="Langfuse 服务器地址"
    )
    langfuse_enabled: bool = Field(default=True, description="是否启用 Langfuse 观测")

    # ==================== OpenTripMap 配置 ====================
    opentripmap_api_key: str = Field(default="", description="OpenTripMap API 密钥")
    opentripmap_timeout: int = Field(default=15, description="OpenTripMap API 超时（秒）", gt=0)
    opentripmap_max_retries: int = Field(default=3, description="OpenTripMap 最大重试次数", ge=0)

    # ==================== Nominatim 配置 ====================
    nominatim_user_agent: str = Field(
        default="TravelAgent/1.0", description="Nominatim API User-Agent"
    )
    nominatim_timeout: int = Field(default=15, description="Nominatim API 超时（秒）", gt=0)
    nominatim_max_retries: int = Field(default=3, description="Nominatim 最大重试次数", ge=0)

    # ==================== OSRM 配置 ====================
    osrm_base_url: str = Field(
        default="http://router.project-osrm.org/route/v1",
        description="OSRM 路由服务基础 URL",
    )
    osrm_timeout: int = Field(default=15, description="OSRM API 超时（秒）", gt=0)
    osrm_max_retries: int = Field(default=3, description="OSRM 最大重试次数", ge=0)

    # ==================== Open-Meteo 配置 ====================
    openmeteo_timeout: int = Field(default=15, description="Open-Meteo API 超时（秒）", gt=0)
    openmeteo_max_retries: int = Field(default=3, description="Open-Meteo 最大重试次数", ge=0)

    # ==================== Mem0 配置 ====================
    mem0_api_key: str = Field(default="", description="Mem0 API 密钥")
    mem0_chroma_path: str = Field(
        default="./data/chroma_db", description="ChromaDB 持久化路径"
    )
    mem0_collection_name: str = Field(
        default="travel_memory", description="ChromaDB 集合名称"
    )

    # ==================== 安全相关配置 ====================
    max_iteration_count: int = Field(
        default=10, description="LangGraph 最大迭代次数（防循环）", gt=0
    )
    enable_safety_guard: bool = Field(default=True, description="是否启用安全审查")
    high_risk_keywords: list[str] = Field(
        default_factory=lambda: [
            "预订", "付款", "支付", "下单", "购买", "预约",
            "信用卡", "银行卡", "支付宝", "微信",
            "身份证", "护照", "证件号",
            "不可退款", "不可取消",
        ],
        description="高风险操作关键词列表",
    )

    # ==================== FastAPI 配置 ====================
    api_host: str = Field(default="0.0.0.0", description="API 监听地址")
    api_port: int = Field(default=8000, description="API 监听端口", gt=0, le=65535)
    api_workers: int = Field(default=1, description="API 工作进程数", ge=1)
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"],
        description="CORS 允许的源地址",
    )

    # ==================== 预算估算配置 ====================
    budget_city_tiers: dict[str, float] = Field(
        default_factory=lambda: {
            "杭州": 1.2, "上海": 1.5, "北京": 1.5, "深圳": 1.4,
            "成都": 0.9, "西安": 0.8, "昆明": 0.7, "拉萨": 1.0,
        },
        description="城市消费等级系数",
    )
    budget_accommodation_rates: dict[str, tuple[float, float]] = Field(
        default_factory=lambda: {
            "hotel": (200, 500),
            "hostel": (50, 150),
            "homestay": (150, 400),
            "resort": (500, 1500),
        },
        description="住宿类型基准价格（元/晚）",
    )
    budget_companion_multiplier: dict[str, float] = Field(
        default_factory=lambda: {
            "solo": 1.0, "couple": 0.7, "family": 1.3,
            "friends": 0.8, "group": 0.6,
        },
        description="同行人类型费用系数",
    )

    @property
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.app_env == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    获取全局配置单例

    使用 lru_cache 确保配置只被解析一次，提高性能。

    Returns:
        Settings: 全局配置实例
    """
    return Settings()


# 导出配置实例（向后兼容）
settings = get_settings()
