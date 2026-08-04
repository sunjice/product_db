"""产品数据库路由 — 分类/品牌/规格分组/产品 CRUD，含产品对比。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_perm
from app.response import Result
from app.system.product.schemas import (
    BrandCreate, BrandQuery, BrandUpdate,
    CategoryCreate, CategoryQuery, CategoryUpdate,
    ProductCreate, ProductQuery, ProductUpdate,
    SpecGroupCreate, SpecGroupQuery, SpecGroupUpdate,
)
from app.system.product.service import ProductService

router = APIRouter(prefix="/api/v1", tags=["产品数据库"])


# ═══════════════ 分类 ═══════════════

@router.get("/categories", summary="分类分页列表", dependencies=[Depends(require_perm("category:list"))])
async def get_category_page(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    keywords: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = CategoryQuery(pageNum=pageNum, pageSize=pageSize, keywords=keywords)
    return Result(data=await ProductService(db).get_category_page(query))


@router.get("/categories/options", summary="分类下拉选项", dependencies=[Depends(require_perm("category:list"))])
async def get_category_options(db: AsyncSession = Depends(get_db)):
    return Result(data=await ProductService(db).get_category_options())


@router.get("/categories/{cat_id}", summary="分类详情", dependencies=[Depends(require_perm("category:list"))])
async def get_category(cat_id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await ProductService(db).get_category_by_id(cat_id))


@router.post("/categories", summary="创建分类", dependencies=[Depends(require_perm("category:create"))])
async def create_category(form: CategoryCreate, db: AsyncSession = Depends(get_db)):
    return Result(data=await ProductService(db).create_category(form))


@router.put("/categories/{cat_id}", summary="更新分类", dependencies=[Depends(require_perm("category:update"))])
async def update_category(cat_id: int, form: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    form.id = cat_id
    return Result(data=await ProductService(db).update_category(form))


@router.delete("/categories/{ids}", summary="删除分类", dependencies=[Depends(require_perm("category:delete"))])
async def delete_categories(ids: str, db: AsyncSession = Depends(get_db)):
    count = await ProductService(db).delete_category(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")


# ═══════════════ 品牌 ═══════════════

@router.get("/brands", summary="品牌分页列表", dependencies=[Depends(require_perm("brand:list"))])
async def get_brand_page(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    keywords: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = BrandQuery(pageNum=pageNum, pageSize=pageSize, keywords=keywords)
    return Result(data=await ProductService(db).get_brand_page(query))


@router.get("/brands/options", summary="品牌下拉选项", dependencies=[Depends(require_perm("brand:list"))])
async def get_brand_options(db: AsyncSession = Depends(get_db)):
    return Result(data=await ProductService(db).get_brand_options())


@router.get("/brands/{brand_id}", summary="品牌详情", dependencies=[Depends(require_perm("brand:list"))])
async def get_brand(brand_id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await ProductService(db).get_brand_by_id(brand_id))


@router.post("/brands", summary="创建品牌", dependencies=[Depends(require_perm("brand:create"))])
async def create_brand(form: BrandCreate, db: AsyncSession = Depends(get_db)):
    return Result(data=await ProductService(db).create_brand(form))


@router.put("/brands/{brand_id}", summary="更新品牌", dependencies=[Depends(require_perm("brand:update"))])
async def update_brand(brand_id: int, form: BrandUpdate, db: AsyncSession = Depends(get_db)):
    form.id = brand_id
    return Result(data=await ProductService(db).update_brand(form))


@router.delete("/brands/{ids}", summary="删除品牌", dependencies=[Depends(require_perm("brand:delete"))])
async def delete_brands(ids: str, db: AsyncSession = Depends(get_db)):
    count = await ProductService(db).delete_brand(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")


# ═══════════════ 规格分组 ═══════════════

@router.get("/specgroups", summary="规格分组分页列表", dependencies=[Depends(require_perm("specgroup:list"))])
async def get_spec_group_page(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    category_id: int | None = Query(default=None),
    keywords: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = SpecGroupQuery(pageNum=pageNum, pageSize=pageSize, category_id=category_id, keywords=keywords)
    return Result(data=await ProductService(db).get_spec_group_page(query))


@router.get("/specgroups/options", summary="规格分组下拉选项", dependencies=[Depends(require_perm("specgroup:list"))])
async def get_spec_group_options(
    category_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    return Result(data=await ProductService(db).get_spec_group_options(category_id))


@router.post("/specgroups", summary="创建规格分组", dependencies=[Depends(require_perm("specgroup:create"))])
async def create_spec_group(form: SpecGroupCreate, db: AsyncSession = Depends(get_db)):
    return Result(data=await ProductService(db).create_spec_group(form))


@router.put("/specgroups/{group_id}", summary="更新规格分组", dependencies=[Depends(require_perm("specgroup:update"))])
async def update_spec_group(group_id: int, form: SpecGroupUpdate, db: AsyncSession = Depends(get_db)):
    form.id = group_id
    return Result(data=await ProductService(db).update_spec_group(form))


@router.delete("/specgroups/{ids}", summary="删除规格分组", dependencies=[Depends(require_perm("specgroup:delete"))])
async def delete_spec_groups(ids: str, db: AsyncSession = Depends(get_db)):
    count = await ProductService(db).delete_spec_group(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")


# ═══════════════ 产品 ═══════════════

@router.get("/products/compare", summary="产品对比", dependencies=[Depends(require_perm("product:compare"))])
async def compare_products(ids: str = Query(..., description="产品ID，逗号分隔（2-4个）"), db: AsyncSession = Depends(get_db)):
    return Result(data=await ProductService(db).compare_products(ids))


@router.get("/products", summary="产品分页列表", dependencies=[Depends(require_perm("product:list"))])
async def get_product_page(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    categoryId: int | None = Query(default=None),
    brandId: int | None = Query(default=None),
    keywords: str | None = Query(default=None),
    status: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = ProductQuery(pageNum=pageNum, pageSize=pageSize, categoryId=categoryId, brandId=brandId, keywords=keywords, status=status)
    return Result(data=await ProductService(db).get_product_page(query))


@router.get("/products/{product_id}", summary="产品详情", dependencies=[Depends(require_perm("product:list"))])
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await ProductService(db).get_product_by_id(product_id))


@router.post("/products", summary="创建产品", dependencies=[Depends(require_perm("product:create"))])
async def create_product(form: ProductCreate, db: AsyncSession = Depends(get_db)):
    return Result(data=await ProductService(db).create_product(form))


@router.put("/products/{product_id}", summary="更新产品", dependencies=[Depends(require_perm("product:update"))])
async def update_product(product_id: int, form: ProductUpdate, db: AsyncSession = Depends(get_db)):
    form.id = product_id
    return Result(data=await ProductService(db).update_product(form))


@router.delete("/products/{ids}", summary="删除产品", dependencies=[Depends(require_perm("product:delete"))])
async def delete_products(ids: str, db: AsyncSession = Depends(get_db)):
    count = await ProductService(db).delete_product(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")
