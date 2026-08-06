"""种子数据：在 sys_menu 表中插入「AI日志」菜单（系统管理 > AI日志）。
使用方式：python -m app.system.product.seed_llm_log_menu
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.database import AsyncSessionLocal
from app.system.menu.models import SysMenu
from sqlalchemy import select, func


async def seed():
    async with AsyncSessionLocal() as db:
        # 查找「系统管理」菜单（route_path=/system）
        parent_result = await db.execute(
            select(SysMenu).where(SysMenu.route_path == "/system", SysMenu.type == "C")
        )
        parent = parent_result.scalar_one_or_none()
        if parent is None:
            print("未找到「系统管理」菜单，请确保基础数据已初始化。")
            return

        # 检查是否已存在
        exist_result = await db.execute(
            select(func.count()).select_from(SysMenu).where(
                SysMenu.parent_id == parent.id,
                SysMenu.route_name == "LlmLog",
            )
        )
        if exist_result.scalar() and exist_result.scalar() > 0:
            print("「AI日志」菜单已存在，跳过。")
            return

        # 构造菜单
        menu = SysMenu(
            parent_id=parent.id,
            tree_path=f"{parent.tree_path}",
            name="AI日志",
            type="M",
            route_name="LlmLog",
            route_path="llm-log",
            component="system/llm-log/index",
            perm="sys:llm-log:list",
            icon="monitor",
            sort=99,
            visible=1,
            keep_alive=0,
            always_show=0,
        )
        db.add(menu)
        await db.flush()

        # 回填 tree_path
        menu.tree_path = f"{parent.tree_path},{menu.id}"
        await db.flush()
        await db.commit()

        print(f"菜单已插入：「AI日志」id={menu.id} parent_id={parent.id} tree_path={menu.tree_path}")


if __name__ == "__main__":
    asyncio.run(seed())
