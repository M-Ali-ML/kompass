"""ORM model for the global, cross-trip user profile."""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# Single global profile is stored under a fixed primary key. The app is
# currently single-user; this keeps the "preferences carry across trips"
# behaviour simple while leaving room for real multi-user profiles later.
DEFAULT_PROFILE_ID = "default"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserProfile(Base):
    """Learned traveler preferences shared across all trips."""

    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=DEFAULT_PROFILE_ID)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
