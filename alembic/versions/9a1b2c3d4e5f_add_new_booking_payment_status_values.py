"""add new booking and payment status values

Revision ID: 9a1b2c3d4e5f
Revises: 953b4d6d05e7
Create Date: 2026-08-19 02:13:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a1b2c3d4e5f'
down_revision: Union[str, None] = '953b4d6d05e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add AWAITING_PAYMENT to booking_status enum
    op.execute("ALTER TYPE booking_status ADD VALUE IF NOT EXISTS 'AWAITING_PAYMENT'")
    # Add PAYMENT_EXPIRED to booking_status enum
    op.execute("ALTER TYPE booking_status ADD VALUE IF NOT EXISTS 'PAYMENT_EXPIRED'")
    # Add AWAITING_PAYMENT to payment_status enum
    op.execute("ALTER TYPE payment_status ADD VALUE IF NOT EXISTS 'AWAITING_PAYMENT'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values directly.
    # This migration is irreversible - the enum values are additive only.
    pass