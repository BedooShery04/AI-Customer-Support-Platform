from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.user import UserRole, UserStatus
from app.database.base_class import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    role: Mapped[UserRole] = mapped_column(
        SQLEnum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_class: [item.value for item in enum_class]
        ),
        nullable=False,
        default=UserRole.CUSTOMER
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(
            UserStatus,
            name="user_status",
            values_callable=lambda enum_class: [item.value for item in enum_class]
        ),
        nullable=False,
        default=UserStatus.ACTIVE
    )

    # Customer -> Tickets
    customer_tickets = relationship(
        "Ticket",
        back_populates="customer",
        foreign_keys="Ticket.customer_id"
    )

    # Agent -> Assigned Tickets
    assigned_tickets = relationship(
        "Ticket",
        back_populates="assigned_agent",
        foreign_keys="Ticket.assigned_agent_id"
    )

    # User -> Messages
    messages = relationship(
        "Message",
        back_populates="sender"
    )

    ai_chat_messages = relationship(
    "AIChatMessage",
    back_populates="user",
    cascade="all, delete-orphan"
    )

    # Admin -> Audit Logs
    audit_logs = relationship(
        "AuditLog",
        back_populates="admin"
    )