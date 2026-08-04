"""检查并修复产品菜单的 tree_path 格式。"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.database import AsyncSessionLocal
from sqlalchemy import text

async def fix():
    async with AsyncSessionLocal() as db:
        # 查看当前数据
        rows = await db.execute(text(
            "SELECT id, parent_id, tree_path, name FROM sys_menu "
            "WHERE route_path = '/product' OR parent_id IN "
            "(SELECT id FROM sys_menu WHERE route_path = '/product') "
            "ORDER BY sort"
        ))
        records = rows.all()
        print("=== 修复前 ===")
        for r in records:
            print(f"  id={r[0]} parent={r[1]} tree_path='{r[2]}' name={r[3]}")

        # 找到父菜单 ID
        parent_id = None
        for r in records:
            if r[1] == 0:  # parent_id == 0 说明是顶级
                parent_id = r[0]
                break

        if not parent_id:
            print("未找到产品库父菜单")
            return

        # 修复父菜单 tree_path = "0"
        await db.execute(
            text("UPDATE sys_menu SET tree_path = '0' WHERE id = :pid"),
            {"pid": parent_id},
        )
        print(f"\n父菜单 id={parent_id} tree_path 已修复为 '0'")

        # 修复子菜单 tree_path = "0,{parent_id},{child_id}"
        children = [r for r in records if r[1] == parent_id]
        for child in children:
            new_path = f"0,{parent_id},{child[0]}"
            await db.execute(
                text("UPDATE sys_menu SET tree_path = :tp WHERE id = :cid"),
                {"tp": new_path, "cid": child[0]},
            )
            print(f"子菜单 id={child[0]} tree_path 已修复为 '{new_path}'")

        await db.commit()
        print("\n=== 修复完成 ===")


if __name__ == "__main__":
    asyncio.run(fix())
