"""种子数据：在 sys_menu 表中插入产品数据库菜单。
使用方式：.venv\Scripts\python.exe -m app.system.product.seed_menus
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
        # 检查是否已存在
        exist = await db.execute(
            select(func.count()).select_from(SysMenu).where(SysMenu.route_path == "/product")
        )
        if exist.scalar() and exist.scalar() > 0:
            print("产品库菜单已存在，跳过。")
            return

        # 1. 插入父菜单：产品库（目录）
        parent = SysMenu(
            parent_id=0,
            name="产品库",
            type="C",
            route_name="Product",
            route_path="/product",
            component="Layout",
            redirect="/product/list",
            icon="goods",
            sort=10,
            visible=1,
            always_show=0,
            keep_alive=0,
        )
        db.add(parent)
        await db.flush()
        parent_id = parent.id

        # 2. 插入子菜单
        children = [
            SysMenu(
                parent_id=parent_id,
                name="产品管理",
                type="M",
                route_name="ProductList",
                route_path="list",
                component="product/index",
                perm="product:list",
                icon="goods",
                sort=1,
                visible=1,
            ),
            SysMenu(
                parent_id=parent_id,
                name="产品分类",
                type="M",
                route_name="ProductCategory",
                route_path="category",
                component="product/category",
                perm="category:list",
                icon="goods",
                sort=2,
                visible=1,
            ),
            SysMenu(
                parent_id=parent_id,
                name="品牌管理",
                type="M",
                route_name="ProductBrand",
                route_path="brand",
                component="product/brand",
                perm="brand:list",
                icon="goods",
                sort=3,
                visible=1,
            ),
            SysMenu(
                parent_id=parent_id,
                name="规格分组",
                type="M",
                route_name="ProductSpecGroup",
                route_path="specgroup",
                component="product/specgroup",
                perm="specgroup:list",
                icon="goods",
                sort=4,
                visible=1,
            ),
            SysMenu(
                parent_id=parent_id,
                name="产品详情",
                type="M",
                route_name="ProductDetail",
                route_path="detail/:id",
                component="product/detail",
                sort=5,
                visible=0,
            ),
            SysMenu(
                parent_id=parent_id,
                name="产品对比",
                type="M",
                route_name="ProductCompare",
                route_path="compare",
                component="product/compare",
                perm="product:compare",
                sort=6,
                visible=0,
            ),
        ]
        db.add_all(children)
        await db.flush()

        # 3. 更新 tree_path
        parent.tree_path = f"{parent_id}"
        for child in children:
            child.tree_path = f"{parent_id}/{child.id}"

        await db.commit()
        print(f"菜单已插入：1 个目录 + {len(children)} 个子菜单，parent_id={parent_id}")


if __name__ == "__main__":
    asyncio.run(seed())
