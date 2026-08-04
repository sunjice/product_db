"""add is_sample column to ai_tc_cases

Revision ID: b8e9f0a1d2c4
Revises: a7d8e9f1c2b3
Create Date: 2026-08-02 14:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b8e9f0a1d2c4'
down_revision: Union[str, None] = 'a7d8e9f1c2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ai_tc_cases',
        sa.Column(
            'is_sample',
            sa.SmallInteger(),
            nullable=False,
            server_default='0',
            comment='是否样本用例 0-否 1-是'
        )
    )


def downgrade() -> None:
    op.drop_column('ai_tc_cases', 'is_sample')
