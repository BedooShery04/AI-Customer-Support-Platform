from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import TicketCategory, TicketPriority
from app.database.base_class import Base


class TicketAIClassification(Base):
    __tablename__ = "ticket_ai_classifications"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
       
    )

    ticket_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tickets.id",ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    category: Mapped[TicketCategory] = mapped_column(
        SQLEnum(
            TicketCategory,
            name="ticket_category",
            values_callable=lambda enum_class: [item.value for item in enum_class]
        ),
        nullable=False
    )

    priority: Mapped[TicketPriority] = mapped_column(
        SQLEnum(
            TicketPriority,
            name="ticket_priority",
            values_callable=lambda enum_class: [item.value for item in enum_class]
        ),
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
        nullable=False,
        default=datetime.utcnow
    )

    # Classification -> Ticket
    ticket = relationship(
        "Ticket",
        back_populates="ai_classification"
    )