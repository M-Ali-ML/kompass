"""ORM models for persisted trip conversations and their messages."""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Trip(Base):
    """A persisted trip-planning conversation.

    The primary key is the AG-UI/CopilotKit ``thread_id`` so that the agent
    endpoint can upsert a trip by the thread it is streaming for.
    """

    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, default="New Trip")
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # Full AG-UI/CopilotKit message history (user/assistant/tool turns including
    # tool calls and their results) serialized as JSON. This is what lets the
    # generative-UI cards (scenario comparisons, flight lists, etc.) rehydrate on
    # reload — the flattened `messages` rows below only carry plain text turns.
    message_history: Mapped[list | None] = mapped_column(JSON, nullable=True)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )


class Message(Base):
    """A single conversational turn (user or assistant) within a trip."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[str] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    trip: Mapped[Trip] = relationship(back_populates="messages")
