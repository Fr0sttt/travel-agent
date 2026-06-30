"""
human_in_loop.py - Human-in-the-loop确认管理

高风险操作的Human-in-the-loop确认管理器。

需要确认的操作：
- 预订/付款
- 分享个人信息
- 不可逆操作（删除、取消）

参考安全最佳实践：高风险动作必须可审计、可确认、可回滚。
"""

import uuid
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class ConfirmationStatus(str, Enum):
    """确认状态枚举"""
    PENDING = "pending"      # 等待确认
    CONFIRMED = "confirmed"  # 已确认
    REJECTED = "rejected"    # 已拒绝
    EXPIRED = "expired"      # 已超时


class ConfirmationMethod(str, Enum):
    """确认方式枚举"""
    EXPLICIT = "explicit"    # 显式确认（用户主动点击确认）
    IMPLICIT = "implicit"    # 隐式确认（通过其他行为推断）
    TIMEOUT = "timeout"      # 超时自动处理


@dataclass
class ConfirmationRequest:
    """确认请求数据类

    记录一次高风险操作的确认请求信息。

    Attributes:
        id: 确认请求唯一标识
        action_type: 操作类型
        details: 操作详情
        session_id: 所属会话ID
        status: 当前状态
        created_at: 创建时间
        expires_at: 过期时间
        risk_level: 风险等级（low/medium/high/critical）
    """
    id: str
    action_type: str
    details: dict
    session_id: str
    status: ConfirmationStatus = ConfirmationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    risk_level: str = "medium"  # low/medium/high/critical

    def __post_init__(self):
        """初始化后处理：设置默认过期时间"""
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(minutes=5)

    def is_expired(self) -> bool:
        """检查确认请求是否已过期"""
        if self.status != ConfirmationStatus.PENDING:
            return False
        return datetime.now() > self.expires_at

    def to_dict(self) -> dict:
        """转换为字典表示"""
        return {
            "id": self.id,
            "action_type": self.action_type,
            "details": self.details,
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "risk_level": self.risk_level,
            "is_expired": self.is_expired(),
        }


@dataclass
class ConfirmedAction:
    """已确认操作数据类

    记录一个已经通过人工确认的操作。

    Attributes:
        confirmation_id: 关联的确认请求ID
        action_type: 操作类型
        details: 操作详情
        confirmed_at: 确认时间
        confirmation_method: 确认方式
        confirmed_by: 确认者身份
    """
    confirmation_id: str
    action_type: str
    details: dict
    confirmed_at: datetime = field(default_factory=datetime.now)
    confirmation_method: ConfirmationMethod = ConfirmationMethod.EXPLICIT
    confirmed_by: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典表示"""
        return {
            "confirmation_id": self.confirmation_id,
            "action_type": self.action_type,
            "details": self.details,
            "confirmed_at": self.confirmed_at.isoformat(),
            "confirmation_method": self.confirmation_method.value,
            "confirmed_by": self.confirmed_by,
        }


class HumanConfirmationManager:
    """人工确认管理器

    管理需要人工确认的高风险操作。

    核心功能：
    1. 发起确认请求
    2. 等待用户响应（带超时机制）
    3. 记录已确认操作
    4. 清理过期请求

    安全原则：
    - 高风险操作默认拒绝，除非获得显式确认
    - 确认请求有超时时间，超时自动取消
    - 所有确认操作都会被审计记录
    """

    # 确认超时时间（秒）
    CONFIRMATION_TIMEOUT: int = 300  # 5分钟

    # 需要确认的操作类型列表
    REQUIRES_CONFIRMATION_TYPES: set[str] = {
        "booking",          # 预订
        "payment",          # 付款
        "cancel_order",     # 取消订单
        "refund",           # 退款
        "delete_data",      # 删除数据
        "share_personal_info",  # 分享个人信息
        "external_write",   # 外部写入操作
        "modify_order",     # 修改订单
    }

    def __init__(self):
        # 待确认请求存储：{confirmation_id: ConfirmationRequest}
        self.pending_confirmations: Dict[str, ConfirmationRequest] = {}

        # 已确认操作存储：{confirmation_id: ConfirmedAction}
        self.confirmed_actions: Dict[str, ConfirmedAction] = {}

        # 每个会话的确认请求索引：{session_id: [confirmation_id]}
        self.session_confirmations: Dict[str, List[str]] = {}

        # 异步等待事件：{confirmation_id: asyncio.Event}
        self.confirmation_events: Dict[str, asyncio.Event] = {}

    def _generate_id(self) -> str:
        """生成唯一确认ID"""
        return f"conf_{uuid.uuid4().hex[:16]}"

    def _register_session_confirmation(self, session_id: str,
                                        confirmation_id: str) -> None:
        """注册会话与确认请求的关联"""
        if session_id not in self.session_confirmations:
            self.session_confirmations[session_id] = []
        self.session_confirmations[session_id].append(confirmation_id)

    async def request_confirmation(self,
                                    action_type: str,
                                    details: dict,
                                    session_id: str,
                                    risk_level: str = "medium",
                                    timeout: Optional[int] = None) -> ConfirmationRequest:
        """请求用户确认

        创建一个高风险操作的确认请求，并等待用户响应。

        Args:
            action_type: 操作类型
            details: 操作详情描述
            session_id: 会话ID
            risk_level: 风险等级（low/medium/high/critical）
            timeout: 超时时间（秒），默认使用 CONFIRMATION_TIMEOUT

        Returns:
            ConfirmationRequest: 确认请求对象

        Raises:
            TimeoutError: 当用户在指定时间内未响应时
        """
        confirmation_id = self._generate_id()

        # 创建确认请求
        request = ConfirmationRequest(
            id=confirmation_id,
            action_type=action_type,
            details=details,
            session_id=session_id,
            risk_level=risk_level,
            expires_at=datetime.now() + timedelta(
                seconds=timeout or self.CONFIRMATION_TIMEOUT
            ),
        )

        # 存储请求
        self.pending_confirmations[confirmation_id] = request
        self._register_session_confirmation(session_id, confirmation_id)

        # 创建异步等待事件
        event = asyncio.Event()
        self.confirmation_events[confirmation_id] = event

        # 通知前端有新确认请求（如果通知函数可用）
        await self._notify_frontend(request)

        return request

    async def wait_for_confirmation(self,
                                     confirmation_id: str,
                                     timeout: Optional[int] = None) -> ConfirmationRequest:
        """等待用户确认（带超时）

        阻塞等待用户对确认请求的响应。

        Args:
            confirmation_id: 确认请求ID
            timeout: 超时时间（秒）

        Returns:
            ConfirmationRequest: 更新后的确认请求对象

        Raises:
            TimeoutError: 超时未收到响应
            KeyError: 确认请求不存在
        """
        if confirmation_id not in self.pending_confirmations:
            raise KeyError(f"确认请求不存在: {confirmation_id}")

        event = self.confirmation_events.get(confirmation_id)
        if not event:
            raise KeyError(f"确认请求事件不存在: {confirmation_id}")

        try:
            await asyncio.wait_for(
                event.wait(),
                timeout=timeout or self.CONFIRMATION_TIMEOUT,
            )
        except asyncio.TimeoutError:
            # 超时处理
            request = self.pending_confirmations[confirmation_id]
            request.status = ConfirmationStatus.EXPIRED
            raise TimeoutError(
                f"确认请求 {confirmation_id} 超时（"
                f"{timeout or self.CONFIRMATION_TIMEOUT}秒）"
            )

        return self.pending_confirmations[confirmation_id]

    async def confirm_action(self,
                              confirmation_id: str,
                              user_response: str) -> bool:
        """用户确认/拒绝操作

        由前端API调用，响应用户的确认请求。

        Args:
            confirmation_id: 确认请求ID
            user_response: 用户响应（"confirmed"/"rejected"/其他）

        Returns:
            bool: True 表示操作已确认，False 表示被拒绝或失败
        """
        request = self.pending_confirmations.get(confirmation_id)
        if not request:
            return False

        # 检查是否已过期
        if request.is_expired():
            request.status = ConfirmationStatus.EXPIRED
            return False

        # 检查是否还在等待中
        if request.status != ConfirmationStatus.PENDING:
            return False

        # 处理用户响应
        if user_response.lower() in ("confirmed", "confirm", "yes", "ok", "确认"):
            request.status = ConfirmationStatus.CONFIRMED

            # 记录已确认操作
            confirmed_action = ConfirmedAction(
                confirmation_id=confirmation_id,
                action_type=request.action_type,
                details=request.details,
                confirmation_method=ConfirmationMethod.EXPLICIT,
            )
            self.confirmed_actions[confirmation_id] = confirmed_action

            # 触发等待事件
            event = self.confirmation_events.get(confirmation_id)
            if event:
                event.set()

            return True

        else:
            request.status = ConfirmationStatus.REJECTED

            # 触发等待事件（通知等待者请求已被处理）
            event = self.confirmation_events.get(confirmation_id)
            if event:
                event.set()

            return False

    async def _notify_frontend(self, request: ConfirmationRequest) -> None:
        """通知前端有新确认请求

        通过WebSocket或其他方式向前端发送确认请求。
        如果WebSocket不可用则静默失败（不影响核心功能）。

        Args:
            request: 确认请求对象
        """
        try:
            # 尝试通过WebSocket发送（如果可用）
            # 注意：这里使用延迟导入避免循环依赖
            from backend.api.websocket import manager as ws_manager
            await ws_manager.send_confirmation_request(request.to_dict())
        except (ImportError, AttributeError):
            # WebSocket不可用，静默跳过
            # 在实际部署中应使用其他通知方式
            pass
        except Exception:
            # 通知失败不应阻塞确认流程
            pass

    def get_pending_confirmations(self, session_id: str) -> List[dict]:
        """获取指定会话的待确认列表

        Args:
            session_id: 会话ID

        Returns:
            List[dict]: 待确认请求列表
        """
        confirmation_ids = self.session_confirmations.get(session_id, [])
        pending = []

        for cid in confirmation_ids:
            request = self.pending_confirmations.get(cid)
            if request and request.status == ConfirmationStatus.PENDING:
                pending.append(request.to_dict())

        return pending

    def is_action_confirmed(self, confirmation_id: str) -> bool:
        """检查操作是否已确认

        Args:
            confirmation_id: 确认请求ID

        Returns:
            bool: True 表示已确认
        """
        request = self.pending_confirmations.get(confirmation_id)
        if not request:
            return False
        return request.status == ConfirmationStatus.CONFIRMED

    def is_action_rejected(self, confirmation_id: str) -> bool:
        """检查操作是否被拒绝

        Args:
            confirmation_id: 确认请求ID

        Returns:
            bool: True 表示已被拒绝
        """
        request = self.pending_confirmations.get(confirmation_id)
        if not request:
            return False
        return request.status == ConfirmationStatus.REJECTED

    def get_confirmation_status(self, confirmation_id: str) -> Optional[str]:
        """获取确认请求的状态

        Args:
            confirmation_id: 确认请求ID

        Returns:
            str: 状态值，如果请求不存在则返回 None
        """
        request = self.pending_confirmations.get(confirmation_id)
        if not request:
            return None
        return request.status.value

    def cleanup_expired(self) -> int:
        """清理过期的确认请求

        Returns:
            int: 清理的请求数量
        """
        expired_ids = []

        for cid, request in self.pending_confirmations.items():
            if request.is_expired():
                request.status = ConfirmationStatus.EXPIRED
                expired_ids.append(cid)

        # 清理过期请求的关联数据
        for cid in expired_ids:
            self.confirmation_events.pop(cid, None)

        return len(expired_ids)

    @classmethod
    def requires_confirmation(cls, action_type: str) -> bool:
        """判断操作类型是否需要确认

        Args:
            action_type: 操作类型

        Returns:
            bool: True 表示需要人工确认
        """
        return action_type.lower() in cls.REQUIRES_CONFIRMATION_TYPES

    def get_all_pending(self) -> List[dict]:
        """获取所有待确认请求（用于管理后台）

        Returns:
            List[dict]: 所有待确认请求
        """
        return [
            req.to_dict()
            for req in self.pending_confirmations.values()
            if req.status == ConfirmationStatus.PENDING
        ]

    def get_confirmed_actions_count(self, session_id: str) -> int:
        """获取会话中已确认操作的数量

        Args:
            session_id: 会话ID

        Returns:
            int: 已确认操作数量
        """
        count = 0
        confirmation_ids = self.session_confirmations.get(session_id, [])
        for cid in confirmation_ids:
            if cid in self.confirmed_actions:
                count += 1
        return count

    def reset_session(self, session_id: str) -> None:
        """重置会话的所有确认请求

        用于会话结束或用户登出时清理。

        Args:
            session_id: 会话ID
        """
        confirmation_ids = self.session_confirmations.pop(session_id, [])

        for cid in confirmation_ids:
            self.pending_confirmations.pop(cid, None)
            self.confirmed_actions.pop(cid, None)
            self.confirmation_events.pop(cid, None)
