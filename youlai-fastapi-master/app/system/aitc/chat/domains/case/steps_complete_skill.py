"""补写测试步骤 Skill — 根据用例标题和测试思想，AI 补写测试步骤和预期结果。

SYNC 模式：在对话内即时返回步骤建议。
"""

from app.system.aitc.chat.skill_base import BaseSkill, SkillMode, SkillResult, skill_registry
from app.system.aitc.chat.domains.case.tools import _get_case_detail


class StepsCompleteSkill(BaseSkill):
    name = "steps_complete"
    description = "根据用例的标题和测试目的，补写详细的测试步骤和预期结果。当用户说'补写步骤'、'补充步骤'、'写测试步骤'时触发。"
    domain = "case"
    mode = SkillMode.SYNC
    keywords = ["步骤", "补写步骤", "补充步骤", "测试步骤", "预期结果", "steps", "写步骤"]

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "case_id": {"type": "integer", "description": "用例 ID"},
                "case_title": {"type": "string", "description": "用例标题（无 ID 时可传标题描述需求）"},
            },
            "required": [],
        }

    async def execute(self, params: dict, context: dict) -> SkillResult:
        case_id = params.get("case_id")
        case_title = params.get("case_title")

        if case_id:
            db = context.get("db_session")
            case = await _get_case_detail(db, case_id)
            if case is None:
                return SkillResult(
                    success=False,
                    content=f"未找到用例 ID={case_id}。",
                    error="用例不存在",
                )
            case_name = case.name
            case_summary = case.summary or ""
            target = "「" + case_name + "」"
        elif case_title:
            case_name = case_title
            case_summary = case_title
            target = "「" + case_title + "」"
        else:
            return SkillResult(
                success=False,
                msg_type="clarify_card",
                content="请告诉我你需要为哪个用例补写步骤？可以给我用例 ID 或用例标题。",
                error="缺少用例信息",
            )

        return SkillResult(
            success=True,
            msg_type="draft_card",
            content=f"正在根据 {target} 的目的，补写详细的测试步骤和预期结果...",
            draft_type="steps_complete",
            draft_data={
                "case_id": case_id,
                "case_name": case_name,
                "case_summary": case_summary,
            },
            metadata={"case_id": case_id, "case_name": case_name},
        )


steps_complete_skill = StepsCompleteSkill()
skill_registry.register(steps_complete_skill)
