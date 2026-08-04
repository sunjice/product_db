"""fix aitc menu component paths: case/index, review-index, remove aiconfig menu

Revision ID: d1e2f3a4b5c6
Revises: b70bb6265a9e, c9f0a1b2d3e5
Create Date: 2026-08-04 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = ('b70bb6265a9e', 'c9f0a1b2d3e5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 用例管理: aitc/index → aitc/case
    op.execute(sa.text("""
        UPDATE sys_menu SET component = 'aitc/case'
        WHERE id = 3010 AND component = 'aitc/index'
    """))

    # 2. 审核工作台: aitc/review → aitc/task/review-index
    op.execute(sa.text("""
        UPDATE sys_menu SET component = 'aitc/task/review-index'
        WHERE id = 3060 AND component = 'aitc/review'
    """))

    # 3. 删除 AI配置 菜单及角色关联 (ids 3050~3054)
    op.execute(sa.text("""
        DELETE FROM sys_role_menu WHERE menu_id IN (3050, 3051, 3052, 3053, 3054)
    """))
    op.execute(sa.text("""
        DELETE FROM sys_menu WHERE id IN (3050, 3051, 3052, 3053, 3054)
    """))


def downgrade() -> None:
    # 1. 还原 component 路径
    op.execute(sa.text("""
        UPDATE sys_menu SET component = 'aitc/index'
        WHERE id = 3010 AND component = 'aitc/case'
    """))
    op.execute(sa.text("""
        UPDATE sys_menu SET component = 'aitc/review'
        WHERE id = 3060 AND component = 'aitc/task/review-index'
    """))

    # 2. 恢复 AI配置 菜单
    op.execute(sa.text("""
        INSERT INTO sys_menu (id, parent_id, tree_path, name, type, route_name, route_path, component, perm, always_show, keep_alive, visible, sort, icon, redirect, create_time, update_time, params)
        VALUES
        (3050, 3000, '0,3000', 'AI配置', 'M', 'AITCAiConfig', 'aiconfig', 'aitc/aiconfig', 'aitc:aiconfig:list', NULL, 1, 1, 5, 'setting', NULL, now(), now(), NULL),
        (3051, 3050, '0,3000,3050', '配置查询', 'B', NULL, '', NULL, 'aitc:aiconfig:list', NULL, NULL, 1, 1, '', NULL, now(), now(), NULL),
        (3052, 3050, '0,3000,3050', '配置创建', 'B', NULL, '', NULL, 'aitc:aiconfig:create', NULL, NULL, 1, 2, '', NULL, now(), now(), NULL),
        (3053, 3050, '0,3000,3050', '配置编辑', 'B', NULL, '', NULL, 'aitc:aiconfig:update', NULL, NULL, 1, 3, '', NULL, now(), now(), NULL),
        (3054, 3050, '0,3000,3050', '配置删除', 'B', NULL, '', NULL, 'aitc:aiconfig:delete', NULL, NULL, 1, 4, '', NULL, now(), now(), NULL)
        ON CONFLICT (id) DO NOTHING
    """))
