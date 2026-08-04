"""用例审核 Skill — 对指定模块下的用例进行 AI 质量审核。"""

from app.ai.agent.skills.base import BaseSkill, SkillMode, SkillResult, skill_registry
from app.ai.agent.skills.case.tools import (
    _count_cases_in_suite, _get_project_name, _get_suite_name, resolve_scope,
)
from app.system.aitc.constants import TaskType


class CaseReviewSkill(BaseSkill):
    name = "case_review"
    description = "审核指定模块下测试用例质量，找出缺失字段、不清晰的步骤、不符合规范的地方。当用户说'审核用例'、'检查用例'、'评审用例'时触发。"
    domain = "case"
    mode = SkillMode.ASYNC
    keywords = ["审核", "检查", "评审", "review", "审核用例", "检查用例", "用例审核", "用例质量"]
    required_page = "case"

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "项目 ID"},
                "suite_id": {"type": "integer", "description": "模块 ID"},
            },
            "required": ["project_id", "suite_id"],
        }

    async def execute(self, params: dict, context: dict) -> SkillResult:
        project_id = params.get("project_id") or context.get("project_id")
        suite_id = params.get("suite_id") or context.get("suite_id")
        context_json = context.get("context_json", {})
        raw_selected_case_ids = context_json.get("selected_case_ids", []) if context_json else []
        raw_current_case_id = context_json.get("current_case_id") if context_json else None
        db = context.get("db_session")

        if not project_id or not suite_id:
            return SkillResult(
                success=False,
                msg_type="clarify_card",
                content="请先选择项目和模块。",
                error="缺少 project_id 或 suite_id",
            )

        total = await _count_cases_in_suite(db, int(suite_id))

        if total == 0:
            return SkillResult(
                success=False,
                content="所选模块下没有用例。",
                error="用例数为 0",
            )

        # 防御校验 + 优先级裁决：current_case_id > selected_case_ids > 全模块
        target_case_ids = await resolve_scope(
            db, int(suite_id), raw_selected_case_ids, raw_current_case_id,
        )
        scope_total = len(target_case_ids) if target_case_ids else total
        scope_desc = f"已选中的 {scope_total} 条" if target_case_ids else "当前模块下的"

        # 获取项目名和模块名，构建确认卡片
        project_name = await _get_project_name(db, int(project_id))
        suite_name = await _get_suite_name(db, int(suite_id))
        task_type_label = TaskType.labels().get(TaskType.CASE_REVIEW, "用例审核")

        content = (
            f"即将创建**{task_type_label}**任务，将对{scope_desc}用例逐条进行质量审核，请确认以下信息：\n\n"
            f"| 项目 | {project_name} |\n"
            f"| 模块 | {suite_name} |\n"
            f"| 任务类型 | {task_type_label} |\n"
            f"| 用例数量 | {scope_total} 条 |\n"
        )

        # 不直接创建任务，返回确认卡片供用户确认
        return SkillResult(
            success=True,
            msg_type="confirm_card",
            content=content,
            metadata={
                "skill_name": self.name,
                "task_type": TaskType.CASE_REVIEW.value,
                "project_id": int(project_id),
                "suite_id": int(suite_id),
                "case_ids": target_case_ids,
                "project_name": project_name,
                "suite_name": suite_name,
                "total": scope_total,
            },
        )


case_review_skill = CaseReviewSkill()
skill_registry.register(case_review_skill)