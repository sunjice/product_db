"""Token 用量记录器 — LangChain Callback + 通用日志。"""

import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chat.models import AiUsageLog


class TokenMeter:
    """Token 用量计量器 — 用于单次 LLM 调用的 token 统计。

    用法:
        meter = TokenMeter(model="gpt-4")
        # ... LLM 调用 ...
        meter.capture(prompt_tokens=150, completion_tokens=80)
        await meter.save(db, module="chat", session_id=1)
    """

    def __init__(self, model: str = "unknown"):
        self.model = model
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self._start = time.monotonic()

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def duration_ms(self) -> int:
        return int((time.monotonic() - self._start) * 1000)

    def capture(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ):
        """累加 token 计数（支持多次调用累积）。"""
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens

    async def save(
        self,
        db: AsyncSession,
        module: str = "chat",
        session_id: int | None = None,
        task_id: int | None = None,
    ):
        """将用量记录写入数据库。"""
        if self.total_tokens == 0:
            return
        log = AiUsageLog(
            module=module,
            session_id=session_id,
            task_id=task_id,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.total_tokens,
            duration_ms=self.duration_ms,
        )
        db.add(log)
        await db.flush()


class LangChainTokenCallback(BaseCallbackHandler):
    """LangChain callback — 自动拦截 LLM 调用的 token 信息。

    继承 BaseCallbackHandler 以兼容 LangChain 0.3+ 的 callback manager。
    """

    def __init__(self, meter: TokenMeter):
        self.meter = meter

    def on_llm_end(self, response, **kwargs) -> None:
        """LLM 调用结束时自动捕获 token 用量。"""
        try:
            # LangChain v0.2+ 的 usage_metadata
            if hasattr(response, "llm_output") and response.llm_output:
                usage = response.llm_output.get("token_usage", {})
                if usage:
                    self.meter.capture(
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                    )
                    return

            # 尝试从 generations 获取
            if hasattr(response, "generations"):
                for gen_list in response.generations:
                    for gen in gen_list:
                        if hasattr(gen, "generation_info"):
                            usage = gen.generation_info.get("usage_metadata", {})
                            if usage:
                                self.meter.capture(
                                    prompt_tokens=usage.get("input_tokens", 0),
                                    completion_tokens=usage.get("output_tokens", 0),
                                )
                                return

            # 尝试从 usage_metadata 直接获取 (LangChain >= 0.3)
            if hasattr(response, "usage_metadata"):
                um = response.usage_metadata
                if isinstance(um, dict):
                    self.meter.capture(
                        prompt_tokens=um.get("input_tokens", 0),
                        completion_tokens=um.get("output_tokens", 0),
                    )
        except Exception:
            pass  # token 统计失败不应影响主流程
