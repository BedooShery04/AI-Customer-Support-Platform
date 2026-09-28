"""add ticket classification status

Revision ID: c7f092bd6ad3
Revises: 212a2afef9cb
Create Date: 2026-09-28 12:01:30.577752

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7f092bd6ad3'
down_revision: Union[str, Sequence[str], None] = '212a2afef9cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the classification status column.
    # Existing tickets initially receive "pending".
    op.add_column(
        "tickets",
        sa.Column(
            "classification_status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
    )

    # Tickets with an existing AI classification
    # have already been classified successfully.
    op.execute(
        """
        UPDATE tickets AS t
        SET classification_status = 'completed'
        WHERE EXISTS (
            SELECT 1
            FROM ticket_ai_classifications AS c
            WHERE c.ticket_id = t.id
        )
        """
    )


def downgrade() -> None:
    op.drop_column(
        "tickets",
        "classification_status",
    )