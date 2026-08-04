"""用例域插件 — 用例相关的 Skill 和 Tool。"""

# 导入以触发远程注册
from app.system.aitc.chat.domains.case import tools  # noqa: F401
from app.system.aitc.chat.domains.case import core_select_skill  # noqa: F401
from app.system.aitc.chat.domains.case import case_review_skill  # noqa: F401
from app.system.aitc.chat.domains.case import script_gen_skill  # noqa: F401
from app.system.aitc.chat.domains.case import field_complete_skill  # noqa: F401
from app.system.aitc.chat.domains.case import steps_complete_skill  # noqa: F401
from app.system.aitc.chat.domains.case import case_design_skill  # noqa: F401
from app.system.aitc.chat.domains.case import contexts  # noqa: F401

# 注册公开工具到 ToolBus
tools.register_case_tools()
