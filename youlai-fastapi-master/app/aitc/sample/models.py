"""样本域 — ORM 模型（Sample）。"""

from sqlalchemy import BigInteger, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, BaseIdMixin, SoftDeleteMixin, TimestampMixin


class AiTcSample(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """样本库（用例样本 / 脚本样本）。"""
    __tablename__ = "ai_tc_samples"

    project_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ai_tc_projects.id"), nullable=True, comment="项目ID，NULL 为通用"
    )
    sample_type: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="类型 case-用例样本 script-脚本样本"
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="样本名称")
    language: Mapped[str | None] = mapped_column(String(32), comment="语言（脚本样本用）")
    framework: Mapped[str | None] = mapped_column(String(32), default="pytest", comment="框架")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="样本内容")
    description: Mapped[str | None] = mapped_column(String(512), comment="样本描述")
    status: Mapped[int] = mapped_column(
        SmallInteger, default=1, server_default="1", comment="状态 0-停用 1-启用"
    )

    project: Mapped["AiTcProject | None"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("idx_aitc_sample_type", "sample_type", "project_id"),
    )
