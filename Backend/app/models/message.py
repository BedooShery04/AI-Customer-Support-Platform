from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base


class Message(Base):
    __tablename__ = "messages"

    __table_args__ = (
        Index("idx_messages_sender_id", "sender_id"),
        Index("idx_messages_ticket_id", "ticket_id")
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    ticket_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tickets.id", ondelete='CASCADE'),
        nullable=False
    )

    sender_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Message -> Ticket
    ticket = relationship(
        "Ticket",
        back_populates="messages"
    )

    # Message -> Sender
    sender = relationship(
        "User",
        back_populates="messages"
    )