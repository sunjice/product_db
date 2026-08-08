"""任务域 — Pydantic Schemas（Task / TaskItem / Review）。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.pagination import PageQuery
from app.serializers import BigId


# ═══════════════ AI 任务 ═══════════════

class TaskCreate(BaseModel):
    task_type: str = Field(..., description="core_select/case_review/script_gen")
    project_id: BigId = Field(..., description="项目ID")
    suite_id: BigId | None = Field(default=None, description="目标套件ID（未指定case_ids时必填）")
    spec_ids: list[BigId] | None = Field(default=None, description="规范ID列表（核心挑选时使用）")
    ai_config_id: BigId | None = Field(default=None, description="AI配置ID")
    case_ids: list[BigId] | None = Field(default=None, description="指定用例ID列表，为空则取全子树")
    session_id: BigId | None = Field(default=None, description="创建任务的会话ID（从对话中发起任务时传入）")


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
    spec_ids: list | None = Field(default=None)
    ai_config_id: BigId | None = None
    model: str | None = None
    status: int = 0
    total_count: int = 0
    done_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    session_id: BigId | None = None
    error_msg: str | None = None
    create_by: str | None = None
    create_time: str | None = None
    model_config = {"from_attributes": True}


class TaskItemVO(BaseModel):
    id: BigId | None = None
    task_id: BigId | None = None
    case_id: BigId | None = None
    case_name: str = ""
    project_prefix: str = ""
    external_id: str | None = None
    purpose: str = ""
    importance: int = 2
    output: dict | None = None
    item_status: int = 0
    confirm_status: int = 0
    final_content: str | None = None
    reviewed_by: str | None = None
    review_time: str | None = None
    is_core: bool | None = Field(default=None, description="审核后的最终核心决策（core_select）")
    model_config = {"from_attributes": True}


class TaskConfirmItem(BaseModel):
    """单条确认请求。"""
    item_id: BigId
    confirm_status: int = Field(..., description="1-采纳 2-忽略 3-编辑采纳")
    final_content: str | None = None
    is_core: bool | None = Field(default=None, description="core_select 专用：最终核心决策")


class TaskConfirmReq(BaseModel):
    items: list[TaskConfirmItem]


class ReviewRecordVO(BaseModel):
    """审核记录 VO。"""
    id: BigId | None = None
    task_id: BigId | None = None
    task_item_id: BigId | None = None
    case_id: BigId | None = None
    case_name: str | None = None
    review_action: str = ""
    field_name: str | None = None
    before_value: str | None = None
    after_value: str | None = None
    reviewer: str | None = None
    reviewer_ip: str | None = None
    review_time: datetime | None = None
    memo: str | None = None
    create_time: datetime | None = None
    model_config = {"from_attributes": True}


class TaskItemWithCaseVO(TaskItemVO):
    """任务明细 + 用例详情（供审核页面使用）。"""
    case_detail: Any | None = None


class ReviewFieldItem(BaseModel):
    """逐字段审核请求。"""
    field_name: str = Field(..., description="字段名：name/summary/preconditions/steps/test_data")
    action: str = Field(..., description="accept/ignore")
    edited_value: Any | None = Field(default=None, description="编辑采纳后的值（文本/JSON数组均可）")


class ReviewItemReq(BaseModel):
    """审核单条明细请求。"""
    task_id: BigId
    item_id: BigId
    confirm_status: int = Field(..., description="1-采纳 2-忽略 3-编辑采纳")
    fields: list[ReviewFieldItem] = Field(default_factory=list, description="逐字段审核明细")
    final_content: str | None = Field(default=None, description="编辑采纳的最终内容")
