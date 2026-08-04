"""产品数据库 ORM 模型。"""

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, BaseIdMixin, SoftDeleteMixin, TimestampMixin


class ProductCategory(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """产品分类。"""
    __tablename__ = "product_categories"

    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="分类名称")
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="分类标识")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", comment="排序")

    spec_groups: Mapped[list["ProductSpecGroup"]] = relationship(
        back_populates="category", lazy="selectin",
    )


class ProductBrand(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """产品品牌。"""
    __tablename__ = "product_brands"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="品牌名称")
    logo_url: Mapped[str | None] = mapped_column(String(255), comment="品牌Logo URL")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", comment="排序")


class Product(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """产品主表。"""
    __tablename__ = "products"

    category_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product_categories.id"), nullable=False, comment="分类ID"
    )
    brand_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product_brands.id"), nullable=False, comment="品牌ID"
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="产品名称")
    model: Mapped[str | None] = mapped_column(String(64), comment="产品型号")
    description: Mapped[str | None] = mapped_column(Text, comment="产品描述")
    image_urls: Mapped[list | None] = mapped_column(JSONB, comment="图片URL列表")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1", comment="状态 1-上架 0-下架")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", comment="排序")

    category: Mapped["ProductCategory"] = relationship(lazy="selectin")
    brand: Mapped["ProductBrand"] = relationship(lazy="selectin")
    specifications: Mapped[list["ProductSpecification"]] = relationship(
        back_populates="product", lazy="selectin", cascade="all, delete-orphan",
    )


class ProductSpecGroup(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """规格分组。"""
    __tablename__ = "product_spec_groups"

    category_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product_categories.id"), nullable=False, comment="分类ID"
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="分组名称")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", comment="排序")

    category: Mapped["ProductCategory"] = relationship(back_populates="spec_groups")


class ProductSpecification(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """规格明细。"""
    __tablename__ = "product_specifications"

    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, comment="产品ID"
    )
    group_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product_spec_groups.id"), nullable=False, comment="规格分组ID"
    )
    spec_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="规格名称")
    spec_value: Mapped[str | None] = mapped_column(String(255), comment="规格值")
    spec_unit: Mapped[str | None] = mapped_column(String(32), comment="规格单位")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", comment="排序")

    product: Mapped["Product"] = relationship(back_populates="specifications")
    group: Mapped["ProductSpecGroup"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("idx_product_group_order", "product_id", "group_id", "sort_order"),
        Index("idx_group_spec_name", "group_id", "spec_name"),
    )
