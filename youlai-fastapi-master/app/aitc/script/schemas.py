"""脚本域 — Pydantic Schemas。"""

from pydantic import BaseModel, Field

from app.pagination import PageQuery
from app.serializers import BigId


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
