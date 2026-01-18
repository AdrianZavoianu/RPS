"""add max_axial to column_axials

Revision ID: d3f8a92b1c45
Revises: 88c1909ee2a1
Create Date: 2025-12-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f8a92b1c45'
down_revision: Union[str, Sequence[str], None] = '88c1909ee2a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add max_axial column to column_axials table."""
    op.add_column(
        'column_axials',
        sa.Column('max_axial', sa.Float(), nullable=True)
    )


def downgrade() -> None:
    """Remove max_axial column from column_axials table."""
    op.drop_column('column_axials', 'max_axial')
