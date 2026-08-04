"""给 ADMIN 角色授权产品数据库菜单。"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.database import AsyncSessionLocal
from sqlalchemy import text

PRODUCT_ROUTES = ["/product", "list", "category", "brand", "specgroup", r"detail/:id", "compare"]


async def seed():
    async with AsyncSessionLocal() as db:
        # 获取产品库所有菜单 ID
        rows = await db.execute(text("SELECT id, route_path FROM sys_menu WHERE parent_id IN (SELECT id FROM sys_menu WHERE route_path = '/product') OR route_path = '/product'"))
        menu_ids = [row[0] for row in rows]
        print(f"Found {len(menu_ids)} product menu ids")

        # 获取 ADMIN 角色 ID
        role_id = (await db.execute(
            text("SELECT id FROM sys_role WHERE code = 'ADMIN'")
        )).scalar()

        if not role_id:
            print("ADMIN 角色不存在，跳过。")
            return

        # 插入 sys_role_menu（跳过已存在的）
        count = 0
        for mid in menu_ids:
            exist = await db.execute(
                text("SELECT 1 FROM sys_role_menu WHERE role_id = :rid AND menu_id = :mid"),
                {"rid": role_id, "mid": mid},
            )
            if not exist.scalar():
                await db.execute(
                    text("INSERT INTO sys_role_menu (role_id, menu_id) VALUES (:rid, :mid)"),
                    {"rid": role_id, "mid": mid},
                )
                count += 1
        await db.commit()
        print(f"已为 ADMIN 角色新增 {count} 个菜单授权")


if __name__ == "__main__":
    asyncio.run(seed())
