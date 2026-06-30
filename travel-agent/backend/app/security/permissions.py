"""
permissions.py - 权限分级系统

实现工具调用的权限分级控制，参考 Agent 安全最佳实践：
- Read: 搜索公开数据
- Draft: 写草稿、本地临时文件
- Internal Read: 查询内部只读数据
- External Write: 发邮件、发消息、提交表单
- Destructive: 删除、付款、取消订单
"""

from enum import Enum
from typing import Dict, Set


class PermissionLevel(str, Enum):
    """权限等级枚举

    从低到高排列，每个等级对应不同的操作风险和授权策略。
    """
    READ = "read"                   # 读取公开数据（搜索、查询天气等）
    DRAFT = "draft"                 # 写草稿、本地临时文件
    INTERNAL_READ = "internal_read"  # 查询内部只读数据
    EXTERNAL_WRITE = "external_write"  # 发邮件、发消息、提交表单
    DESTRUCTIVE = "destructive"      # 删除、付款、取消订单


# 高风险操作关键词（用于内容风险识别）
HIGH_RISK_KEYWORDS: Set[str] = {
    "预订", "付款", "支付", "下单", "购买", "预约",
    "取消订单", "退款", "改签",
    "删除", "修改", "提交表单",
    "booking", "payment", "pay", "order", "purchase",
    "cancel", "delete", "remove", "submit",
}

# 敏感信息正则模式（用于检测Secret泄露）
SENSITIVE_PATTERNS: Dict[str, str] = {
    "api_key": r"[a-zA-Z0-9_-]{32,64}",
    "credit_card": r"\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}",
    "id_card": r"\d{17}[\dXx]|\d{15}",
    "phone": r"1[3-9]\d{9}",
    "password": r"password[=:]\s*\S+|pwd[=:]\s*\S+|密码[=:]\s*\S+",
    "aws_key": r"AKIA[0-9A-Z]{16}",
    "openai_key": r"sk-[a-zA-Z0-9]{20,}",
    "jwt_token": r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
}


class PermissionManager:
    """权限管理器

    管理工具与权限等级的映射关系，提供权限检查功能。
    每个工具调用前必须通过 PermissionManager 检查权限。
    """

    # 工具权限映射表：工具名 -> 所需权限等级
    TOOL_PERMISSIONS: Dict[str, PermissionLevel] = {
        # READ 级别：只读公开数据
        "search_places": PermissionLevel.READ,
        "geocode_location": PermissionLevel.READ,
        "get_weather": PermissionLevel.READ,
        "estimate_route": PermissionLevel.READ,
        "estimate_budget": PermissionLevel.READ,
        "collect_preferences": PermissionLevel.READ,
        # EXTERNAL_WRITE 级别：需要人工确认
        "request_confirmation": PermissionLevel.EXTERNAL_WRITE,
    }

    # 用户角色到最大允许权限的映射
    ROLE_PERMISSIONS: Dict[str, PermissionLevel] = {
        "guest": PermissionLevel.READ,           # 访客只能读
        "user": PermissionLevel.EXTERNAL_WRITE,   # 普通用户可写
        "admin": PermissionLevel.DESTRUCTIVE,     # 管理员可执行危险操作
    }

    def get_tool_permission(self, tool_name: str) -> PermissionLevel:
        """获取工具的权限等级

        Args:
            tool_name: 工具名称

        Returns:
            PermissionLevel: 该工具所需的权限等级，未注册的工具默认 READ
        """
        return self.TOOL_PERMISSIONS.get(tool_name, PermissionLevel.READ)

    def check_permission(self, tool_name: str,
                         user_role: str = "user") -> bool:
        """检查用户是否有权限使用工具

        比较用户的角色权限是否大于等于工具所需的权限等级。

        Args:
            tool_name: 工具名称
            user_role: 用户角色（guest/user/admin）

        Returns:
            bool: True 表示用户有权限使用该工具
        """
        tool_permission = self.get_tool_permission(tool_name)
        user_max_permission = self.ROLE_PERMISSIONS.get(
            user_role, PermissionLevel.READ
        )

        # 权限等级排序（数值越大权限越高）
        permission_order = [
            PermissionLevel.READ,
            PermissionLevel.DRAFT,
            PermissionLevel.INTERNAL_READ,
            PermissionLevel.EXTERNAL_WRITE,
            PermissionLevel.DESTRUCTIVE,
        ]

        try:
            tool_level = permission_order.index(tool_permission)
            user_level = permission_order.index(user_max_permission)
        except ValueError:
            # 未知权限等级，默认拒绝
            return False

        return user_level >= tool_level

    def get_required_confirmation(self, tool_name: str) -> bool:
        """判断工具是否需要人工确认

        EXTERNAL_WRITE 及以上权限等级的工具需要人工确认。

        Args:
            tool_name: 工具名称

        Returns:
            bool: True 表示需要人工确认
        """
        tool_permission = self.get_tool_permission(tool_name)
        return tool_permission in [
            PermissionLevel.EXTERNAL_WRITE,
            PermissionLevel.DESTRUCTIVE,
        ]

    def get_permission_level_for_role(self, user_role: str) -> PermissionLevel:
        """获取角色对应的最大权限等级

        Args:
            user_role: 用户角色

        Returns:
            PermissionLevel: 该角色允许的最大权限等级
        """
        return self.ROLE_PERMISSIONS.get(user_role, PermissionLevel.READ)

    @classmethod
    def get_all_tools_at_permission(
        cls, permission: PermissionLevel
    ) -> list[str]:
        """获取指定权限等级的所有工具

        Args:
            permission: 权限等级

        Returns:
            list: 该权限等级下的所有工具名称
        """
        return [
            tool for tool, perm in cls.TOOL_PERMISSIONS.items()
            if perm == permission
        ]

    @classmethod
    def is_tool_registered(cls, tool_name: str) -> bool:
        """检查工具是否已在权限系统中注册

        Args:
            tool_name: 工具名称

        Returns:
            bool: True 表示工具已注册
        """
        return tool_name in cls.TOOL_PERMISSIONS


def authorize_tool_call(tool_name: str, user_role: str = "user") -> bool:
    """便捷函数：授权工具调用

    供外部模块快速检查工具调用权限。

    Args:
        tool_name: 工具名称
        user_role: 用户角色，默认为 "user"

    Returns:
        bool: 是否授权通过
    """
    manager = PermissionManager()
    return manager.check_permission(tool_name, user_role)
