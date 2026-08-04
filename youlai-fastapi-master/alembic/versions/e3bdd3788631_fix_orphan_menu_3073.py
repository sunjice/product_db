"""fix_orphan_menu_3073

删除孤立的顶层菜单 id=3073（与 id=3080 重复的"规范管理"）
修复 id=3060 的 tree_path（0,3060 → 0,3000）
"""

from alembic import op

# revision identifiers
revision: str = 'e3bdd3788631'
down_revision: str = '99bbb7b233f9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 删除孤立的顶层"规范管理"菜单(id=3073, parent_id=0)
    #    这会阻塞前端路由注册（顶层出现非 Layout 的 M 类型路由）
    op.execute("DELETE FROM sys_menu WHERE id = 3073")

    # 2. 修复"用例审核"(id=3060)的 tree_path，上次迁移遗漏
    op.execute("UPDATE sys_menu SET tree_path = '0,3000' WHERE id = 3060 AND tree_path = '0,3060'")


def downgrade() -> None:
    # 恢复 id=3073（注意：手动通过 API 重新创建更好，此处不做反向操作）
    pass
