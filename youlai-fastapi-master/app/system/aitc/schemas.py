"""测试部 AI 助手 — Pydantic Schemas。"""

from typing import Any

from pydantic import BaseModel, Field

from app.pagination import PageQuery
from app.serializers import BigId


# ═══════════════ 测试项目 ═══════════════

class ProjectQuery(PageQuery):
    keywords: str | None = Field(default=None, description="搜索关键词")


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="项目名称")
    prefix: str = Field(..., min_length=1, max_length=64, description="项目标识")
    description: str | None = Field(default=None, description="项目描述")


class ProjectUpdate(ProjectCreate):
    id: BigId | None = Field(default=None, description="项目ID")


class ProjectVO(BaseModel):
    id: BigId | None = None
    name: str = ""
    prefix: str = ""
    description: str | None = None
    last_sync_time: str | None = None
    create_time: str | None = None
    update_time: str | None = None
    model_config = {"from_attributes": True}


# ═══════════════ 套件树 ═══════════════

class SuiteNodeVO(BaseModel):
    """套件树节点（供 el-tree），node_type 区分套件(module)和用例(case)。"""
    id: BigId
    label: str
    name: str = ""
    project_id: BigId | None = None
    parent_id: BigId = 0
    sort_order: int = 0
    case_count: int = 0
    node_type: str = "suite"  # suite | case
    external_id: str | None = None  # 仅 case 节点有值（用例编号）
    children: list["SuiteNodeVO"] = Field(default_factory=list)
    model_config = {"from_attributes": True}


class SuiteVO(BaseModel):
    id: BigId | None = None
    project_id: BigId | None = None
    parent_id: BigId = 0
    tree_path: str = ""
    name: str = ""
    sort_order: int = 0
    create_time: str | None = None
    update_time: str | None = None
    model_config = {"from_attributes": True}


# ═══════════════ 用例 ═══════════════

class CaseStep(BaseModel):
    """测试步骤。"""
    step_no: int = 0
    action: str = ""
    expected: str = ""


class CaseQuery(PageQuery):
    projectId: BigId | None = Field(default=None, description="项目ID")
    suiteId: BigId | None = Field(default=None, description="套件ID（含子树）")
    isCore: int | None = Field(default=None, description="是否核心 0/1")
    isSample: int | None = Field(default=None, description="是否样本 0/1")
    reviewStatus: int | None = Field(default=None, description="审核状态 0/1")
    importance: int | None = Field(default=None, description="级别 1/2/3")
    keywords: str | None = Field(default=None, description="搜索关键词")
    sortField: str | None = Field(default=None, description="排序字段")
    sortOrder: str | None = Field(default=None, description="排序方向 ascending/descending")


class CaseVO(BaseModel):
    """用例列表行 / 详情。"""
    id: BigId | None = None
    project_id: BigId | None = None
    suite_id: BigId | None = None
    suite_name: str = ""
    external_id: str | None = None
    name: str = ""
    summary: str | None = None
    preconditions: str | None = None
    topo: str | None = None
    test_data: str | None = None
    steps: list[CaseStep] = Field(default_factory=list)
    importance: int = 2
    is_core: int = 0
    core_reason: str | None = None
    core_source: int | None = None
    is_sample: int = 0
    review_status: int = 0
    script_count: int = 0
    create_time: str | None = None
    update_time: str | None = None
    model_config = {"from_attributes": True}


class CaseUpdate(BaseModel):
    """人工编辑用例。"""
    external_id: str | None = Field(default=None, max_length=64, description="用例编号")
    name: str = Field(..., min_length=1, max_length=256)
    summary: str | None = None
    preconditions: str | None = None
    topo: str | None = None
    test_data: str | None = None
    steps: list[CaseStep] = Field(default_factory=list)
    importance: int = 2


class CaseCoreMark(BaseModel):
    """人工标记/取消核心。"""
    case_id: BigId = Field(..., description="用例ID")
    is_core: int = Field(..., description="0/1")
    reason: str | None = Field(default=None, max_length=512)


class CaseSampleMark(BaseModel):
    """人工标记/取消样本。"""
    case_id: BigId = Field(..., description="用例ID")
    is_sample: int = Field(..., description="0/1")


# ═══════════════ Excel 导入 ═══════════════

class ImportResult(BaseModel):
    """Excel 导入结果。"""
    created: int = 0
    updated: int = 0
    errors: list[dict] = Field(default_factory=list)  # [{row, msg}]


# ═══════════════ 样本库 ═══════════════

class SampleQuery(PageQuery):
    projectId: BigId | None = Field(default=None, description="项目ID")
    sampleType: str | None = Field(default=None, description="类型 case/script")
    keywords: str | None = Field(default=None, description="搜索关键词")


class SampleCreate(BaseModel):
    project_id: BigId | None = Field(default=None, description="项目ID，空为通用")
    sample_type: str = Field(..., min_length=1, max_length=16, description="case/script")
    name: str = Field(..., min_length=1, max_length=128, description="样本名称")
    language: str | None = Field(default=None, max_length=32, description="语言")
    framework: str | None = Field(default=None, max_length=32, description="框架")
    content: str = Field(..., min_length=1, description="样本内容")
    description: str | None = Field(default=None, max_length=512)
    status: int = Field(default=1, description="状态 0-停用 1-启用")


class SampleUpdate(SampleCreate):
    id: BigId | None = Field(default=None, description="样本ID")


class SampleVO(BaseModel):
    id: BigId | None = None
    project_id: BigId | None = None
    project_name: str | None = None
    sample_type: str = ""
    name: str = ""
    language: str | None = None
    framework: str | None = None
    content: str = ""
    description: str | None = None
    status: int = 1
    create_time: str | None = None
    update_time: str | None = None
    model_config = {"from_attributes": True}


# ═══════════════ AI 配置 ═══════════════

class AiConfigQuery(PageQuery):
    keywords: str | None = Field(default=None, description="搜索关键词")
    provider: str | None = Field(default=None, description="提供方")
    status: int | None = Field(default=None, description="状态 0/1")


class AiConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="配置名称")
    provider: str = Field(default="openai_compat", max_length=32)
    api_base: str = Field(..., min_length=1, max_length=256, description="API地址")
    api_key: str = Field(..., min_length=1, max_length=512, description="API密钥")
    model: str = Field(..., min_length=1, max_length=64, description="模型名")
    temperature: float = Field(default=0.3, ge=0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=32768)
    scenes: list[str] = Field(default_factory=list, description="适用场景列表")
    is_default: int = Field(default=0)
    status: int = Field(default=1)
    remark: str | None = Field(default=None, max_length=512)


class AiConfigUpdate(AiConfigCreate):
    id: BigId | None = Field(default=None, description="配置ID")


class AiConfigVO(BaseModel):
    id: BigId | None = None
    name: str = ""
    provider: str = ""
    api_base: str = ""
    api_key: str = ""  # 返回脱敏后的密钥
    model: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096
    scenes: list[str] = Field(default_factory=list)
    is_default: int = 0
    status: int = 1
    remark: str | None = None
    create_time: str | None = None
    update_time: str | None = None
    model_config = {"from_attributes": True}


# ═══════════════ AI 任务 ═══════════════

class TaskCreate(BaseModel):
    task_type: str = Field(..., description="core_select/case_review/script_gen")
    project_id: BigId = Field(..., description="项目ID")
    suite_id: BigId | None = Field(default=None, description="目标套件ID（未指定case_ids时必填）")
    sample_ids: list[BigId] = Field(default_factory=list, description="样本ID列表")
    spec_ids: list[BigId] | None = Field(default=None, description="规范ID列表（核心挑选时使用）")
    ai_config_id: BigId | None = Field(default=None, description="AI配置ID")
    case_ids: list[BigId] | None = Field(default=None, description="指定用例ID列表，为空则取全子树")


class TaskQuery(PageQuery):
    projectId: BigId | None = Field(default=None)
    taskType: str | None = Field(default=None)
    status: int | None = Field(default=None)


class TaskVO(BaseModel):
    id: BigId | None = None
    task_type: str = ""
    project_id: BigId | None = None
    project_name: str = ""
    suite_id: BigId | None = None
    suite_name: str = ""
    sample_ids: list = Field(default_factory=list)
    spec_ids: list | None = Field(default=None)
    ai_config_id: BigId | None = None
    model: str | None = None
    status: int = 0
    total_count: int = 0
    done_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    error_msg: str | None = None
    create_by: str | None = None
    create_time: str | None = None
    model_config = {"from_attributes": True}


class TaskItemVO(BaseModel):
    id: BigId | None = None
    task_id: BigId | None = None
    case_id: BigId | None = None
    case_name: str = ""
    output: dict | None = None
    item_status: int = 0
    confirm_status: int = 0
    final_content: str | None = None
    reviewed_by: str | None = None
    review_time: str | None = None
    model_config = {"from_attributes": True}


class TaskConfirmItem(BaseModel):
    """单条确认请求。"""
    item_id: BigId
    confirm_status: int = Field(..., description="1-采纳 2-忽略 3-编辑采纳")
    final_content: str | None = None


class TaskConfirmReq(BaseModel):
    items: list[TaskConfirmItem]


class ReviewRecordVO(BaseModel):
    """审核记录 VO。"""
    id: BigId | None = None
    task_id: BigId | None = None
    task_item_id: BigId | None = None
    case_id: BigId | None = None
    review_action: str = ""
    field_name: str | None = None
    before_value: str | None = None
    after_value: str | None = None
    reviewer: str | None = None
    reviewer_ip: str | None = None
    review_time: str | None = None
    memo: str | None = None
    create_time: str | None = None
    model_config = {"from_attributes": True}


class TaskItemWithCaseVO(TaskItemVO):
    """任务明细 + 用例详情（供审核页面使用）。"""
    case_detail: "CaseVO | None" = None


class ReviewFieldItem(BaseModel):
    """逐字段审核请求。"""
    field_name: str = Field(..., description="字段名：name/summary/preconditions/steps/test_data")
    action: str = Field(..., description="accept/ignore")
    edited_value: str | None = Field(default=None, description="编辑采纳后的值")


class ReviewItemReq(BaseModel):
    """审核单条明细请求。"""
    task_id: BigId
    item_id: BigId
    confirm_status: int = Field(..., description="1-采纳 2-忽略 3-编辑采纳")
    fields: list[ReviewFieldItem] = Field(default_factory=list, description="逐字段审核明细")
    final_content: str | None = Field(default=None, description="编辑采纳的最终内容")


# ═══════════════ 测试脚本 ═══════════════

class ScriptQuery(PageQuery):
    caseId: BigId | None = Field(default=None, description="用例ID")
    projectId: BigId | None = Field(default=None, description="项目ID")
    status: int | None = Field(default=None, description="1-草稿 2-已入库")
    source: int | None = Field(default=None, description="1-AI 2-人工")


class ScriptVO(BaseModel):
    id: BigId | None = None
    case_id: BigId | None = None
    case_name: str = ""
    language: str = "python"
    framework: str = "pytest"
    content: str = ""
    source: int = 1
    task_item_id: BigId | None = None
    version: int = 1
    status: int = 1
    reviewed_by: str | None = None
    create_time: str | None = None
    update_time: str | None = None
    model_config = {"from_attributes": True}


class ScriptUpdate(BaseModel):
    content: str = Field(..., min_length=1, description="脚本内容")
    version: int = Field(default=1, description="版本号")


# ═══════════════ 用例审核工作台 ═══════════════

class PendingSuiteNodeVO(BaseModel):
    """套件树节点（含待审核计数）。"""
    id: BigId
    label: str
    name: str = ""
    project_id: BigId | None = None
    parent_id: BigId = 0
    sort_order: int = 0
    case_count: int = 0
    pending_count: int = 0
    children: list["PendingSuiteNodeVO"] = Field(default_factory=list)
    cases: list["PendingCaseVO"] = Field(default_factory=list)
    model_config = {"from_attributes": True}


class PendingCaseVO(BaseModel):
    """待审核用例摘要。"""
    id: BigId
    external_id: str | None = None
    name: str = ""
    importance: int = 2


class FieldSuggestionVO(BaseModel):
    """单个字段的 AI 修改建议。"""
    field_name: str = ""
    original: Any | None = None
    suggested: Any | None = None
    has_suggestion: bool = False
    conclusion: str = ""        # pass / fail
    rule_violated: str = ""     # 违反的规范说明


class CaseReviewDetailVO(BaseModel):
    """用例审核详情（原用例 + AI 建议）。"""
    case: CaseVO | None = None
    task_item_id: BigId | None = None
    task_id: BigId | None = None
    score: int | None = None
    issues: list[str] = Field(default_factory=list)
    suggestions: list[FieldSuggestionVO] = Field(default_factory=list)
    overall_assessment: str = ""  # 整体评价


class CaseFieldReviewItem(BaseModel):
    """逐字段审核结果。"""
    field_name: str = Field(..., description="字段名")
    action: str = Field(..., description="accept/ignore")
    edited_value: Any | None = None


class CaseReviewReq(BaseModel):
    """提交用例审核请求。"""
    case_id: BigId
    task_item_id: BigId
    fields: list[CaseFieldReviewItem] = Field(default_factory=list)


# ═══════════════ 下拉选项 ═══════════════

class OptionVO(BaseModel):
    value: BigId
    label: str


# ═══════════════ 规范管理 ═══════════════

class SpecQuery(PageQuery):
    projectId: BigId | None = Field(default=None, description="项目ID")
    suiteId: BigId | None = Field(default=None, description="模块ID")
    taskType: str | None = Field(default=None, description="任务类型 core_select/case_review/script_gen")
    specType: str | None = Field(default=None, description="规范类型 general/module_specific/common_issues")
    keywords: str | None = Field(default=None, description="搜索关键词")


class SpecCreate(BaseModel):
    project_id: BigId | None = Field(default=None, description="项目ID，空为全局通用")
    suite_id: BigId | None = Field(default=None, description="模块ID（套件ID），模块专用规范时使用")
    task_type: str = Field(..., min_length=1, max_length=32, description="任务类型 core_select/case_review/script_gen")
    spec_type: str = Field(..., min_length=1, max_length=32, description="规范类型 general/module_specific/common_issues")
    content: str = Field(..., min_length=1, description="规范内容（Markdown）")
    sort_order: int = Field(default=0, description="排序号")
    status: int = Field(default=1, description="状态 0-停用 1-启用")




class SpecUpdate(SpecCreate):
    id: BigId | None = Field(default=None, description="规范ID")


class SpecVO(BaseModel):
    id: BigId | None = None
    project_id: BigId | None = None
    project_name: str | None = None
    suite_id: BigId | None = None
    suite_name: str | None = None
    task_type: str = ""
    spec_type: str = ""
    content: str = ""
    sort_order: int = 0
    status: int = 1
    create_time: str | None = None
    update_time: str | None = None
    model_config = {"from_attributes": True}
