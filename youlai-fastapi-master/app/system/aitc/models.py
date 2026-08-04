"""测试部 AI 助手 — ORM 模型（10 张表）。"""

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, BaseIdMixin, SoftDeleteMixin, TimestampMixin


class AiTcProject(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """测试项目（用例集 / 产品）。"""
    __tablename__ = "ai_tc_projects"

    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="项目名称")
    prefix: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="项目标识")
    description: Mapped[str | None] = mapped_column(Text, comment="项目描述")
    last_sync_time: Mapped[str | None] = mapped_column(String(32), comment="最后导入时间")

    suites: Mapped[list["AiTcSuite"]] = relationship(
        back_populates="project", lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("prefix", name="uq_aitc_project_prefix"),
    )


class AiTcSuite(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """测试套件（模块树节点）。"""
    __tablename__ = "ai_tc_suites"

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ai_tc_projects.id"), nullable=False, comment="项目ID"
    )
    parent_id: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0", comment="父套件ID，0 为根"
    )
    tree_path: Mapped[str] = mapped_column(String(512), default="", server_default="", comment="祖先路径如 0,1,5")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="套件名称")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", comment="排序")

    project: Mapped["AiTcProject"] = relationship(back_populates="suites", lazy="selectin")
    cases: Mapped[list["AiTcCase"]] = relationship(back_populates="suite", lazy="selectin")

    __table_args__ = (
        Index("idx_aitc_suite_project", "project_id", "is_deleted"),
        Index("idx_aitc_suite_parent", "parent_id"),
        Index("idx_aitc_suite_tree", "tree_path"),
    )


class AiTcCase(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """测试用例。"""
    __tablename__ = "ai_tc_cases"

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ai_tc_projects.id"), nullable=False, comment="项目ID"
    )
    suite_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ai_tc_suites.id"), nullable=False, comment="所属套件ID"
    )
    external_id: Mapped[str | None] = mapped_column(String(64), comment="Excel用例ID，项目内唯一")
    name: Mapped[str] = mapped_column(String(256), nullable=False, comment="用例名称")
    summary: Mapped[str | None] = mapped_column(Text, comment="测试思想")
    preconditions: Mapped[str | None] = mapped_column(Text, comment="前置条件")
    topo: Mapped[str | None] = mapped_column(String(512), comment="测试Topo")
    test_data: Mapped[str | None] = mapped_column(Text, comment="测试数据")
    steps: Mapped[list | None] = mapped_column(JSONB, comment="测试步骤 [{action, expected, step_no}]")
    importance: Mapped[int] = mapped_column(
        SmallInteger, default=2, server_default="2", comment="级别 1-低 2-中 3-高"
    )
    is_core: Mapped[int] = mapped_column(
        SmallInteger, default=0, server_default="0", comment="是否核心用例 0-否 1-是"
    )
    core_reason: Mapped[str | None] = mapped_column(String(512), comment="标记为核心的原因")
    core_source: Mapped[int | None] = mapped_column(
        SmallInteger, comment="核心来源 1-AI挑选 2-人工标记"
    )
    is_sample: Mapped[int] = mapped_column(
        SmallInteger, default=0, server_default="0", comment="是否样本用例 0-否 1-是"
    )
    review_status: Mapped[int] = mapped_column(
        SmallInteger, default=0, server_default="0", comment="审核状态 0-未审核 1-已审核"
    )
    script_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", comment="关联脚本数量（冗余计数）"
    )

    suite: Mapped["AiTcSuite"] = relationship(back_populates="cases", lazy="selectin")
    project: Mapped["AiTcProject"] = relationship(lazy="selectin")
    scripts: Mapped[list["AiTcScript"]] = relationship(back_populates="case", lazy="selectin")

    __table_args__ = (
        Index("idx_aitc_case_suite", "suite_id", "is_deleted"),
        Index("idx_aitc_case_project_core", "project_id", "is_core"),
        Index("idx_aitc_case_review", "project_id", "review_status"),
        UniqueConstraint("project_id", "external_id", name="uq_aitc_case_extid"),
    )


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


class AiTcAiConfig(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """AI 服务配置。"""
    __tablename__ = "ai_tc_ai_configs"

    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="配置名称")
    provider: Mapped[str] = mapped_column(
        String(32), default="openai_compat", server_default="'openai_compat'", comment="提供方 deepseek/openai_compat"
    )
    api_base: Mapped[str] = mapped_column(String(256), nullable=False, comment="API 地址")
    api_key: Mapped[str] = mapped_column(String(512), nullable=False, comment="API 密钥")
    model: Mapped[str] = mapped_column(String(64), nullable=False, comment="模型名")
    temperature: Mapped[float] = mapped_column(
        default=0.3, server_default="0.3", comment="采样温度"
    )
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096, server_default="4096", comment="最大输出token")
    scenes: Mapped[list | None] = mapped_column(JSONB, comment="适用场景列表如 ['core_select','case_review']")
    is_default: Mapped[int] = mapped_column(
        SmallInteger, default=0, server_default="0", comment="全局兜底默认"
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, default=1, server_default="1", comment="状态 0-停用 1-启用"
    )
    remark: Mapped[str | None] = mapped_column(String(512), comment="备注")


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
        BigInteger, ForeignKey("ai_tc_ai_configs.id"), comment="AI配置ID"
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
