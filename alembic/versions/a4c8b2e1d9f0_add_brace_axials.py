"""add brace axial results

Revision ID: a4c8b2e1d9f0
Revises: 6361e378f827
Create Date: 2026-05-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4c8b2e1d9f0"
down_revision: Union[str, Sequence[str], None] = "6361e378f827"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brace_axials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("element_id", sa.Integer(), nullable=False),
        sa.Column("story_id", sa.Integer(), nullable=False),
        sa.Column("load_case_id", sa.Integer(), nullable=False),
        sa.Column("result_category_id", sa.Integer(), nullable=True),
        sa.Column("min_axial", sa.Float(), nullable=False),
        sa.Column("max_axial", sa.Float(), nullable=True),
        sa.Column("story_sort_order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["element_id"], ["elements.id"]),
        sa.ForeignKeyConstraint(["load_case_id"], ["load_cases.id"]),
        sa.ForeignKeyConstraint(["result_category_id"], ["result_categories.id"]),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_braceaxial_element_story_case",
        "brace_axials",
        ["element_id", "story_id", "load_case_id"],
        unique=False,
    )
    op.create_index(
        "ix_braceaxial_category",
        "brace_axials",
        ["result_category_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_braceaxial_category", table_name="brace_axials")
    op.drop_index("ix_braceaxial_element_story_case", table_name="brace_axials")
    op.drop_table("brace_axials")
