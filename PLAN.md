## 产品概述
在现有的 youlai-fastapi + vue3-element-admin 项目基础上，新增一个"产品数据库"模块，供测试部存储和管理网卡、路由器产品的关键参数及核心测试数据，并能够在前端展示产品详细的情况，以及像汽车之家一样，可以对比两个同类产品的参数。

## 核心功能
- **产品管理**：支持网卡、路由器产品的增删改查，按分类/关键字/品牌筛选
- **规格管理**：每个产品关联多个规格分组（如基础参数、性能指标、接口规格），分组内包含多条规格项（名称+值+单位），支持按分类预设分组模板
- **产品详情**：以分组卡片形式展示产品的完整规格参数
- **产品对比**：选择 2 个同类产品，按规格分组对齐展示参数差异，差异项高亮标记（类似汽车网站对比功能）
- **分类管理**：支持产品分类（网卡、路由器等）的 CRUD，以及每个分类下的规格分组模板维护
- **品牌管理**：支持品牌的增删改查，品牌作为独立实体管理而非自由文本字段

## 技术栈
- 后端：Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) + asyncpg + PostgreSQL 16
- 前端：Vue 3.5 + TypeScript + Element Plus 2.14 + Pinia + Vue Router 5 (hash)
- 数据库：PostgreSQL（本地容器，端口15432），JSONB 字段存储图片列表

## 实现方案

### 数据库设计（5张表）
采用"公共属性 + 分组规格"模型，具备品类扩展能力，基础数据（分类/品牌/规格分组）均为独立表，支持前端管理页面增删改查：

| 表 | 说明 | 关键字段 |
|---|---|---|
| product_categories | 产品分类 | id, name, slug, sort_order |
| product_brands | 品牌 | id, name, logo_url, sort_order |
| products | 产品主表 | id, category_id(FK), brand_id(FK), name, model, description, image_urls(JSONB), status, sort_order |
| product_spec_groups | 规格分组 | id, category_id(FK), name, sort_order |
| product_specifications | 规格明细 | id, product_id(FK), group_id(FK), spec_name, spec_value, spec_unit, sort_order |

继承项目已有的 `Base + BaseIdMixin + TimestampMixin + SoftDeleteMixin` mixin，products.category_id 定义外键。关键索引：`(product_id, group_id, sort_order)` 用于详情查询，`(group_id, spec_name)` 用于对比对齐。所有查询需过滤 `is_deleted == 0`（软删除）。

### 后端模块结构
位置 `app/system/product/`，参照 user 模块的四文件结构：models.py / schemas.py / service.py / router.py。

路由前缀 `/api/v1/products`、`/api/v1/categories`、`/api/v1/brands`、`/api/v1/specgroups`，在 `app/main.py` 的 `create_app()` 中延迟导入并挂载。

### 模型注册与路由挂载
新增模块后需修改 3 处才能生效：
1. **`app/registry.py`**：添加 `from app.system.product import models as _product_models  # noqa: F401`，使 Alembic 能发现新表
2. **`app/main.py`**：在 `create_app()` 中添加：
   ```python
   from app.system.product.router import router as product_router
   app.include_router(product_router)
   ```
3. **数据库迁移**：运行 `alembic revision --autogenerate -m "add product tables"` 生成迁移脚本，再 `alembic upgrade head` 执行建表

核心 API：
- `GET /api/v1/products` — 分页列表，按 categoryId/keywords/brandId 筛选
- `GET /api/v1/products/{id}` — 详情，JOIN 查询规格并组装为嵌套分组结构
- `POST /api/v1/products` — 创建（products 行 + 批量 product_specifications 行）
- `PUT /api/v1/products/{id}` — 更新（先删旧 specs 再批量插入，全量替换策略）
- `DELETE /api/v1/products/{id}` — 软删除（设置 is_deleted=1）或物理删除（级联删 specs）
- `GET /api/v1/products/compare?ids=1,2` — 对比，同时查 2 个产品的完整信息，提取公共分组名
- `GET/POST/PUT/DELETE /api/v1/categories` — 分类 CRUD
- `GET/POST/PUT/DELETE /api/v1/brands` — 品牌 CRUD
- `GET/POST/PUT/DELETE /api/v1/specgroups` — 规格分组 CRUD

Pydantic schema 模型：`ProductQuery`（继承 `app.pagination.PageQuery`，扩展 categoryId/keywords/brandId 筛选字段）、`ProductCreate/ProductUpdate`（含嵌套 `specifications: list[SpecItem]`）、`ProductVO`（含嵌套 `groups: list[SpecGroupVO]`、`SpecGroupVO`（含 `items: list[SpecItemVO]`））、`ProductCompareVO`（`products: list[ProductVO]` + `commonGroups: list[str]`）。service 层使用项目已有的 `paginate_query()` 执行分页。前端 `ProductQueryParams` 继承 `BaseQueryParams` 扩展筛选字段，响应类型复用 `PageResult<T>`。

### 权限与国际化
**后端权限码**（`app/system/product/constants.py`）：
- `product:list` / `product:create` / `product:update` / `product:delete` / `product:compare`
- `category:list` / `category:create` / `category:update` / `category:delete`
- `brand:list` / `brand:create` / `brand:update` / `brand:delete`
- `specgroup:list` / `specgroup:create` / `specgroup:update` / `specgroup:delete`

router 接口需添加权限依赖，示例：
```python
@router.get("", dependencies=[Depends(require_perm("product:list"))])
```

**前端权限控制**：路由 meta 配置 `perms` 字段，操作按钮使用 `v-hasPerm` 指令控制显示（如 `<el-button v-hasPerm="'product:delete'">删除</el-button>`）。

**国际化**：规划 `product.*` 前缀的 i18n key（如 `product.list.title`、`product.detail.specGroup`、`product.compare.title`），中英文语言文件在 `src/lang/` 下维护。

### 前端模块结构
位置 `src/views/product/` + `src/api/product/`。

**产品页面（3个）**：
1. **产品列表页** `views/product/index.vue`：搜索区（分类下拉+品牌下拉+关键字）+ el-table + 分页，使用 `usePageTable` composable，行操作含详情/编辑/删除按钮。分类和品牌下拉选项通过 `GET /api/v1/categories` 和 `GET /api/v1/brands` 动态加载
2. **产品详情页** `views/product/detail.vue`：路由参数 `:id`，基本信息卡片 + 按分组渲染规格（每组一个 el-card 内嵌 el-descriptions 或表格行），底部操作按钮含"加入对比"
3. **产品对比页** `views/product/compare.vue`：路由 query `?ids=1,2`，两产品基本信息左右并列，下方对比表格（行按分组，列：规格名称 | 产品A | 产品B），缺失格显示"—"，差异格用 warning 色边框高亮

**基础数据管理页面（3个）**：每个页面为标准的 el-table 列表页，支持搜索、分页、新增/编辑弹窗、单行/批量删除
4. **分类管理页** `views/product/category.vue`：管理 product_categories，支持名称/slug/排序编辑
5. **品牌管理页** `views/product/brand.vue`：管理 product_brands，支持名称/logo/排序编辑
6. **规格分组管理页** `views/product/specgroup.vue`：管理 product_spec_groups，关联分类，支持名称/排序编辑

**弹窗组件（1个）**：`views/product/components/ProductFormDialog.vue`，el-dialog 内嵌 tabs 表单（基础信息 + 规格编辑），规格编辑区在新建时根据所选分类自动加载规格分组模板。品牌和分类下拉从对应 API 动态获取。

路由在开发阶段于 `src/router/index.ts` 的 constantRoutes 中临时新增 `/product` 父路由及六个子路由（产品列表/详情/对比 + 分类/品牌/规格分组管理）；正式上线后改为通过后端菜单管理配置动态路由，由权限守卫自动加载。

API 层：`src/api/product/types.ts` 定义完整 TypeScript 接口（含 Category、Brand、SpecGroup 实体类型），`src/api/product/index.ts` 封装所有 axios 请求方法。

### 数据库迁移与种子数据
建表使用 Alembic 自动迁移：`alembic revision --autogenerate -m "add product tables"` 生成迁移脚本，`alembic upgrade head` 执行建表。种子数据使用独立 Python 脚本，预置数据：
- **分类**："网卡""路由器" 2 条
- **品牌**："Intel""Mellanox""Broadcom""TP-Link""ASUS""Xiaomi" 等若干条
- **规格分组模板**：网卡（基础参数、性能指标、硬件规格、兼容性），路由器（基础参数、端口规格、无线规格、性能指标、功能特性），每组 3-5 条规格模板

### 实施顺序
1. 后端 models.py（继承 `Base + BaseIdMixin + TimestampMixin + SoftDeleteMixin`，5 张表含 product_brands）
2. 后端 schemas.py + service.py + router.py（`ProductQuery` 继承 `PageQuery`，含分类/品牌/规格分组完整 CRUD）
3. `app/registry.py` 注册模型 + `app/main.py` 注册路由
4. Alembic 自动生成迁移脚本并执行建表（`alembic revision` + `alembic upgrade head`）
5. 种子数据脚本（预置分类 + 品牌 + 分组模板）
6. 前端 API 层（types.ts + index.ts，复用 `BaseQueryParams`/`PageResult`，含 Category/Brand/SpecGroup 类型）
7. 前端产品列表页（使用 `usePageTable` composable，分类和品牌下拉动态加载，按钮加 `v-hasPerm` 指令）
8. 前端产品详情页
9. 前端产品对比页
10. 前端分类/品牌/规格分组管理页（各含列表+弹窗增删改）
11. 前端表单弹窗组件（品牌和分类下拉动态加载，图片上传复用 `src/components/Upload/`）
12. 前端路由配置（constantRoutes 临时添加，含 3 个产品页 + 3 个管理页，meta 配置权限和 i18n key）
13. 权限指令 + i18n 语言文件配置

## 设计风格
延续现有项目风格，采用 Element Plus 组件库，配合 UnoCSS 原子化 CSS 和项目已有的 SCSS 变量体系（`--el-color-primary`、`--el-bg-color-overlay`、`--card-border`、`--card-radius`、`--card-shadow`）。整体风格简洁专业，明暗主题自动适配。

## 页面设计

### 产品列表页
- 顶部搜索区：el-card 包裹，el-form inline 横向排列（分类下拉 + 品牌下拉 + 关键字输入框 + 搜索/重置按钮）。空状态显示 el-empty 引导
- 表格区域：el-table 展示（名称、型号、品牌、分类、状态 Tag、创建时间、操作列）。操作列含"详情""编辑""删除"三个 el-button（text 类型），并有一个"产品对比"入口按钮，点击后弹出 el-dialog 选择 2 个同类产品
- 新增按钮：表格上方工具栏左侧，点击弹出 ProductFormDialog 弹窗

### 产品详情页
- 返回按钮 + 产品标题在顶部
- 基本信息卡片：el-descriptions 3 列布局（名称、型号、品牌、分类、状态、创建/更新时间），图片以 el-image 列表展示
- 规格区域：按分组名展示，每组一个 el-card（标题为分组名），内部用 2 列 el-descriptions 或紧凑表格行渲染每条规格（名称：值 单位）

### 产品对比页
- 顶部：返回按钮 + 标题"产品对比"
- 基本信息区：el-row 左右两列，每列一张产品小卡（名称、图片、型号、品牌）
- 差异对比表格：el-table，首列固定为"规格名称"，后续列按分组渲染（可合并分组表头行），产品A列和产品B列
- 差异高亮：值不同的单元格加上右/下边框 warning 色（`border-bottom: 2px solid var(--el-color-warning)`），视觉上醒目
- 规格不存在时显示"—"（灰色文字）

### 产品表单弹窗
- el-dialog 宽度约 700px，标题区分"新增产品"/"编辑产品"
- 基础信息区：el-form（分类下拉、名称、型号、品牌、描述 textarea、图片上传、状态 switch）。图片上传复用项目已有的 `app/tool/file/` 后端上传接口，前端使用 `src/components/Upload/` 组件，上传成功后将返回的 URL 数组写入 `products.image_urls`（JSONB）字段
- 规格编辑区：分类切换时自动加载对应分组的规格模板；每组可动态增删行（el-table + 行内 input），支持拖拽排序
- 底部：取消 + 保存按钮，保存按钮带 loading

## Agent Extensions
### SubAgent
- **code-explorer**
  - Purpose：在后端 `app/system/` 和前端 `src/` 下进行批量文件创建前的目录结构确认
  - Expected outcome：确认目标文件位置无冲突，获取现有模块的完整代码模板作为参考

## TODOS

- [ ] 创建 product/models.py（继承 Base + BaseIdMixin + TimestampMixin + SoftDeleteMixin，5 张表含 product_brands）
- [ ] 创建 product/schemas.py（ProductQuery 继承 PageQuery，定义含 Category/Brand/SpecGroup 的完整 Pydantic 模型）
- [ ] 创建 product/service.py（使用 paginate_query 分页，查询过滤 is_deleted == 0，含分类/品牌/规格分组/产品全部 CRUD）
- [ ] 创建 product/router.py（定义权限码 require_perm，路径 /api/v1/products|categories|brands|specgroups）
- [ ] 在 app/registry.py 注册模型 + app/main.py 注册路由
- [ ] Alembic 自动生成迁移脚本并执行建表
- [ ] 编写种子数据脚本，预置分类 + 品牌 + 规格分组模板
- [ ] 创建前端 API 层（复用 BaseQueryParams/PageResult，封装 products/categories/brands/specgroups 全部请求方法）
- [ ] 创建产品列表页（分类和品牌下拉动态加载，使用 usePageTable composable，v-hasPerm 指令控制按钮）
- [ ] 创建产品详情页（按规格分组卡片展示，品牌信息关联展示，图片复用 Upload 组件）
- [ ] 创建产品对比页（规格对齐对比表格，差异高亮标记）
- [ ] 创建分类管理页（列表+弹窗 CRUD）
- [ ] 创建品牌管理页（列表+弹窗 CRUD，含 logo 上传）
- [ ] 创建规格分组管理页（列表+弹窗 CRUD，关联分类下拉）
- [ ] 创建 ProductFormDialog（品牌和分类下拉动态加载，图片上传复用 src/components/Upload/）
- [ ] 前端路由配置（constantRoutes 临时添加 3 个产品页 + 3 个管理页，meta 配置 perms/i18n key）
- [ ] 权限指令 + i18n 语言文件配置