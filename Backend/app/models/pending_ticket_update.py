
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base_class import Base


class PendingTicketUpdate(Base):
    __tablename__ = "pending_ticket_updates"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    ticket_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
    )

    subject: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(5000),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )