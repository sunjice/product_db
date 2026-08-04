"""核心用例挑选 Skill — 对指定模块下的用例，挑选核心用例。"""

from app.ai.agent.skills.base import BaseSkill, SkillMode, SkillResult, skill_registry
from app.ai.agent.skills.case.tools import (
    _count_cases_in_suite, _get_project_name, _get_suite_name, resolve_scope,
)
from app.system.aitc.constants import TaskType


class CoreSelectSkill(BaseSkill):
    name = "core_select"
    description = "从指定模块下挑选核心/重要的测试用例。当用户说'挑选核心用例'、'挑重要用例'、'核心用例'时触发。"
    domain = "case"
    mode = SkillMode.ASYNC
    keywords = ["核心用例", "重要用例", "挑选核心", "挑重要", "核心挑选", "core", "核心的用例"]
    required_page = "case"

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "项目 ID"},
                "suite_id": {"type": "integer", "description": "模块 ID（必填，只处理该模块下的用例）"},
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

        if not project_id:
            return SkillResult(
                success=False,
                msg_type="clarify_card",
                content="请先在左侧选择一个项目。",
                error="缺少 project_id",
            )

        if not suite_id:
            return SkillResult(
                success=False,
                msg_type="clarify_card",
                content="请先在左侧模块树中选择要处理的模块（只对该模块下的用例执行）。",
                error="缺少 suite_id",
            )

        total = await _count_cases_in_suite(db, int(suite_id))

        if total == 0:
            return SkillResult(
                success=False,
                content="所选模块下没有用例，请先导入用例或选择其他模块。",
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
        task_type_label = TaskType.labels().get(TaskType.CORE_SELECT, "挑选核心用例")

        content = (
            f"即将创建**{task_type_label}**任务，将对{scope_desc}用例进行核心挑选，请确认以下信息：\n\n"
            f"| 项目 | {project_name} |\n"
            f"| 模块 | {suite_name} |\n"
            f"| 任务类型 | {task_type_label} |\n"
            f"| 用例数量 | {scope_total} 条 |\n"
        )

        return SkillResult(
            success=True,
            msg_type="confirm_card",
            content=content,
            metadata={
                "skill_name": self.name,
                "task_type": TaskType.CORE_SELECT.value,
                "project_id": int(project_id),
                "suite_id": int(suite_id),
                "case_ids": target_case_ids,
                "project_name": project_name,
                "suite_name": suite_name,
                "total": scope_total,
            },
        )


core_select_skill = CoreSelectSkill()
skill_registry.register(core_select_skill)