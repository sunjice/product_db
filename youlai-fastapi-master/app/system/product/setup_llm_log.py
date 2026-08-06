"""一键建表 + 挂菜单脚本。
使用方式：python -m app.system.product.setup_llm_log
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.database import AsyncSessionLocal, engine
from app.system.menu.models import SysMenu
from sqlalchemy import select, text, func


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ai_llm_logs (
    id BIGSERIAL PRIMARY KEY,
    trace_id VARCHAR(128) DEFAULT '' NOT NULL,
    span_seq INTEGER DEFAULT 0 NOT NULL,
    attempt INTEGER DEFAULT 0 NOT NULL,
    module VARCHAR(50) DEFAULT 'chat' NOT NULL,
    action VARCHAR(80) DEFAULT '' NOT NULL,
    session_id BIGINT,
    task_id BIGINT,
    message_id BIGINT,
    model VARCHAR(100) DEFAULT '' NOT NULL,
    status VARCHAR(20) DEFAULT 'success' NOT NULL,
    error_msg TEXT,
    messages JSONB,
    response_raw TEXT,
    response_json JSONB,
    prompt_tokens INTEGER DEFAULT 0 NOT NULL,
    completion_tokens INTEGER DEFAULT 0 NOT NULL,
    duration_ms INTEGER DEFAULT 0 NOT NULL,
    create_time TIMESTAMP DEFAULT now() NOT NULL
)
"""

INDEX_SQLS = [
    "CREATE INDEX IF NOT EXISTS idx_llm_log_session ON ai_llm_logs (session_id, create_time)",
    "CREATE INDEX IF NOT EXISTS idx_llm_log_trace ON ai_llm_logs (trace_id)",
    "CREATE INDEX IF NOT EXISTS idx_llm_log_status ON ai_llm_logs (status, create_time)",
    "CREATE INDEX IF NOT EXISTS idx_llm_log_action ON ai_llm_logs (action)",
]


async def setup():
    steps = []

    # ── Step 1: 建表（独立连接）──
    print("[1/2] Creating ai_llm_logs table...")
    try:
        async with engine.begin() as conn:
            await conn.execute(text(CREATE_TABLE_SQL))
            for idx_sql in INDEX_SQLS:
                await conn.execute(text(idx_sql))
        print("  OK - table created")
        steps.append("table")
    except Exception as e:
        print(f"  SKIP (may already exist): {e}")

    # ── Step 2: 挂菜单（独立会话）──
    print("[2/2] Inserting menu item...")
    try:
        async with AsyncSessionLocal() as db:
            parent_result = await db.execute(
                select(SysMenu).where(SysMenu.route_path == "/system", SysMenu.type == "C")
            )
            parent = parent_result.scalar_one_or_none()
            if parent is None:
                print("  FAIL - 'system management' menu not found. Ensure base data is initialized.")
                return

            exist_result = await db.execute(
                select(func.count()).select_from(SysMenu).where(
                    SysMenu.parent_id == parent.id,
                    SysMenu.route_name == "LlmLog",
                )
            )
            if exist_result.scalar() and exist_result.scalar() > 0:
                print("  OK - menu already exists, skip")
            else:
                menu = SysMenu(
                    parent_id=parent.id,
                    tree_path=f"{parent.tree_path}",
                    name="AI\u65e5\u5fd7",  # AI日志
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
                menu.tree_path = f"{parent.tree_path},{menu.id}"
                await db.flush()
                await db.commit()
                print(f"  OK - menu inserted id={menu.id} parent_id={parent.id}")
            steps.append("menu")
    except Exception as e:
        print(f"  FAIL: {e}")

    print(f"\nALL DONE! ({', '.join(steps)})")
    print("Restart backend & frontend, then check System > AI Log page.")


if __name__ == "__main__":
    asyncio.run(setup())
