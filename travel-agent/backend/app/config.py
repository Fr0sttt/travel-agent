"""
Travel Agent 全局配置。

所有配置都支持通过环境变量或 `.env` 文件覆盖。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_CONFIG_DIR = Path(__file__).resolve().parent
_ENV_FILE = _CONFIG_DIR.parent / ".env"


class Settings(BaseSettings):
    """Travel Agent 全局配置类。"""

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
        default="development",
        description="运行环境",
    )
    debug: bool = Field(default=False, description="调试模式")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="日志级别",
    )

    # ==================== OpenAI 配置 ====================
    openai_api_key: str = Field(default="", description="OpenAI API 密钥")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API 基础 URL",
    )
    openai_model: str = Field(default="gpt-4o-mini", description="默认使用的大模型")
    openai_temperature: float = Field(
        default=0.3,
        description="LLM 温度参数",
        ge=0.0,
        le=2.0,
    )
    openai_max_tokens: int = Field(
        default=4096,
        description="最大输出 token 数",
        gt=0,
    )
    openai_timeout: int = Field(
        default=60,
        description="OpenAI API 超时时间（秒）",
        gt=0,
    )

    # ==================== Langfuse 配置 ====================
    langfuse_public_key: str = Field(default="", description="Langfuse 公钥")
    langfuse_secret_key: str = Field(default="", description="Langfuse 私钥")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        description="Langfuse 服务器地址",
    )
    langfuse_enabled: bool = Field(default=True, description="是否启用 Langfuse 观测")

    # ==================== OpenTripMap 配置 ====================
    opentripmap_api_key: str = Field(default="", description="OpenTripMap API 密钥")
    opentripmap_timeout: int = Field(
        default=15,
        description="OpenTripMap API 超时（秒）",
        gt=0,
    )
    opentripmap_max_retries: int = Field(
        default=3,
        description="OpenTripMap 最大重试次数",
        ge=0,
    )

    # ==================== Nominatim 配置 ====================
    nominatim_user_agent: str = Field(
        default="TravelAgent/1.0",
        description="Nominatim API User-Agent",
    )
    nominatim_timeout: int = Field(
        default=15,
        description="Nominatim API 超时（秒）",
        gt=0,
    )
    nominatim_max_retries: int = Field(
        default=3,
        description="Nominatim 最大重试次数",
        ge=0,
    )

    # ==================== OSRM 配置 ====================
    osrm_base_url: str = Field(
        default="http://router.project-osrm.org/route/v1",
        description="OSRM 路由服务基础 URL",
    )
    osrm_timeout: int = Field(default=15, description="OSRM API 超时（秒）", gt=0)
    osrm_max_retries: int = Field(default=3, description="OSRM 最大重试次数", ge=0)

    # ==================== Open-Meteo 配置 ====================
    openmeteo_timeout: int = Field(
        default=15,
        description="Open-Meteo API 超时（秒）",
        gt=0,
    )
    openmeteo_max_retries: int = Field(
        default=3,
        description="Open-Meteo 最大重试次数",
        ge=0,
    )

    # ==================== 高德 MCP 配置 ====================
    amap_maps_api_key: str = Field(
        default="b8d3f1cefd141df6a58386a2de081592",
        description="高德地图 API 密钥",
    )
    amap_mcp_enabled: bool = Field(default=True, description="是否启用高德 MCP 连接")
    amap_mcp_command: str = Field(default="npx", description="高德 MCP 启动命令")
    amap_mcp_args: list[str] = Field(
        default_factory=lambda: ["-y", "@amap/amap-maps-mcp-server"],
        description="高德 MCP 启动参数",
    )
    amap_mcp_cwd: str = Field(default="", description="高德 MCP 工作目录")
    amap_mcp_env: dict[str, str] = Field(
        default_factory=dict,
        description="高德 MCP 附加环境变量",
    )
    amap_mcp_request_timeout_seconds: int = Field(
        default=30,
        description="高德 MCP 接口超时时间（秒）",
        gt=0,
    )

    # ==================== JustOneAPI 小红书攻略源 ====================
    justoneapi_enabled: bool = Field(default=False, description="是否启用 JustOneAPI 小红书攻略搜索")
    justoneapi_key: str = Field(default="", description="JustOneAPI 访问令牌")
    justoneapi_base_url: str = Field(
        default="https://api.justoneapi.com",
        description="JustOneAPI 基础 URL，大陆网络不稳定时可改为 http://47.117.133.51:30015",
    )
    justoneapi_timeout: int = Field(default=30, description="JustOneAPI 请求超时（秒）", gt=0)
    justoneapi_cache_dir: str = Field(
        default="./runtime/justoneapi_cache",
        description="JustOneAPI 小红书搜索结果本地缓存目录",
    )
    justoneapi_cache_ttl_hours: int = Field(default=168, description="JustOneAPI 缓存有效期（小时）", ge=1)
    justoneapi_max_notes_per_plan: int = Field(default=12, description="每次规划最多解析的小红书笔记数", ge=1)
    justoneapi_max_pois_per_plan: int = Field(default=8, description="每次规划最多引入的小红书候选 POI 数", ge=1)

    # ==================== DeepSeek 提取配置 ====================
    deepseek_enabled: bool = Field(default=True, description="是否启用 DeepSeek 作为攻略候选抽取器")
    deepseek_api_key: str = Field(default="", description="DeepSeek API 密钥")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com",
        description="DeepSeek API 基础 URL",
    )
    deepseek_model: str = Field(
        default="deepseek-v4-flash",
        description="DeepSeek 候选抽取模型",
    )
    deepseek_timeout: int = Field(default=30, description="DeepSeek 请求超时（秒）", gt=0)
    deepseek_max_notes_per_request: int = Field(
        default=8,
        description="单次提交给 DeepSeek 的笔记数上限",
        ge=1,
    )

    # ==================== Mem0 配置 ====================
    mem0_api_key: str = Field(default="", description="Mem0 API 密钥")
    mem0_chroma_path: str = Field(
        default="./data/chroma_db",
        description="ChromaDB 持久化路径",
    )
    mem0_collection_name: str = Field(
        default="travel_memory",
        description="ChromaDB 集合名称",
    )

    # ==================== 记忆后端配置 ====================
    memory_backend: Literal["chromadb", "elasticsearch"] = Field(
        default="chromadb",
        description="长期记忆后端，默认使用 ChromaDB，需要时可切换为 Elasticsearch",
    )
    elasticsearch_url: str = Field(
        default="http://127.0.0.1:9200",
        description="Elasticsearch HTTP 地址",
    )
    elasticsearch_username: str = Field(
        default="",
        description="Elasticsearch 用户名",
    )
    elasticsearch_password: str = Field(
        default="",
        description="Elasticsearch 密码",
    )
    elasticsearch_index_prefix: str = Field(
        default="travel_memory",
        description="Elasticsearch 索引前缀",
    )
    elasticsearch_vector_dims: int = Field(
        default=384,
        description="Elasticsearch dense_vector 维度",
        gt=0,
    )

    # ==================== 会话历史 PostgreSQL ====================
    session_history_db_url: str = Field(
        default="postgresql+psycopg2://travel:travel@127.0.0.1:5432/travel_agent",
        description="会话历史 PostgreSQL 连接串",
    )

    # ==================== 安全相关配置 ====================
    max_iteration_count: int = Field(
        default=10,
        description="LangGraph 最大迭代次数（防止死循环）",
        gt=0,
    )
    enable_safety_guard: bool = Field(default=True, description="是否启用安全审查")
    high_risk_keywords: list[str] = Field(
        default_factory=lambda: [
            "预订",
            "付款",
            "支付",
            "下单",
            "购买",
            "预约",
            "信用卡",
            "银行卡",
            "支付宝",
            "微信",
            "身份证",
            "护照",
            "证件号",
            "不可退",
            "不可取消",
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
    frontend_dist_dir: str = Field(
        default="",
        description="前端静态文件目录，配置后后端可直接托管前端页面",
    )

    # ==================== SSH 隧道配置 ====================
    remote_middleware_ssh_enabled: bool = Field(
        default=False,
        description="是否通过 SSH 隧道连接远端中间件",
    )
    remote_middleware_ssh_host: str = Field(
        default="",
        description="远端 SSH 主机",
    )
    remote_middleware_ssh_port: int = Field(
        default=22,
        description="远端 SSH 端口",
        gt=0,
        le=65535,
    )
    remote_middleware_ssh_username: str = Field(
        default="",
        description="远端 SSH 用户名",
    )
    remote_middleware_ssh_password: str = Field(
        default="",
        description="远端 SSH 密码",
    )
    remote_middleware_auto_start: bool = Field(
        default=False,
        description="本地启动时是否自动触发远端中间件拉起",
    )
    remote_postgres_host: str = Field(
        default="127.0.0.1",
        description="远端 PostgreSQL 主机",
    )
    remote_postgres_port: int = Field(
        default=5432,
        description="远端 PostgreSQL 端口",
        gt=0,
        le=65535,
    )
    remote_elasticsearch_host: str = Field(
        default="127.0.0.1",
        description="远端 Elasticsearch 主机",
    )
    remote_elasticsearch_port: int = Field(
        default=9200,
        description="远端 Elasticsearch 端口",
        gt=0,
        le=65535,
    )
    local_postgres_port: int = Field(
        default=15432,
        description="本地 PostgreSQL 隧道端口",
        gt=0,
        le=65535,
    )
    local_elasticsearch_port: int = Field(
        default=19200,
        description="本地 Elasticsearch 隧道端口",
        gt=0,
        le=65535,
    )

    # ==================== 预算估算配置 ====================
    budget_city_tiers: dict[str, float] = Field(
        default_factory=lambda: {
            "杭州": 1.2,
            "上海": 1.5,
            "北京": 1.5,
            "深圳": 1.4,
            "成都": 0.9,
            "西安": 0.8,
            "昆明": 0.7,
            "拉萨": 1.0,
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
            "solo": 1.0,
            "couple": 0.7,
            "family": 1.3,
            "friends": 0.8,
            "group": 0.6,
        },
        description="同行人类型费用系数",
    )

    @property
    def is_production(self) -> bool:
        """判断是否为生产环境。"""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """判断是否为开发环境。"""
        return self.app_env == "development"


@lru_cache()
def get_settings() -> Settings:
    """获取全局配置单例。"""
    return Settings()


settings = get_settings()
