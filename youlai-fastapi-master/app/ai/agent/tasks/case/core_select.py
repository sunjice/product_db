"""核心用例挑选任务。"""

import json

from loguru import logger
from sqlalchemy import select

from app.aitc.constants import ConfirmStatus, ItemStatus, TaskType
from app.aitc.models import AiTcCase, AiTcTaskItem
from app.aitc.task.store import TaskStore
from app.aitc.case.service import CaseService
from app.ai.agent.tasks.base import BaseTask, TaskContext
from app.ai.agent.tasks.case.constants import CoreSelectConfig


class CoreSelectTask(BaseTask):
    """从一批用例中挑选核心用例。"""

    task_type = TaskType.CORE_SELECT
    batch_size = CoreSelectConfig.BATCH_SIZE
    system_prompt = "你是一个资深的测试架构师。请根据用例信息，挑选出核心用例。只返回 JSON。"

    # ── 执行 ──

    async def execute(self, ctx: TaskContext) -> None:
        """批量挑选核心用例。每批调用一次 AI，返回每个用例的 selected + reason。"""
        done = 0

        for batch_start in range(0, len(ctx.items), self.batch_size):
            batch_items = ctx.items[batch_start: batch_start + self.batch_size]

            # 加载本批用例详情
            case_ids_batch = [it.case_id for it in batch_items]
            cases = (await ctx.db.execute(
                select(AiTcCase).where(AiTcCase.id.in_(case_ids_batch))
            )).scalars().all()
            case_map = {c.id: c for c in cases}

            cases_data = []
            for it in batch_items:
                c = case_map.get(it.case_id)
                if c:
                    cases_data.append({
                        "name": c.name or "",
                        "purpose": c.purpose or "",
                        "summary": c.summary or "",
                        "importance": c.importance or 2,
                    })
                else:
                    cases_data.append({"name": it.case_name, "purpose": "", "summary": "", "importance": 2})

            try:
                user_prompt = self.build_user_prompt(
                    cases_data, ctx.prompt, ctx.samples, ctx.specs,
                )
                raw = await ctx.client.chat_json(self.system_prompt, user_prompt)
                results = self.parse_result(raw, cases_data)

                for i, it in enumerate(batch_items):
                    r = results[i] if i < len(results) else {"selected": False, "reason": ""}
                    self._mark_item_success(it, r)
                    done += 1
            except Exception as e:
                logger.error(f"Core select batch failed at offset {batch_start}: {e}")
                for it in batch_items:
                    self._mark_item_failed(it, str(e))

            await self._update_progress(ctx, done)

    # ── Prompt 构建 ──

    def build_user_prompt(
        self, cases_batch: list[dict], template: str,
        samples: str = "", specs: str = "",
    ) -> str:
        """构建核心用例挑选的用户 prompt。"""
        case_list = []
        for i, c in enumerate(cases_batch):
            case_list.append({
                "index": i,
                "name": c.get("name", ""),
                "purpose": c.get("purpose", ""),
                "summary": c.get("summary", ""),
                "importance": c.get("importance", 2),
            })

        case_list_json = json.dumps(case_list, ensure_ascii=False, indent=2)

        if template:
            return template.replace("{{cases}}", case_list_json).replace("{{samples}}", samples).replace("{{specs}}", specs)

        return f"""以下是一批测试用例信息，请根据下方规范从中挑选出核心用例；若未提供规范，则按高风险、核心业务流程、关键功能原则判断。

{specs}

请对每个用例判断是否为核心，返回 JSON 数组：
{{
  "results": [
    {{"index": 0, "selected": true, "reason": "覆盖登录主流程，属高风险功能"}},
    {{"index": 1, "selected": false, "reason": "边缘场景"}}
  ]
}}

用例列表：
{case_list_json}"""

    # ── 结果解析 ──

    @staticmethod
    def parse_result(output: dict | list, cases_batch: list[dict]) -> list[dict]:
        """解析核心用例挑选结果。"""
        if isinstance(output, dict):
            results = output.get("results", [])
        elif isinstance(output, list):
            results = output
        else:
            return [{"selected": False, "reason": ""} for _ in cases_batch]

        mapped = [{"selected": False, "reason": ""} for _ in cases_batch]
        for r in results:
            if isinstance(r, dict) and "index" in r:
                idx = r["index"]
                if 0 <= idx < len(mapped):
                    mapped[idx] = {
                        "selected": r.get("selected", False),
                        "reason": r.get("reason", ""),
                    }
        return mapped

    # ── 确认回写 ──

    async def apply_result(
        self,
        svc: TaskStore,
        item: AiTcTaskItem,
        output: dict,
        confirm_status: int,
        final_content: str = "",
        is_core: bool | None = None,
    ) -> None:
        """确认：将所有行的最终决策写入用例表。

        未明确指定 is_core 时（兼容旧逻辑），仅 ACCEPTED→is_core=1。
        明确指定 is_core=False 时，写入 is_core=0。
        """
        if is_core is None:
            # 兼容旧调用：仅 ACCEPTED/EDITED_ACCEPTED 才写
            if confirm_status not in (ConfirmStatus.ACCEPTED, ConfirmStatus.EDITED_ACCEPTED):
                return
            is_core = True

        reason = (
            output.get("reason", "").strip()
            or final_content.strip()
            or "人工确认"
        )[:512]
        case_svc = CaseService(svc.db)
        await case_svc.apply_core_select_result(item.case_id, reason, is_core=is_core)
