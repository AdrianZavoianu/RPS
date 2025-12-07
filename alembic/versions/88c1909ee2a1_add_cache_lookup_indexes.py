"""add cache lookup indexes

Revision ID: 88c1909ee2a1
Revises: c69a26130dbf
Create Date: 2025-12-04 16:57:10.324320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88c1909ee2a1'
down_revision: Union[str, Sequence[str], None] = 'c69a26130dbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with additional cache lookup indexes for performance."""
    op.create_index(
        "ix_global_cache_project_type",
        "global_results_cache",
        ["project_id", "result_type"],
    )
    op.create_index(
        "ix_element_cache_project_type",
        "element_results_cache",
        ["project_id", "result_type"],
    )
    op.create_index(
        "ix_joint_cache_project_type",
        "joint_results_cache",
        ["project_id", "result_type"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_global_cache_project_type", table_name="global_results_cache")
    op.drop_index("ix_element_cache_project_type", table_name="element_results_cache")
    op.drop_index("ix_joint_cache_project_type", table_name="joint_results_cache")
