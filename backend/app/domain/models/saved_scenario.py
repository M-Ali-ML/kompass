"""ORM model for user-saved trip scenarios.

A saved scenario captures one option the traveler explicitly bookmarked from a
scenario comparison. The full structured scenario (cost breakdown, stress
factors, highlights, itinerary, reasoning) is stored as JSON, while a handful of
key fields are denormalized into columns so the table stays queryable
(filter/sort by destination, price, stress, dates).
"""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SavedScenario(Base):
    """A travel scenario the user saved from a comparison."""

    __tablename__ = "saved_scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # The conversation/thread this scenario came from. Nullable + SET NULL so a
    # saved scenario can outlive a deleted conversation.
    trip_id: Mapped[str | None] = mapped_column(
        ForeignKey("trips.id", ondelete="SET NULL"), index=True, nullable=True
    )

    # Denormalized, queryable summary fields.
    destination: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    label: Mapped[str] = mapped_column(String, default="Saved scenario")
    comparison_label: Mapped[str | None] = mapped_column(String, nullable=True)
    start_date: Mapped[str | None] = mapped_column(String, nullable=True)
    end_date: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String, default="EUR")
    grand_total: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    stress_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Full structured scenario payload (Scenario.model_dump from the agent).
    scenario: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
