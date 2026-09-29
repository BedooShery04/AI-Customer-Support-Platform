"""add multiple ai chats

Revision ID: 10f49b875f53
Revises: af1b88885f5f
Create Date: 2026-09-29 04:34:46.834217

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10f49b875f53'
down_revision: Union[str, Sequence[str], None] = 'af1b88885f5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    # 1. Create the AI chats table.
    op.create_table(
        "ai_chats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
            server_default="New Chat",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_index(
        "idx_ai_chats_user_id",
        "ai_chats",
        ["user_id"],
    )

    op.create_index(
        "idx_ai_chats_updated_at",
        "ai_chats",
        ["updated_at"],
    )

    # 2. Add chat_id as nullable temporarily.
    op.add_column(
        "ai_chat_messages",
        sa.Column("chat_id", sa.Integer(), nullable=True),
    )

    # 3. Create one chat for each user with existing messages.
    op.execute(
        """
        INSERT INTO ai_chats (
            user_id,
            title,
            created_at,
            updated_at
        )
        SELECT
            user_id,
            'Previous Chat',
            MIN(created_at),
            MAX(created_at)
        FROM ai_chat_messages
        GROUP BY user_id
        """
    )

    # 4. Associate existing messages with their user's chat.
    op.execute(
        """
        UPDATE ai_chat_messages AS m
        SET chat_id = c.id
        FROM ai_chats AS c
        WHERE m.user_id = c.user_id
          AND m.chat_id IS NULL
        """
    )

    # 5. Make chat_id required after migrating existing messages.
    op.alter_column(
        "ai_chat_messages",
        "chat_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.create_foreign_key(
        "fk_ai_chat_messages_chat_id",
        "ai_chat_messages",
        "ai_chats",
        ["chat_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index(
        "ix_ai_chat_messages_chat_id",
        "ai_chat_messages",
        ["chat_id"],
    )


def downgrade() -> None:
    # Remove chat associations while preserving messages.
    op.drop_index(
        "ix_ai_chat_messages_chat_id",
        table_name="ai_chat_messages",
    )

    op.drop_constraint(
        "fk_ai_chat_messages_chat_id",
        "ai_chat_messages",
        type_="foreignkey",
    )

    op.drop_column(
        "ai_chat_messages",
        "chat_id",
    )

    op.drop_index(
        "idx_ai_chats_updated_at",
        table_name="ai_chats",
    )

    op.drop_index(
        "idx_ai_chats_user_id",
        table_name="ai_chats",
    )

    op.drop_table("ai_chats")