"""ORM model for a trip's generated "vibe" background image.

One row per trip (keyed by the AG-UI ``thread_id``). The image bytes are stored
inline so delivery is a single endpoint read with no filesystem/static wiring.
The row also acts as a generation lock/state machine: a ``pending`` row is
inserted before generation starts so concurrent turns don't kick off duplicate
jobs.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TripBackground(Base):
    """A generated destination/vibe background image for a trip."""

    __tablename__ = "trip_backgrounds"

    # Same id as the trip/thread this image belongs to.
    trip_id: Mapped[str] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), primary_key=True
    )

    # Generation lifecycle: "pending" | "ready" | "error".
    status: Mapped[str] = mapped_column(String, default="pending")

    # The destination + scene description the image was generated from (handy for
    # debugging and for detecting whether an explicit regen changed the subject).
    destination: Mapped[str | None] = mapped_column(String, nullable=True)
    scene_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The encoded image bytes + their MIME type (null until ready).
    image: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    mime: Mapped[str] = mapped_column(String, default="image/webp")

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
