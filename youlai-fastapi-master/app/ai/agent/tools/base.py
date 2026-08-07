"""工具基础设施 — ToolContext + 工具注册表。"""

from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ToolContext:
    """每次请求的工具上下文，注入到所有工具中。

    工具通过此上下文获取 db session、当前页面状态等信息，
    而不是通过全局变量，确保线程/协程安全。
    """

    db: AsyncSession
    session_id: int
    domain: str = "case"
    project_id: int | None = None
    suite_id: int | None = None
    page_type: str = ""
    context_json: dict[str, Any] = field(default_factory=dict)
    user_id: int = 0  # 操作人 ID，用于审计和权限控制


# 工具工厂类型
ToolFactory = Callable[["ToolContext"], Any]
