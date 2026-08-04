"""任务域 — ORM 模型（Task / TaskItem / ReviewRecord）。"""

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, BaseIdMixin, SoftDeleteMixin, TimestampMixin


class AiTcTask(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """AI 任务。"""
    __tablename__ = "ai_tc_tasks"

    task_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="任务类型 core_select/case_review/script_gen"
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ai_tc_projects.id"), nullable=False, comment="项目ID"
    )
    suite_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ai_tc_suites.id"), nullable=False, comment="目标套件ID"
    )
    sample_ids: Mapped[list | None] = mapped_column(JSONB, comment="使用的样本ID列表")
    spec_ids: Mapped[list | None] = mapped_column(JSONB, comment="使用的规范ID列表（核心挑选等）")
    ai_config_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="AI配置ID（不再作为 FK，仅冗余快照）"
    )
    model: Mapped[str | None] = mapped_column(String(64), comment="实际使用的模型名（快照）")
    status: Mapped[int] = mapped_column(
        SmallInteger, default=0, server_default="0",
        comment="状态 0-排队 1-运行中 2-已完成 3-失败 4-已确认"
    )
    total_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", comment="总用例数"
    )
    done_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", comment="已完成数"
    )
    input_tokens: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", comment="输入token数"
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", comment="输出token数"
    )
    error_msg: Mapped[str | None] = mapped_column(Text, comment="错误信息")
    create_by: Mapped[str | None] = mapped_column(String(64), comment="创建人")

    project: Mapped["AiTcProject"] = relationship(lazy="selectin")
    suite: Mapped["AiTcSuite"] = relationship(lazy="selectin")
    items: Mapped[list["AiTcTaskItem"]] = relationship(back_populates="task", lazy="selectin")

    __table_args__ = (
        Index("idx_aitc_task_project", "project_id", "task_type"),
    )


class AiTcTaskItem(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """AI 任务明细（每一条用例的处理结果）。"""
    __tablename__ = "ai_tc_task_items"

    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ai_tc_tasks.id"), nullable=False, comment="任务ID"
    )
    case_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ai_tc_cases.id"), nullable=False, comment="用例ID"
    )
    case_name: Mapped[str] = mapped_column(String(256), nullable=False, comment="用例名称（快照）")
    output: Mapped[dict | None] = mapped_column(JSONB, comment="AI输出结果")
    item_status: Mapped[int] = mapped_column(
        SmallInteger, default=0, server_default="0", comment="明细状态 0-待处理 1-成功 2-失败"
    )
    confirm_status: Mapped[int] = mapped_column(
        SmallInteger, default=0, server_default="0", comment="确认状态 0-待确认 1-采纳 2-忽略 3-编辑采纳"
    )
    final_content: Mapped[str | None] = mapped_column(Text, comment="人工修改后的最终内容")
    reviewed_by: Mapped[str | None] = mapped_column(String(64), comment="审核人")
    review_time: Mapped[str | None] = mapped_column(String(32), comment="审核时间")

    task: Mapped["AiTcTask"] = relationship(back_populates="items", lazy="selectin")
    case: Mapped["AiTcCase"] = relationship(lazy="selectin")


class AiTcReviewRecord(Base, BaseIdMixin, TimestampMixin):
    """审核记录（审计日志）。"""
    __tablename__ = "ai_tc_review_records"

    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ai_tc_tasks.id"), nullable=False, comment="任务ID"
    )
    task_item_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ai_tc_task_items.id"), nullable=False, comment="任务明细ID"
    )
    case_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ai_tc_cases.id"), nullable=False, comment="用例ID"
    )
    review_action: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="操作 accept/ignore/edit_accept/field_accept"
    )
    field_name: Mapped[str | None] = mapped_column(
        String(64), comment="审核字段名（name/summary/preconditions/steps/script等）"
    )
    before_value: Mapped[str | None] = mapped_column(Text, comment="修改前的值")
    after_value: Mapped[str | None] = mapped_column(Text, comment="修改后的值")
    reviewer: Mapped[str | None] = mapped_column(String(64), comment="审核人")
    reviewer_ip: Mapped[str | None] = mapped_column(String(64), comment="审核人IP")
    review_time: Mapped[str | None] = mapped_column(String(32), comment="审核时间")
    memo: Mapped[str | None] = mapped_column(String(512), comment="备注")

    __table_args__ = (
        Index("idx_aitc_review_task", "task_id"),
        Index("idx_aitc_review_item", "task_item_id"),
        Index("idx_aitc_review_case", "case_id"),
    )
