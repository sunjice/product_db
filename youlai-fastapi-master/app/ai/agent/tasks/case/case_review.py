"""用例审核任务。"""

import json

from loguru import logger
from sqlalchemy import select

from app.aitc.constants import ConfirmStatus, TaskType
from app.aitc.models import AiTcCase, AiTcTask, AiTcTaskItem
from app.aitc.task.store import TaskStore
from app.aitc.case.service import CaseService
from app.ai.agent.tasks.base import TaskContext
from app.ai.agent.tasks.case.case_task import CaseTask
from app.ai.agent.tasks.case.constants import CaseReviewConfig


class CaseReviewTask(CaseTask):
    """逐字段审核测试用例。"""

    task_type = TaskType.CASE_REVIEW
    batch_size = CaseReviewConfig.BATCH_SIZE
    commit_every = CaseReviewConfig.COMMIT_EVERY
    sample_limit = CaseReviewConfig.SAMPLE_LIMIT
    system_prompt = (
        "你是一个资深的测试专家。请逐字段审核给定的测试用例，"
        "对每个字段判断合格/不合格，指出违反的规范并给出修改建议。只返回 JSON。"
    )

    # ── 执行 ──

    async def execute(self, ctx: TaskContext) -> None:
        """逐条调用 AI 审核用例。

        从任务关联的套件下加载样本用例（is_sample=1），替换 ctx.samples。
        """
        suite_samples = await self._load_suite_samples(ctx)
        if suite_samples:
            ctx.samples = suite_samples

        await self._execute_per_item(ctx)

    async def _load_suite_samples(self, ctx: TaskContext) -> str:
        """从套件下加载标记为样本的用例，构建样本文本。

        Returns
        -------
        str
            格式化的样本用例文本，无样本时返回空字符串。
        """
        # 加载任务记录获取 suite_id
        task = await ctx.db.get(AiTcTask, ctx.task_id)
        if task is None:
            return ""

        # 查询套件下标记为样本的用例
        stmt = (
            select(AiTcCase)
            .where(
                AiTcCase.suite_id == task.suite_id,
                AiTcCase.is_sample == 1,
                AiTcCase.is_deleted == 0,
            )
            .limit(self.sample_limit)
        )
        result = await ctx.db.execute(stmt)
        sample_cases = result.scalars().all()

        if not sample_cases:
            return ""

        sample_dicts = [self._format_sample_case(c) for c in sample_cases]
        samples_json = json.dumps(sample_dicts, ensure_ascii=False, indent=2)

        logger.info(
            f"Task {ctx.task_id}: loaded {len(sample_cases)} sample cases "
            f"from suite {task.suite_id}"
        )
        return "同模块样本用例（格式与待审核用例一致，供参考）：\n" + samples_json

    @staticmethod
    def _format_sample_case(case: AiTcCase) -> dict:
        """将一条样本用例构建为与待审核用例同结构的 dict。"""
        return CaseTask._build_case_detail(case)

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
- 测试目的：应清晰说明该用例要验证的业务目标或功能点，一句话概括。
- 测试思想：应清晰说明测试策略、风险点和验证目标，体现测试设计思路。
- 前置条件：应完整列出执行测试前必须满足的环境、数据、权限等条件。
- 测试数据：应明确列出测试所需的具体数据内容、格式和来源。
- 测试Topo：应描述测试的网络拓扑、服务依赖关系。
- 测试步骤：每步应包含明确的操作(action)和可验证的预期结果(expected)，步骤逻辑连贯，无歧义。

审核指引：
1. 审核优先级：通用规范 > 模块规范（如有）> 常见问题（如有）。
2. 如果上面提供了同模块的样本用例，务必参考样本用例中各字段的写法风格、粒度、术语表达。
3. 提出修改建议时，应充分参考同模块样本用例中对应字段的写法，保持与模块内其他用例的一致性。
   例如：测试目的的表述方式、前置条件的粒度、步骤的 action/expected 格式等。

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
      "field_name": "purpose",
      "conclusion": "fail",
      "rule_violated": "缺少测试目的，未说明该用例要验证的业务目标",
      "suggested_value": "验证SSID名称长度超过32字符时系统拒绝并提示错误"
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
            text_field_names = ["name", "purpose", "summary", "preconditions", "test_data", "topo"]
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
        svc: TaskStore,
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
        case_svc = CaseService(svc.db)
        update_fields: dict[str, str | list] = self._extract_review_updates(output)

        if update_fields:
            await case_svc.apply_case_review_result(item.case_id, update_fields)

        # 无论如何更新审核状态
        await case_svc.mark_case_reviewed(item.case_id)

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
                if fn in ("name", "purpose", "summary", "preconditions", "test_data", "topo", "steps"):
                    updates[fn] = sv
            if updates:
                return updates

        # 旧格式：rewritten
        rewritten = output.get("rewritten")
        if rewritten and isinstance(rewritten, dict):
            for fn in ("name", "purpose", "summary", "preconditions", "topo", "steps"):
                val = rewritten.get(fn)
                if val and fn == "name":
                    updates["name"] = val
                elif val:
                    updates[fn] = val
        return updates
