"""测试部 AI 助手 — API 路由（项目/套件/用例/提示词/样本/配置/脚本）。"""

from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_perm
from app.response import Result
from app.system.aitc.schemas import (
    AiConfigCreate, AiConfigQuery, AiConfigUpdate,
    CaseCoreMark, CaseQuery, CaseUpdate,
    CaseSampleMark,
    CaseReviewReq,
    ProjectCreate, ProjectQuery, ProjectUpdate,
    SampleCreate, SampleQuery, SampleUpdate,
    ScriptQuery, ScriptUpdate,
    TaskCreate, TaskQuery, TaskConfirmReq, ReviewItemReq,
    SpecCreate, SpecQuery, SpecUpdate,
)
from app.system.aitc.service import AiTcService
from app.system.aitc.task_engine import TaskEngine
from app.system.aitc.constants import (
    PERM_PROJECT_LIST, PERM_PROJECT_CREATE, PERM_PROJECT_UPDATE, PERM_PROJECT_DELETE,
    PERM_CASE_LIST, PERM_CASE_IMPORT, PERM_CASE_UPDATE, PERM_CASE_DELETE, PERM_CASE_CORE, PERM_CASE_SAMPLE,
    PERM_SAMPLE_LIST, PERM_SAMPLE_CREATE, PERM_SAMPLE_UPDATE, PERM_SAMPLE_DELETE,
    PERM_AICONFIG_LIST, PERM_AICONFIG_CREATE, PERM_AICONFIG_UPDATE, PERM_AICONFIG_DELETE,
    PERM_TASK_CREATE, PERM_TASK_LIST, PERM_TASK_CONFIRM,
    PERM_SCRIPT_LIST, PERM_SCRIPT_UPDATE,
    PERM_SPEC_LIST, PERM_SPEC_CREATE, PERM_SPEC_UPDATE, PERM_SPEC_DELETE,
)
from app.dependencies import get_current_user
from app.auth.schemas import SysUserDetails
from fastapi import Request

router = APIRouter(prefix="/api/v1/aitc", tags=["测试部AI助手"])


# ═══════════════ 项目 ═══════════════

@router.get("/projects", summary="项目分页列表", dependencies=[Depends(require_perm(PERM_PROJECT_LIST))])
async def get_project_page(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    keywords: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = ProjectQuery(pageNum=pageNum, pageSize=pageSize, keywords=keywords)
    return Result(data=await AiTcService(db).get_project_page(query))


@router.get("/projects/options", summary="项目下拉选项", dependencies=[Depends(require_perm(PERM_PROJECT_LIST))])
async def get_project_options(db: AsyncSession = Depends(get_db)):
    return Result(data=await AiTcService(db).get_project_options())


@router.get("/projects/{pid}", summary="项目详情", dependencies=[Depends(require_perm(PERM_PROJECT_LIST))])
async def get_project(pid: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await AiTcService(db).get_project_by_id(pid))


@router.post("/projects", summary="创建项目", dependencies=[Depends(require_perm(PERM_PROJECT_CREATE))])
async def create_project(form: ProjectCreate, db: AsyncSession = Depends(get_db)):
    return Result(data=await AiTcService(db).create_project(form))


@router.put("/projects/{pid}", summary="更新项目", dependencies=[Depends(require_perm(PERM_PROJECT_UPDATE))])
async def update_project(pid: int, form: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    form.id = pid
    return Result(data=await AiTcService(db).update_project(form))


@router.delete("/projects/{ids}", summary="删除项目", dependencies=[Depends(require_perm(PERM_PROJECT_DELETE))])
async def delete_projects(ids: str, db: AsyncSession = Depends(get_db)):
    count = await AiTcService(db).delete_project(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")


# ═══════════════ 套件树 ═══════════════

@router.get("/suites/tree", summary="套件树", dependencies=[Depends(require_perm(PERM_CASE_LIST))])
async def get_suite_tree(
    projectId: int = Query(..., description="项目ID"),
    db: AsyncSession = Depends(get_db),
):
    return Result(data=await AiTcService(db).get_suite_tree(projectId))


@router.get("/suites/{suite_id}/children", summary="套件子节点（懒加载）", dependencies=[Depends(require_perm(PERM_CASE_LIST))])
async def get_suite_children(
    suite_id: int,
    projectId: int | None = Query(None, description="项目ID（suite_id=0 时必传）"),
    db: AsyncSession = Depends(get_db),
):
    return Result(data=await AiTcService(db).get_suite_children(suite_id, projectId))


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
    return Result(data=await AiTcService(db).get_case_page(query))


@router.get("/cases/pending-tree", summary="待审核用例树", dependencies=[Depends(require_perm(PERM_CASE_LIST))])
async def get_pending_review_tree(
    projectId: int = Query(..., description="项目ID"),
    db: AsyncSession = Depends(get_db),
):
    """获取项目下套件树，每个节点标注待审核用例数。"""
    return Result(data=await AiTcService(db).get_pending_review_tree(projectId))


@router.get("/cases/pending-list", summary="套件下待审核用例列表", dependencies=[Depends(require_perm(PERM_CASE_LIST))])
async def get_pending_case_list(
    suiteId: int = Query(..., description="套件ID"),
    db: AsyncSession = Depends(get_db),
):
    """获取套件及其子树下所有待审核用例。"""
    return Result(data=await AiTcService(db).get_pending_case_list(suiteId))


@router.get("/cases/{case_id}", summary="用例详情", dependencies=[Depends(require_perm(PERM_CASE_LIST))])
async def get_case(case_id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await AiTcService(db).get_case_by_id(case_id))


@router.put("/cases/{case_id}", summary="编辑用例", dependencies=[Depends(require_perm(PERM_CASE_UPDATE))])
async def update_case(case_id: int, form: CaseUpdate, db: AsyncSession = Depends(get_db)):
    return Result(data=await AiTcService(db).update_case(case_id, form))


@router.patch("/cases/core", summary="标记/取消核心用例", dependencies=[Depends(require_perm(PERM_CASE_CORE))])
async def mark_case_core(form: CaseCoreMark, db: AsyncSession = Depends(get_db)):
    await AiTcService(db).mark_case_core(form)
    return Result(msg="操作成功")


@router.patch("/cases/sample", summary="标记/取消样本用例", dependencies=[Depends(require_perm(PERM_CASE_SAMPLE))])
async def mark_case_sample(form: CaseSampleMark, db: AsyncSession = Depends(get_db)):
    await AiTcService(db).mark_case_sample(form)
    return Result(msg="操作成功")


@router.delete("/cases/{ids}", summary="删除用例", dependencies=[Depends(require_perm(PERM_CASE_DELETE))])
async def delete_cases(ids: str, db: AsyncSession = Depends(get_db)):
    count = await AiTcService(db).delete_cases(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")


# ═══════════════ 用例审核详情 ═══════════════


@router.get("/cases/{case_id}/review-detail", summary="用例审核详情（原用例+AI建议）", dependencies=[Depends(require_perm(PERM_CASE_LIST))])
async def get_case_review_detail(
    case_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取用例原始内容 + AI 修改建议对比。"""
    return Result(data=await AiTcService(db).get_case_review_detail(case_id))


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
    await AiTcService(db).review_case(form, reviewed_by=user.username, reviewer_ip=reviewer_ip)
    return Result(msg="审核完成")


# ═══════════════ Excel 导入/模板 ═══════════════

@router.get("/cases/import/template", summary="下载导入模板", dependencies=[Depends(require_perm(PERM_CASE_IMPORT))])
async def download_template(db: AsyncSession = Depends(get_db)):
    content = await AiTcService(db).download_template()
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
    result = await AiTcService(db).import_cases(projectId, content)
    return Result(data=result)


# ═══════════════ 提示词模板 ═══════════════

# ═══════════════ 样本库 ═══════════════

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
    return Result(data=await AiTcService(db).get_sample_page(query))


@router.post("/samples", summary="创建样本", dependencies=[Depends(require_perm(PERM_SAMPLE_CREATE))])
async def create_sample(form: SampleCreate, db: AsyncSession = Depends(get_db)):
    return Result(data=await AiTcService(db).create_sample(form))


@router.put("/samples/{sid}", summary="更新样本", dependencies=[Depends(require_perm(PERM_SAMPLE_UPDATE))])
async def update_sample(sid: int, form: SampleUpdate, db: AsyncSession = Depends(get_db)):
    form.id = sid
    return Result(data=await AiTcService(db).update_sample(form))


@router.delete("/samples/{ids}", summary="删除样本", dependencies=[Depends(require_perm(PERM_SAMPLE_DELETE))])
async def delete_samples(ids: str, db: AsyncSession = Depends(get_db)):
    count = await AiTcService(db).delete_sample(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")


# ═══════════════ AI 配置 ═══════════════

@router.get("/aiconfigs", summary="AI配置列表", dependencies=[Depends(require_perm(PERM_AICONFIG_LIST))])
async def get_ai_config_page(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    keywords: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    status: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = AiConfigQuery(pageNum=pageNum, pageSize=pageSize, keywords=keywords, provider=provider, status=status)
    return Result(data=await AiTcService(db).get_ai_config_page(query))


@router.get("/aiconfigs/options", summary="AI配置下拉选项", dependencies=[Depends(require_perm(PERM_AICONFIG_LIST))])
async def get_ai_config_options(
    scene: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    return Result(data=await AiTcService(db).get_ai_config_options(scene))


@router.post("/aiconfigs", summary="创建AI配置", dependencies=[Depends(require_perm(PERM_AICONFIG_CREATE))])
async def create_ai_config(form: AiConfigCreate, db: AsyncSession = Depends(get_db)):
    return Result(data=await AiTcService(db).create_ai_config(form))


@router.put("/aiconfigs/{cid}", summary="更新AI配置", dependencies=[Depends(require_perm(PERM_AICONFIG_UPDATE))])
async def update_ai_config(cid: int, form: AiConfigUpdate, db: AsyncSession = Depends(get_db)):
    form.id = cid
    return Result(data=await AiTcService(db).update_ai_config(form))


@router.delete("/aiconfigs/{ids}", summary="删除AI配置", dependencies=[Depends(require_perm(PERM_AICONFIG_DELETE))])
async def delete_ai_configs(ids: str, db: AsyncSession = Depends(get_db)):
    count = await AiTcService(db).delete_ai_config(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")


# ═══════════════ AI 任务 ═══════════════

@router.post("/tasks", summary="创建AI任务", dependencies=[Depends(require_perm(PERM_TASK_CREATE))])
async def create_task(
    form: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user: SysUserDetails = Depends(get_current_user),
):
    """创建 AI 任务并启动后台执行。"""
    engine = TaskEngine(db)
    result = await engine.create_task(form, create_by=user.username)
    return Result(data=result, msg="任务已创建，已加入排队队列")


@router.get("/tasks", summary="任务分页列表", dependencies=[Depends(require_perm(PERM_TASK_LIST))])
async def get_task_page(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    projectId: int | None = Query(default=None),
    taskType: str | None = Query(default=None),
    status: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = TaskQuery(pageNum=pageNum, pageSize=pageSize, projectId=projectId, taskType=taskType, status=status)
    engine = TaskEngine(db)
    return Result(data=await engine.get_task_page(query))


@router.get("/tasks/{task_id}", summary="任务详情（含明细）", dependencies=[Depends(require_perm(PERM_TASK_LIST))])
async def get_task_detail(task_id: int, db: AsyncSession = Depends(get_db)):
    engine = TaskEngine(db)
    return Result(data=await engine.get_task_detail(task_id))


@router.get("/tasks/{task_id}/items", summary="任务明细列表", dependencies=[Depends(require_perm(PERM_TASK_LIST))])
async def get_task_items(task_id: int, db: AsyncSession = Depends(get_db)):
    engine = TaskEngine(db)
    return Result(data=await engine.get_task_items(task_id))


@router.post("/tasks/{task_id}/rerun", summary="重新执行任务", dependencies=[Depends(require_perm(PERM_TASK_CREATE))])
async def rerun_task(task_id: int, db: AsyncSession = Depends(get_db)):
    engine = TaskEngine(db)
    await engine.rerun_task(task_id)
    return Result(msg="任务已重新加入排队队列")


@router.post("/tasks/{task_id}/confirm", summary="确认任务结果", dependencies=[Depends(require_perm(PERM_TASK_CONFIRM))])
async def confirm_task_items(
    task_id: int,
    form: TaskConfirmReq,
    db: AsyncSession = Depends(get_db),
    user: SysUserDetails = Depends(get_current_user),
    request: Request = None,
):
    engine = TaskEngine(db)
    reviewer_ip = request.client.host if request and request.client else ""
    await engine.confirm_task_items(task_id, form, reviewed_by=user.username, reviewer_ip=reviewer_ip)
    return Result(msg="确认成功，结果已应用")


@router.get("/tasks/{task_id}/items/{item_id}", summary="获取单条任务明细+用例详情", dependencies=[Depends(require_perm(PERM_TASK_LIST))])
async def get_task_item_with_case(
    task_id: int, item_id: int, db: AsyncSession = Depends(get_db),
):
    engine = TaskEngine(db)
    return Result(data=await engine.get_item_with_case(task_id, item_id))


@router.post("/tasks/{task_id}/items/{item_id}/review", summary="审核单条明细（含逐字段审核记录）", dependencies=[Depends(require_perm(PERM_TASK_CONFIRM))])
async def review_task_item(
    task_id: int,
    item_id: int,
    form: ReviewItemReq,
    db: AsyncSession = Depends(get_db),
    user: SysUserDetails = Depends(get_current_user),
    request: Request = None,
):
    engine = TaskEngine(db)
    reviewer_ip = request.client.host if request and request.client else ""
    await engine.review_single_item(task_id, item_id, form, reviewed_by=user.username, reviewer_ip=reviewer_ip)
    return Result(msg="审核成功")


@router.get("/tasks/{task_id}/review-records", summary="查询任务审核记录", dependencies=[Depends(require_perm(PERM_TASK_LIST))])
async def get_review_records(task_id: int, db: AsyncSession = Depends(get_db)):
    engine = TaskEngine(db)
    return Result(data=await engine.get_review_records(task_id))


# ═══════════════ 脚本库 ═══════════════

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
    return Result(data=await AiTcService(db).get_script_page(query))


@router.put("/scripts/{sid}", summary="编辑脚本", dependencies=[Depends(require_perm(PERM_SCRIPT_UPDATE))])
async def update_script(sid: int, form: ScriptUpdate, db: AsyncSession = Depends(get_db)):
    return Result(data=await AiTcService(db).update_script(sid, form))


@router.post("/scripts/{sid}/publish", summary="脚本入库", dependencies=[Depends(require_perm(PERM_SCRIPT_UPDATE))])
async def publish_script(sid: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await AiTcService(db).publish_script(sid))


@router.get("/scripts/{sid}/export", summary="导出脚本文件", dependencies=[Depends(require_perm(PERM_SCRIPT_LIST))])
async def export_script(sid: int, db: AsyncSession = Depends(get_db)):
    """导出指定脚本为文件下载。"""
    from fastapi.responses import PlainTextResponse
    content, filename = await AiTcService(db).export_script(sid)
    return PlainTextResponse(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.delete("/scripts/{ids}", summary="删除脚本", dependencies=[Depends(require_perm(PERM_SCRIPT_UPDATE))])
async def delete_scripts(ids: str, db: AsyncSession = Depends(get_db)):
    count = await AiTcService(db).delete_scripts(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")


# ═══════════════ 规范管理 ═══════════════

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
    return Result(data=await AiTcService(db).get_spec_page(query))


@router.get("/specs/options", summary="规范下拉选项", dependencies=[Depends(require_perm(PERM_SPEC_LIST))])
async def get_spec_options(
    projectId: int | None = Query(default=None, description="项目ID"),
    taskType: str | None = Query(default=None, description="任务类型"),
    specType: str | None = Query(default=None, description="规范类型"),
    db: AsyncSession = Depends(get_db),
):
    return Result(data=await AiTcService(db).get_spec_options(projectId, taskType, specType))


@router.get("/specs/{spec_id}", summary="规范详情", dependencies=[Depends(require_perm(PERM_SPEC_LIST))])
async def get_spec(spec_id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await AiTcService(db).get_spec_by_id(spec_id))


@router.post("/specs", summary="创建规范", dependencies=[Depends(require_perm(PERM_SPEC_CREATE))])
async def create_spec(form: SpecCreate, db: AsyncSession = Depends(get_db)):
    return Result(data=await AiTcService(db).create_spec(form))


@router.put("/specs/{spec_id}", summary="更新规范", dependencies=[Depends(require_perm(PERM_SPEC_UPDATE))])
async def update_spec(spec_id: int, form: SpecUpdate, db: AsyncSession = Depends(get_db)):
    form.id = spec_id
    return Result(data=await AiTcService(db).update_spec(form))


@router.delete("/specs/{ids}", summary="删除规范", dependencies=[Depends(require_perm(PERM_SPEC_DELETE))])
async def delete_specs(ids: str, db: AsyncSession = Depends(get_db)):
    count = await AiTcService(db).delete_spec(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")
