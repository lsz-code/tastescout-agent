"""add photo to favorite_restaurants

Revision ID: 7b6f0f8a4d21
Revises: 3ae0193f0026
Create Date: 2026-05-13 21:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7b6f0f8a4d21"
down_revision: Union[str, None] = "3ae0193f0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "favorite_restaurants",
        sa.Column("photo", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("favorite_restaurants", "photo")
