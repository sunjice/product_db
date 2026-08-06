"""add session_id column to ai_tc_tasks

Revision ID: cb6916a13de7
Revises: e3bdd3788631
Create Date: 2026-08-06 00:16:57.568387
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb6916a13de7'
down_revision: Union[str, None] = 'e3bdd3788631'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ai_tc_tasks',
        sa.Column(
            'session_id',
            sa.BigInteger(),
            nullable=True,
            comment='创建任务的会话ID（从对话中发起任务时记录）'
        )
    )


def downgrade() -> None:
    op.drop_column('ai_tc_tasks', 'session_id')
