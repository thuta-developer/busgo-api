"""add unique constraint on routes origin destination

Revision ID: 9f2c4e8a1b3d
Revises: b416ea67f567
Create Date: 2026-08-15 01:37:30.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f2c4e8a1b3d'
down_revision: Union[str, None] = 'b416ea67f567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add unique constraint on (origin, destination) to prevent duplicate routes at DB level
    op.create_unique_constraint(
        'uq_routes_origin_destination',
        'routes',
        ['origin', 'destination'],
    )
    # Add check constraint to prevent origin == destination at DB level
    op.create_check_constraint(
        'ck_routes_origin_not_destination',
        'routes',
        'lower(origin) <> lower(destination)',
    )


def downgrade() -> None:
    op.drop_constraint(
        'ck_routes_origin_not_destination',
        'routes',
        type_='check',
    )
    op.drop_constraint(
        'uq_routes_origin_destination',
        'routes',
        type_='unique',
    )
