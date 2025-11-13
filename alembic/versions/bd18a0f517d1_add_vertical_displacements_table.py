"""add_vertical_displacements_table

Revision ID: bd18a0f517d1
Revises: 281011a1bde8
Create Date: 2025-11-11 20:07:18.200929

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd18a0f517d1'
down_revision: Union[str, Sequence[str], None] = '281011a1bde8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'vertical_displacements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('result_set_id', sa.Integer(), nullable=True),
        sa.Column('result_category_id', sa.Integer(), nullable=True),
        sa.Column('load_case_id', sa.Integer(), nullable=False),
        sa.Column('story', sa.String(length=20), nullable=False),
        sa.Column('label', sa.String(length=50), nullable=False),
        sa.Column('unique_name', sa.String(length=50), nullable=False),
        sa.Column('min_displacement', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['load_case_id'], ['load_cases.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['result_category_id'], ['result_categories.id'], ),
        sa.ForeignKeyConstraint(['result_set_id'], ['result_sets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vertdisp_loadcase', 'vertical_displacements', ['load_case_id'], unique=False)
    op.create_index('ix_vertdisp_project_resultset', 'vertical_displacements', ['project_id', 'result_set_id'], unique=False)
    op.create_index('ix_vertdisp_unique', 'vertical_displacements', ['project_id', 'result_set_id', 'unique_name', 'load_case_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_vertdisp_unique', table_name='vertical_displacements')
    op.drop_index('ix_vertdisp_project_resultset', table_name='vertical_displacements')
    op.drop_index('ix_vertdisp_loadcase', table_name='vertical_displacements')
    op.drop_table('vertical_displacements')
