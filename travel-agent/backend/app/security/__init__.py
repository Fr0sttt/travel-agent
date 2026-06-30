"""
安全防护包

Travel Agent 的安全防护系统，实现完整的权限控制、Prompt Injection防护和Secret管理。

核心安全原则：
- 模型可以建议，系统负责授权
- 外部内容永远是数据，不是指令
- 高风险动作必须可审计、可确认、可回滚

模块说明：
- permissions.py: 权限分级系统
- guard.py: 安全守卫（核心授权检查）
- sanitizers.py: 数据清洗与输入验证
- human_in_loop.py: 高风险操作的人工确认
- audit_logger.py: 安全审计日志

使用示例：
    from security import SecurityGuard, authorize_tool_call

    # 创建安全守卫实例
    guard = SecurityGuard()

    # 授权工具调用
    result = await guard.authorize("search_places", {"query": "巴黎景点"})
    if result.allowed:
        # 执行工具调用
        ...
    else:
        # 处理拒绝
        print(result.reason)
"""

# 权限系统
from .permissions import (
    PermissionLevel,
    PermissionManager,
    authorize_tool_call,
    SENSITIVE_PATTERNS,
    HIGH_RISK_KEYWORDS,
)

# 安全守卫
from .guard import (
    SecurityGuard,
    SecurityResult,
    guard_authorize_tool_call,
    async_authorize_tool_call,
    security_guard,
)

# 数据清洗
from .sanitizers import (
    ContentSanitizer,
    InputValidator,
)

# 人工确认
from .human_in_loop import (
    HumanConfirmationManager,
    ConfirmationRequest,
    ConfirmedAction,
    ConfirmationStatus,
    ConfirmationMethod,
)

# 审计日志
from .audit_logger import (
    AuditLogger,
    get_audit_logger,
)

__all__ = [
    # 权限系统
    "PermissionLevel",
    "PermissionManager",
    "authorize_tool_call",
    "SENSITIVE_PATTERNS",
    "HIGH_RISK_KEYWORDS",
    # 安全守卫
    "SecurityGuard",
    "SecurityResult",
    "guard_authorize_tool_call",
    "async_authorize_tool_call",
    "security_guard",
    # 数据清洗
    "ContentSanitizer",
    "InputValidator",
    # 人工确认
    "HumanConfirmationManager",
    "ConfirmationRequest",
    "ConfirmedAction",
    "ConfirmationStatus",
    "ConfirmationMethod",
    # 审计日志
    "AuditLogger",
    "get_audit_logger",
]
