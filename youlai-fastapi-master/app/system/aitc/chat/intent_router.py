"""意图路由器 — 一期基于关键词匹配 + 参数提取。

二期升级为 LangChain function calling (LLM 路由)。
"""

import re

from app.system.aitc.chat.skill_base import BaseSkill, SkillRegistry, skill_registry


class IntentRoute:
    """一条路由规则 — 匹配关键词后路由到指定 Skill。"""

    def __init__(self, skill: BaseSkill, priority: int = 0):
        self.skill = skill
        self.priority = priority


class IntentRouter:
    """关键词匹配意图路由器。"""

    def __init__(self, registry: SkillRegistry = skill_registry):
        self.registry = registry

    def match(self, message: str, domain: str = "case") -> BaseSkill | None:
        """根据用户消息匹配最合适的 Skill。

        匹配策略：
        1. 按域过滤 Skill
        2. 关键词匹配（任一命中即匹配）
        3. 多个命中时取优先级最高（关键词命中数最多）的
        """
        skills = self.registry.list_by_domain(domain)
        if not skills:
            return None

        best_skill = None
        best_score = 0

        for skill in skills:
            score = self._score(skill, message)
            if score > best_score:
                best_score = score
                best_skill = skill

        # 如果没有任何关键词匹配，检查是否在讨论/继续对话
        if best_score == 0:
            return None  # 退回给 LLM 做自由对话

        return best_skill

    def _score(self, skill: BaseSkill, message: str) -> int:
        """计算 Skill 对消息的匹配度分数。"""
        msg_lower = message.lower()
        score = 0
        for kw in skill.keywords:
            if kw.lower() in msg_lower:
                score += 1
        return score

    def extract_params(self, skill: BaseSkill, message: str) -> dict:
        """从消息中提取参数。"""
        params = {}

        # 提取 case_id (数字 + 用例关键词上下文)
        m = re.search(r'(?:用例|案例|TC|tc).*?(\d+)', message)
        if m:
            params["case_id"] = int(m.group(1))

        # 提取 project_id
        m = re.search(r'(?:项目|project).*?(\d+)', message)
        if m:
            params["project_id"] = int(m.group(1))

        # 提取 suite_id
        m = re.search(r'(?:套件|模块|suite).*?(\d+)', message)
        if m:
            params["suite_id"] = int(m.group(1))

        # 字段提示
        if "前置" in message or "precondition" in message.lower():
            params["field_hint"] = "preconditions"
        elif "数据" in message or "test_data" in message.lower():
            params["field_hint"] = "test_data"
        elif "topo" in message.lower() or "拓扑" in message:
            params["field_hint"] = "topo"

        return params


# 全局单例
intent_router = IntentRouter()
