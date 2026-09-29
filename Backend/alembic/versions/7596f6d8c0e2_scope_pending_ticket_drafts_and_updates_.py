"""Scope pending ticket drafts and updates to chats."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# Replace this value with the generated revision ID.
revision: str = "7596f6d8c0e2"
down_revision: Union[str, None] = "10f49b875f53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def replace_primary_key(table_name, columns):
    """Replace a table's existing primary key."""
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    primary_key = inspector.get_pk_constraint(
        table_name
    )

    op.drop_constraint(
        primary_key["name"],
        table_name,
        type_="primary",
    )

    op.create_primary_key(
        f"{table_name}_pkey",
        table_name,
        columns,
    )


def upgrade() -> None:
    # Add nullable columns before migrating existing records.
    op.add_column(
        "pending_ticket_drafts",
        sa.Column(
            "chat_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "pending_ticket_updates",
        sa.Column(
            "chat_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    # Create a chat for users who have pending records
    # but do not have any existing AI chats.
    op.execute(
        """
        INSERT INTO ai_chats (
            user_id,
            title,
            created_at,
            updated_at
        )
        SELECT
            pending.user_id,
            'Previous Chat',
            NOW(),
            NOW()
        FROM (
            SELECT user_id
            FROM pending_ticket_drafts

            UNION

            SELECT user_id
            FROM pending_ticket_updates
        ) AS pending
        WHERE NOT EXISTS (
            SELECT 1
            FROM ai_chats AS existing
            WHERE existing.user_id = pending.user_id
        )
        """
    )

    # Assign legacy drafts to each user's latest chat.
    op.execute(
        """
        UPDATE pending_ticket_drafts AS draft
        SET chat_id = (
            SELECT chat.id
            FROM ai_chats AS chat
            WHERE chat.user_id = draft.user_id
            ORDER BY
                chat.updated_at DESC,
                chat.id DESC
            LIMIT 1
        )
        """
    )

    # Assign legacy updates to each user's latest chat.
    op.execute(
        """
        UPDATE pending_ticket_updates AS pending
        SET chat_id = (
            SELECT chat.id
            FROM ai_chats AS chat
            WHERE chat.user_id = pending.user_id
            ORDER BY
                chat.updated_at DESC,
                chat.id DESC
            LIMIT 1
        )
        """
    )

    # Make chat_id mandatory after backfilling.
    op.alter_column(
        "pending_ticket_drafts",
        "chat_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.alter_column(
        "pending_ticket_updates",
        "chat_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # Replace user-only primary keys with composite keys.
    replace_primary_key(
        "pending_ticket_drafts",
        ["user_id", "chat_id"],
    )

    replace_primary_key(
        "pending_ticket_updates",
        ["user_id", "chat_id"],
    )

    # Delete pending records when their chat is deleted.
    op.create_foreign_key(
        "fk_pending_ticket_drafts_chat_id",
        "pending_ticket_drafts",
        "ai_chats",
        ["chat_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_pending_ticket_updates_chat_id",
        "pending_ticket_updates",
        "ai_chats",
        ["chat_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Keep only the latest pending record per user.
    # Older records from other chats cannot fit into
    # the original user-only primary key.
    for table_name in (
        "pending_ticket_drafts",
        "pending_ticket_updates",
    ):
        op.execute(
            sa.text(
                f"""
                DELETE FROM {table_name} AS pending
                WHERE pending.ctid IN (
                    SELECT row_id
                    FROM (
                        SELECT
                            ctid AS row_id,
                            ROW_NUMBER() OVER (
                                PARTITION BY user_id
                                ORDER BY
                                    created_at DESC,
                                    chat_id DESC
                            ) AS row_number
                        FROM {table_name}
                    ) AS ranked
                    WHERE row_number > 1
                )
                """
            )
        )

    op.drop_constraint(
        "fk_pending_ticket_drafts_chat_id",
        "pending_ticket_drafts",
        type_="foreignkey",
    )

    op.drop_constraint(
        "fk_pending_ticket_updates_chat_id",
        "pending_ticket_updates",
        type_="foreignkey",
    )

    replace_primary_key(
        "pending_ticket_drafts",
        ["user_id"],
    )

    replace_primary_key(
        "pending_ticket_updates",
        ["user_id"],
    )

    op.drop_column(
        "pending_ticket_drafts",
        "chat_id",
    )

    op.drop_column(
        "pending_ticket_updates",
        "chat_id",
    )