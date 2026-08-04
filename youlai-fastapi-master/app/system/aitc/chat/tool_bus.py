"""跨域工具总线 — ToolBus。

Skill 通过 ToolBus 调用其他域的公开工具，例如:
    result = await tool_bus.call("bug.bugs_by_case", case_id=123)

工具用 @tool(public=True) 装饰器标识为公开跨域工具。
"""

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolDef:
    """工具定义。"""
    name: str           # 完整名 "domain.tool_name"
    domain: str         # 域
    tool_name: str      # 工具名（不含域前缀）
    func: Callable      # 异步函数
    description: str = ""
    public: bool = False  # 是否允许跨域调用


class ToolBus:
    """跨域工具总线。

    每个域的工具文件将其工具注册到 ToolBus，
    Skill 通过 tool_bus.call("domain.tool_name", ...) 调用公开工具。
    """

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool_def: ToolDef):
        if tool_def.name in self._tools:
            raise ValueError(f"Tool '{tool_def.name}' 已注册")
        self._tools[tool_def.name] = tool_def

    def get(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    async def call(self, name: str, **kwargs) -> Any:
        """跨域调用公开工具。"""
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Tool '{name}' 未注册")
        if not tool.public:
            raise PermissionError(f"Tool '{name}' 不是公开工具，不可跨域调用")
        return await tool.func(**kwargs)

    def list_public(self) -> list[ToolDef]:
        return [t for t in self._tools.values() if t.public]

    def list_by_domain(self, domain: str) -> list[ToolDef]:
        return [t for t in self._tools.values() if t.domain == domain]


# 全局单例
tool_bus = ToolBus()
