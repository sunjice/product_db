"""补全字段 Skill — AI 根据用例标题和测试思想，补全用例的前置条件、测试数据、预期结果等字段。

SYNC 模式：在对话内即时返回补全建议。
"""

from app.system.aitc.chat.skill_base import BaseSkill, SkillMode, SkillResult, skill_registry
from app.system.aitc.chat.domains.case.tools import _get_case_detail


class FieldCompleteSkill(BaseSkill):
    name = "field_complete"
    description = "根据用例标题和测试思想，补全用例字段（前置条件、测试数据、测试拓扑等）。当用户说'补全字段'、'完善信息'、'补充前置'时触发。"
    domain = "case"
    mode = SkillMode.SYNC
    keywords = ["补全", "补充", "完善", "填充", "补写", "缺少", "完整"]

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "case_id": {"type": "integer", "description": "用例 ID"},
                "field_hint": {"type": "string", "description": "要补全的字段提示，如 preconditions/topo/test_data/all"},
            },
            "required": ["case_id"],
        }

    async def execute(self, params: dict, context: dict) -> SkillResult:
        case_id = params.get("case_id")
        field_hint = params.get("field_hint", "all")

        if not case_id:
            return SkillResult(
                success=False,
                msg_type="clarify_card",
                content="请指定需要补全字段的用例。你可以说'帮我补全用例 TC-001 的前置条件'。",
                error="缺少 case_id",
            )

        db = context.get("db_session")
        case = await _get_case_detail(db, case_id)

        if case is None:
            return SkillResult(
                success=False,
                content=f"未找到用例 ID={case_id}。",
                error="用例不存在",
            )

        # 构建用例摘要
        case_summary = {
            "id": case.id,
            "name": case.name,
            "summary": case.summary or "",
            "preconditions": case.preconditions or "",
            "topo": case.topo or "",
            "test_data": case.test_data or "",
            "importance": case.importance,
            "steps": case.steps or [],
        }

        return SkillResult(
            success=True,
            msg_type="draft_card",
            content=f"正在分析用例「{case.name}」，准备补全 {field_hint} 字段...",
            draft_type="field_complete",
            draft_data={
                "case_id": case.id,
                "case_name": case.name,
                "case_summary": case_summary,
                "field_hint": field_hint,
            },
            metadata={"case_id": case.id, "field_hint": field_hint},
        )


field_complete_skill = FieldCompleteSkill()
skill_registry.register(field_complete_skill)
