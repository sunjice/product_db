"""LLM 调用日志写入器 — 使用独立 DB 会话写入 ai_llm_logs 表，不污染业务事务。"""

import time
import uuid
from typing import Any

from loguru import logger as loguru_logger

from app.database import AsyncSessionLocal
from app.ai.llm_log.models import AiLlmLog


class LlmLogWriter:
    """LLM 调用日志写入器 — 每次调用使用独立 DB 会话，异常不影响主流程。"""

    @staticmethod
    async def write(
        *,
        trace_id: str = "",
        span_seq: int = 0,
        attempt: int = 0,
        module: str = "chat",
        action: str = "",
        session_id: int | None = None,
        task_id: int | None = None,
        message_id: int | None = None,
        model: str = "",
        status: str = "success",
        error_msg: str | None = None,
        messages: list[dict] | None = None,
        response_raw: str | None = None,
        response_json: dict | list | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        duration_ms: int = 0,
    ) -> int | None:
        """写入一条 LLM 调用日志，返回记录 ID。异常时仅 log 不抛出。"""
        try:
            async with AsyncSessionLocal() as db:
                log = AiLlmLog(
                    trace_id=trace_id,
                    span_seq=span_seq,
                    attempt=attempt,
                    module=module,
                    action=action,
                    session_id=session_id,
                    task_id=task_id,
                    message_id=message_id,
                    model=model,
                    status=status,
                    error_msg=error_msg,
                    messages=messages,
                    response_raw=response_raw,
                    response_json=response_json,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    duration_ms=duration_ms,
                )
                db.add(log)
                await db.commit()
                await db.refresh(log)
                return log.id
        except Exception as e:
            loguru_logger.warning(f"Failed to write LLM log: {e}")
            return None


def make_trace_id(prefix: str, *parts: Any) -> str:
    """生成唯一的 trace_id，格式: {prefix}_{parts}_{uuid8}。"""
    parts_str = "_".join(str(p) for p in parts if p is not None)
    short_uid = uuid.uuid4().hex[:8]
    return f"{prefix}_{parts_str}_{short_uid}"
