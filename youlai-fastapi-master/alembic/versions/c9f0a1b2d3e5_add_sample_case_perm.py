"""add aitc:case:sample permission to sys_menu

Revision ID: c9f0a1b2d3e5
Revises: b8e9f0a1d2c4
Create Date: 2026-08-02 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9f0a1b2d3e5'
down_revision: Union[str, None] = 'b8e9f0a1d2c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("""
        INSERT INTO sys_menu (id, parent_id, tree_path, name, type, route_name, route_path, component, perm, always_show, keep_alive, visible, sort, icon, redirect, create_time, update_time, params)
        VALUES (3024, 3010, '0,3000,3010', '标记样本', 'B', NULL, '', NULL, 'aitc:case:sample', NULL, NULL, 1, 10, '', NULL, now(), now(), NULL)
        ON CONFLICT (id) DO NOTHING
    """))

    # 授权：ROOT + ADMIN 获取该按钮权限
    op.execute(sa.text("""
        INSERT INTO sys_role_menu (role_id, menu_id)
        SELECT r.id, 3024 FROM sys_role r
        WHERE r.code IN ('ROOT', 'ADMIN')
          AND NOT EXISTS (SELECT 1 FROM sys_role_menu rm WHERE rm.role_id = r.id AND rm.menu_id = 3024)
    """))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM sys_role_menu WHERE menu_id = 3024"))
    op.execute(sa.text("DELETE FROM sys_menu WHERE id = 3024"))
