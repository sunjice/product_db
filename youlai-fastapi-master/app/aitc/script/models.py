"""脚本域 — ORM 模型（Script）。"""

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, BaseIdMixin, SoftDeleteMixin, TimestampMixin


class AiTcScript(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """测试脚本库。"""
    __tablename__ = "ai_tc_scripts"

    case_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ai_tc_cases.id"), nullable=False, comment="用例ID"
    )
    language: Mapped[str] = mapped_column(
        String(32), default="python", server_default="'python'", comment="脚本语言"
    )
    framework: Mapped[str] = mapped_column(
        String(32), default="pytest", server_default="'pytest'", comment="测试框架"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="脚本内容")
    source: Mapped[int] = mapped_column(
        SmallInteger, default=1, server_default="1", comment="来源 1-AI生成 2-人工录入"
    )
    task_item_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ai_tc_task_items.id"), comment="来源任务明细ID"
    )
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", comment="版本号"
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, default=1, server_default="1", comment="状态 1-草稿 2-已入库"
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(64), comment="审核人")

    case: Mapped["AiTcCase"] = relationship(back_populates="scripts", lazy="selectin")

    __table_args__ = (
        Index("idx_aitc_script_case", "case_id", "is_deleted"),
    )
