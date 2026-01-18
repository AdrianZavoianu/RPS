"""add absolute maxmin drifts table

Revision ID: b7f4c5d2e1a9
Revises: a9e8846463ae
Create Date: 2025-10-24 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7f4c5d2e1a9'
down_revision = 'a9e8846463ae'
branch_labels = None
depends_on = None


def upgrade():
    # Create absolute_maxmin_drifts table
    op.create_table(
        'absolute_maxmin_drifts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('result_set_id', sa.Integer(), nullable=False),
        sa.Column('story_id', sa.Integer(), nullable=False),
        sa.Column('load_case_id', sa.Integer(), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('absolute_max_drift', sa.Float(), nullable=False),
        sa.Column('sign', sa.String(length=10), nullable=False),
        sa.Column('original_max', sa.Float(), nullable=False),
        sa.Column('original_min', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['load_case_id'], ['load_cases.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['result_set_id'], ['result_sets.id'], ),
        sa.ForeignKeyConstraint(['story_id'], ['stories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(
        'ix_absmaxmin_lookup',
        'absolute_maxmin_drifts',
        ['project_id', 'result_set_id', 'story_id', 'load_case_id', 'direction'],
        unique=True
    )
    op.create_index(
        'ix_absmaxmin_resultset',
        'absolute_maxmin_drifts',
        ['result_set_id'],
        unique=False
    )


def downgrade():
    # Drop indexes
    op.drop_index('ix_absmaxmin_resultset', table_name='absolute_maxmin_drifts')
    op.drop_index('ix_absmaxmin_lookup', table_name='absolute_maxmin_drifts')

    # Drop table
    op.drop_table('absolute_maxmin_drifts')
