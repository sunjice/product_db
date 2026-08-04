"""用例审核任务。"""

import json

from loguru import logger

from app.system.aitc.constants import ConfirmStatus, TaskType
from app.system.aitc.models import AiTcTaskItem
from app.system.aitc.service import AiTcService
from app.system.aitc.tasks.base import BaseTask, TaskContext
from app.system.aitc.tasks.case.constants import CaseReviewConfig


class CaseReviewTask(BaseTask):
    """逐字段审核测试用例。"""

    task_type = TaskType.CASE_REVIEW
    batch_size = CaseReviewConfig.BATCH_SIZE
    commit_every = CaseReviewConfig.COMMIT_EVERY
    system_prompt = (
        "你是一个资深的测试专家。请逐字段审核给定的测试用例，"
        "对每个字段判断合格/不合格，指出违反的规范并给出修改建议。只返回 JSON。"
    )

    # ── 执行 ──

    async def execute(self, ctx: TaskContext) -> None:
        """逐条调用 AI 审核用例。"""
        await self._execute_per_item(ctx)

    # ── Prompt 构建 ──

    def build_user_prompt(
        self, case_detail: dict, template: str,
        samples: str = "", specs: str = "",
    ) -> str:
        """构建用例审核的用户 prompt。"""
        case_json = json.dumps(case_detail, ensure_ascii=False, indent=2)

        if template:
            return template.replace("{{case}}", case_json).replace("{{samples}}", samples).replace("{{specs}}", specs)

        return f"""请审核以下测试用例。对每个字段逐一审查，判断是否合格（pass/fail），如不合格需指出违反的具体规范并给出修改建议，最后给出整体评分。

{samples}

审核规范：
- 用例名称：应简洁明确，准确概括测试对象和核心场景，不超过30字。
- 测试思想：应清晰说明测试策略、风险点和验证目标，体现测试设计思路。
- 前置条件：应完整列出执行测试前必须满足的环境、数据、权限等条件。
- 测试数据：应明确列出测试所需的具体数据内容、格式和来源。
- 测试Topo：应描述测试的网络拓扑、服务依赖关系。
- 测试步骤：每步应包含明确的操作(action)和可验证的预期结果(expected)，步骤逻辑连贯，无歧义。

返回 JSON：
{{
  "score": 75,
  "overall_assessment": "整体评价...",
  "fields": [
    {{
      "field_name": "name",
      "conclusion": "pass",
      "rule_violated": "",
      "suggested_value": ""
    }},
    {{
      "field_name": "summary",
      "conclusion": "fail",
      "rule_violated": "测试思想过于笼统，未说明测试策略和风险点",
      "suggested_value": "验证在并发场景下用户登录接口的幂等性..."
    }},
    {{
      "field_name": "preconditions",
      "conclusion": "pass",
      "rule_violated": "",
      "suggested_value": ""
    }},
    {{
      "field_name": "test_data",
      "conclusion": "fail",
      "rule_violated": "未明确测试数据的具体内容",
      "suggested_value": "账号: test_user_001, 密码: Abc12345, 角色: 普通用户"
    }},
    {{
      "field_name": "topo",
      "conclusion": "pass",
      "rule_violated": "",
      "suggested_value": ""
    }},
    {{
      "field_name": "steps",
      "conclusion": "fail",
      "rule_violated": "步骤3缺少明确的预期结果，步骤2和3顺序不合理",
      "suggested_value": [
        {{
          "step_no": 1,
          "action": "...",
          "expected": "..."
        }}
      ]
    }}
  ]
}}

用例内容：
{case_json}"""

    # ── 结果解析 ──

    @staticmethod
    def parse_result(output: dict | list) -> dict:
        """解析用例审核结果（兼容新旧格式）。"""
        if not isinstance(output, dict):
            return {"score": 0, "overall_assessment": "", "fields": []}

        score = output.get("score", 0)
        overall = output.get("overall_assessment", "")

        # 新格式：逐字段结论
        raw_fields = output.get("fields") or []
        if raw_fields:
            fields = []
            for f in raw_fields:
                if not isinstance(f, dict):
                    continue
                suggested = f.get("suggested_value")
                conclusion = f.get("conclusion", "pass")
                fields.append({
                    "field_name": f.get("field_name", ""),
                    "conclusion": conclusion,
                    "rule_violated": f.get("rule_violated", ""),
                    "suggested_value": suggested if conclusion == "fail" else None,
                })
            return {
                "score": score,
                "overall_assessment": overall or output.get("suggestion", ""),
                "fields": fields,
            }

        # 旧格式兼容：从 rewritten + issues 转换
        rewritten = output.get("rewritten")
        if rewritten and isinstance(rewritten, dict):
            fields = []
            old_issues = output.get("issues", [])
            issues_text = "; ".join(old_issues) if old_issues else ""
            text_field_names = ["name", "summary", "preconditions", "test_data", "topo"]
            for fn in text_field_names:
                sv = rewritten.get(fn)
                has_sug = sv is not None and sv != ""
                fields.append({
                    "field_name": fn,
                    "conclusion": "fail" if has_sug else "pass",
                    "rule_violated": issues_text if has_sug else "",
                    "suggested_value": sv if has_sug else None,
                })
            # steps
            steps_sv = rewritten.get("steps")
            if steps_sv is not None:
                fields.append({
                    "field_name": "steps",
                    "conclusion": "fail",
                    "rule_violated": issues_text,
                    "suggested_value": steps_sv,
                })
            else:
                fields.append({
                    "field_name": "steps",
                    "conclusion": "pass",
                    "rule_violated": "",
                    "suggested_value": None,
                })
            return {
                "score": score,
                "overall_assessment": overall or output.get("suggestion", ""),
                "fields": fields,
            }

        # 完全旧格式无 rewritten
        return {
            "score": score,
            "overall_assessment": overall or output.get("suggestion", ""),
            "fields": [],
        }

    # ── 确认回写 ──

    async def apply_result(
        self,
        svc: AiTcService,
        item: AiTcTaskItem,
        output: dict,
        confirm_status: int,
        final_content: str = "",
    ) -> None:
        """确认：将 AI 建议的字段值写入用例。

        兼容两种 AI 输出格式：
        1. 新格式 fields[]: 从 fields[].suggested_value 提取
        2. 旧格式 rewritten: 从 rewritten.name/summary/... 提取
        """
        update_fields: dict[str, str | list] = self._extract_review_updates(output)

        if update_fields:
            await svc.apply_case_review_result(item.case_id, update_fields)

        # 无论如何更新审核状态
        await svc.mark_case_reviewed(item.case_id)

    @staticmethod
    def _extract_review_updates(output: dict) -> dict[str, str | list]:
        """从 AI 输出中提取需要更新的字段。

        优先使用新格式 fields[]，fallback 到旧格式 rewritten。
        """
        updates: dict = {}

        # 新格式：fields[]
        fields = output.get("fields") or []
        if fields:
            for f in fields:
                if not isinstance(f, dict):
                    continue
                if f.get("conclusion") != "fail":
                    continue
                sv = f.get("suggested_value")
                if sv is None or sv == "":
                    continue
                fn = f.get("field_name", "")
                if fn in ("name", "summary", "preconditions", "test_data", "topo", "steps"):
                    updates[fn] = sv
            if updates:
                return updates

        # 旧格式：rewritten
        rewritten = output.get("rewritten")
        if rewritten and isinstance(rewritten, dict):
            for fn in ("name", "summary", "preconditions", "steps"):
                val = rewritten.get(fn)
                if val and fn == "name":
                    updates["name"] = val
                elif val:
                    updates[fn] = val
        return updates
