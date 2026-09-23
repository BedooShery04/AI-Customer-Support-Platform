from datetime import datetime

from sqlalchemy import (
    DateTime,
    FetchedValue,
    func,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.enums import (
    TicketCategory,
    TicketPriority,
    TicketStatus,
)
from app.database.base_class import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    assigned_agent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    subject: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
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
        nullable=False,
        default=TicketPriority.MEDIUM
    )

    status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(
            TicketStatus,
            name="ticket_status",
            values_callable=lambda enum_class: [item.value for item in enum_class]
        ),
        nullable=False,
        default=TicketStatus.OPEN
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        server_onupdate=FetchedValue()
    )

    # Ticket -> Customer
    customer = relationship(
        "User",
        back_populates="customer_tickets",
        foreign_keys=[customer_id]
    )

    # Ticket -> Assigned Agent
    assigned_agent = relationship(
        "User",
        back_populates="assigned_tickets",
        foreign_keys=[assigned_agent_id]
    )

    # Ticket -> Messages
    messages = relationship(
        "Message",
        back_populates="ticket",
        cascade="all, delete-orphan"
    )

    # Ticket -> AI Classification
    ai_classification = relationship(
        "TicketAIClassification",
        back_populates="ticket",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # Ticket -> Audit Logs
    audit_logs = relationship(
        "AuditLog",
        back_populates="ticket",
        cascade="all, delete-orphan"
    )