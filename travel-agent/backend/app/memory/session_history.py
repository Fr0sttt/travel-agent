"""会话历史的 PostgreSQL 持久化存储。

这里负责两类数据：
1. 逐条消息：用于前端切换会话后重新渲染聊天记录
2. 会话摘要：用于会话列表、最近更新时间、标题和状态快照
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, create_engine, delete, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类。"""


class ChatSession(Base):
    """会话摘要表。"""

    __tablename__ = "chat_sessions"

    session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="新会话")
    preview: Mapped[str] = mapped_column(Text, nullable=False, default="")
    state_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class ChatMessage(Base):
    """会话消息表。"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


@dataclass(slots=True)
class SessionSummary:
    """给前端会话列表用的轻量摘要。"""

    session_id: str
    title: str
    preview: str
    message_count: int
    created_at: str
    updated_at: str
    last_message_at: str


class SessionHistoryStore:
    """PostgreSQL 会话历史存储。"""

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        connect_retries: int = 30,
        connect_retry_interval: float = 2.0,
    ):
        if not database_url:
            raise ValueError("session_history_db_url 不能为空")

        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            echo=echo,
            future=True,
            pool_pre_ping=True,
        )
        self._session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )

        last_error: Exception | None = None
        for attempt in range(1, connect_retries + 1):
            try:
                with self.engine.connect():
                    pass
                Base.metadata.create_all(self.engine)
                break
            except Exception as exc:
                last_error = exc
                if attempt >= connect_retries:
                    raise RuntimeError(
                        "PostgreSQL 暂时不可用，已重试多次仍未连接成功。"
                        "请先确认服务器上的数据库中间件已启动。"
                    ) from exc
                time.sleep(connect_retry_interval)

        if last_error is not None:
            last_error = None

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _ensure_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def _compact_text(text: str, limit: int) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 1].rstrip() + "…"

    @classmethod
    def _derive_title(
        cls,
        state: dict[str, Any] | None = None,
        fallback_text: str | None = None,
    ) -> str:
        state = state or {}
        preference = state.get("preference") if isinstance(state, dict) else {}
        if isinstance(preference, dict):
            destination = preference.get("destination")
            if destination:
                return cls._compact_text(f"{destination} 行程", 40)

        destination = state.get("destination") if isinstance(state, dict) else None
        if destination:
            return cls._compact_text(f"{destination} 行程", 40)

        if fallback_text:
            return cls._compact_text(fallback_text, 40)

        return "新会话"

    @classmethod
    def _derive_preview(
        cls,
        state: dict[str, Any] | None = None,
        fallback_text: str | None = None,
    ) -> str:
        state = state or {}
        itinerary = state.get("itinerary") if isinstance(state, dict) else None
        if isinstance(itinerary, str) and itinerary.strip():
            return cls._compact_text(itinerary.strip(), 80)

        if fallback_text:
            return cls._compact_text(fallback_text, 80)

        return "暂无内容"

    def _open(self) -> Session:
        return self._session_factory()

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """追加一条消息，并同步更新会话摘要。"""
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False, default=str)
        now = self._now()

        with self._open() as db:
            db.add(
                ChatMessage(
                    session_id=session_id,
                    role=role,
                    content=content,
                    metadata_json=metadata_json,
                    created_at=now,
                )
            )

            summary = db.get(ChatSession, session_id)
            if summary is None:
                summary = ChatSession(session_id=session_id)
                db.add(summary)

            summary.message_count = (summary.message_count or 0) + 1
            summary.preview = self._derive_preview(
                state=metadata.get("state") if metadata else None,
                fallback_text=content,
            )
            if not summary.title or summary.title == "新会话":
                summary.title = self._derive_title(
                    state=metadata.get("state") if metadata else None,
                    fallback_text=content,
                )
            summary.last_message_at = now
            db.commit()

    def append_turn(
        self,
        session_id: str,
        user_input: str,
        assistant_output: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """把一轮对话拆成 user / assistant 两条消息保存。"""
        self.append_message(
            session_id=session_id,
            role="user",
            content=user_input,
            metadata=metadata,
        )
        self.append_message(
            session_id=session_id,
            role="assistant",
            content=assistant_output,
            metadata=metadata,
        )

    def save_session_snapshot(
        self,
        session_id: str,
        state: dict[str, Any],
        title_hint: str | None = None,
        preview_hint: str | None = None,
    ) -> None:
        """保存当前会话状态快照，供切换会话时恢复。"""
        payload = self._ensure_text(state)
        now = self._now()

        with self._open() as db:
            summary = db.get(ChatSession, session_id)
            if summary is None:
                summary = ChatSession(session_id=session_id)
                db.add(summary)

            derived_title = self._derive_title(state=state, fallback_text=title_hint)
            if not summary.title or summary.title == "新会话" or title_hint:
                summary.title = derived_title

            summary.preview = self._derive_preview(
                state=state,
                fallback_text=preview_hint or title_hint,
            )
            summary.state_json = payload
            summary.last_message_at = now
            db.commit()

    def get_session_snapshot(self, session_id: str) -> dict[str, Any] | None:
        """读取会话状态快照。"""
        with self._open() as db:
            row = db.get(ChatSession, session_id)
            if row is None or not row.state_json:
                return None

            try:
                data = json.loads(row.state_json)
            except json.JSONDecodeError:
                data = {}

            if not isinstance(data, dict):
                data = {}
            data.setdefault("session_id", session_id)
            return data

    def get_recent_messages(self, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """读取最近消息，按时间正序返回。"""
        if limit <= 0:
            return []

        with self._open() as db:
            rows = db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
                .limit(limit)
            ).scalars().all()

        messages: list[dict[str, Any]] = []
        for row in reversed(rows):
            try:
                metadata = json.loads(row.metadata_json or "{}")
            except json.JSONDecodeError:
                metadata = {}
            messages.append(
                {
                    "role": row.role,
                    "content": row.content,
                    "timestamp": row.created_at.isoformat(),
                    "metadata": metadata,
                }
            )
        return messages

    def list_sessions(self, limit: int = 50) -> list[SessionSummary]:
        """按最近活跃时间倒序列出会话摘要。"""
        if limit <= 0:
            return []

        with self._open() as db:
            rows = db.execute(
                select(ChatSession)
                .order_by(ChatSession.last_message_at.desc())
                .limit(limit)
            ).scalars().all()

        summaries: list[SessionSummary] = []
        for row in rows:
            summaries.append(
                SessionSummary(
                    session_id=row.session_id,
                    title=row.title,
                    preview=row.preview or "",
                    message_count=int(row.message_count or 0),
                    created_at=row.created_at.isoformat(),
                    updated_at=row.updated_at.isoformat(),
                    last_message_at=row.last_message_at.isoformat(),
                )
            )
        return summaries

    def clear_session(self, session_id: str) -> None:
        """删除一个会话的所有历史和摘要。"""
        with self._open() as db:
            db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
            row = db.get(ChatSession, session_id)
            if row is not None:
                db.delete(row)
            db.commit()

    def clear_all(self) -> None:
        """清空全部会话数据。"""
        with self._open() as db:
            db.execute(delete(ChatMessage))
            db.execute(delete(ChatSession))
            db.commit()

    def count(self, session_id: str | None = None) -> int:
        """统计消息数。"""
        with self._open() as db:
            stmt = select(func.count(ChatMessage.id))
            if session_id:
                stmt = stmt.where(ChatMessage.session_id == session_id)
            result = db.execute(stmt).scalar_one()
        return int(result or 0)
