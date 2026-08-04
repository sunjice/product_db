"""脚本域 — 业务逻辑层。"""

from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessException
from app.pagination import PageResult
from app.response import ResultCode
from app.aitc.script.models import AiTcScript
from app.aitc.case.models import AiTcCase
from app.aitc.script.schemas import (
    ScriptQuery, ScriptUpdate, ScriptVO,
)
from app.aitc.constants import ScriptStatus


class ScriptService:
    """脚本域全部业务逻辑。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ═══════════════ 脚本库 CRUD ═══════════════

    async def get_script_page(self, query: ScriptQuery) -> PageResult:
        conditions = [AiTcScript.is_deleted == 0]
        if query.caseId is not None:
            conditions.append(AiTcScript.case_id == query.caseId)
        if query.status is not None:
            conditions.append(AiTcScript.status == query.status)
        if query.source is not None:
            conditions.append(AiTcScript.source == query.source)
        if query.projectId is not None:
            case_subq = select(AiTcCase.id).where(AiTcCase.project_id == query.projectId, AiTcCase.is_deleted == 0).subquery()
            conditions.append(AiTcScript.case_id.in_(select(case_subq)))

        stmt = select(AiTcScript).where(*conditions).order_by(AiTcScript.update_time.desc())
        count_q = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        offset = (query.pageNum - 1) * query.pageSize
        rows = await self.db.execute(stmt.offset(offset).limit(query.pageSize))
        items = rows.scalars().all()

        # 批量查用例名
        cids = list({s.case_id for s in items})
        cname_map: dict[int, str] = {}
        if cids:
            crows = await self.db.execute(
                select(AiTcCase.id, AiTcCase.name).where(AiTcCase.id.in_(cids))
            )
            cname_map = {r.id: r.name for r in crows}

        return PageResult(
            records=[self._script_to_vo(s, cname_map.get(s.case_id)) for s in items],
            total=total, pageNum=query.pageNum, pageSize=query.pageSize,
        )

    async def update_script(self, script_id: int, form: ScriptUpdate) -> ScriptVO:
        result = await self.db.execute(
            select(AiTcScript).where(AiTcScript.id == script_id, AiTcScript.is_deleted == 0)
        )
        s = result.scalar_one_or_none()
        if s is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="脚本不存在")
        s.content = form.content
        if form.version:
            s.version = form.version
        s.update_time = datetime.now()
        await self.db.flush()
        return self._script_to_vo(s)

    async def publish_script(self, script_id: int) -> ScriptVO:
        """脚本入库（状态改为已入库）。"""
        result = await self.db.execute(
            select(AiTcScript).where(AiTcScript.id == script_id, AiTcScript.is_deleted == 0)
        )
        s = result.scalar_one_or_none()
        if s is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="脚本不存在")
        s.status = ScriptStatus.PUBLISHED
        s.update_time = datetime.now()
        await self.db.flush()
        return self._script_to_vo(s)

    async def export_script(self, script_id: int) -> tuple[str, str]:
        """导出脚本为文件，返回 (content, filename)。"""
        result = await self.db.execute(
            select(AiTcScript).where(AiTcScript.id == script_id, AiTcScript.is_deleted == 0)
        )
        s = result.scalar_one_or_none()
        if s is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="脚本不存在")

        case = await self.db.get(AiTcCase, s.case_id)
        case_name = (case.name if case else "test").replace("/", "_").replace("\\", "_").replace(" ", "_")

        ext_map = {"python": ".py", "javascript": ".js", "java": ".java", "go": ".go"}
        ext = ext_map.get(s.language or "python", ".txt")
        filename = f"{case_name}{ext}"

        return s.content, filename

    async def delete_scripts(self, ids: str) -> int:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
        if not id_list:
            raise BusinessException(code=ResultCode.PARAM_VALID_FAIL, msg="请选择脚本")
        await self.db.execute(
            text("UPDATE ai_tc_scripts SET is_deleted = 1 WHERE id = ANY(:ids)"),
            {"ids": id_list},
        )
        return len(id_list)

    async def create_script_record(
        self, case_id: int, language: str, framework: str,
        content: str, source: int, task_item_id: int,
    ) -> AiTcScript:
        script = AiTcScript(
            case_id=case_id,
            language=language,
            framework=framework,
            content=content,
            source=source,
            task_item_id=task_item_id,
            version=1,
            status=ScriptStatus.DRAFT,
        )
        self.db.add(script)
        return script

    # ═══════════════ VO 组装 ═══════════════

    def _script_to_vo(self, s: AiTcScript, case_name: str = "") -> ScriptVO:
        return ScriptVO(
            id=s.id, case_id=s.case_id, case_name=case_name,
            language=s.language, framework=s.framework, content=s.content,
            source=s.source, task_item_id=s.task_item_id,
            version=s.version, status=s.status, reviewed_by=s.reviewed_by,
            create_time=str(s.create_time) if s.create_time else None,
            update_time=str(s.update_time) if s.update_time else None,
        )
