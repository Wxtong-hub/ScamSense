import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> int:
    return int(datetime.now(UTC).timestamp())


def database_url() -> str:
    configured = os.getenv("DATABASE_URL")
    if configured:
        return configured
    folder = Path(__file__).resolve().parents[1] / "data"
    folder.mkdir(exist_ok=True)
    return "sqlite:///" + (folder / "scamsense.sqlite3").as_posix()


def engine_for(url: str):
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 5})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    return engine


class Base(DeclarativeBase):
    pass


class Training(Base):
    __tablename__ = "training_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    token_digest: Mapped[str] = mapped_column(String(64))
    phase: Mapped[str] = mapped_column(String(2), default="S0")
    status: Mapped[str] = mapped_column(String(16), default="active")
    version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(Integer, index=True)
    final_request: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    report: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))


class Turn(Base):
    __tablename__ = "training_turns"
    __table_args__ = (
        UniqueConstraint("session_id", "client_id", name="uq_turn_request"),
    )
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("training_sessions.id", ondelete="CASCADE"), index=True
    )
    client_id: Mapped[str] = mapped_column(String(36))
    user_id: Mapped[str] = mapped_column(String(36), unique=True)
    reply_id: Mapped[str] = mapped_column(String(36), unique=True)
    role_id: Mapped[str] = mapped_column(String(12))
    user_text: Mapped[str] = mapped_column(Text)
    reply: Mapped[str] = mapped_column(Text)
    facts: Mapped[dict] = mapped_column(JSON)
    presented: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[int] = mapped_column(Integer)
