from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base_class import Base


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

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
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