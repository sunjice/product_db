"""用例域 — 数据库查询工具集。

为 Skill 提供用例数据的读取和操作能力。
与 AI 调用无关，全部是纯 Python 产物。
"""

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.aitc.models import AiTcCase, AiTcProject, AiTcSuite
from app.ai.agent.skills.bus import ToolBus, ToolDef, tool_bus


# ═══════════════ 工具函数 ═══════════════

async def _get_project(db: AsyncSession, project_id: int) -> AiTcProject | None:
    result = await db.execute(
        select(AiTcProject).where(
            AiTcProject.id == project_id,
            AiTcProject.is_deleted == 0,
        )
    )
    return result.scalar_one_or_none()


async def _get_cases_by_suite(
    db: AsyncSession,
    suite_id: int,
    limit: int = 200,
) -> list[AiTcCase]:
    """获取套件下的所有用例。"""
    result = await db.execute(
        select(AiTcCase)
        .where(
            AiTcCase.suite_id == suite_id,
            AiTcCase.is_deleted == 0,
        )
        .limit(limit)
    )
    return list(result.scalars().all())


async def _get_cases_by_project(
    db: AsyncSession,
    project_id: int,
    limit: int = 200,
) -> list[AiTcCase]:
    """获取项目下的所有用例。"""
    result = await db.execute(
        select(AiTcCase)
        .where(
            AiTcCase.project_id == project_id,
            AiTcCase.is_deleted == 0,
        )
        .limit(limit)
    )
    return list(result.scalars().all())


async def _get_case_detail(db: AsyncSession, case_id: int) -> AiTcCase | None:
    """获取用例详情。"""
    result = await db.execute(
        select(AiTcCase).where(
            AiTcCase.id == case_id,
            AiTcCase.is_deleted == 0,
        )
    )
    return result.scalar_one_or_none()


async def _get_suite_tree(db: AsyncSession, project_id: int) -> list[AiTcSuite]:
    """获取项目套件树。"""
    result = await db.execute(
        select(AiTcSuite).where(
            AiTcSuite.project_id == project_id,
            AiTcSuite.is_deleted == 0,
        )
    )
    return list(result.scalars().all())


async def _count_cases(db: AsyncSession, project_id: int) -> int:
    """统计项目下的用例总数。"""
    result = await db.execute(
        select(func.count(AiTcCase.id)).where(
            AiTcCase.project_id == project_id,
            AiTcCase.is_deleted == 0,
        )
    )
    return result.scalar() or 0


async def _search_cases(
    db: AsyncSession,
    project_id: int,
    keywords: str,
    limit: int = 50,
) -> list[AiTcCase]:
    """按关键字搜索用例。"""
    pattern = f"%{keywords}%"
    result = await db.execute(
        select(AiTcCase)
        .where(
            AiTcCase.project_id == project_id,
            AiTcCase.is_deleted == 0,
            AiTcCase.name.ilike(pattern),
        )
        .limit(limit)
    )
    return list(result.scalars().all())


async def _count_cases_in_suite(db: AsyncSession, suite_id: int) -> int:
    """统计指定套件（含子套件）下的用例数。"""
    # 获取套件信息（用于 tree_path 前缀匹配）
    suite = await db.get(AiTcSuite, suite_id)
    if suite is None or suite.is_deleted:
        return 0

    prefix = f"{suite.tree_path}{suite_id},"
    suite_rows = await db.execute(
        select(AiTcSuite.id).where(
            AiTcSuite.tree_path.like(f"{prefix}%"),
            AiTcSuite.is_deleted == 0,
        )
    )
    all_suite_ids = [suite_id] + [r[0] for r in suite_rows]

    result = await db.execute(
        select(func.count(AiTcCase.id)).where(
            AiTcCase.suite_id.in_(all_suite_ids),
            AiTcCase.is_deleted == 0,
        )
    )
    return result.scalar() or 0


async def _get_project_name(db: AsyncSession, project_id: int) -> str:
    """获取项目名称。"""
    project = await _get_project(db, project_id)
    return project.name if project else ""


async def _get_suite_name(db: AsyncSession, suite_id: int) -> str:
    """获取套件名称。"""
    suite = await db.get(AiTcSuite, suite_id)
    return suite.name if suite else ""


async def resolve_scope(
    db: AsyncSession,
    suite_id: int,
    selected_case_ids: list[int] | None = None,
    current_case_id: int | None = None,
) -> list[int] | None:
    """防御校验 + 优先级裁决：返回最终要处理的用例 ID 列表。

    优先级：current_case_id > selected_case_ids > None（处理整个模块）。

    同时过滤掉已被删除、不属于当前模块（含子模块）的无效 ID，
    防御用例被删除、覆盖导入等极端情况，也防止未来新加入口绕过前端规则。

    Returns:
        list[int]: 单个用例（current_case_id 有效时）或选中的多个用例（selected_case_ids 有效时）。
        None: 两者都为空或都无效，应由调用方退化为处理整个模块。
    """
    # 1. 获取当前模块及其所有子模块的 suite_id 列表
    suite = await db.get(AiTcSuite, suite_id)
    if suite is None or suite.is_deleted:
        return None

    prefix = f"{suite.tree_path}{suite_id},"
    suite_rows = await db.execute(
        select(AiTcSuite.id).where(
            AiTcSuite.tree_path.like(f"{prefix}%"),
            AiTcSuite.is_deleted == 0,
        )
    )
    all_suite_ids = {suite_id} | {r[0] for r in suite_rows}

    # 2. 收集所有需要校验的用例 ID
    candidate_ids = set()
    if selected_case_ids:
        candidate_ids.update(int(c) for c in selected_case_ids)
    if current_case_id is not None:
        candidate_ids.add(int(current_case_id))

    if not candidate_ids:
        return None

    # 3. 批量查询：只保留存在、未删除且属于目标模块的用例
    result = await db.execute(
        select(AiTcCase.id).where(
            AiTcCase.id.in_(list(candidate_ids)),
            AiTcCase.suite_id.in_(list(all_suite_ids)),
            AiTcCase.is_deleted == 0,
        )
    )
    valid_ids = {r[0] for r in result}

    # 4. 检测被过滤掉的 ID，记录日志
    invalid_ids = candidate_ids - valid_ids
    if invalid_ids:
        logger.warning(
            f"[resolve_scope] suite_id={suite_id} 过滤掉无效用例 ID: {sorted(invalid_ids)}"
            f"（可能已被删除或不属于当前模块）"
        )

    # 5. 优先级裁决：current_case_id > selected_case_ids
    if current_case_id is not None and int(current_case_id) in valid_ids:
        return [int(current_case_id)]

    if selected_case_ids:
        valid_selected = [int(c) for c in selected_case_ids if int(c) in valid_ids]
        if valid_selected:
            return valid_selected

    return None


# ═══════════════ 公开的 ToolBus 工具（供跨域调用） ═══════════════


async def case_detail_for_bug(case_id: int, db: AsyncSession) -> dict | None:
    """供 bug 域跨域调用 — 根据用例 ID 获取基本信息。"""
    case = await _get_case_detail(db, case_id)
    if case is None:
        return None
    return {
        "id": case.id,
        "name": case.name,
        "suite_id": case.suite_id,
        "project_id": case.project_id,
        "summary": case.summary,
        "is_core": case.is_core,
    }


async def cases_by_project_for_bug(project_id: int, db: AsyncSession) -> list[dict]:
    """供 bug 域跨域调用 — 获取项目下核心用例列表。"""
    cases = await _get_cases_by_project(db, project_id, limit=500)
    return [
        {"id": c.id, "name": c.name, "suite_id": c.suite_id, "is_core": c.is_core}
        for c in cases
        if c.is_core == 1
    ]


def register_case_tools():
    """注册用例域公开工具到 ToolBus。"""
    tool_bus.register(ToolDef(
        name="case.case_detail",
        domain="case",
        tool_name="case_detail",
        func=case_detail_for_bug,
        description="根据用例 ID 获取用例基本信息（名称/所属模块/测试思想）",
        public=True,
    ))
    tool_bus.register(ToolDef(
        name="case.cases_by_project",
        domain="case",
        tool_name="cases_by_project",
        func=cases_by_project_for_bug,
        description="获取项目中所有核心用例列表",
        public=True,
    ))
