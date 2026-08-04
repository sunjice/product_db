"""add chat tables (chat_sessions, chat_messages, chat_drafts, ai_usage_logs)

Revision ID: b70bb6265a9e
Revises: a7d8e9f1c2b3
Create Date: 2026-08-01 15:26:39.556538
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b70bb6265a9e'
down_revision: Union[str, None] = 'a7d8e9f1c2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ai_usage_logs ──
    op.create_table('ai_usage_logs',
        sa.Column('module', sa.String(length=50), server_default='chat', nullable=False, comment='来源模块 chat/task_engine'),
        sa.Column('session_id', sa.BigInteger(), nullable=True, comment='会话ID（chat 模块）'),
        sa.Column('task_id', sa.BigInteger(), nullable=True, comment='任务ID（task_engine 模块）'),
        sa.Column('model', sa.String(length=100), nullable=False, comment='模型名称'),
        sa.Column('prompt_tokens', sa.Integer(), server_default='0', nullable=False, comment='输入 token'),
        sa.Column('completion_tokens', sa.Integer(), server_default='0', nullable=False, comment='输出 token'),
        sa.Column('total_tokens', sa.Integer(), server_default='0', nullable=False, comment='总 token'),
        sa.Column('duration_ms', sa.Integer(), server_default='0', nullable=False, comment='耗时(毫秒)'),
        sa.Column('created_at', sa.String(length=32), nullable=False, comment='创建时间'),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_usage_module', 'ai_usage_logs', ['module', 'created_at'], unique=False)
    op.create_index('idx_usage_session', 'ai_usage_logs', ['session_id'], unique=False)

    # ── chat_sessions ──
    op.create_table('chat_sessions',
        sa.Column('title', sa.String(length=200), server_default='新对话', nullable=False, comment='会话标题'),
        sa.Column('domain', sa.String(length=50), server_default='case', nullable=False, comment='会话域 case/bug/analytics'),
        sa.Column('context_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='页面上下文快照 {project_id, suite_id, ...}'),
        sa.Column('message_count', sa.Integer(), server_default='0', nullable=False, comment='消息数量'),
        sa.Column('is_pinned', sa.SmallInteger(), server_default='0', nullable=False, comment='是否置顶 0-否 1-是'),
        sa.Column('user_id', sa.BigInteger(), nullable=True, comment='所属用户ID（单用户模式可为空）'),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
        sa.Column('is_deleted', sa.SmallInteger(), server_default='0', nullable=False, comment='逻辑删除 0-未删除 1-已删除'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_session_domain', 'chat_sessions', ['domain'], unique=False)
    op.create_index('idx_chat_session_user', 'chat_sessions', ['user_id', 'is_deleted'], unique=False)

    # ── chat_messages ──
    op.create_table('chat_messages',
        sa.Column('session_id', sa.BigInteger(), nullable=False, comment='所属会话ID'),
        sa.Column('role', sa.String(length=20), nullable=False, comment='角色 user/assistant/system'),
        sa.Column('msg_type', sa.String(length=30), server_default='text', nullable=False, comment='消息类型 text/action_card/task_card/draft_card/clarify_card/help_card'),
        sa.Column('content', sa.Text(), nullable=False, comment='消息正文（Markdown）'),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='附加数据 {skill_name, tool_calls, tokens, execution_time_ms, ...}'),
        sa.Column('draft_id', sa.BigInteger(), nullable=True, comment='关联的 Draft ID（如有产出）'),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_msg_session', 'chat_messages', ['session_id', 'id'], unique=False)

    # ── chat_drafts ──
    op.create_table('chat_drafts',
        sa.Column('session_id', sa.BigInteger(), nullable=False, comment='所属会话ID'),
        sa.Column('message_id', sa.BigInteger(), nullable=False, comment='关联消息ID'),
        sa.Column('draft_type', sa.String(length=30), nullable=False, comment='草稿类型 core_select/case_review/script_gen/field_complete/steps_complete/case_design'),
        sa.Column('title', sa.String(length=200), server_default='', nullable=False, comment='草稿标题'),
        sa.Column('content_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='草稿内容'),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False, comment='状态 pending/confirmed/applied/discarded'),
        sa.Column('confirmed_by', sa.String(length=64), nullable=True, comment='确认人'),
        sa.Column('confirmed_at', sa.String(length=32), nullable=True, comment='确认时间'),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_draft_msg', 'chat_drafts', ['message_id'], unique=False)
    op.create_index('idx_chat_draft_session', 'chat_drafts', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_chat_draft_session', table_name='chat_drafts')
    op.drop_index('idx_chat_draft_msg', table_name='chat_drafts')
    op.drop_table('chat_drafts')

    op.drop_index('idx_chat_msg_session', table_name='chat_messages')
    op.drop_table('chat_messages')

    op.drop_index('idx_chat_session_user', table_name='chat_sessions')
    op.drop_index('idx_chat_session_domain', table_name='chat_sessions')
    op.drop_table('chat_sessions')

    op.drop_index('idx_usage_session', table_name='ai_usage_logs')
    op.drop_index('idx_usage_module', table_name='ai_usage_logs')
    op.drop_table('ai_usage_logs')
