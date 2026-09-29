
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base_class import Base


class PendingTicketDraft(Base):
    __tablename__ = "pending_ticket_drafts"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    chat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ai_chats.id", ondelete="CASCADE"),
        primary_key=True,
    )

    customer_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    tickets: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )