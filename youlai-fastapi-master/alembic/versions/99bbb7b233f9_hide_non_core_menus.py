"""hide_non_core_menus

隐藏除系统管理(id=1)、AITC(id=3000)之外的所有菜单及其子孙
通过 tree_path 判断归属，保留 root id=1/3000 及其子树
"""

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '99bbb7b233f9'
down_revision: str = '4e01c2c52b72'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """先修正 AITC 子菜单 tree_path，再隐藏非核心菜单"""
    # 1. 修正 4 个 AITC 二级菜单的 tree_path（之前申请时只写了自身 id 导致断裂）
    op.execute("""
        UPDATE sys_menu SET tree_path = '0,3000' WHERE id IN (3010, 3020, 3040, 3060)
    """)

    # 2. 隐藏非核心菜单：只保留 系统管理(tree_path 0,1%) 和 AITC(tree_path 0,3000%)
    op.execute("""
        UPDATE sys_menu
        SET visible = 0
        WHERE visible = 1
          AND tree_path NOT LIKE '0,1%'
          AND tree_path NOT LIKE '0,3000%'
          AND id NOT IN (1, 3000)
    """)


def downgrade() -> None:
    """恢复所有菜单为可见，tree_path 不做回退（历史数据修复）"""
    op.execute("UPDATE sys_menu SET visible = 1")
