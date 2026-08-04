"""add product tables

Revision ID: 6c5cde3e4fbe
Revises:
Create Date: 2026-07-30 21:39:44.800672
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '6c5cde3e4fbe'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('product_brands',
    sa.Column('name', sa.String(length=64), nullable=False, comment='品牌名称'),
    sa.Column('logo_url', sa.String(length=255), nullable=True, comment='品牌Logo URL'),
    sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False, comment='排序'),
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
    sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
    sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
    sa.Column('is_deleted', sa.SmallInteger(), server_default='0', nullable=False, comment='逻辑删除 0-未删除 1-已删除'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('product_categories',
    sa.Column('name', sa.String(length=64), nullable=False, comment='分类名称'),
    sa.Column('slug', sa.String(length=64), nullable=False, comment='分类标识'),
    sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False, comment='排序'),
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
    sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
    sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
    sa.Column('is_deleted', sa.SmallInteger(), server_default='0', nullable=False, comment='逻辑删除 0-未删除 1-已删除'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_table('product_spec_groups',
    sa.Column('category_id', sa.BigInteger(), nullable=False, comment='分类ID'),
    sa.Column('name', sa.String(length=64), nullable=False, comment='分组名称'),
    sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False, comment='排序'),
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
    sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
    sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
    sa.Column('is_deleted', sa.SmallInteger(), server_default='0', nullable=False, comment='逻辑删除 0-未删除 1-已删除'),
    sa.ForeignKeyConstraint(['category_id'], ['product_categories.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('products',
    sa.Column('category_id', sa.BigInteger(), nullable=False, comment='分类ID'),
    sa.Column('brand_id', sa.BigInteger(), nullable=False, comment='品牌ID'),
    sa.Column('name', sa.String(length=128), nullable=False, comment='产品名称'),
    sa.Column('model', sa.String(length=64), nullable=True, comment='产品型号'),
    sa.Column('description', sa.Text(), nullable=True, comment='产品描述'),
    sa.Column('image_urls', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='图片URL列表'),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=False, comment='状态 1-上架 0-下架'),
    sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False, comment='排序'),
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
    sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
    sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
    sa.Column('is_deleted', sa.SmallInteger(), server_default='0', nullable=False, comment='逻辑删除 0-未删除 1-已删除'),
    sa.ForeignKeyConstraint(['brand_id'], ['product_brands.id'], ),
    sa.ForeignKeyConstraint(['category_id'], ['product_categories.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('product_specifications',
    sa.Column('product_id', sa.BigInteger(), nullable=False, comment='产品ID'),
    sa.Column('group_id', sa.BigInteger(), nullable=False, comment='规格分组ID'),
    sa.Column('spec_name', sa.String(length=64), nullable=False, comment='规格名称'),
    sa.Column('spec_value', sa.String(length=255), nullable=True, comment='规格值'),
    sa.Column('spec_unit', sa.String(length=32), nullable=True, comment='规格单位'),
    sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False, comment='排序'),
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
    sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
    sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
    sa.Column('is_deleted', sa.SmallInteger(), server_default='0', nullable=False, comment='逻辑删除 0-未删除 1-已删除'),
    sa.ForeignKeyConstraint(['group_id'], ['product_spec_groups.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_group_spec_name', 'product_specifications', ['group_id', 'spec_name'], unique=False)
    op.create_index('idx_product_group_order', 'product_specifications', ['product_id', 'group_id', 'sort_order'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_product_group_order', table_name='product_specifications')
    op.drop_index('idx_group_spec_name', table_name='product_specifications')
    op.drop_table('product_specifications')
    op.drop_table('products')
    op.drop_table('product_spec_groups')
    op.drop_table('product_categories')
    op.drop_table('product_brands')
