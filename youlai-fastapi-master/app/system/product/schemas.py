"""产品模块 Schemas。"""

from pydantic import BaseModel, Field

from app.pagination import PageQuery
from app.serializers import BigId


# ── 分类 ──

class CategoryQuery(PageQuery):
    keywords: str | None = Field(default=None, description="搜索关键词")


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="分类名称")
    slug: str = Field(..., min_length=1, max_length=64, description="分类标识")
    sort_order: int = Field(default=0, description="排序")


class CategoryUpdate(CategoryCreate):
    id: BigId = Field(..., description="分类ID")


class CategoryVO(BaseModel):
    id: BigId | None = None
    name: str = ""
    slug: str = ""
    sort_order: int = 0
    create_time: str | None = None
    update_time: str | None = None
    model_config = {"from_attributes": True}


# ── 品牌 ──

class BrandQuery(PageQuery):
    keywords: str | None = Field(default=None, description="搜索关键词")


class BrandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="品牌名称")
    logo_url: str | None = Field(default=None, max_length=255, description="品牌Logo")
    sort_order: int = Field(default=0, description="排序")


class BrandUpdate(BrandCreate):
    id: BigId = Field(..., description="品牌ID")


class BrandVO(BaseModel):
    id: BigId | None = None
    name: str = ""
    logo_url: str | None = None
    sort_order: int = 0
    create_time: str | None = None
    update_time: str | None = None
    model_config = {"from_attributes": True}


# ── 规格分组 ──

class SpecGroupQuery(PageQuery):
    category_id: BigId | None = Field(default=None, description="分类ID")
    keywords: str | None = Field(default=None, description="搜索关键词")


class SpecGroupCreate(BaseModel):
    category_id: BigId = Field(..., description="分类ID")
    name: str = Field(..., min_length=1, max_length=64, description="分组名称")
    sort_order: int = Field(default=0, description="排序")


class SpecGroupUpdate(SpecGroupCreate):
    id: BigId = Field(..., description="分组ID")


class SpecGroupVO(BaseModel):
    id: BigId | None = None
    category_id: BigId | None = None
    category_name: str | None = None
    name: str = ""
    sort_order: int = 0
    create_time: str | None = None
    update_time: str | None = None
    model_config = {"from_attributes": True}


# ── 规格项 ──

class SpecItem(BaseModel):
    id: BigId | None = None
    group_id: BigId | None = None
    group_name: str | None = None
    spec_name: str = ""
    spec_value: str | None = ""
    spec_unit: str | None = ""
    sort_order: int = 0


# ── 产品 ──

class ProductQuery(PageQuery):
    categoryId: BigId | None = Field(default=None, description="分类ID")
    brandId: BigId | None = Field(default=None, description="品牌ID")
    keywords: str | None = Field(default=None, description="搜索关键词（名称/型号）")
    status: int | None = Field(default=None, description="状态")


class ProductCreate(BaseModel):
    category_id: BigId = Field(..., description="分类ID")
    brand_id: BigId = Field(..., description="品牌ID")
    name: str = Field(..., min_length=1, max_length=128, description="产品名称")
    model: str | None = Field(default=None, max_length=64, description="产品型号")
    description: str | None = Field(default=None, description="产品描述")
    image_urls: list[str] = Field(default_factory=list, description="图片URL列表")
    status: int = Field(default=1, description="状态 1-上架 0-下架")
    sort_order: int = Field(default=0, description="排序")
    specifications: list[SpecItem] = Field(default_factory=list, description="规格列表")


class ProductUpdate(ProductCreate):
    id: BigId = Field(..., description="产品ID")


class SpecGroupDetailVO(BaseModel):
    """规格分组详情 VO — 包含分组内规格项列表（用于产品详情嵌套）。"""
    group_id: BigId | None = None
    group_name: str = ""
    sort_order: int = 0
    items: list[SpecItem] = Field(default_factory=list)


class ProductVO(BaseModel):
    id: BigId | None = None
    category_id: BigId | None = None
    category_name: str | None = None
    brand_id: BigId | None = None
    brand_name: str | None = None
    name: str = ""
    model: str | None = None
    description: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    status: int = 1
    sort_order: int = 0
    groups: list[SpecGroupDetailVO] = Field(default_factory=list)
    create_time: str | None = None
    update_time: str | None = None
    model_config = {"from_attributes": True}


class ProductCompareVO(BaseModel):
    products: list[ProductVO] = Field(default_factory=list)
    common_groups: list[str] = Field(default_factory=list)


# ── 下拉选项 ──

class OptionVO(BaseModel):
    value: BigId
    label: str
