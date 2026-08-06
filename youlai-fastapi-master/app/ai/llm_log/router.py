"""AI LLM 调用日志 — API 路由。"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_perm
from app.auth.schemas import SysUserDetails
from app.response import Result, ResultCode
from app.exceptions import BusinessException
from app.pagination import PageQuery
from app.ai.llm_log.service import LlmLogService

router = APIRouter(prefix="/api/v1/llm-logs", tags=["AI日志"])


# ── 分页列表 ──

@router.get("", summary="AI 调用日志分页列表")
async def list_llm_logs(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    session_id: int | None = Query(None, description="会话ID"),
    trace_id: str | None = Query(None, description="调用链ID"),
    action: str | None = Query(None, description="动作名称"),
    status: str | None = Query(None, description="状态 success/error"),
    module: str | None = Query(None, description="来源模块"),
    db: AsyncSession = Depends(get_db),
):
    """分页查询 LLM 调用日志，支持按会话/动作/状态筛选。"""
    service = LlmLogService(db)
    page = PageQuery(pageNum=pageNum, pageSize=pageSize)
    result = await service.query_logs(
        page,
        session_id=session_id,
        trace_id=trace_id,
        action=action,
        status=status,
        module=module,
    )
    return Result(data=result)


# ── 有日志的会话（必须在 /{log_id} 之前，防止路径冲突）──

@router.get("/sessions/list", summary="有 LLM 调用的会话列表")
async def list_log_sessions(
    db: AsyncSession = Depends(get_db),
):
    """返回最近有 AI 调用的会话列表，给页面下拉框用。"""
    service = LlmLogService(db)
    data = await service.get_log_sessions()
    return Result(data=data)


# ── 导出（必须在 /{log_id} 之前，防止路径冲突）──

@router.get("/export", summary="导出 LLM 调用日志")
async def export_llm_logs(
    format: str = Query(default="json", description="导出格式 json/txt"),
    session_id: int | None = Query(None, description="会话ID"),
    trace_id: str | None = Query(None, description="调用链ID"),
    action: str | None = Query(None, description="动作名称"),
    status: str | None = Query(None, description="状态"),
    module: str | None = Query(None, description="来源模块"),
    db: AsyncSession = Depends(get_db),
):
    """导出全部符合条件的 LLM 调用日志为 JSON 或 TXT 文件下载。"""
    service = LlmLogService(db)
    logs = await service.export_logs(
        session_id=session_id,
        trace_id=trace_id,
        action=action,
        status=status,
        module=module,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "txt":
        lines = []
        for i, rec in enumerate(logs, 1):
            lines.append(f"{'='*80}")
            lines.append(f"[{i}] ID={rec['id']} | session={rec['session_id']} | "
                         f"action={rec['action']} | model={rec['model']} | "
                         f"status={rec['status']} | tokens={rec['prompt_tokens']}+{rec['completion_tokens']} | "
                         f"time={rec['create_time']}")
            lines.append(f"{'='*80}")
            if rec.get("messages"):
                lines.append("--- MESSAGES ---")
                lines.append(json.dumps(rec["messages"], ensure_ascii=False, indent=2))
            if rec.get("response_raw"):
                lines.append("--- RESPONSE ---")
                lines.append(rec["response_raw"])
            if rec.get("error_msg"):
                lines.append("--- ERROR ---")
                lines.append(rec["error_msg"])
            lines.append("")
        content = "\n".join(lines)
        filename = f"llm_logs_{timestamp}.txt"
        media_type = "text/plain; charset=utf-8"
    else:
        content = json.dumps(logs, ensure_ascii=False, indent=2, default=str)
        filename = f"llm_logs_{timestamp}.json"
        media_type = "application/json; charset=utf-8"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ── 单条详情（动态路由放最后）──

@router.get("/{log_id}", summary="AI 调用日志详情")
async def get_llm_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取单条 LLM 日志完整内容（含 messages / response）。"""
    service = LlmLogService(db)
    log = await service.get_log(log_id)
    if log is None:
        raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="日志记录不存在")
    return Result(data=log)
