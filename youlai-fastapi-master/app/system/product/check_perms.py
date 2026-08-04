"""检查 ADMIN 用户的 perms 是否包含产品权限。"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as db:
        # 获取 ADMIN 角色的所有 perms
        rows = await db.execute(text("""
            SELECT DISTINCT m.perm, m.name, m.type
            FROM sys_menu m
            INNER JOIN sys_role_menu rm ON m.id = rm.menu_id
            INNER JOIN sys_role r ON rm.role_id = r.id
            WHERE r.code = 'ADMIN' AND m.perm IS NOT NULL AND m.perm != ''
            ORDER BY m.perm
        """))
        perms = rows.all()
        print(f"ADMIN 角色共有 {len(perms)} 个权限:")
        for p in perms:
            marker = " <<<" if p[0].startswith(("product", "category", "brand", "specgroup")) else ""
            print(f"  {p[0]:30s} [{p[2]}] {p[1]}{marker}")


if __name__ == "__main__":
    asyncio.run(check())
