"""add promotion reference to bookings

Revision ID: 7c2a1f4e8b90
Revises: 56bd83480696
Create Date: 2026-08-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "7c2a1f4e8b90"
down_revision: Union[str, None] = "56bd83480696"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bookings",
        sa.Column("promotion_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_bookings_promotion_id", "bookings", ["promotion_id"], unique=False
    )
    op.create_foreign_key(
        "fk_bookings_promotion_id_promotions",
        "bookings",
        "promotions",
        ["promotion_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_bookings_promotion_id_promotions", "bookings", type_="foreignkey"
    )
    op.drop_index("ix_bookings_promotion_id", table_name="bookings")
    op.drop_column("bookings", "promotion_id")
