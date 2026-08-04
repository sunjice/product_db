"""任务基类 — 定义 AI 任务的标准接口与通用能力。"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AiClient
from app.system.aitc.service import AiTcService
from app.system.aitc.models import AiTcCase, AiTcTaskItem
from app.system.aitc.constants import ItemStatus, TaskStatus

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


@dataclass
class TaskContext:
    """任务执行上下文，由 execute_task_bg 统一构建后传入。"""
    db: AsyncSession
    svc: AiTcService
    client: AiClient
    task_id: int
    items: list[AiTcTaskItem]
    prompt: str
    samples: str
    specs: str


class BaseTask(ABC):
    """AI 任务抽象基类。

    子类需声明：
    - task_type: str        —— 任务类型标识（对应 TaskType 枚举值）
    - batch_size: int       —— 每批处理的用例数
    - system_prompt: str    —— 发送给 AI 的系统提示词
    - commit_every: int     —— 每处理多少条向 DB 提交一次 done_count 进度
    """

    task_type: str
    batch_size: int = 1
    system_prompt: str = ""
    commit_every: int = 1

    # ── 公共能力 ──

    @classmethod
    def load_prompt(cls) -> str:
        """从 prompts/ 目录加载对应场景的提示词模板文件。"""
        filename = f"{cls.task_type}.txt"
        filepath = PROMPTS_DIR / filename
        if filepath.exists():
            return filepath.read_text(encoding="utf-8")
        logger.warning(f"Prompt file not found: {filepath}, using empty prompt")
        return ""

    # ── 抽象方法（子类必须实现） ──

    @abstractmethod
    async def execute(self, ctx: TaskContext) -> None:
        """执行任务主逻辑：遍历 ctx.items，逐条/批量调 AI，写入结果。"""
        ...

    @abstractmethod
    async def apply_result(
        self,
        svc: AiTcService,
        item: AiTcTaskItem,
        output: dict,
        confirm_status: int,
        final_content: str = "",
    ) -> None:
        """确认时将 AI 输出结果写入实际数据表。

        Parameters
        ----------
        svc : AiTcService
            当前 DB 会话对应的 service 实例。
        item : AiTcTaskItem
            任务明细记录，含 case_id、output 等。
        output : dict
            item.output 解析后的 dict。
        confirm_status : int
            ConfirmStatus 枚举值。
        final_content : str
            编辑采纳时用户修改后的最终内容。
        """
        ...

    # ── 公共工具方法 ──

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

    @staticmethod
    def _mark_item_success(item: AiTcTaskItem, output: dict) -> None:
        """标记一条明细为成功。"""
        item.output = output
        item.item_status = ItemStatus.SUCCESS

    @staticmethod
    def _mark_item_failed(item: AiTcTaskItem, error: str, max_len: int = 500) -> None:
        """标记一条明细为失败。"""
        item.item_status = ItemStatus.FAILED
        item.output = {"error": error[:max_len]}

    async def _update_progress(self, ctx: TaskContext, done: int) -> None:
        """更新任务进度并提交 DB。"""
        await ctx.svc.update_task_done_count(ctx.task_id, done)
        await ctx.db.commit()

    # ── 默认 execute 实现（逐条迭代，适用于 case_review / script_gen） ──

    async def _execute_per_item(self, ctx: TaskContext) -> None:
        """逐条执行模板：加载全量用例 → 逐条 build prompt + 调 AI + 解析 → 写结果。"""
        # 加载全部用例详情
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

    # ── 子类可覆盖的 hook（需在子类实现或在 _execute_per_item 调用前定义） ──

    def build_user_prompt(
        self, case_detail: dict, prompt_template: str,
        samples_text: str = "", specs_text: str = "",
    ) -> str:
        """构建用户 prompt（子类按需覆盖）。"""
        raise NotImplementedError

    def parse_result(self, output: dict | list) -> dict | list:
        """解析 AI 返回结果（子类按需覆盖）。"""
        return output
