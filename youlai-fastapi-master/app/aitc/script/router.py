"""脚本域 — API 路由。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_perm
from app.response import Result
from app.aitc.script.schemas import (
    ScriptQuery, ScriptUpdate,
)
from app.aitc.script.service import ScriptService
from app.aitc.constants import (
    PERM_SCRIPT_LIST, PERM_SCRIPT_UPDATE,
)

router = APIRouter(tags=["脚本域"])


@router.get("/scripts", summary="脚本列表", dependencies=[Depends(require_perm(PERM_SCRIPT_LIST))])
async def get_script_page(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    caseId: int | None = Query(default=None),
    projectId: int | None = Query(default=None),
    status: int | None = Query(default=None),
    source: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = ScriptQuery(
        pageNum=pageNum, pageSize=pageSize,
        caseId=caseId, projectId=projectId, status=status, source=source,
    )
    return Result(data=await ScriptService(db).get_script_page(query))


@router.put("/scripts/{sid}", summary="编辑脚本", dependencies=[Depends(require_perm(PERM_SCRIPT_UPDATE))])
async def update_script(sid: int, form: ScriptUpdate, db: AsyncSession = Depends(get_db)):
    return Result(data=await ScriptService(db).update_script(sid, form))


@router.post("/scripts/{sid}/publish", summary="脚本入库", dependencies=[Depends(require_perm(PERM_SCRIPT_UPDATE))])
async def publish_script(sid: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await ScriptService(db).publish_script(sid))


@router.get("/scripts/{sid}/export", summary="导出脚本文件", dependencies=[Depends(require_perm(PERM_SCRIPT_LIST))])
async def export_script(sid: int, db: AsyncSession = Depends(get_db)):
    """导出指定脚本为文件下载。"""
    from fastapi.responses import PlainTextResponse
    content, filename = await ScriptService(db).export_script(sid)
    return PlainTextResponse(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.delete("/scripts/{ids}", summary="删除脚本", dependencies=[Depends(require_perm(PERM_SCRIPT_UPDATE))])
async def delete_scripts(ids: str, db: AsyncSession = Depends(get_db)):
    count = await ScriptService(db).delete_scripts(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")
