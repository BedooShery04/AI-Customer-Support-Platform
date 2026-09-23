from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    __table_args__ = (
        Index("idx_audit_logs_admin_id", "admin_id"),
        Index("idx_audit_logs_ticket_id", "ticket_id"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    admin_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    ticket_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False
    )

    action: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    admin = relationship(
        "User",
        back_populates="audit_logs"
    )

    ticket = relationship(
        "Ticket",
        back_populates="audit_logs"
    )