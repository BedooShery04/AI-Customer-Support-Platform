from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base_class import Base


class TicketAIClassification(Base):
    __tablename__ = "ticket_ai_classifications"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    ticket_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tickets.id"),
        nullable=False,
        unique=True
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    suggested_action: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Classification -> Ticket
    ticket = relationship(
        "Ticket",
        back_populates="ai_classification"
    )