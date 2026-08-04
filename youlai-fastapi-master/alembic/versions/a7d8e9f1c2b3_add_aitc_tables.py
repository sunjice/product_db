"""add ai_tc tables — 测试部AI助手 9张表

Revision ID: a7d8e9f1c2b3
Revises: 6c5cde3e4fbe
Create Date: 2026-07-31 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a7d8e9f1c2b3'
down_revision: Union[str, None] = '6c5cde3e4fbe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 测试项目
    op.create_table('ai_tc_projects',
        sa.Column('name', sa.String(length=128), nullable=False, comment='项目名称'),
        sa.Column('prefix', sa.String(length=64), nullable=False, comment='项目标识'),
        sa.Column('description', sa.Text(), nullable=True, comment='项目描述'),
        sa.Column('last_sync_time', sa.String(length=32), nullable=True, comment='最后导入时间'),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
        sa.Column('is_deleted', sa.SmallInteger(), server_default='0', nullable=False, comment='逻辑删除 0-未删除 1-已删除'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('prefix', name='uq_aitc_project_prefix'),
    )

    # 2. 测试套件
    op.create_table('ai_tc_suites',
        sa.Column('project_id', sa.BigInteger(), nullable=False, comment='项目ID'),
        sa.Column('parent_id', sa.BigInteger(), server_default='0', nullable=False, comment='父套件ID，0为根'),
        sa.Column('tree_path', sa.String(length=512), server_default='', nullable=False, comment='祖先路径'),
        sa.Column('name', sa.String(length=128), nullable=False, comment='套件名称'),
        sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False, comment='排序'),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
        sa.Column('is_deleted', sa.SmallInteger(), server_default='0', nullable=False, comment='逻辑删除 0-未删除 1-已删除'),
        sa.ForeignKeyConstraint(['project_id'], ['ai_tc_projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_aitc_suite_project', 'ai_tc_suites', ['project_id', 'is_deleted'])
    op.create_index('idx_aitc_suite_parent', 'ai_tc_suites', ['parent_id'])
    op.create_index('idx_aitc_suite_tree', 'ai_tc_suites', ['tree_path'])

    # 3. 测试用例
    op.create_table('ai_tc_cases',
        sa.Column('project_id', sa.BigInteger(), nullable=False, comment='项目ID'),
        sa.Column('suite_id', sa.BigInteger(), nullable=False, comment='所属套件ID'),
        sa.Column('external_id', sa.String(length=64), nullable=True, comment='Excel用例ID，项目内唯一'),
        sa.Column('name', sa.String(length=256), nullable=False, comment='用例名称'),
        sa.Column('summary', sa.Text(), nullable=True, comment='测试思想'),
        sa.Column('preconditions', sa.Text(), nullable=True, comment='前置条件'),
        sa.Column('topo', sa.String(length=512), nullable=True, comment='测试Topo'),
        sa.Column('test_data', sa.Text(), nullable=True, comment='测试数据'),
        sa.Column('steps', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='测试步骤 [{action, expected, step_no}]'),
        sa.Column('importance', sa.SmallInteger(), server_default='2', nullable=False, comment='级别 1-低 2-中 3-高'),
        sa.Column('is_core', sa.SmallInteger(), server_default='0', nullable=False, comment='是否核心用例 0-否 1-是'),
        sa.Column('core_reason', sa.String(length=512), nullable=True, comment='标记为核心的原因'),
        sa.Column('core_source', sa.SmallInteger(), nullable=True, comment='核心来源 1-AI挑选 2-人工标记'),
        sa.Column('review_status', sa.SmallInteger(), server_default='0', nullable=False, comment='审核状态 0-未审核 1-已审核'),
        sa.Column('script_count', sa.Integer(), server_default='0', nullable=False, comment='关联脚本数量'),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
        sa.Column('is_deleted', sa.SmallInteger(), server_default='0', nullable=False, comment='逻辑删除 0-未删除 1-已删除'),
        sa.ForeignKeyConstraint(['project_id'], ['ai_tc_projects.id'], ),
        sa.ForeignKeyConstraint(['suite_id'], ['ai_tc_suites.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'external_id', name='uq_aitc_case_extid'),
    )
    op.create_index('idx_aitc_case_suite', 'ai_tc_cases', ['suite_id', 'is_deleted'])
    op.create_index('idx_aitc_case_project_core', 'ai_tc_cases', ['project_id', 'is_core'])
    op.create_index('idx_aitc_case_review', 'ai_tc_cases', ['project_id', 'review_status'])

    # 4. 提示词模板
    op.create_table('ai_tc_prompts',
        sa.Column('project_id', sa.BigInteger(), nullable=True, comment='项目ID，NULL为通用模板'),
        sa.Column('scene', sa.String(length=32), nullable=False, comment='场景 core_select/case_review/script_gen'),
        sa.Column('name', sa.String(length=128), nullable=False, comment='模板名称'),
        sa.Column('content', sa.Text(), nullable=False, comment='提示词内容'),
        sa.Column('is_default', sa.SmallInteger(), server_default='0', nullable=False, comment='是否默认'),
        sa.Column('status', sa.SmallInteger(), server_default='1', nullable=False, comment='状态 0-停用 1-启用'),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
        sa.Column('is_deleted', sa.SmallInteger(), server_default='0', nullable=False, comment='逻辑删除 0-未删除 1-已删除'),
        sa.ForeignKeyConstraint(['project_id'], ['ai_tc_projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_aitc_prompt_scene', 'ai_tc_prompts', ['scene', 'project_id'])

    # 5. 样本库
    op.create_table('ai_tc_samples',
        sa.Column('project_id', sa.BigInteger(), nullable=True, comment='项目ID，NULL为通用'),
        sa.Column('sample_type', sa.String(length=16), nullable=False, comment='类型 case-用例样本 script-脚本样本'),
        sa.Column('name', sa.String(length=128), nullable=False, comment='样本名称'),
        sa.Column('language', sa.String(length=32), nullable=True, comment='语言'),
        sa.Column('framework', sa.String(length=32), server_default='pytest', nullable=True, comment='框架'),
        sa.Column('content', sa.Text(), nullable=False, comment='样本内容'),
        sa.Column('description', sa.String(length=512), nullable=True, comment='样本描述'),
        sa.Column('status', sa.SmallInteger(), server_default='1', nullable=False, comment='状态 0-停用 1-启用'),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
        sa.Column('is_deleted', sa.SmallInteger(), server_default='0', nullable=False, comment='逻辑删除 0-未删除 1-已删除'),
        sa.ForeignKeyConstraint(['project_id'], ['ai_tc_projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_aitc_sample_type', 'ai_tc_samples', ['sample_type', 'project_id'])

    # 6. AI服务配置
    op.create_table('ai_tc_ai_configs',
        sa.Column('name', sa.String(length=128), nullable=False, comment='配置名称'),
        sa.Column('provider', sa.String(length=32), server_default="'openai_compat'", nullable=False, comment='提供方'),
        sa.Column('api_base', sa.String(length=256), nullable=False, comment='API地址'),
        sa.Column('api_key', sa.String(length=512), nullable=False, comment='API密钥'),
        sa.Column('model', sa.String(length=64), nullable=False, comment='模型名'),
        sa.Column('temperature', sa.Float(), server_default='0.3', nullable=False, comment='采样温度'),
        sa.Column('max_tokens', sa.Integer(), server_default='4096', nullable=False, comment='最大输出token'),
        sa.Column('scenes', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='适用场景列表'),
        sa.Column('is_default', sa.SmallInteger(), server_default='0', nullable=False, comment='全局兜底默认'),
        sa.Column('status', sa.SmallInteger(), server_default='1', nullable=False, comment='状态 0-停用 1-启用'),
        sa.Column('remark', sa.String(length=512), nullable=True, comment='备注'),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
        sa.Column('is_deleted', sa.SmallInteger(), server_default='0', nullable=False, comment='逻辑删除 0-未删除 1-已删除'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 7. AI任务
    op.create_table('ai_tc_tasks',
        sa.Column('task_type', sa.String(length=32), nullable=False, comment='任务类型'),
        sa.Column('project_id', sa.BigInteger(), nullable=False, comment='项目ID'),
        sa.Column('suite_id', sa.BigInteger(), nullable=False, comment='目标套件ID'),
        sa.Column('prompt_id', sa.BigInteger(), nullable=True, comment='提示词模板ID'),
        sa.Column('sample_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='样本ID列表'),
        sa.Column('ai_config_id', sa.BigInteger(), nullable=True, comment='AI配置ID'),
        sa.Column('model', sa.String(length=64), nullable=True, comment='实际使用的模型名'),
        sa.Column('status', sa.SmallInteger(), server_default='0', nullable=False, comment='0-排队 1-运行中 2-完成 3-失败 4-已确认'),
        sa.Column('total_count', sa.Integer(), server_default='0', nullable=False, comment='总用例数'),
        sa.Column('done_count', sa.Integer(), server_default='0', nullable=False, comment='已完成数'),
        sa.Column('input_tokens', sa.Integer(), server_default='0', nullable=False, comment='输入token数'),
        sa.Column('output_tokens', sa.Integer(), server_default='0', nullable=False, comment='输出token数'),
        sa.Column('error_msg', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('create_by', sa.String(length=64), nullable=True, comment='创建人'),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
        sa.Column('is_deleted', sa.SmallInteger(), server_default='0', nullable=False, comment='逻辑删除 0-未删除 1-已删除'),
        sa.ForeignKeyConstraint(['ai_config_id'], ['ai_tc_ai_configs.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['ai_tc_projects.id'], ),
        sa.ForeignKeyConstraint(['prompt_id'], ['ai_tc_prompts.id'], ),
        sa.ForeignKeyConstraint(['suite_id'], ['ai_tc_suites.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_aitc_task_project', 'ai_tc_tasks', ['project_id', 'task_type'])

    # 8. AI任务明细
    op.create_table('ai_tc_task_items',
        sa.Column('task_id', sa.BigInteger(), nullable=False, comment='任务ID'),
        sa.Column('case_id', sa.BigInteger(), nullable=False, comment='用例ID'),
        sa.Column('case_name', sa.String(length=256), nullable=False, comment='用例名称（快照）'),
        sa.Column('output', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='AI输出结果'),
        sa.Column('item_status', sa.SmallInteger(), server_default='0', nullable=False, comment='0-待处理 1-成功 2-失败'),
        sa.Column('confirm_status', sa.SmallInteger(), server_default='0', nullable=False, comment='0-待确认 1-采纳 2-忽略 3-编辑采纳'),
        sa.Column('final_content', sa.Text(), nullable=True, comment='人工修改后最终内容'),
        sa.Column('reviewed_by', sa.String(length=64), nullable=True, comment='审核人'),
        sa.Column('review_time', sa.String(length=32), nullable=True, comment='审核时间'),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
        sa.Column('is_deleted', sa.SmallInteger(), server_default='0', nullable=False, comment='逻辑删除 0-未删除 1-已删除'),
        sa.ForeignKeyConstraint(['case_id'], ['ai_tc_cases.id'], ),
        sa.ForeignKeyConstraint(['task_id'], ['ai_tc_tasks.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    # 9. 测试脚本库
    op.create_table('ai_tc_scripts',
        sa.Column('case_id', sa.BigInteger(), nullable=False, comment='用例ID'),
        sa.Column('language', sa.String(length=32), server_default="'python'", nullable=False, comment='脚本语言'),
        sa.Column('framework', sa.String(length=32), server_default="'pytest'", nullable=False, comment='测试框架'),
        sa.Column('content', sa.Text(), nullable=False, comment='脚本内容'),
        sa.Column('source', sa.SmallInteger(), server_default='1', nullable=False, comment='来源 1-AI生成 2-人工录入'),
        sa.Column('task_item_id', sa.BigInteger(), nullable=True, comment='来源任务明细ID'),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False, comment='版本号'),
        sa.Column('status', sa.SmallInteger(), server_default='1', nullable=False, comment='状态 1-草稿 2-已入库'),
        sa.Column('reviewed_by', sa.String(length=64), nullable=True, comment='审核人'),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('create_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
        sa.Column('is_deleted', sa.SmallInteger(), server_default='0', nullable=False, comment='逻辑删除 0-未删除 1-已删除'),
        sa.ForeignKeyConstraint(['case_id'], ['ai_tc_cases.id'], ),
        sa.ForeignKeyConstraint(['task_item_id'], ['ai_tc_task_items.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_aitc_script_case', 'ai_tc_scripts', ['case_id', 'is_deleted'])


def downgrade() -> None:
    op.drop_index('idx_aitc_script_case', table_name='ai_tc_scripts')
    op.drop_table('ai_tc_scripts')
    op.drop_table('ai_tc_task_items')
    op.drop_index('idx_aitc_task_project', table_name='ai_tc_tasks')
    op.drop_table('ai_tc_tasks')
    op.drop_table('ai_tc_ai_configs')
    op.drop_index('idx_aitc_sample_type', table_name='ai_tc_samples')
    op.drop_table('ai_tc_samples')
    op.drop_index('idx_aitc_prompt_scene', table_name='ai_tc_prompts')
    op.drop_table('ai_tc_prompts')
    op.drop_index('idx_aitc_case_review', table_name='ai_tc_cases')
    op.drop_index('idx_aitc_case_project_core', table_name='ai_tc_cases')
    op.drop_index('idx_aitc_case_suite', table_name='ai_tc_cases')
    op.drop_table('ai_tc_cases')
    op.drop_index('idx_aitc_suite_tree', table_name='ai_tc_suites')
    op.drop_index('idx_aitc_suite_parent', table_name='ai_tc_suites')
    op.drop_index('idx_aitc_suite_project', table_name='ai_tc_suites')
    op.drop_table('ai_tc_suites')
    op.drop_table('ai_tc_projects')
