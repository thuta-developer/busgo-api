"""booking add server_default is_active

Revision ID: 4f1a2b3c4d5e
Revises: 3356822e9616
Create Date: 2026-08-23 03:55:30.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f1a2b3c4d5e'
down_revision: Union[str, None] = '3356822e9616'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Backfill existing rows with is_active = true
    op.execute("UPDATE bookings SET is_active = true WHERE is_active IS NULL")
    # 2. Set server default so new INSERTs get true automatically
    op.alter_column(
        'bookings',
        'is_active',
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text('true'),
    )


def downgrade() -> None:
    # Remove the server default (keep the column NOT NULL)
    op.alter_column(
        'bookings',
        'is_active',
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=None,
    )