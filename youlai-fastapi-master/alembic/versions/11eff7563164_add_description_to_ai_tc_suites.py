"""add description to ai_tc_suites

Revision ID: 11eff7563164
Revises: cb6916a13de7
Create Date: 2026-08-08 10:56:37.857838
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11eff7563164'
down_revision: Union[str, None] = 'cb6916a13de7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ai_tc_suites', sa.Column('description', sa.Text(), nullable=True, comment='套件描述'))


def downgrade() -> None:
    op.drop_column('ai_tc_suites', 'description')
