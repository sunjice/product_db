"""用例域 — API 路由（项目/套件/用例/审核/导入）。"""

from fastapi import APIRouter, Depends, Query, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_perm, get_current_user
from app.response import Result
from app.auth.schemas import SysUserDetails
from app.aitc.case.schemas import (
    CaseCoreMark, CaseQuery, CaseUpdate,
    CaseSampleMark,
    CaseReviewReq,
    ProjectCreate, ProjectQuery, ProjectUpdate,
)
from app.aitc.case.service import CaseService
from app.aitc.constants import (
    PERM_PROJECT_LIST, PERM_PROJECT_CREATE, PERM_PROJECT_UPDATE, PERM_PROJECT_DELETE,
    PERM_CASE_LIST, PERM_CASE_IMPORT, PERM_CASE_UPDATE, PERM_CASE_DELETE,
    PERM_CASE_CORE, PERM_CASE_SAMPLE,
    PERM_TASK_CONFIRM,
)

router = APIRouter(tags=["用例域"])


# ═══════════════ 项目 ═══════════════

@router.get("/projects", summary="项目分页列表", dependencies=[Depends(require_perm(PERM_PROJECT_LIST))])
async def get_project_page(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    keywords: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = ProjectQuery(pageNum=pageNum, pageSize=pageSize, keywords=keywords)
    return Result(data=await CaseService(db).get_project_page(query))


@router.get("/projects/options", summary="项目下拉选项", dependencies=[Depends(require_perm(PERM_PROJECT_LIST))])
async def get_project_options(db: AsyncSession = Depends(get_db)):
    return Result(data=await CaseService(db).get_project_options())


@router.get("/projects/{pid}", summary="项目详情", dependencies=[Depends(require_perm(PERM_PROJECT_LIST))])
async def get_project(pid: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await CaseService(db).get_project_by_id(pid))


@router.post("/projects", summary="创建项目", dependencies=[Depends(require_perm(PERM_PROJECT_CREATE))])
async def create_project(form: ProjectCreate, db: AsyncSession = Depends(get_db)):
    return Result(data=await CaseService(db).create_project(form))


@router.put("/projects/{pid}", summary="更新项目", dependencies=[Depends(require_perm(PERM_PROJECT_UPDATE))])
async def update_project(pid: int, form: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    form.id = pid
    return Result(data=await CaseService(db).update_project(form))


@router.delete("/projects/{ids}", summary="删除项目", dependencies=[Depends(require_perm(PERM_PROJECT_DELETE))])
async def delete_projects(ids: str, db: AsyncSession = Depends(get_db)):
    count = await CaseService(db).delete_project(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")


# ═══════════════ 套件树 ═══════════════

@router.get("/suites/tree", summary="套件树", dependencies=[Depends(require_perm(PERM_CASE_LIST))])
async def get_suite_tree(
    projectId: int = Query(..., description="项目ID"),
    db: AsyncSession = Depends(get_db),
):
    return Result(data=await CaseService(db).get_suite_tree(projectId))


@router.get("/suites/{suite_id}/children", summary="套件子节点（懒加载）", dependencies=[Depends(require_perm(PERM_CASE_LIST))])
async def get_suite_children(
    suite_id: int,
    projectId: int | None = Query(None, description="项目ID（suite_id=0 时必传）"),
    db: AsyncSession = Depends(get_db),
):
    return Result(data=await CaseService(db).get_suite_children(suite_id, projectId))


# ═══════════════ 用例 ═══════════════

@router.get("/cases", summary="用例分页列表", dependencies=[Depends(require_perm(PERM_CASE_LIST))])
async def get_case_page(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    projectId: int | None = Query(default=None, description="项目ID"),
    suiteId: int | None = Query(default=None, description="套件ID（含子树）"),
    isCore: int | None = Query(default=None, description="是否核心 0/1"),
    isSample: int | None = Query(default=None, description="是否样本 0/1"),
    reviewStatus: int | None = Query(default=None, description="审核状态 0/1"),
    importance: int | None = Query(default=None, description="级别 1/2/3"),
    keywords: str | None = Query(default=None, description="搜索关键词"),
    sortField: str | None = Query(default=None, description="排序字段"),
    sortOrder: str | None = Query(default=None, description="排序方向 ascending/descending"),
    db: AsyncSession = Depends(get_db),
):
    query = CaseQuery(
        pageNum=pageNum, pageSize=pageSize,
        projectId=projectId, suiteId=suiteId,
        isCore=isCore, isSample=isSample, reviewStatus=reviewStatus,
        importance=importance, keywords=keywords,
        sortField=sortField, sortOrder=sortOrder,
    )
    return Result(data=await CaseService(db).get_case_page(query))


@router.get("/cases/pending-tree", summary="待审核用例树", dependencies=[Depends(require_perm(PERM_CASE_LIST))])
async def get_pending_review_tree(
    projectId: int = Query(..., description="项目ID"),
    db: AsyncSession = Depends(get_db),
):
    """获取项目下套件树，每个节点标注待审核用例数。"""
    return Result(data=await CaseService(db).get_pending_review_tree(projectId))


@router.get("/cases/pending-list", summary="套件下待审核用例列表", dependencies=[Depends(require_perm(PERM_CASE_LIST))])
async def get_pending_case_list(
    suiteId: int = Query(..., description="套件ID"),
    db: AsyncSession = Depends(get_db),
):
    """获取套件及其子树下所有待审核用例。"""
    return Result(data=await CaseService(db).get_pending_case_list(suiteId))


@router.get("/cases/{case_id}", summary="用例详情", dependencies=[Depends(require_perm(PERM_CASE_LIST))])
async def get_case(case_id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await CaseService(db).get_case_by_id(case_id))


@router.put("/cases/{case_id}", summary="编辑用例", dependencies=[Depends(require_perm(PERM_CASE_UPDATE))])
async def update_case(case_id: int, form: CaseUpdate, db: AsyncSession = Depends(get_db)):
    return Result(data=await CaseService(db).update_case(case_id, form))


@router.patch("/cases/core", summary="标记/取消核心用例", dependencies=[Depends(require_perm(PERM_CASE_CORE))])
async def mark_case_core(form: CaseCoreMark, db: AsyncSession = Depends(get_db)):
    await CaseService(db).mark_case_core(form)
    return Result(msg="操作成功")


@router.patch("/cases/sample", summary="标记/取消样本用例", dependencies=[Depends(require_perm(PERM_CASE_SAMPLE))])
async def mark_case_sample(form: CaseSampleMark, db: AsyncSession = Depends(get_db)):
    await CaseService(db).mark_case_sample(form)
    return Result(msg="操作成功")


@router.delete("/cases/{ids}", summary="删除用例", dependencies=[Depends(require_perm(PERM_CASE_DELETE))])
async def delete_cases(ids: str, db: AsyncSession = Depends(get_db)):
    count = await CaseService(db).delete_cases(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")


# ═══════════════ 用例审核详情 ═══════════════

@router.get("/cases/{case_id}/review-detail", summary="用例审核详情（原用例+AI建议）", dependencies=[Depends(require_perm(PERM_CASE_LIST))])
async def get_case_review_detail(
    case_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取用例原始内容 + AI 修改建议对比。"""
    return Result(data=await CaseService(db).get_case_review_detail(case_id))


@router.post("/cases/{case_id}/review", summary="提交用例审核", dependencies=[Depends(require_perm(PERM_TASK_CONFIRM))])
async def review_case(
    case_id: int,
    form: CaseReviewReq,
    db: AsyncSession = Depends(get_db),
    user: SysUserDetails = Depends(get_current_user),
    request: Request = None,
):
    """提交逐字段审核结果，采纳的字段写入用例，生成审计记录。"""
    reviewer_ip = request.client.host if request and request.client else ""
    form.case_id = case_id
    await CaseService(db).review_case(form, reviewed_by=user.username, reviewer_ip=reviewer_ip)
    return Result(msg="审核完成")


# ═══════════════ Excel 导入/模板 ═══════════════

@router.get("/cases/import/template", summary="下载导入模板", dependencies=[Depends(require_perm(PERM_CASE_IMPORT))])
async def download_template(db: AsyncSession = Depends(get_db)):
    content = await CaseService(db).download_template()
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=用例导入模板.xlsx"},
    )


@router.post("/cases/import", summary="Excel导入用例", dependencies=[Depends(require_perm(PERM_CASE_IMPORT))])
async def import_cases(
    projectId: int = Query(..., description="目标项目ID"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    result = await CaseService(db).import_cases(projectId, content)
    return Result(data=result)
