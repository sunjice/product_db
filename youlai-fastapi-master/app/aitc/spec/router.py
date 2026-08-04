"""规范域 — API 路由。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_perm
from app.response import Result
from app.aitc.spec.schemas import (
    SpecCreate, SpecQuery, SpecUpdate,
)
from app.aitc.spec.service import SpecService
from app.aitc.constants import (
    PERM_SPEC_LIST, PERM_SPEC_CREATE, PERM_SPEC_UPDATE, PERM_SPEC_DELETE,
)

router = APIRouter(tags=["规范域"])


@router.get("/specs", summary="规范分页列表", dependencies=[Depends(require_perm(PERM_SPEC_LIST))])
async def get_spec_page(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    projectId: int | None = Query(default=None, description="项目ID"),
    suiteId: int | None = Query(default=None, description="模块ID"),
    taskType: str | None = Query(default=None, description="任务类型"),
    specType: str | None = Query(default=None, description="规范类型"),
    keywords: str | None = Query(default=None, description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
):
    query = SpecQuery(
        pageNum=pageNum, pageSize=pageSize,
        projectId=projectId, suiteId=suiteId,
        taskType=taskType, specType=specType,
        keywords=keywords,
    )
    return Result(data=await SpecService(db).get_spec_page(query))


@router.get("/specs/options", summary="规范下拉选项", dependencies=[Depends(require_perm(PERM_SPEC_LIST))])
async def get_spec_options(
    projectId: int | None = Query(default=None, description="项目ID"),
    taskType: str | None = Query(default=None, description="任务类型"),
    specType: str | None = Query(default=None, description="规范类型"),
    db: AsyncSession = Depends(get_db),
):
    return Result(data=await SpecService(db).get_spec_options(projectId, taskType, specType))


@router.get("/specs/{spec_id}", summary="规范详情", dependencies=[Depends(require_perm(PERM_SPEC_LIST))])
async def get_spec(spec_id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await SpecService(db).get_spec_by_id(spec_id))


@router.post("/specs", summary="创建规范", dependencies=[Depends(require_perm(PERM_SPEC_CREATE))])
async def create_spec(form: SpecCreate, db: AsyncSession = Depends(get_db)):
    return Result(data=await SpecService(db).create_spec(form))


@router.put("/specs/{spec_id}", summary="更新规范", dependencies=[Depends(require_perm(PERM_SPEC_UPDATE))])
async def update_spec(spec_id: int, form: SpecUpdate, db: AsyncSession = Depends(get_db)):
    form.id = spec_id
    return Result(data=await SpecService(db).update_spec(form))


@router.delete("/specs/{ids}", summary="删除规范", dependencies=[Depends(require_perm(PERM_SPEC_DELETE))])
async def delete_specs(ids: str, db: AsyncSession = Depends(get_db)):
    count = await SpecService(db).delete_spec(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")
