"""AI 客户端 — 统一 OpenAI 兼容接口封装，从 ai_tc_ai_configs 表加载配置。

职责边界：仅负责底层 AI 交互（chat_json + JSON 解析 + token 统计）。
任务相关的 prompt 构建、结果解析、业务逻辑已迁移到 tasks/ 目录下各任务文件。
"""

import json
import re
from typing import Any

from loguru import logger
from openai import AsyncOpenAI

from app.config import settings


class AiClient:
    """OpenAI 兼容异步客户端，支持 DeepSeek / OpenAI / 其他兼容 provider。

    用法:
        config = await db.get(AiTcAiConfig, config_id)
        client = AiClient(config)
        result = await client.chat_json(system_prompt, user_prompt)
    """

    def __init__(self, ai_config: Any):
        """ai_config: AiTcAiConfig ORM 实例，如果为 None 则使用 .env 兜底。"""
        if ai_config is None:
            self.api_base = settings.AI_API_BASE
            self.api_key = settings.AI_API_KEY
            self.model = settings.AI_MODEL
            self.temperature = 0.3
            self.max_tokens = 4096
        else:
            self.api_base = ai_config.api_base
            self.api_key = ai_config.api_key
            self.model = ai_config.model
            self.temperature = ai_config.temperature or 0.3
            self.max_tokens = ai_config.max_tokens or 4096

        # 标准 OpenAI SDK 写法：api_key + base_url，SDK 自动处理鉴权
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            timeout=120.0,
            max_retries=1,
        )
        # Token 用量累计
        self.input_tokens = 0
        self.output_tokens = 0

    # ── 底层调用 ──

    async def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        retry: int = 1,
    ) -> dict | list:
        """发送 Chat Completion 请求，返回解析后的 JSON（优先 JSON Mode，失败则正则兜底解析 + 重试）。"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens

        for attempt in range(retry + 1):
            try:
                # 优先使用 JSON Mode（部分 provider 不支持，失败降级）
                try:
                    resp = await self._client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=temp,
                        max_tokens=max_tok,
                        response_format={"type": "json_object"},
                    )
                except Exception:
                    # JSON Mode 不支持时降级为普通模式
                    resp = await self._client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=temp,
                        max_tokens=max_tok,
                    )

                text = resp.choices[0].message.content or ""
                parsed = self._extract_json(text)

                if parsed is not None:
                    self.input_tokens += resp.usage.prompt_tokens if resp.usage else 0
                    self.output_tokens += resp.usage.completion_tokens if resp.usage else 0
                    logger.debug(f"AI response parsed successfully, tokens: in={resp.usage.prompt_tokens if resp.usage else 0} out={resp.usage.completion_tokens if resp.usage else 0}")
                    return parsed

                if attempt < retry:
                    logger.warning(f"JSON parse failed, retry {attempt + 1}/{retry}. Raw: {text[:200]}")
                    messages.append({"role": "user", "content": "请严格按照 JSON 格式输出，不要包含任何多余的文字。"})
                else:
                    logger.error(f"JSON parse failed after {retry + 1} attempts. Raw: {text[:500]}")

            except Exception as e:
                logger.error(f"AI API call error (attempt {attempt + 1}): {e}")
                if attempt >= retry:
                    raise

        return {}  # fallback

    # ── JSON 解析 ──

    @staticmethod
    def _extract_json(text: str) -> dict | list | None:
        """从 AI 返回文本中提取 JSON，优先直接解析，失败则正则提取。"""
        text = text.strip()
        # 1) 直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2) 提取 ```json ... ``` 代码块
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 3) 提取首对 {} 或 []
        m = re.search(r"(\{[\s\S]*?\}|\[[\s\S]*?\])", text)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass

        return None
