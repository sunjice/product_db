"""AI LLM 调用日志 — ORM 模型。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BaseIdMixin


class AiLlmLog(Base, BaseIdMixin):
    """每次 LLM 调用的完整请求/响应记录。"""
    __tablename__ = "ai_llm_logs"

    # ── 调用链追踪 ──
    trace_id: Mapped[str] = mapped_column(
        String(128), default="", server_default="''", comment="调用链 ID，同一用户动作的多次 LLM 调用共享"
    )
    span_seq: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", comment="调用链内序号，从 0 开始"
    )
    attempt: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", comment="重试次数"
    )

    # ── 模块/动作 ──
    module: Mapped[str] = mapped_column(
        String(50), default="chat", server_default="'chat'", comment="来源模块 chat/task_engine"
    )
    action: Mapped[str] = mapped_column(
        String(80), default="", server_default="''",
        comment="动作名称 intent_recognize/case_review/script_gen 等"
    )

    # ── 关联业务 ──
    session_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="关联会话ID（chat 模块）"
    )
    task_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="关联任务ID（task_engine 模块）"
    )
    message_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="关联消息ID（chat 模块）"
    )

    # ── 模型与状态 ──
    model: Mapped[str] = mapped_column(String(100), default="", server_default="''", comment="模型名称")
    status: Mapped[str] = mapped_column(
        String(20), default="success", server_default="'success'",
        comment="调用状态 success/error/timeout"
    )
    error_msg: Mapped[str | None] = mapped_column(Text, comment="错误信息")

    # ── 请求/响应（核心排查数据）──
    messages: Mapped[dict | None] = mapped_column(
        JSONB, comment="请求 messages 完整 JSON（系统提示词 + 历史消息 + 用户输入）"
    )
    response_raw: Mapped[str | None] = mapped_column(Text, comment="LLM 原始返回文本")
    response_json: Mapped[dict | None] = mapped_column(
        JSONB, comment="LLM 结构化返回（JSON parse 后）"
    )

    # ── 用量统计 ──
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", comment="输入 token"
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", comment="输出 token"
    )
    duration_ms: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", comment="耗时(毫秒)"
    )

    # ── 时间 ──
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now(), comment="创建时间"
    )

    __table_args__ = (
        Index("idx_llm_log_session", "session_id", "create_time"),
        Index("idx_llm_log_trace", "trace_id"),
        Index("idx_llm_log_status", "status", "create_time"),
        Index("idx_llm_log_action", "action"),
    )
