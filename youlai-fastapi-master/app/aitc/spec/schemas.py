"""规范域 — Pydantic Schemas。"""

from pydantic import BaseModel, Field

from app.pagination import PageQuery
from app.serializers import BigId


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
