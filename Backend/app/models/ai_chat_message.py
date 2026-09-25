from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base


class AIChatMessage(Base):
    __tablename__ = "ai_chat_messages"

    __table_args__ = (
        Index("idx_ai_chat_messages_user_id", "user_id"),
        Index("idx_ai_chat_messages_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        Text,
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

    user = relationship(
        "User",
        back_populates="ai_chat_messages"
    )