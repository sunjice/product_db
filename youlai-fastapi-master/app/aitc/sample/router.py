"""样本域 — API 路由。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_perm
from app.response import Result
from app.aitc.sample.schemas import (
    SampleCreate, SampleQuery, SampleUpdate,
)
from app.aitc.sample.service import SampleService
from app.aitc.constants import (
    PERM_SAMPLE_LIST, PERM_SAMPLE_CREATE, PERM_SAMPLE_UPDATE, PERM_SAMPLE_DELETE,
)

router = APIRouter(tags=["样本域"])


@router.get("/samples", summary="样本列表", dependencies=[Depends(require_perm(PERM_SAMPLE_LIST))])
async def get_sample_page(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    projectId: int | None = Query(default=None),
    sampleType: str | None = Query(default=None),
    keywords: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = SampleQuery(
        pageNum=pageNum, pageSize=pageSize,
        projectId=projectId, sampleType=sampleType, keywords=keywords,
    )
    return Result(data=await SampleService(db).get_sample_page(query))


@router.post("/samples", summary="创建样本", dependencies=[Depends(require_perm(PERM_SAMPLE_CREATE))])
async def create_sample(form: SampleCreate, db: AsyncSession = Depends(get_db)):
    return Result(data=await SampleService(db).create_sample(form))


@router.put("/samples/{sid}", summary="更新样本", dependencies=[Depends(require_perm(PERM_SAMPLE_UPDATE))])
async def update_sample(sid: int, form: SampleUpdate, db: AsyncSession = Depends(get_db)):
    form.id = sid
    return Result(data=await SampleService(db).update_sample(form))


@router.delete("/samples/{ids}", summary="删除样本", dependencies=[Depends(require_perm(PERM_SAMPLE_DELETE))])
async def delete_samples(ids: str, db: AsyncSession = Depends(get_db)):
    count = await SampleService(db).delete_sample(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")
