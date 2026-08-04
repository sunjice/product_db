"""插入产品模块的按钮权限菜单（type=B），并授权给 ADMIN 角色。"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.database import AsyncSessionLocal
from app.system.menu.models import SysMenu
from sqlalchemy import select, text

async def seed():
    async with AsyncSessionLocal() as db:
        # 检查是否已存在
        exist = await db.execute(text(
            "SELECT count(*) FROM sys_menu WHERE perm = 'product:create'"
        ))
        if exist.scalar() and exist.scalar() > 0:
            print("产品按钮权限已存在，跳过。")
            return

        # 获取各菜单的 ID
        menus = await db.execute(text(
            "SELECT id, route_path, name FROM sys_menu WHERE route_path IN ('list', 'category', 'brand', 'specgroup') AND parent_id IN (SELECT id FROM sys_menu WHERE route_path = '/product')"
        ))
        menu_map = {row[1]: row[0] for row in menus}
        print(f"菜单映射: {menu_map}")

        # 定义按钮权限
        buttons = [
            # 产品管理
            (menu_map.get("list"), "新增产品", "product:create", 1),
            (menu_map.get("list"), "编辑产品", "product:update", 2),
            (menu_map.get("list"), "删除产品", "product:delete", 3),
            # 产品分类
            (menu_map.get("category"), "新增分类", "category:create", 1),
            (menu_map.get("category"), "编辑分类", "category:update", 2),
            (menu_map.get("category"), "删除分类", "category:delete", 3),
            # 品牌管理
            (menu_map.get("brand"), "新增品牌", "brand:create", 1),
            (menu_map.get("brand"), "编辑品牌", "brand:update", 2),
            (menu_map.get("brand"), "删除品牌", "brand:delete", 3),
            # 规格分组
            (menu_map.get("specgroup"), "新增分组", "specgroup:create", 1),
            (menu_map.get("specgroup"), "编辑分组", "specgroup:update", 2),
            (menu_map.get("specgroup"), "删除分组", "specgroup:delete", 3),
        ]

        # 插入按钮菜单
        created_ids = []
        for parent_id, name, perm, sort in buttons:
            if not parent_id:
                print(f"警告: 跳过 {name} (perm={perm})，找不到父菜单")
                continue
            # 获取父菜单的 tree_path
            parent = await db.execute(text("SELECT tree_path FROM sys_menu WHERE id = :pid"), {"pid": parent_id})
            parent_tree = parent.scalar() or "0"

            btn = SysMenu(
                parent_id=parent_id,
                tree_path=f"{parent_tree},{0}",  # 占位，后面更新
                name=name,
                type="B",
                perm=perm,
                sort=sort,
                visible=1,
            )
            db.add(btn)
            await db.flush()
            btn.tree_path = f"{parent_tree},{btn.id}"
            created_ids.append(btn.id)

        await db.flush()

        # 授权给 ADMIN 角色
        role_id = (await db.execute(text("SELECT id FROM sys_role WHERE code = 'ADMIN'"))).scalar()
        if role_id:
            for mid in created_ids:
                exist = await db.execute(
                    text("SELECT 1 FROM sys_role_menu WHERE role_id = :rid AND menu_id = :mid"),
                    {"rid": role_id, "mid": mid},
                )
                if not exist.scalar():
                    await db.execute(
                        text("INSERT INTO sys_role_menu (role_id, menu_id) VALUES (:rid, :mid)"),
                        {"rid": role_id, "mid": mid},
                    )

        await db.commit()
        print(f"已插入 {len(created_ids)} 个按钮权限并授权给 ADMIN 角色")


if __name__ == "__main__":
    asyncio.run(seed())
