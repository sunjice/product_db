"""上下文构造器 — 为自由对话模式按域注入页面上下文。

每个 domain 可以注册一个 BaseContextBuilder，_freeform_chat 在指纹变化时
调用对应 builder 生成上下文文本块，注入到 LLM 的 SystemMessage 中。
"""

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession


class BaseContextBuilder(ABC):
    """上下文构造器基类 — 一个 domain 一个 builder。

    子类只需设置 domain 类属性，实现 build() 方法。
    build() 返回一段 Markdown 文本，将被拼接到 SystemMessage 末尾。
    """

    domain: str = ""

    @abstractmethod
    async def build(self, context_json: dict, db: AsyncSession) -> str:
        """根据 context_json 和数据库查询，生成上下文描述文本。

        Args:
            context_json: 前端注册的页面上下文 dict
            db: 数据库会话

        Returns:
            上下文文本块，如 "项目:XX | 模块:登录 | 用例35条"
        """
        ...


class ContextBuilderRegistry:
    """全局上下文构造器注册表 — 按域管理。"""

    def __init__(self):
        self._builders: dict[str, BaseContextBuilder] = {}

    def register(self, builder: BaseContextBuilder):
        if builder.domain in self._builders:
            raise ValueError(f"ContextBuilder for domain '{builder.domain}' 已注册")
        self._builders[builder.domain] = builder

    def get(self, domain: str) -> BaseContextBuilder | None:
        return self._builders.get(domain)


# 全局单例
context_builder_registry = ContextBuilderRegistry()
