"""clarify 工具 — 向用户提问，收集确认信息后再发起任务。

content_and_artifact 模式:
- content → 给模型看的简短提示
- artifact → clarify_card 数据，前端渲染交互式问答表单
"""

import json
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.ai.agent.tools.base import ToolContext


class ClarifyQuestion(BaseModel):
    """单个澄清问题。"""
    id: str = Field(description="问题唯一标识")
    label: str = Field(description="问题标签，展示给用户")
    type: str = Field(default="text", description="输入类型: text / select")
    placeholder: str | None = Field(default=None, description="输入框占位文本")
    options: list[dict] | None = Field(default=None, description="选择项 [{id, label}]")
    required: bool = Field(default=True, description="是否必填")


class AskQuestionsArgs(BaseModel):
    """ask_question 工具参数。"""
    title: str = Field(description="问题集合的标题，例如'审核用例前需要确认以下信息'")
    questions: list[ClarifyQuestion] = Field(description="需要用户回答的问题列表")


# ═══════════════ 工具工厂 ═══════════════


def _make_ask_question_tool(ctx: ToolContext) -> BaseTool:
    """创建一个「向用户提问」的工具。

    返回 (content, artifact) 元组：
    - content: 给模型的简短文本提示
    - artifact: clarify_card 完整数据（前端渲染交互式表单）
    """

    async def run(title: str, questions: list[ClarifyQuestion]) -> tuple[str, dict]:
        qs = [
            {
                "id": q.id,
                "label": q.label,
                "type": q.type,
                "placeholder": q.placeholder or "",
                "options": q.options or [],
                "required": q.required,
            }
            for q in questions
        ]

        artifact = {
            "msg_type": "clarify_card",
            "content": title,
            "metadata": {"questions": qs},
        }
        content = f"已向用户提问：{title}。等待用户回答后再继续。"

        return (content, artifact)

    return StructuredTool.from_function(
        name="ask_question",
        description=(
            "向用户提问，收集确认信息。"
            "当以下场景使用：\n"
            "1. 用户意图模糊，需要确认项目/模块等关键信息\n"
            "2. 任务类操作前需要确认范围（例如审核全部还是选中）\n"
            "3. 任何需要用户做出选择后才能继续的场景\n"
            "不要在调用此工具的同时调用任务类工具（create_*），"
            "应等待用户回答后再调用任务工具。"
        ),
        coroutine=run,
        args_schema=AskQuestionsArgs,
        response_format="content_and_artifact",
    )


def build_clarify_tools(ctx: ToolContext) -> list[BaseTool]:
    """构建 clarify 类工具列表。"""
    return [_make_ask_question_tool(ctx)]
