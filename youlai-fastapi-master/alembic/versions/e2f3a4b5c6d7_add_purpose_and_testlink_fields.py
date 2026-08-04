"""add purpose and testlink fields to ai_tc_cases, ai_tc_projects, ai_tc_suites

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-08-04 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. ai_tc_projects: testlink_project_id ──
    op.add_column(
        'ai_tc_projects',
        sa.Column(
            'testlink_project_id',
            sa.BigInteger(),
            nullable=True,
            comment='TestLink testproject id',
        ),
    )

    # ── 2. ai_tc_suites: testlink_suite_id ──
    op.add_column(
        'ai_tc_suites',
        sa.Column(
            'testlink_suite_id',
            sa.BigInteger(),
            nullable=True,
            comment='TestLink testsuite id',
        ),
    )

    # ── 3. ai_tc_cases: purpose + 12 个 TestLink 同步字段 ──
    op.add_column(
        'ai_tc_cases',
        sa.Column(
            'purpose',
            sa.String(256),
            nullable=True,
            comment='测试目的 / 中文用例名称（如 SSID长度验证）',
        ),
    )
    op.add_column(
        'ai_tc_cases',
        sa.Column(
            'testlink_tc_id',
            sa.BigInteger(),
            nullable=True,
            comment='TestLink 内部 testcase_id',
        ),
    )
    op.add_column(
        'ai_tc_cases',
        sa.Column(
            'testlink_version_id',
            sa.BigInteger(),
            nullable=True,
            comment='TestLink tcversion_id（每次远端编辑会变）',
        ),
    )
    op.add_column(
        'ai_tc_cases',
        sa.Column(
            'sync_status',
            sa.SmallInteger(),
            nullable=False,
            server_default='0',
            comment='同步状态 0-未关联 1-已同步 2-待反写 3-远端有更新 4-冲突 5-反写失败 6-远端已删除',
        ),
    )
    op.add_column(
        'ai_tc_cases',
        sa.Column(
            'synced_version',
            sa.Integer(),
            nullable=True,
            comment='上次同步时的 TestLink version',
        ),
    )
    op.add_column(
        'ai_tc_cases',
        sa.Column(
            'synced_hash',
            sa.String(64),
            nullable=True,
            comment='上次同步内容的 SHA256（本地脏检测基准）',
        ),
    )
    op.add_column(
        'ai_tc_cases',
        sa.Column(
            'synced_snapshot',
            postgresql.JSONB(),
            nullable=True,
            comment='上次同步时的字段快照（三方合并用）',
        ),
    )
    op.add_column(
        'ai_tc_cases',
        sa.Column(
            'last_sync_at',
            sa.DateTime(),
            nullable=True,
            comment='上次同步时间',
        ),
    )
    op.add_column(
        'ai_tc_cases',
        sa.Column(
            'last_push_at',
            sa.DateTime(),
            nullable=True,
            comment='上次反写时间',
        ),
    )
    op.add_column(
        'ai_tc_cases',
        sa.Column(
            'testlink_modified_at',
            sa.DateTime(),
            nullable=True,
            comment='TestLink 端 modification_ts',
        ),
    )
    op.add_column(
        'ai_tc_cases',
        sa.Column(
            'testlink_modifier',
            sa.String(128),
            nullable=True,
            comment='TestLink 端最后修改人',
        ),
    )
    op.add_column(
        'ai_tc_cases',
        sa.Column(
            'auto_sync',
            sa.SmallInteger(),
            nullable=False,
            server_default='1',
            comment='修改后是否自动反写 0-否 1-是',
        ),
    )
    op.add_column(
        'ai_tc_cases',
        sa.Column(
            'sync_error',
            sa.Text(),
            nullable=True,
            comment='最近一次反写失败原因',
        ),
    )

    # ── 4. 索引 ──
    op.create_index(
        'idx_aitc_case_tl_tc',
        'ai_tc_cases',
        ['testlink_tc_id'],
    )
    op.create_index(
        'idx_aitc_case_sync_status',
        'ai_tc_cases',
        ['project_id', 'sync_status'],
    )

    # ── 5. 数据迁移：现有数据 purpose 用 name 回填 ──
    op.execute(sa.text("""
        UPDATE ai_tc_cases
        SET purpose = name
        WHERE purpose IS NULL AND name IS NOT NULL
          AND is_deleted = 0
    """))


def downgrade() -> None:
    # ── 索引 ──
    op.drop_index('idx_aitc_case_sync_status', table_name='ai_tc_cases')
    op.drop_index('idx_aitc_case_tl_tc', table_name='ai_tc_cases')

    # ── ai_tc_cases 列 ──
    op.drop_column('ai_tc_cases', 'sync_error')
    op.drop_column('ai_tc_cases', 'auto_sync')
    op.drop_column('ai_tc_cases', 'testlink_modifier')
    op.drop_column('ai_tc_cases', 'testlink_modified_at')
    op.drop_column('ai_tc_cases', 'last_push_at')
    op.drop_column('ai_tc_cases', 'last_sync_at')
    op.drop_column('ai_tc_cases', 'synced_snapshot')
    op.drop_column('ai_tc_cases', 'synced_hash')
    op.drop_column('ai_tc_cases', 'synced_version')
    op.drop_column('ai_tc_cases', 'sync_status')
    op.drop_column('ai_tc_cases', 'testlink_version_id')
    op.drop_column('ai_tc_cases', 'testlink_tc_id')
    op.drop_column('ai_tc_cases', 'purpose')

    # ── ai_tc_suites 列 ──
    op.drop_column('ai_tc_suites', 'testlink_suite_id')

    # ── ai_tc_projects 列 ──
    op.drop_column('ai_tc_projects', 'testlink_project_id')
