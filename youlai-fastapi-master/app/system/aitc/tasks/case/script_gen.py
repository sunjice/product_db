"""脚本生成任务。"""

import json

from app.system.aitc.constants import ConfirmStatus, ScriptSource, TaskType
from app.system.aitc.models import AiTcTaskItem
from app.system.aitc.service import AiTcService
from app.system.aitc.tasks.base import BaseTask, TaskContext
from app.system.aitc.tasks.case.constants import ScriptGenConfig


class ScriptGenTask(BaseTask):
    """为测试用例生成 pytest 自动化测试脚本。"""

    task_type = TaskType.SCRIPT_GEN
    batch_size = ScriptGenConfig.BATCH_SIZE
    system_prompt = (
        "你是一个资深的测试开发工程师。请根据用例信息生成可执行的测试脚本。只返回 JSON。"
    )

    # ── 执行 ──

    async def execute(self, ctx: TaskContext) -> None:
        """逐条调用 AI 生成测试脚本。"""
        await self._execute_per_item(ctx)

    # ── Prompt 构建 ──

    def build_user_prompt(
        self, case_detail: dict, template: str,
        samples: str = "", specs: str = "",
    ) -> str:
        """构建脚本生成的用户 prompt。"""
        case_json = json.dumps(case_detail, ensure_ascii=False, indent=2)

        if template:
            return template.replace("{{case}}", case_json).replace("{{samples}}", samples)

        return f"""请根据以下测试用例，生成 pytest 格式的自动化测试脚本。

{samples}

返回 JSON：
{{
  "language": "python",
  "framework": "pytest",
  "script": "import pytest\\n\\ndef test_xxx():\\n    ..."
}}

用例内容：
{case_json}"""

    # ── 结果解析 ──

    @staticmethod
    def parse_result(output: dict | list) -> dict:
        """解析脚本生成结果。"""
        if isinstance(output, dict):
            return {
                "language": output.get("language", "python"),
                "framework": output.get("framework", "pytest"),
                "script": output.get("script", ""),
            }
        return {"language": "python", "framework": "pytest", "script": ""}

    # ── 确认回写 ──

    async def apply_result(
        self,
        svc: AiTcService,
        item: AiTcTaskItem,
        output: dict,
        confirm_status: int,
        final_content: str = "",
    ) -> None:
        """确认：将生成的脚本写入脚本库。"""
        script_content = (
            final_content
            if confirm_status == ConfirmStatus.EDITED_ACCEPTED and final_content
            else output.get("script", "")
        )

        if script_content:
            language = output.get("language", "python")
            framework = output.get("framework", "pytest")
            await svc.create_script_record(
                case_id=item.case_id,
                language=language,
                framework=framework,
                content=script_content,
                source=ScriptSource.AI,
                task_item_id=item.id,
            )
            await svc.increment_case_script_count(item.case_id)
