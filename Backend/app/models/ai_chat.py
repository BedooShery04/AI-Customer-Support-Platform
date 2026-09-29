from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base


class AIChat(Base):
    __tablename__ = "ai_chats"

    __table_args__ = (
        Index(
            "idx_ai_chats_user_id",
            "user_id",
        ),
        Index(
            "idx_ai_chats_updated_at",
            "updated_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="New Chat",
        server_default="New Chat",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="ai_chats",
    )

    messages = relationship(
        "AIChatMessage",
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="AIChatMessage.created_at",
    )