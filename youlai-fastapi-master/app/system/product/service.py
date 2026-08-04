"""产品数据库模块：分类/品牌/规格分组/产品的完整 CRUD，以及产品对比查询。"""

from datetime import datetime

from sqlalchemy import func, select, text, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.pagination import PageResult
from app.exceptions import BusinessException
from app.response import ResultCode
from app.system.product.models import (
    Product, ProductBrand, ProductCategory, ProductSpecGroup, ProductSpecification,
)
from app.system.product.schemas import (
    BrandCreate, BrandQuery, BrandUpdate, BrandVO,
    CategoryCreate, CategoryQuery, CategoryUpdate, CategoryVO,
    ProductCompareVO, ProductCreate, ProductQuery, ProductUpdate, ProductVO,
    SpecGroupCreate, SpecGroupDetailVO, SpecGroupQuery, SpecGroupUpdate, SpecGroupVO,
    SpecItem, OptionVO,
)


class ProductService:
    """产品数据库全部业务逻辑。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ═══════════════ 分类 CRUD ═══════════════

    async def get_category_page(self, query: CategoryQuery) -> PageResult:
        conditions = [ProductCategory.is_deleted == 0]
        if query.keywords:
            kw = f"%{query.keywords}%"
            conditions.append(ProductCategory.name.ilike(kw))

        stmt = select(ProductCategory).where(*conditions).order_by(ProductCategory.sort_order, ProductCategory.id)
        count_q = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        offset = (query.pageNum - 1) * query.pageSize
        rows = await self.db.execute(stmt.offset(offset).limit(query.pageSize))
        items = rows.scalars().all()

        return PageResult(
            records=[self._category_to_vo(c) for c in items],
            total=total, pageNum=query.pageNum, pageSize=query.pageSize,
        )

    async def get_category_options(self) -> list[OptionVO]:
        rows = await self.db.execute(
            select(ProductCategory.id, ProductCategory.name)
            .where(ProductCategory.is_deleted == 0)
            .order_by(ProductCategory.sort_order)
        )
        return [OptionVO(value=r.id, label=r.name) for r in rows]

    async def get_category_by_id(self, cat_id: int) -> CategoryVO:
        result = await self.db.execute(
            select(ProductCategory).where(ProductCategory.id == cat_id, ProductCategory.is_deleted == 0)
        )
        cat = result.scalar_one_or_none()
        if cat is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="分类不存在")
        return self._category_to_vo(cat)

    async def create_category(self, form: CategoryCreate) -> CategoryVO:
        # 查全部记录（含软删除），避免唯一约束冲突
        exist = await self.db.execute(
            select(ProductCategory).where(ProductCategory.slug == form.slug)
        )
        existing = exist.scalar_one_or_none()
        if existing is not None:
            if existing.is_deleted == 0:
                raise BusinessException(code=ResultCode.DUPLICATE_KEY, msg="分类标识已存在")
            # 恢复软删除的记录
            existing.name = form.name
            existing.slug = form.slug
            existing.sort_order = form.sort_order
            existing.is_deleted = 0
            existing.update_time = datetime.now()
            await self.db.flush()
            logger.info(f"Category restored: {form.name} id={existing.id}")
            return self._category_to_vo(existing)
        cat = ProductCategory(**form.model_dump())
        self.db.add(cat)
        await self.db.flush()
        logger.info(f"Category created: {form.name} id={cat.id}")
        return self._category_to_vo(cat)

    async def update_category(self, form: CategoryUpdate) -> CategoryVO:
        result = await self.db.execute(
            select(ProductCategory).where(ProductCategory.id == form.id, ProductCategory.is_deleted == 0)
        )
        cat = result.scalar_one_or_none()
        if cat is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="分类不存在")
        # 查全部记录（含软删除），排除自身
        exist = await self.db.execute(
            select(ProductCategory.id).where(
                ProductCategory.slug == form.slug,
                ProductCategory.id != form.id,
                ProductCategory.is_deleted == 0,
            )
        )
        if exist.scalar() is not None:
            raise BusinessException(code=ResultCode.DUPLICATE_KEY, msg="分类标识已存在")
        cat.name = form.name
        cat.slug = form.slug
        cat.sort_order = form.sort_order
        cat.update_time = datetime.now()
        await self.db.flush()
        logger.info(f"Category updated: {form.name} id={form.id}")
        return self._category_to_vo(cat)

    async def delete_category(self, ids: str) -> int:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
        if not id_list:
            raise BusinessException(code=ResultCode.PARAM_VALID_FAIL, msg="请选择要删除的分类")
        await self.db.execute(
            text("UPDATE product_categories SET is_deleted = 1 WHERE id = ANY(:ids)"),
            {"ids": id_list},
        )
        logger.info(f"Categories deleted: {id_list}")
        return len(id_list)

    # ═══════════════ 品牌 CRUD ═══════════════

    async def get_brand_page(self, query: BrandQuery) -> PageResult:
        conditions = [ProductBrand.is_deleted == 0]
        if query.keywords:
            kw = f"%{query.keywords}%"
            conditions.append(ProductBrand.name.ilike(kw))

        stmt = select(ProductBrand).where(*conditions).order_by(ProductBrand.sort_order, ProductBrand.id)
        count_q = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        offset = (query.pageNum - 1) * query.pageSize
        rows = await self.db.execute(stmt.offset(offset).limit(query.pageSize))
        items = rows.scalars().all()

        return PageResult(
            records=[self._brand_to_vo(b) for b in items],
            total=total, pageNum=query.pageNum, pageSize=query.pageSize,
        )

    async def get_brand_options(self) -> list[OptionVO]:
        rows = await self.db.execute(
            select(ProductBrand.id, ProductBrand.name)
            .where(ProductBrand.is_deleted == 0)
            .order_by(ProductBrand.sort_order)
        )
        return [OptionVO(value=r.id, label=r.name) for r in rows]

    async def get_brand_by_id(self, brand_id: int) -> BrandVO:
        result = await self.db.execute(
            select(ProductBrand).where(ProductBrand.id == brand_id, ProductBrand.is_deleted == 0)
        )
        brand = result.scalar_one_or_none()
        if brand is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="品牌不存在")
        return self._brand_to_vo(brand)

    async def create_brand(self, form: BrandCreate) -> BrandVO:
        # 查全部记录（含软删除），避免唯一约束冲突
        exist = await self.db.execute(
            select(ProductBrand).where(ProductBrand.name == form.name)
        )
        existing = exist.scalar_one_or_none()
        if existing is not None:
            if existing.is_deleted == 0:
                raise BusinessException(code=ResultCode.DUPLICATE_KEY, msg="品牌名称已存在")
            # 恢复软删除的记录
            existing.name = form.name
            existing.logo_url = form.logo_url
            existing.sort_order = form.sort_order
            existing.is_deleted = 0
            existing.update_time = datetime.now()
            await self.db.flush()
            logger.info(f"Brand restored: {form.name} id={existing.id}")
            return self._brand_to_vo(existing)
        brand = ProductBrand(**form.model_dump())
        self.db.add(brand)
        await self.db.flush()
        logger.info(f"Brand created: {form.name} id={brand.id}")
        return self._brand_to_vo(brand)

    async def update_brand(self, form: BrandUpdate) -> BrandVO:
        result = await self.db.execute(
            select(ProductBrand).where(ProductBrand.id == form.id, ProductBrand.is_deleted == 0)
        )
        brand = result.scalar_one_or_none()
        if brand is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="品牌不存在")
        exist = await self.db.execute(
            select(ProductBrand.id).where(
                ProductBrand.name == form.name,
                ProductBrand.is_deleted == 0,
                ProductBrand.id != form.id,
            )
        )
        if exist.scalar() is not None:
            raise BusinessException(code=ResultCode.DUPLICATE_KEY, msg="品牌名称已存在")
        brand.name = form.name
        brand.logo_url = form.logo_url
        brand.sort_order = form.sort_order
        brand.update_time = datetime.now()
        await self.db.flush()
        logger.info(f"Brand updated: {form.name} id={form.id}")
        return self._brand_to_vo(brand)

    async def delete_brand(self, ids: str) -> int:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
        if not id_list:
            raise BusinessException(code=ResultCode.PARAM_VALID_FAIL, msg="请选择要删除的品牌")
        await self.db.execute(
            text("UPDATE product_brands SET is_deleted = 1 WHERE id = ANY(:ids)"),
            {"ids": id_list},
        )
        logger.info(f"Brands deleted: {id_list}")
        return len(id_list)

    # ═══════════════ 规格分组 CRUD ═══════════════

    async def get_spec_group_page(self, query: SpecGroupQuery) -> PageResult:
        conditions = [ProductSpecGroup.is_deleted == 0]
        if query.category_id is not None:
            conditions.append(ProductSpecGroup.category_id == query.category_id)
        if query.keywords:
            kw = f"%{query.keywords}%"
            conditions.append(ProductSpecGroup.name.ilike(kw))

        stmt = (
            select(ProductSpecGroup)
            .where(*conditions)
            .order_by(ProductSpecGroup.category_id, ProductSpecGroup.sort_order, ProductSpecGroup.id)
        )
        count_q = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        offset = (query.pageNum - 1) * query.pageSize
        rows = await self.db.execute(stmt.offset(offset).limit(query.pageSize))
        items = rows.scalars().all()

        # 批量获取分类名
        cat_ids = list({g.category_id for g in items})
        cat_map: dict[int, str] = {}
        if cat_ids:
            cat_rows = await self.db.execute(
                select(ProductCategory.id, ProductCategory.name).where(ProductCategory.id.in_(cat_ids))
            )
            cat_map = {r.id: r.name for r in cat_rows}

        return PageResult(
            records=[self._spec_group_to_vo(g, cat_map.get(g.category_id)) for g in items],
            total=total, pageNum=query.pageNum, pageSize=query.pageSize,
        )

    async def get_spec_group_options(self, category_id: int | None = None) -> list[OptionVO]:
        stmt = select(ProductSpecGroup.id, ProductSpecGroup.name).where(ProductSpecGroup.is_deleted == 0)
        if category_id is not None:
            stmt = stmt.where(ProductSpecGroup.category_id == category_id)
        rows = await self.db.execute(stmt.order_by(ProductSpecGroup.sort_order))
        return [OptionVO(value=r.id, label=r.name) for r in rows]

    async def create_spec_group(self, form: SpecGroupCreate) -> SpecGroupVO:
        group = ProductSpecGroup(**form.model_dump())
        self.db.add(group)
        await self.db.flush()
        cat_name = await self._get_category_name(group.category_id)
        logger.info(f"SpecGroup created: {form.name} id={group.id}")
        return self._spec_group_to_vo(group, cat_name)

    async def update_spec_group(self, form: SpecGroupUpdate) -> SpecGroupVO:
        result = await self.db.execute(
            select(ProductSpecGroup).where(ProductSpecGroup.id == form.id, ProductSpecGroup.is_deleted == 0)
        )
        group = result.scalar_one_or_none()
        if group is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="规格分组不存在")
        group.category_id = form.category_id
        group.name = form.name
        group.sort_order = form.sort_order
        group.update_time = datetime.now()
        await self.db.flush()
        cat_name = await self._get_category_name(group.category_id)
        logger.info(f"SpecGroup updated: {form.name} id={form.id}")
        return self._spec_group_to_vo(group, cat_name)

    async def delete_spec_group(self, ids: str) -> int:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
        if not id_list:
            raise BusinessException(code=ResultCode.PARAM_VALID_FAIL, msg="请选择要删除的规格分组")
        await self.db.execute(
            text("UPDATE product_spec_groups SET is_deleted = 1 WHERE id = ANY(:ids)"),
            {"ids": id_list},
        )
        logger.info(f"SpecGroups deleted: {id_list}")
        return len(id_list)

    # ═══════════════ 产品 CRUD ═══════════════

    async def get_product_page(self, query: ProductQuery) -> PageResult:
        conditions = [Product.is_deleted == 0]
        if query.categoryId is not None:
            conditions.append(Product.category_id == query.categoryId)
        if query.brandId is not None:
            conditions.append(Product.brand_id == query.brandId)
        if query.keywords:
            kw = f"%{query.keywords}%"
            conditions.append((Product.name.ilike(kw)) | (Product.model.ilike(kw)))
        if query.status is not None:
            conditions.append(Product.status == query.status)

        stmt = select(Product).where(*conditions).order_by(Product.sort_order, Product.update_time.desc())
        count_q = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        offset = (query.pageNum - 1) * query.pageSize
        rows = await self.db.execute(stmt.offset(offset).limit(query.pageSize))
        products = rows.scalars().all()

        vo_list = await self._batch_product_to_vo(products)
        return PageResult(
            records=vo_list, total=total, pageNum=query.pageNum, pageSize=query.pageSize,
        )

    async def get_product_by_id(self, product_id: int) -> ProductVO:
        result = await self.db.execute(
            select(Product).where(Product.id == product_id, Product.is_deleted == 0)
        )
        product = result.scalar_one_or_none()
        if product is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="产品不存在")
        return await self._product_to_vo(product)

    async def create_product(self, form: ProductCreate) -> ProductVO:
        product = Product(
            category_id=form.category_id,
            brand_id=form.brand_id,
            name=form.name,
            model=form.model,
            description=form.description,
            image_urls=form.image_urls,
            status=form.status,
            sort_order=form.sort_order,
        )
        self.db.add(product)
        await self.db.flush()

        if form.specifications:
            name_to_id = await self._upsert_spec_groups(form.category_id, form.specifications)
            for spec in form.specifications:
                group_id = spec.group_id if spec.group_id else name_to_id.get(spec.group_name)
                if group_id:
                    self.db.add(ProductSpecification(
                        product_id=product.id,
                        group_id=group_id,
                        spec_name=spec.spec_name,
                        spec_value=spec.spec_value,
                        spec_unit=spec.spec_unit,
                        sort_order=spec.sort_order,
                    ))
            await self.db.flush()

        logger.info(f"Product created: {form.name} id={product.id}")
        return await self._product_to_vo(product)

    async def update_product(self, form: ProductUpdate) -> ProductVO:
        result = await self.db.execute(
            select(Product).where(Product.id == form.id, Product.is_deleted == 0)
        )
        product = result.scalar_one_or_none()
        if product is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="产品不存在")

        product.category_id = form.category_id
        product.brand_id = form.brand_id
        product.name = form.name
        product.model = form.model
        product.description = form.description
        product.image_urls = form.image_urls
        product.status = form.status
        product.sort_order = form.sort_order
        product.update_time = datetime.now()
        await self.db.flush()

        # 全量替换规格：先删旧再批量插入
        await self.db.execute(
            sa_delete(ProductSpecification).where(ProductSpecification.product_id == form.id)
        )
        if form.specifications:
            name_to_id = await self._upsert_spec_groups(form.category_id, form.specifications)
            for spec in form.specifications:
                group_id = spec.group_id if spec.group_id else name_to_id.get(spec.group_name)
                if group_id:
                    self.db.add(ProductSpecification(
                        product_id=form.id,
                        group_id=group_id,
                        spec_name=spec.spec_name,
                        spec_value=spec.spec_value,
                        spec_unit=spec.spec_unit,
                        sort_order=spec.sort_order,
                    ))
            await self.db.flush()

        logger.info(f"Product updated: {form.name} id={form.id}")
        return await self._product_to_vo(product)

    async def delete_product(self, ids: str) -> int:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
        if not id_list:
            raise BusinessException(code=ResultCode.PARAM_VALID_FAIL, msg="请选择要删除的产品")
        await self.db.execute(
            text("UPDATE products SET is_deleted = 1 WHERE id = ANY(:ids)"),
            {"ids": id_list},
        )
        logger.info(f"Products deleted: {id_list}")
        return len(id_list)

    async def compare_products(self, ids: str) -> ProductCompareVO:
        """对比多个同类产品的规格（2-4 个）。"""
        id_list = [int(x) for x in ids.split(",") if x.strip()]
        if len(id_list) < 2:
            raise BusinessException(code=ResultCode.PARAM_VALID_FAIL, msg="请至少选择 2 个产品进行对比")
        if len(id_list) > 4:
            raise BusinessException(code=ResultCode.PARAM_VALID_FAIL, msg="最多支持 4 个产品同时对比")

        products = []
        for pid in id_list:
            result = await self.db.execute(
                select(Product).where(Product.id == pid, Product.is_deleted == 0)
            )
            p = result.scalar_one_or_none()
            if p is None:
                raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg=f"产品 ID {pid} 不存在")
            products.append(p)

        vo_list = await self._batch_product_to_vo(products)

        # 提取公共分组名（所有产品共有的分组）
        all_groups: set[str] = set()
        product_group_names: list[set[str]] = []
        for vo in vo_list:
            names = {g.group_name for g in vo.groups}
            all_groups.update(names)
            product_group_names.append(names)

        # 取所有产品分组名的交集
        common = sorted(set.intersection(*product_group_names))

        return ProductCompareVO(products=vo_list, common_groups=common)

    async def _upsert_spec_groups(self, category_id: int, specifications: list[SpecItem]) -> dict[str, int]:
        """确保规格分组存在（按 group_name 查找或自动创建）。返回 {group_name: group_id} 映射。"""
        names = {s.group_name for s in specifications if s.group_name}
        if not names:
            return {}

        rows = await self.db.execute(
            select(ProductSpecGroup.id, ProductSpecGroup.name)
            .where(
                ProductSpecGroup.category_id == category_id,
                ProductSpecGroup.is_deleted == 0,
                ProductSpecGroup.name.in_(names),
            )
        )
        name_to_id: dict[str, int] = {row.name: row.id for row in rows}

        for name in names:
            if name not in name_to_id:
                g = ProductSpecGroup(category_id=category_id, name=name, sort_order=0)
                self.db.add(g)
                await self.db.flush()
                name_to_id[name] = g.id
                logger.info(f"Auto-created spec group: {name} for category {category_id}")

        return name_to_id

    # ── VO 组装 ──

    def _category_to_vo(self, c: ProductCategory) -> CategoryVO:
        return CategoryVO(
            id=c.id, name=c.name, slug=c.slug, sort_order=c.sort_order,
            create_time=str(c.create_time) if c.create_time else None,
            update_time=str(c.update_time) if c.update_time else None,
        )

    def _brand_to_vo(self, b: ProductBrand) -> BrandVO:
        return BrandVO(
            id=b.id, name=b.name, logo_url=b.logo_url, sort_order=b.sort_order,
            create_time=str(b.create_time) if b.create_time else None,
            update_time=str(b.update_time) if b.update_time else None,
        )

    def _spec_group_to_vo(self, g: ProductSpecGroup, cat_name: str | None = None) -> SpecGroupVO:
        return SpecGroupVO(
            id=g.id, category_id=g.category_id, category_name=cat_name,
            name=g.name, sort_order=g.sort_order,
            create_time=str(g.create_time) if g.create_time else None,
            update_time=str(g.update_time) if g.update_time else None,
        )

    async def _batch_product_to_vo(self, products: list[Product]) -> list[ProductVO]:
        if not products:
            return []

        # 收集所有产品的规格
        product_ids = [p.id for p in products]
        spec_rows = await self.db.execute(
            select(ProductSpecification).where(
                ProductSpecification.product_id.in_(product_ids),
                ProductSpecification.is_deleted == 0,
            ).order_by(ProductSpecification.group_id, ProductSpecification.sort_order)
        )
        specs = spec_rows.scalars().all()

        # 规格分组名映射
        group_ids = list({s.group_id for s in specs})
        group_map: dict[int, str] = {}
        if group_ids:
            g_rows = await self.db.execute(
                select(ProductSpecGroup.id, ProductSpecGroup.name, ProductSpecGroup.sort_order)
                .where(ProductSpecGroup.id.in_(group_ids), ProductSpecGroup.is_deleted == 0)
            )
            for row in g_rows:
                group_map[row.id] = row.name

        # 批量查分类名 — 不用 lazy load，防止 MissingGreenlet
        cat_ids = list({p.category_id for p in products if p.category_id})
        cat_map: dict[int, str] = {}
        if cat_ids:
            c_rows = await self.db.execute(
                select(ProductCategory.id, ProductCategory.name).where(ProductCategory.id.in_(cat_ids))
            )
            for row in c_rows:
                cat_map[row.id] = row.name

        # 批量查品牌名 — 不用 lazy load
        brand_ids = list({p.brand_id for p in products if p.brand_id})
        brand_map: dict[int, str] = {}
        if brand_ids:
            b_rows = await self.db.execute(
                select(ProductBrand.id, ProductBrand.name).where(ProductBrand.id.in_(brand_ids))
            )
            for row in b_rows:
                brand_map[row.id] = row.name

        # 组装
        grouped_specs: dict[int, dict[str, list[SpecItem]]] = {}
        for s in specs:
            grouped_specs.setdefault(s.product_id, {}).setdefault(
                group_map.get(s.group_id, f"group_{s.group_id}"), []
            ).append(SpecItem(
                id=s.id, group_id=s.group_id,
                group_name=group_map.get(s.group_id),
                spec_name=s.spec_name, spec_value=s.spec_value,
                spec_unit=s.spec_unit, sort_order=s.sort_order,
            ))

        result = []
        for p in products:
            spec_groups_dict = grouped_specs.get(p.id, {})
            groups = [
                SpecGroupDetailVO(group_name=name, items=items)
                for name, items in spec_groups_dict.items()
            ]
            result.append(ProductVO(
                id=p.id,
                category_id=p.category_id,
                category_name=cat_map.get(p.category_id),
                brand_id=p.brand_id,
                brand_name=brand_map.get(p.brand_id),
                name=p.name, model=p.model, description=p.description,
                image_urls=p.image_urls or [],
                status=p.status, sort_order=p.sort_order,
                groups=groups,
                create_time=str(p.create_time) if p.create_time else None,
                update_time=str(p.update_time) if p.update_time else None,
            ))
        return result

    async def _product_to_vo(self, product: Product) -> ProductVO:
        result = await self._batch_product_to_vo([product])
        return result[0]

    async def _get_category_name(self, cat_id: int) -> str | None:
        row = await self.db.execute(select(ProductCategory.name).where(ProductCategory.id == cat_id))
        return row.scalar()
