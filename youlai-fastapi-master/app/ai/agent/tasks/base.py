"""任务基类 — 定义 AI 任务的标准接口与通用能力。

用例领域的逐条处理模板已迁移至 app.ai.agent.tasks.case.case_task.CaseTask。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AiClient
from app.aitc.task.store import TaskStore
from app.aitc.models import AiTcTaskItem
from app.aitc.constants import ItemStatus

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


@dataclass
class TaskContext:
    """任务执行上下文，由 execute_task_bg 统一构建后传入。"""
    db: AsyncSession
    svc: TaskStore
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
    - batch_size: int       —— 每批处理的数据量
    - system_prompt: str    —— 发送给 AI 的系统提示词
    - commit_every: int     —— 每处理多少条向 DB 提交一次进度
    """

    task_type: str
    batch_size: int = 1
    system_prompt: str = ""
    commit_every: int = 1

    # ── 公共能力 ──

    @classmethod
    def load_prompt(cls) -> str:
        """从 prompts/ 目录加载对应场景的提示词模板文件。"""
        task_type = cls.task_type.value if isinstance(cls.task_type, Enum) else cls.task_type
        filename = f"{task_type}.txt"
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
        svc: TaskStore,
        item: AiTcTaskItem,
        output: dict,
        confirm_status: int,
        final_content: str = "",
    ) -> None:
        """确认时将 AI 输出结果写入实际数据表。"""
        ...

    # ── 公共工具方法 ──

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

    # ── 子类可覆盖的 hook ──

    def build_user_prompt(
        self, data: dict | list, template: str,
        samples_text: str = "", specs_text: str = "",
    ) -> str:
        """构建用户 prompt（子类按需覆盖）。"""
        raise NotImplementedError

    def parse_result(self, output: dict | list) -> dict | list:
        """解析 AI 返回结果（子类按需覆盖）。"""
        return output
