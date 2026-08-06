"""AI LLM 调用日志 — 查询/导出服务。"""

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.pagination import PageQuery, PageResult
from app.ai.llm_log.models import AiLlmLog


class LlmLogService:
    """LLM 调用日志查询与导出服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 分页查询 ──

    async def query_logs(
        self,
        page: PageQuery,
        *,
        session_id: int | None = None,
        trace_id: str | None = None,
        action: str | None = None,
        status: str | None = None,
        module: str | None = None,
    ) -> PageResult:
        """分页查询 LLM 调用日志。"""
        conditions = []
        if session_id is not None:
            conditions.append(AiLlmLog.session_id == session_id)
        if trace_id:
            conditions.append(AiLlmLog.trace_id == trace_id)
        if action:
            conditions.append(AiLlmLog.action == action)
        if status:
            conditions.append(AiLlmLog.status == status)
        if module:
            conditions.append(AiLlmLog.module == module)

        stmt = select(AiLlmLog).where(*conditions).order_by(desc(AiLlmLog.create_time))
        count_q = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        offset = (page.pageNum - 1) * page.pageSize
        rows = await self.db.execute(stmt.offset(offset).limit(page.pageSize))
        records = [self._to_dict(row, compact=True) for row in rows.scalars().all()]

        return PageResult(records=records, total=total, pageNum=page.pageNum, pageSize=page.pageSize)

    # ── 导出（不分页，全部符合条件的数据）──

    async def export_logs(
        self,
        *,
        session_id: int | None = None,
        trace_id: str | None = None,
        action: str | None = None,
        status: str | None = None,
        module: str | None = None,
    ) -> list[dict]:
        """导出全部符合条件的 LLM 调用日志记录。"""
        stmt = select(AiLlmLog)

        if session_id is not None:
            stmt = stmt.where(AiLlmLog.session_id == session_id)
        if trace_id:
            stmt = stmt.where(AiLlmLog.trace_id == trace_id)
        if action:
            stmt = stmt.where(AiLlmLog.action == action)
        if status:
            stmt = stmt.where(AiLlmLog.status == status)
        if module:
            stmt = stmt.where(AiLlmLog.module == module)

        stmt = stmt.order_by(desc(AiLlmLog.create_time))

        # 限制最多导出 5000 条，避免内存爆炸
        stmt = stmt.limit(5000)

        result = await self.db.execute(stmt)
        return [self._to_dict(row, compact=False) for row in result.scalars().all()]

    # ── 工具 ──

    @staticmethod
    def _to_dict(log: AiLlmLog, compact: bool = True) -> dict:
        """ORM 对象 → 字典。compact=True 时列表不返回大字段。"""
        base = {
            "id": log.id,
            "trace_id": log.trace_id,
            "span_seq": log.span_seq,
            "attempt": log.attempt,
            "module": log.module,
            "action": log.action,
            "session_id": log.session_id,
            "task_id": log.task_id,
            "message_id": log.message_id,
            "model": log.model,
            "status": log.status,
            "error_msg": log.error_msg,
            "prompt_tokens": log.prompt_tokens,
            "completion_tokens": log.completion_tokens,
            "duration_ms": log.duration_ms,
            "create_time": log.create_time.isoformat() if log.create_time else None,
        }
        if not compact:
            base["messages"] = log.messages
            base["response_raw"] = log.response_raw
            base["response_json"] = log.response_json
        return base

    # ── 单条详情 ──

    async def get_log(self, log_id: int) -> dict | None:
        """获取单条日志详情，返回 dict。"""
        result = await self.db.execute(
            select(AiLlmLog).where(AiLlmLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        if log is None:
            return None
        return self._to_dict(log, compact=False)

    # ── 有日志的会话列表 ──

    async def get_log_sessions(self, limit: int = 50) -> list[dict]:
        """获取最近有 AI 调用的会话列表（给前端下拉框用）。"""
        rows = await self.db.execute(
            select(
                AiLlmLog.session_id,
                func.max(AiLlmLog.create_time).label("last_time"),
                func.count(AiLlmLog.id).label("log_count"),
            )
            .where(AiLlmLog.session_id.isnot(None))
            .group_by(AiLlmLog.session_id)
            .order_by(desc("last_time"))
            .limit(limit)
        )
        return [
            {
                "session_id": r.session_id,
                "last_time": r.last_time.isoformat() if r.last_time else None,
                "log_count": r.log_count,
            }
            for r in rows
        ]
