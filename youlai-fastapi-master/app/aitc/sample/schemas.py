"""样本域 — Pydantic Schemas。"""

from pydantic import BaseModel, Field

from app.pagination import PageQuery
from app.serializers import BigId


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
