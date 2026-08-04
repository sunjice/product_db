"""样本域 — 业务逻辑层。"""

from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.exceptions import BusinessException
from app.pagination import PageResult
from app.response import ResultCode
from app.aitc.sample.models import AiTcSample
from app.aitc.case.models import AiTcProject
from app.aitc.sample.schemas import (
    SampleCreate, SampleQuery, SampleUpdate, SampleVO,
)


class SampleService:
    """样本域全部业务逻辑。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ═══════════════ 样本库 CRUD ═══════════════

    async def get_sample_page(self, query: SampleQuery) -> PageResult:
        conditions = [AiTcSample.is_deleted == 0]
        if query.projectId is not None:
            conditions.append(
                (AiTcSample.project_id == query.projectId) | (AiTcSample.project_id.is_(None))
            )
        if query.sampleType:
            conditions.append(AiTcSample.sample_type == query.sampleType)
        if query.keywords:
            kw = f"%{query.keywords}%"
            conditions.append(AiTcSample.name.ilike(kw))

        stmt = select(AiTcSample).where(*conditions).order_by(AiTcSample.project_id.nulls_last(), AiTcSample.id)
        count_q = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        offset = (query.pageNum - 1) * query.pageSize
        rows = await self.db.execute(stmt.offset(offset).limit(query.pageSize))
        items = rows.scalars().all()

        pids = [it.project_id for it in items if it.project_id]
        pname_map: dict[int, str] = {}
        if pids:
            prows = await self.db.execute(
                select(AiTcProject.id, AiTcProject.name).where(AiTcProject.id.in_(pids))
            )
            pname_map = {r.id: r.name for r in prows}

        return PageResult(
            records=[self._sample_to_vo(s, pname_map.get(s.project_id)) for s in items],
            total=total, pageNum=query.pageNum, pageSize=query.pageSize,
        )

    async def create_sample(self, form: SampleCreate) -> SampleVO:
        s = AiTcSample(**form.model_dump())
        self.db.add(s)
        await self.db.flush()
        logger.info(f"Sample created: {form.name} id={s.id}")
        return self._sample_to_vo(s)

    async def update_sample(self, form: SampleUpdate) -> SampleVO:
        result = await self.db.execute(
            select(AiTcSample).where(AiTcSample.id == form.id, AiTcSample.is_deleted == 0)
        )
        s = result.scalar_one_or_none()
        if s is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="样本不存在")
        s.project_id = form.project_id
        s.sample_type = form.sample_type
        s.name = form.name
        s.language = form.language
        s.framework = form.framework
        s.content = form.content
        s.description = form.description
        s.status = form.status
        s.update_time = datetime.now()
        await self.db.flush()
        return self._sample_to_vo(s)

    async def delete_sample(self, ids: str) -> int:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
        if not id_list:
            raise BusinessException(code=ResultCode.PARAM_VALID_FAIL, msg="请选择样本")
        await self.db.execute(
            text("UPDATE ai_tc_samples SET is_deleted = 1 WHERE id = ANY(:ids)"),
            {"ids": id_list},
        )
        return len(id_list)

    async def load_samples_text(self, sample_ids: list[int]) -> str:
        """根据 ID 加载样本内容并拼接为文本。"""
        rows = await self.db.execute(
            select(AiTcSample).where(
                AiTcSample.id.in_(sample_ids),
                AiTcSample.is_deleted == 0,
            )
        )
        parts = []
        for s in rows.scalars().all():
            parts.append(f"【样本：{s.name}】\n{s.content}")
        return "\n\n".join(parts)

    # ═══════════════ VO 组装 ═══════════════

    def _sample_to_vo(self, s: AiTcSample, project_name: str | None = None) -> SampleVO:
        return SampleVO(
            id=s.id, project_id=s.project_id, project_name=project_name,
            sample_type=s.sample_type, name=s.name, language=s.language,
            framework=s.framework, content=s.content,
            description=s.description, status=s.status,
            create_time=str(s.create_time) if s.create_time else None,
            update_time=str(s.update_time) if s.update_time else None,
        )
