"""测试创建会话接口"""
import asyncio
import sys
import traceback


async def test():
    from app.database import AsyncSessionLocal
    from app.system.aitc.chat.service import ChatService
    from app.system.aitc.chat.schemas import SessionCreate

    async with AsyncSessionLocal() as db:
        try:
            service = ChatService(db)
            req = SessionCreate(title="测试对话", domain="case", context_json={"project_id": 1})
            vo = await service.create_session(req)
            print(f"OK: session id={vo.id}, title={vo.title}, context={vo.context_json}")
            await db.rollback()  # 回滚，不真正写入
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")
            traceback.print_exc()


asyncio.run(test())
