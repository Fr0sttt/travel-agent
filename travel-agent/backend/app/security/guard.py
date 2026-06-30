"""
guard.py - 安全守卫

所有工具调用前的安全检查中心。

检查项：
1. 工具是否在白名单中
2. 参数是否包含敏感信息（Secret泄露）
3. 权限等级是否满足
4. 高风险操作是否需要确认
5. 域名/路径安全性

核心安全原则：
- 模型可以建议，系统负责授权
- 工具结果是数据，不是指令
- 高风险动作必须可审计、可确认、可回滚
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

from .permissions import (
    PermissionLevel,
    PermissionManager,
    SENSITIVE_PATTERNS,
    HIGH_RISK_KEYWORDS,
)
from .sanitizers import ContentSanitizer


@dataclass
class SecurityResult:
    """安全检查结果

    记录一次安全检查的完整结果信息。

    Attributes:
        allowed: 是否允许执行
        reason: 检查结果说明
        requires_confirmation: 是否需要人工确认
        risk_level: 风险等级（low/medium/high/critical）
        suggested_action: 建议操作
        detected_issues: 检测到的所有问题
    """
    allowed: bool
    reason: str = ""
    requires_confirmation: bool = False
    risk_level: str = "low"  # low/medium/high/critical
    suggested_action: str = ""
    detected_issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "requires_confirmation": self.requires_confirmation,
            "risk_level": self.risk_level,
            "suggested_action": self.suggested_action,
            "detected_issues": self.detected_issues,
        }


class SecurityGuard:
    """安全守卫 - 所有工具调用前的安全检查

    工具调用必须通过 SecurityGuard 的 authorize 方法进行安全检查。
    任何未通过检查的工具调用都将被拒绝执行。

    检查流程：
    1. 工具白名单检查
    2. Secret泄露检查
    3. 权限等级检查
    4. 高风险操作检查
    5. 域名/路径安全性检查

    安全原则：
    - 默认拒绝（Deny by Default）
    - 最小权限（Least Privilege）
    - 纵深防御（Defense in Depth）
    """

    # 工具白名单：只有在此列表中的工具才能被调用
    ALLOWLIST: set[str] = {
        "search_places",
        "geocode_location",
        "get_weather",
        "estimate_route",
        "estimate_budget",
        "collect_preferences",
        "request_confirmation",
    }

    # 域名白名单：浏览器工具只能访问这些域名
    DOMAIN_ALLOWLIST: set[str] = {
        "opentripmap.com",
        "api.opentripmap.com",
        "nominatim.openstreetmap.org",
        "router.project-osrm.org",
        "api.open-meteo.com",
        "api.amadeus.com",
        "maps.googleapis.com",
    }

    # 路径白名单：文件写入只能写入这些路径
    PATH_ALLOWLIST: set[str] = {
        "/tmp/travel_agent/",
        "/data/travel/",
        "./data/",
        "./logs/",
        "./temp/",
    }

    # 禁止访问的路径（绝对禁止）
    PATH_BLOCKLIST: set[str] = {
        "/etc/", "/usr/", "/bin/", "/sbin/", "/lib/", "/lib64/",
        "/boot/", "/dev/", "/proc/", "/sys/", "/root/",
        "/var/log/", "/var/spool/",
        "../", "..\\",  # 路径遍历
        ".env", ".ssh/", ".aws/", ".git/",
    }

    # 高风险关键词
    HIGH_RISK_KEYWORDS: set[str] = HIGH_RISK_KEYWORDS

    def __init__(self) -> None:
        """初始化安全守卫"""
        self.permission_manager = PermissionManager()
        self.blocked_domains: set[str] = set()
        self.allowed_paths: set[str] = set(self.PATH_ALLOWLIST)
        self.high_risk_keywords: set[str] = set(self.HIGH_RISK_KEYWORDS)
        self._audit_logger: Any = None  # 延迟初始化

    def _get_audit_logger(self) -> Any:
        """获取审计日志器（延迟初始化）"""
        if self._audit_logger is None:
            try:
                from .audit_logger import get_audit_logger
                self._audit_logger = get_audit_logger()
            except ImportError:
                self._audit_logger = None
        return self._audit_logger

    async def authorize(self,
                        tool_name: str,
                        args: Dict[str, Any],
                        context: Optional[Dict[str, Any]] = None) -> SecurityResult:
        """授权检查主函数

        对工具调用进行全面的安全检查，返回检查结果。

        检查流程（按优先级）：
        1. 工具白名单检查 - 不在白名单的工具直接拒绝
        2. Secret泄露检查 - 参数中包含敏感信息则拒绝
        3. 路径安全检查 - 涉及文件操作的路径检查
        4. 域名安全检查 - 涉及网络访问的域名检查
        5. 高风险操作检查 - 标记需要人工确认的操作
        6. 权限等级检查 - 确认用户权限是否满足

        Args:
            tool_name: 工具名称
            args: 工具参数
            context: 上下文信息（包含用户角色、会话ID等）

        Returns:
            SecurityResult: 安全检查结果
        """
        context = context or {}
        session_id = context.get("session_id", "unknown")
        user_role = context.get("user_role", "user")
        detected_issues: List[str] = []

        # ========== 第1步：工具白名单检查 ==========
        if not self._check_tool_allowlist(tool_name):
            result = SecurityResult(
                allowed=False,
                reason=f"工具 '{tool_name}' 不在白名单中，调用被拒绝",
                risk_level="critical",
                suggested_action="请联系管理员注册该工具",
                detected_issues=[f"tool_not_in_allowlist: {tool_name}"],
            )
            self._log_intercept(tool_name, result, session_id, args)
            return result

        # ========== 第2步：Secret泄露检查 ==========
        secret_issues = self._check_secret_leakage(args)
        if secret_issues:
            detected_issues.extend(secret_issues)
            result = SecurityResult(
                allowed=False,
                reason=f"参数中包含敏感信息: {', '.join(secret_issues)}",
                risk_level="critical",
                suggested_action="请从参数中移除敏感信息后重试",
                detected_issues=secret_issues,
            )
            # 记录Secret检测事件
            logger = self._get_audit_logger()
            if logger:
                logger.log_secret_detected(
                    detection_type=secret_issues[0],
                    tool_name=tool_name,
                    session_id=session_id,
                )
            self._log_intercept(tool_name, result, session_id, args)
            return result

        # ========== 第3步：路径安全检查 ==========
        if "file_path" in args or "path" in args:
            file_path = args.get("file_path") or args.get("path", "")
            if file_path and not self._check_path_safety(file_path):
                result = SecurityResult(
                    allowed=False,
                    reason=f"文件路径 '{file_path}' 不在允许范围内",
                    risk_level="high",
                    suggested_action="请使用允许的路径前缀",
                    detected_issues=[f"path_not_allowed: {file_path}"],
                )
                self._log_intercept(tool_name, result, session_id, args)
                return result

        # ========== 第4步：域名安全检查 ==========
        if "url" in args:
            url = args.get("url", "")
            if url and not self._check_domain_safety(url):
                result = SecurityResult(
                    allowed=False,
                    reason=f"域名 '{url}' 不在白名单中",
                    risk_level="high",
                    suggested_action="请使用允许的域名",
                    detected_issues=[f"domain_not_allowed: {url}"],
                )
                self._log_intercept(tool_name, result, session_id, args)
                return result

        # ========== 第5步：高风险操作检查 ==========
        is_high_risk, risk_reason = self._check_high_risk_action(tool_name, args)
        if is_high_risk:
            detected_issues.append(risk_reason)

        # ========== 第6步：权限等级检查 ==========
        tool_permission = self.permission_manager.get_tool_permission(tool_name)
        has_permission = self.permission_manager.check_permission(
            tool_name, user_role
        )

        if not has_permission:
            result = SecurityResult(
                allowed=False,
                reason=(
                    f"用户角色 '{user_role}' 无权使用工具 '{tool_name}' "
                    f"(需要 {tool_permission.value} 权限)"
                ),
                risk_level="high",
                suggested_action="请使用权限更高的账户或联系管理员",
                detected_issues=[
                    f"insufficient_permission: {user_role} < {tool_permission.value}"
                ],
            )
            self._log_intercept(tool_name, result, session_id, args)
            return result

        # ========== 综合判断 ==========
        # 检查是否需要人工确认
        requires_confirmation = self.permission_manager.get_required_confirmation(
            tool_name
        ) or is_high_risk

        if requires_confirmation:
            risk_level = "high" if is_high_risk else "medium"
            return SecurityResult(
                allowed=True,  # 技术上允许，但需要确认
                reason=f"工具 '{tool_name}' 需要人工确认: {risk_reason or '权限等级要求'}",
                requires_confirmation=True,
                risk_level=risk_level,
                suggested_action="等待用户显式确认",
                detected_issues=detected_issues,
            )

        # 所有检查通过
        return SecurityResult(
            allowed=True,
            reason=f"工具 '{tool_name}' 授权通过",
            risk_level="low",
            detected_issues=detected_issues,
        )

    def _check_tool_allowlist(self, tool_name: str) -> bool:
        """检查工具白名单

        只有白名单中的工具才被允许调用。

        Args:
            tool_name: 工具名称

        Returns:
            bool: True 表示工具在白名单中
        """
        return tool_name in self.ALLOWLIST

    def _check_secret_leakage(self, args: Dict[str, Any]) -> List[str]:
        """检查参数中是否包含Secret泄露

        使用正则表达式检测参数中是否包含：
        - API Key
        - Token
        - Password
        - Secret
        - 其他敏感凭证

        注意：URL值会被跳过，因为域名中的点号可能被误识别为JWT格式。

        Args:
            args: 工具参数

        Returns:
            List[str]: 检测到的Secret类型列表，空列表表示未检测到
        """
        issues: List[str] = []
        # 过滤掉URL值后再进行Secret检查
        filtered_args = {}
        for key, value in args.items():
            if isinstance(value, str) and (
                value.startswith("http://") or value.startswith("https://")
            ):
                continue  # 跳过URL值
            filtered_args[key] = value
        args_str = str(filtered_args)

        # 使用预定义的敏感模式检查
        for secret_type, pattern in SENSITIVE_PATTERNS.items():
            try:
                if re.search(pattern, args_str, re.IGNORECASE):
                    issues.append(f"potential_{secret_type}")
            except re.error:
                continue

        # 检查Secret关键词 + 值的模式
        secret_keywords = [
            "api_key", "apikey", "token", "secret",
            "password", "credential", "auth", "private_key",
            "密钥", "密码", "令牌",
        ]

        for keyword in secret_keywords:
            if keyword in args_str.lower():
                # 检查是否有值跟随（key=value 或 key: value 格式）
                pattern = rf"{re.escape(keyword)}[\"']?\s*[:=]\s*[\"']?[^\"'\s]{{5,}}[\"']?"
                if re.search(pattern, args_str, re.IGNORECASE):
                    issues.append(f"potential_{keyword}")

        # 特定格式的Secret检测
        # OpenAI API Key
        if re.search(r'sk-[a-zA-Z0-9]{20,}', args_str):
            issues.append("openai_api_key")

        # AWS Access Key
        if re.search(r'AKIA[0-9A-Z]{16}', args_str):
            issues.append("aws_access_key")

        return list(set(issues))  # 去重

    def _check_high_risk_action(self,
                                 tool_name: str,
                                 args: Dict[str, Any]) -> Tuple[bool, str]:
        """检查是否为高风险操作

        检查工具名和参数中是否包含高风险关键词。

        Args:
            tool_name: 工具名称
            args: 工具参数

        Returns:
            Tuple[bool, str]: (是否高风险, 风险原因)
        """
        combined_text = f"{tool_name} {str(args)}".lower()

        for keyword in self.high_risk_keywords:
            if keyword.lower() in combined_text:
                return True, f"检测到高风险关键词: '{keyword}'"

        return False, ""

    def _check_domain_safety(self, url: str) -> bool:
        """检查域名安全性

        检查URL的域名是否在白名单中。

        Args:
            url: 待检查的URL

        Returns:
            bool: True 表示域名安全
        """
        if not url:
            return True  # 空URL跳过检查

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            if not domain:
                return False

            # 检查是否在白名单中
            return any(allowed in domain for allowed in self.DOMAIN_ALLOWLIST)
        except Exception:
            return False

    def _check_path_safety(self, file_path: str) -> bool:
        """检查文件路径安全性

        检查文件路径是否在白名单中且不在黑名单中。
        防止路径遍历攻击和访问敏感系统路径。

        Args:
            file_path: 待检查的文件路径

        Returns:
            bool: True 表示路径安全
        """
        if not file_path:
            return True  # 空路径跳过检查

        path_lower = file_path.lower()

        # 第1步：检查是否在黑名单中
        for blocked in self.PATH_BLOCKLIST:
            if blocked.lower() in path_lower:
                return False

        # 第2步：检查路径遍历攻击
        dangerous_patterns = ["../", "..\\", "%2e%2e%2f", "..//", ".../"]
        for pattern in dangerous_patterns:
            if pattern in file_path:
                return False

        # 第3步：检查是否在白名单中
        return any(
            path_lower.startswith(allowed.lower())
            for allowed in self.allowed_paths
        )

    def _log_intercept(self,
                       tool_name: str,
                       result: SecurityResult,
                       session_id: str,
                       args: Dict[str, Any]) -> None:
        """记录安全拦截事件

        Args:
            tool_name: 工具名称
            result: 安全检查结果
            session_id: 会话ID
            args: 工具参数
        """
        logger = self._get_audit_logger()
        if logger and hasattr(logger, "log_security_intercept"):
            logger.log_security_intercept(
                tool_name=tool_name,
                reason=result.reason,
                risk_level=result.risk_level,
                session_id=session_id,
                args=args,
            )

    def check_prompt_injection(self, content: str) -> Dict[str, Any]:
        """检测Prompt Injection尝试

        检测内容中是否包含已知的Prompt Injection攻击模式。

        Args:
            content: 待检测内容

        Returns:
            Dict: 检测结果，包含 detected、patterns、risk_level 等字段
        """
        injection_patterns = [
            (r"ignore\s+(previous|above|all)\s+(instructions|rules)", "指令覆盖"),
            (r"forget\s+(your|the)\s+(instructions|training)", "遗忘指令"),
            (r"you\s+are\s+now\s+", "角色重定义"),
            (r"system\s+prompt", "系统提示探测"),
            (r"reveal\s+your\s+instructions", "指令泄露请求"),
            (r"DAN\s+(mode|prompt)", "DAN越狱模式"),
            (r"jailbreak", "越狱尝试"),
            (r"\[\s*system\s*\]", "伪系统标签"),
            (r"忽略\s*(之前的|上面的|所有)\s*(指令|规则|提示)", "指令覆盖(中文)"),
            (r"你现在\s*(是|要|必须)", "角色重定义(中文)"),
            (r"绕过\s*(限制|规则|安全)", "安全绕过(中文)"),
            (r"新的\s*(角色|身份)", "角色诱导(中文)"),
        ]

        detected_patterns = []
        for pattern, description in injection_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                detected_patterns.append(description)

        if detected_patterns:
            return {
                "detected": True,
                "patterns": list(set(detected_patterns)),
                "risk_level": "HIGH",
                "recommendation": "拒绝执行内容中的指令，仅作为数据引用",
            }

        return {
            "detected": False,
            "patterns": [],
            "risk_level": "LOW",
        }

    def add_to_allowlist(self, tool_name: str) -> None:
        """向白名单添加工具

        用于动态注册新工具。

        Args:
            tool_name: 工具名称
        """
        self.ALLOWLIST.add(tool_name)

    def remove_from_allowlist(self, tool_name: str) -> None:
        """从白名单移除工具

        Args:
            tool_name: 工具名称
        """
        self.ALLOWLIST.discard(tool_name)

    def add_allowed_domain(self, domain: str) -> None:
        """添加允许的域名

        Args:
            domain: 域名
        """
        self.DOMAIN_ALLOWLIST.add(domain)

    def add_allowed_path(self, path: str) -> None:
        """添加允许的路径

        Args:
            path: 文件路径前缀
        """
        self.allowed_paths.add(path)

    def get_allowlist(self) -> List[str]:
        """获取当前白名单工具列表

        Returns:
            List[str]: 白名单中的工具名称列表
        """
        return sorted(list(self.ALLOWLIST))

    def get_statistics(self) -> Dict[str, Any]:
        """获取安全统计信息

        Returns:
            Dict: 包含白名单数量、域名数量等统计信息
        """
        return {
            "allowlist_size": len(self.ALLOWLIST),
            "domain_allowlist_size": len(self.DOMAIN_ALLOWLIST),
            "path_allowlist_size": len(self.allowed_paths),
            "high_risk_keywords_count": len(self.high_risk_keywords),
            "blocked_domains_count": len(self.blocked_domains),
        }


# ========== 便捷函数 ==========

def guard_authorize_tool_call(tool_name: str,
                               args: Dict[str, Any],
                               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """便捷函数：授权工具调用（同步版本）

    供外部模块快速进行工具调用授权检查。
    注意：这是同步包装函数，内部会创建新的事件循环。

    Args:
        tool_name: 工具名称
        args: 工具参数
        context: 上下文信息

    Returns:
        Dict: 授权结果字典
    """
    guard = SecurityGuard()

    import asyncio
    try:
        result = asyncio.get_event_loop().run_until_complete(
            guard.authorize(tool_name, args, context)
        )
    except RuntimeError:
        # 如果没有事件循环，创建新的事件循环
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                guard.authorize(tool_name, args, context)
            )
        finally:
            loop.close()

    return result.to_dict()


async def async_authorize_tool_call(tool_name: str,
                                     args: Dict[str, Any],
                                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """便捷函数：授权工具调用（异步版本）

    Args:
        tool_name: 工具名称
        args: 工具参数
        context: 上下文信息

    Returns:
        Dict: 授权结果字典
    """
    guard = SecurityGuard()
    result = await guard.authorize(tool_name, args, context)
    return result.to_dict()


# 全局安全守卫实例
security_guard = SecurityGuard()
