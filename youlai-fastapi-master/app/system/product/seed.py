"""种子数据脚本：预置产品分类、品牌、规格分组模板。
使用方式：在项目根目录执行 `python -m app.system.product.seed`（需确认数据库连接可用）。
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.database import AsyncSessionLocal, engine
from app.system.product.models import ProductCategory, ProductBrand, ProductSpecGroup
from sqlalchemy import select, func


async def seed():
    async with AsyncSessionLocal() as db:
        # ── 分类 ──
        exist = await db.execute(select(func.count()).select_from(ProductCategory).where(ProductCategory.is_deleted == 0))
        if exist.scalar() == 0:
            cats = [
                ProductCategory(name="网卡", slug="network-card", sort_order=1),
                ProductCategory(name="路由器", slug="router", sort_order=2),
            ]
            db.add_all(cats)
            await db.flush()
            print(f"Seeded {len(cats)} categories")

            # 获取分类 ID
            result = await db.execute(select(ProductCategory.id, ProductCategory.slug))
            cat_map = {row.slug: row.id for row in result}

            # ── 规格分组模板 ──
            spec_groups = [
                # 网卡
                ProductSpecGroup(category_id=cat_map["network-card"], name="基础参数", sort_order=1),
                ProductSpecGroup(category_id=cat_map["network-card"], name="性能指标", sort_order=2),
                ProductSpecGroup(category_id=cat_map["network-card"], name="硬件规格", sort_order=3),
                ProductSpecGroup(category_id=cat_map["network-card"], name="兼容性", sort_order=4),
                # 路由器
                ProductSpecGroup(category_id=cat_map["router"], name="基础参数", sort_order=1),
                ProductSpecGroup(category_id=cat_map["router"], name="端口规格", sort_order=2),
                ProductSpecGroup(category_id=cat_map["router"], name="无线规格", sort_order=3),
                ProductSpecGroup(category_id=cat_map["router"], name="性能指标", sort_order=4),
                ProductSpecGroup(category_id=cat_map["router"], name="功能特性", sort_order=5),
            ]
            db.add_all(spec_groups)
            print(f"Seeded {len(spec_groups)} spec groups")

        # ── 品牌 ──
        exist_b = await db.execute(select(func.count()).select_from(ProductBrand).where(ProductBrand.is_deleted == 0))
        if exist_b.scalar() == 0:
            brands = [
                ProductBrand(name="Intel", sort_order=1),
                ProductBrand(name="Mellanox", sort_order=2),
                ProductBrand(name="Broadcom", sort_order=3),
                ProductBrand(name="TP-Link", sort_order=4),
                ProductBrand(name="ASUS", sort_order=5),
                ProductBrand(name="Xiaomi", sort_order=6),
            ]
            db.add_all(brands)
            print(f"Seeded {len(brands)} brands")

        await db.commit()
        print("Seed completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
