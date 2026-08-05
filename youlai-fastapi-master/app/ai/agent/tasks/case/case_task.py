"""用例领域 — 任务中间层，提供逐条处理用例的模板方法。"""

from loguru import logger
from sqlalchemy import select

from app.aitc.models import AiTcCase
from app.ai.agent.tasks.base import BaseTask, TaskContext


class CaseTask(BaseTask):
    """用例领域 AI 任务中间层。

    为逐条处理用例的子类（CaseReviewTask / ScriptGenTask）提供
    _execute_per_item 模板方法：加载用例 → 逐条 build prompt + 调 AI → 写结果。

    需要批量模式的子类（如 CoreSelectTask）直接继承 BaseTask 自行实现 execute()。
    """

    # ── 用例详情构建 ──

    @staticmethod
    def _build_case_detail(case: AiTcCase) -> dict:
        """从 ORM 实例构建用例详情 dict。"""
        return {
            "name": case.name or "",
            "summary": case.summary or "",
            "preconditions": case.preconditions or "",
            "test_data": case.test_data or "",
            "steps": case.steps or [],
            "importance": case.importance or 2,
        }

    # ── 逐条执行模板 ──

    async def _execute_per_item(self, ctx: TaskContext) -> None:
        """逐条执行：加载全量用例 → 逐条 build prompt + 调 AI + 解析 → 写结果。"""
        case_ids = [it.case_id for it in ctx.items]
        cases = (await ctx.db.execute(
            select(AiTcCase).where(AiTcCase.id.in_(case_ids))
        )).scalars().all()
        case_map: dict[int, AiTcCase] = {c.id: c for c in cases}

        done = 0
        for it in ctx.items:
            case = case_map.get(it.case_id)
            if not case:
                self._mark_item_failed(it, "用例不存在")
                done += 1
                continue

            case_detail = self._build_case_detail(case)
            try:
                user_prompt = self.build_user_prompt(
                    case_detail, ctx.prompt, ctx.samples, ctx.specs,
                )
                raw = await ctx.client.chat_json(self.system_prompt, user_prompt)
                result = self.parse_result(raw)
                self._mark_item_success(it, result)
            except Exception as e:
                logger.error(f"{self.task_type} failed for case {case.id}: {e}")
                self._mark_item_failed(it, str(e))

            done += 1
            if done % self.commit_every == 0 or done == len(ctx.items):
                await self._update_progress(ctx, done)
