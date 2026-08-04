"""规范域 — ORM 模型（Spec）。"""

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, BaseIdMixin, SoftDeleteMixin, TimestampMixin


class AiTcSpec(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """AI 规范管理（通用/模块专用规范、常见问题）。"""
    __tablename__ = "ai_tc_specs"

    project_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ai_tc_projects.id"), nullable=True, comment="项目ID，NULL 为全局通用"
    )
    suite_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ai_tc_suites.id"), nullable=True, comment="模块ID，模块专用规范时使用"
    )
    task_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="任务类型 core_select/case_review/script_gen"
    )
    spec_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="规范类型 general/module_specific/common_issues"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="规范内容（Markdown）")
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", comment="排序号"
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, default=1, server_default="1", comment="状态 0-停用 1-启用"
    )

    project: Mapped["AiTcProject | None"] = relationship(lazy="selectin")
    suite: Mapped["AiTcSuite | None"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("idx_aitc_spec_task", "task_type", "spec_type"),
        Index("idx_aitc_spec_project", "project_id", "task_type"),
        Index("idx_aitc_spec_suite", "suite_id"),
    )
