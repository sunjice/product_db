"""清理软删除记录，避免唯一约束冲突。"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.database import AsyncSessionLocal
from sqlalchemy import text

async def cleanup():
    async with AsyncSessionLocal() as db:
        # 删除所有引用软删除记录的规格
        r1 = await db.execute(text("""
            DELETE FROM product_specifications 
            WHERE is_deleted = 1 
               OR product_id IN (SELECT id FROM products WHERE is_deleted = 1)
               OR group_id IN (SELECT id FROM product_spec_groups WHERE is_deleted = 1)
        """))
        # 删除软删除的产品
        r2 = await db.execute(text("DELETE FROM products WHERE is_deleted = 1"))
        # 删除软删除的分组
        r3 = await db.execute(text("DELETE FROM product_spec_groups WHERE is_deleted = 1"))
        # 删除软删除的分类
        r4 = await db.execute(text("DELETE FROM product_categories WHERE is_deleted = 1"))
        # 删除软删除的品牌
        r5 = await db.execute(text("DELETE FROM product_brands WHERE is_deleted = 1"))
        await db.commit()
        print(f"清理: 规格 {r1.rowcount}, 产品 {r2.rowcount}, 分组 {r3.rowcount}, 分类 {r4.rowcount}, 品牌 {r5.rowcount}")

asyncio.run(cleanup())
