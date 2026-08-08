"""Chat Orchestrator — 对话编排器。

使用 LangChain 进行 LLM 调用和 Tool calling 编排。
一期：关键词路由 + 简单 LLM 调用
二期（当前）：LangGraph Agent 模式（用例域，可通过 AI_AGENT_MODE_ENABLED 开关控制）
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, AsyncGenerator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.ai.chat.intent_router import intent_router
from app.ai.agent.skills.base import skill_registry, SkillResult
from app.ai.chat.session_manager import SessionContext
from app.ai.chat.context_builder import context_builder_registry
from app.ai.chat.usage_logger import TokenMeter, LangChainTokenCallback
from app.ai.llm_log.writer import LlmLogWriter, make_trace_id
from app.ai.config import ai_settings


# ── prompt 模板缓存在模块级（只读一次磁盘） ──
_AGENT_PROMPT_TEMPLATE: str | None = None


def _get_agent_prompt_template() -> str:
    """加载 agent prompt 模板（模块级缓存，进程生命周期内只读一次磁盘）。"""
    global _AGENT_PROMPT_TEMPLATE
    if _AGENT_PROMPT_TEMPLATE is None:
        prompt_path = Path(__file__).parent.parent / "agent" / "prompts" / "agent_case.txt"
        try:
            _AGENT_PROMPT_TEMPLATE = prompt_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            _AGENT_PROMPT_TEMPLATE = SYSTEM_PROMPT
    return _AGENT_PROMPT_TEMPLATE


# 系统提示词 — 自由对话模式
SYSTEM_PROMPT = """你是测试部的 AI 助手，专注于帮助测试工程师管理测试用例。

## 你的能力
你可以帮助用户：
1. **挑选核心用例** — 从项目用例中智能挑选最核心的测试用例
2. **审核用例质量** — 检查用例的完整性、规范性、可执行性
3. **生成测试脚本** — 为用例自动生成 pytest 自动化测试脚本
4. **补全用例字段** — 根据标题和测试目的，补全前置条件、测试数据等
5. **补写测试步骤** — 补写详细的测试步骤和预期结果
6. **设计测试用例** — 根据需求描述，从零设计测试用例

## 交互原则
- 回复简洁专业，优先引导用户使用具体技能
- 需要项目/用例信息时，优先使用 [当前页面上下文] 中已提供的数据；如上下文不足，再主动询问
- 涉及数据修改时，先生成草稿等用户确认
- 数学计算、代码片段使用 Markdown 格式
"""


class ChatOrchestrator:
    """对话编排器 — 负责意图识别 → Skill 调度 → LLM 响应编排。"""

    async def process_message(
        self,
        message: str,
        context: SessionContext,
        history: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """处理用户消息，流式返回 SSE 事件。

        处理流程:
        1. [Agent 模式] domain=case 且开关开启 → LangGraph agent 循环
        2. 意图路由 → 匹配 Skill
        3. Skill.execute() → 拿到 SkillResult
        4. 根据 SkillResult 构造响应消息
        5. SSE 推送

        context.working 中需包含:
        - db_session: AsyncSession
        - ai_config: AiConfigSnapshot 实例
        """

        # ── Agent 模式分流 ──
        if ai_settings.AI_AGENT_MODE_ENABLED and context.domain == "case":
            async for event in self._agent_chat(message, context, history):
                yield event
            return

        # ── Skill 路由模式 ──
        async for event in self._skill_chat(message, context, history):
            yield event

    # ═══════════════ Skill 路由模式 ═══════════════

    async def _skill_chat(
        self,
        message: str,
        context: SessionContext,
        history: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Skill 路由模式 — 意图路由 → Skill.execute() → SSE 响应。"""
        skill = intent_router.match(message, domain=context.domain)

        if skill is None:
            # 无匹配 → 自由对话模式
            async for event in self._freeform_chat(message, context, history):
                yield event
            return

        # 提取参数，合并上下文
        params = intent_router.extract_params(skill, message)
        params["project_id"] = params.get("project_id") or context.project_id
        params["suite_id"] = params.get("suite_id") or context.suite_id

        # 页面准入检查
        current_page = context.context_json.get("current_page", "")
        if skill.required_page and current_page != skill.required_page:
            result = SkillResult(
                success=False,
                msg_type="clarify_card",
                content="该功能需要在「用例管理」页面使用。请先切换到用例管理页面，再进行此操作。",
            )
        else:
            result = await skill.execute(params, {
                "session_id": context.session_id,
                "project_id": context.project_id,
                "suite_id": context.suite_id,
                "domain": context.domain,
                "context_json": context.context_json,
                "db_session": context.get_working("db_session"),
            })

        # 构造 SSE 事件序列
        yield self._sse_event("skill_start", {
            "skill_name": skill.name,
            "mode": skill.mode.value,
        })

        yield self._sse_event("message", {
            "role": "assistant",
            "msg_type": result.msg_type,
            "content": result.content,
            "skill_name": skill.name,
            "success": result.success,
            "draft_type": result.draft_type,
            "draft_data": result.draft_data,
            "metadata": result.metadata,
        })

        if result.error and not result.content:
            yield self._sse_event("error", {"message": result.error})

        yield self._sse_event("done", {})

    # ═══════════════ Agent 模式（LangGraph） ═══════════════

    async def _agent_chat(
        self,
        message: str,
        context: SessionContext,
        history: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Agent 模式 — 走 LangGraph agent 循环（模型自主选择工具）。"""
        from app.ai.agent.graph.runner import agent_runner
        from app.ai.agent.tools.base import ToolContext
        from app.ai.agent.tools.case import build_case_tools, generate_tools_prompt

        ai_config = context.get_working("ai_config")
        db = context.get_working("db_session")

        if ai_config is None:
            yield self._sse_event("message", {
                "role": "assistant",
                "msg_type": "text",
                "content": "未配置 AI 服务，请在 .env 中设置 AI_API_KEY 等参数。",
            })
            yield self._sse_event("done", {})
            return

        # ── 构建工具 ──
        tool_ctx = ToolContext(
            db=db,
            session_id=context.session_id,
            domain=context.domain,
            project_id=context.project_id,
            suite_id=context.suite_id,
            page_type=context.context_json.get("current_page", ""),
            context_json=context.context_json,
            user_id=context.context_json.get("user_id") or 0,
        )
        tools = build_case_tools(tool_ctx)

        # ── 加载 system prompt + 动态注入工具描述 ──
        system_prompt = self._load_agent_prompt(context)
        system_prompt += "\n\n" + generate_tools_prompt(tools)

        # ── 执行 agent 图 ──
        async for sse in agent_runner.run(
            message=message,
            context=context,
            history=history,
            tools=tools,
            system_prompt=system_prompt,
            ai_config=ai_config,
        ):
            yield sse

    @staticmethod
    def _load_agent_prompt(context: SessionContext) -> str:
        """构建 agent system prompt（模板缓存 + 每请求注入页面上下文）。"""
        prompt = _get_agent_prompt_template()

        # 注入页面上下文（有 ID 即注入，名称可选）
        project_id = context.project_id
        suite_id = context.suite_id
        project_name = context.context_json.get("project_name", "")
        suite_name = context.context_json.get("suite_name", "")
        selected_case_ids = context.context_json.get("selected_case_ids", [])
        current_case_id = context.context_json.get("current_case_id")

        context_lines = ["\n\n## 当前页面上下文"]
        if project_id:
            name_part = f" {project_name}" if project_name else ""
            context_lines.append(f"- 项目：{project_id}{name_part}")
        if suite_id:
            name_part = f" {suite_name}" if suite_name else ""
            context_lines.append(f"- 模块：{suite_id}{name_part}")
        if current_case_id:
            context_lines.append(f"- 当前查看的用例 ID：{current_case_id}")
        if selected_case_ids:
            ids_str = ", ".join(str(i) for i in selected_case_ids[:20])
            suffix = f" 等共 {len(selected_case_ids)} 条" if len(selected_case_ids) > 20 else f"（共 {len(selected_case_ids)} 条）"
            context_lines.append(f"- 已选中的用例 ID：{ids_str}{suffix}")

        if len(context_lines) > 1:
            prompt += "\n".join(context_lines)
            prompt += "\n\n注意：如果用户有选中用例（selected_case_ids），可优先作为操作对象。但如果用户明确要求对整个模块操作，以用户意图为准。"

        return prompt

    # ═══════════════ 自由对话模式 ═══════════════

    async def _freeform_chat(
        self,
        message: str,
        context: SessionContext,
        history: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """自由对话模式 — 走 LangChain LLM 流式对话。每次调用自动写入 ai_llm_logs。"""
        ai_config = context.get_working("ai_config")
        if ai_config is None:
            yield self._sse_event("message", {
                "role": "assistant",
                "msg_type": "text",
                "content": "未配置 AI 服务，请在 .env 中设置 AI_API_KEY 等参数。",
            })
            yield self._sse_event("done", {})
            return

        meter = TokenMeter(model=ai_config.model or "unknown")
        trace_id = context.get_working("trace_id") or make_trace_id("chat", context.session_id)

        t_start = time.time()
        messages_raw: list[dict] = []
        try:
            # 构建消息列表
            messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]

            # 上下文注入：指纹变化时注入页面上下文
            curr_fingerprint = self._compute_fingerprint(context.domain, context.context_json)
            if curr_fingerprint and curr_fingerprint != context.last_context_fingerprint:
                context_block = await self._build_context_block(context)
                if context_block:
                    messages.append(SystemMessage(content=context_block))
                context.last_context_fingerprint = curr_fingerprint

            if history:
                for h in history[-20:]:
                    if h.get("role") == "user":
                        messages.append(HumanMessage(content=h.get("content", "")))
                    elif h.get("role") == "assistant":
                        messages.append(AIMessage(content=h.get("content", "")))
            messages.append(HumanMessage(content=message))

            # 序列化 messages 用于日志
            messages_raw = _serialize_messages(messages)

            llm = ChatOpenAI(
                model=ai_config.model,
                api_key=ai_config.api_key,
                base_url=ai_config.api_base,
                temperature=ai_config.temperature or 0.3,
                max_tokens=ai_config.max_tokens or 4096,
                streaming=True,
            )

            callback = LangChainTokenCallback(meter)
            full_text = ""

            async for chunk in llm.astream(messages, config={"callbacks": [callback]}):
                if chunk.content:
                    full_text += chunk.content
                    yield self._sse_event("chunk", {"content": chunk.content})

            duration_ms = int((time.time() - t_start) * 1000)

            # ── 写入 LLM 调用日志 ──
            await LlmLogWriter.write(
                trace_id=trace_id,
                span_seq=0,
                attempt=0,
                module="chat",
                action="freeform_chat",
                session_id=context.session_id,
                model=ai_config.model or "unknown",
                status="success",
                messages=messages_raw,
                response_raw=full_text,
                prompt_tokens=meter.prompt_tokens,
                completion_tokens=meter.completion_tokens,
                duration_ms=duration_ms,
            )

            # 最终完整消息
            yield self._sse_event("message", {
                "role": "assistant",
                "msg_type": "text",
                "content": full_text,
                "metadata": {
                    "tokens": {
                        "prompt": meter.prompt_tokens,
                        "completion": meter.completion_tokens,
                        "total": meter.total_tokens,
                    },
                    "duration_ms": duration_ms,
                },
            })

            yield self._sse_event("done", {})

        except Exception as e:
            duration_ms = int((time.time() - t_start) * 1000)
            # ── 写入失败日志 ──
            await LlmLogWriter.write(
                trace_id=trace_id,
                span_seq=0,
                attempt=0,
                module="chat",
                action="freeform_chat",
                session_id=context.session_id,
                model=ai_config.model if ai_config else "unknown",
                status="error",
                error_msg=str(e)[:500],
                messages=messages_raw if messages_raw else None,
                prompt_tokens=meter.prompt_tokens,
                completion_tokens=meter.completion_tokens,
                duration_ms=duration_ms,
            )
            yield self._sse_event("error", {"message": str(e)})
            yield self._sse_event("done", {})

    @staticmethod
    def _compute_fingerprint(domain: str, context_json: dict) -> str:
        """计算上下文字段指纹，用于判断是否需要重新注入。"""
        if not context_json:
            return ""
        raw = f"{domain}:{json.dumps(context_json, sort_keys=True, default=str)}"
        return hashlib.md5(raw.encode()).hexdigest()

    async def _build_context_block(self, context: SessionContext) -> str:
        """按 domain 调用对应的 ContextBuilder 生成上下文文本块。"""
        builder = context_builder_registry.get(context.domain)
        if builder is None:
            return ""
        db = context.get_working("db_session")
        if db is None:
            return ""
        return await builder.build(context.context_json, db)

    @staticmethod
    def _sse_event(event: str, data: dict) -> str:
        """构造 SSE 事件字符串。"""
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# 全局单例
chat_orchestrator = ChatOrchestrator()


def _serialize_messages(messages: list[BaseMessage]) -> list[dict]:
    """将 LangChain BaseMessage 列表序列化为普通 dict 列表，用于存储日志。"""
    result = []
    for m in messages:
        role_map = {
            "system": "system", "human": "user", "ai": "assistant",
            "tool": "tool", "function": "function",
        }
        role = role_map.get(m.type, m.type)
        entry = {"role": role, "content": m.content}
        if hasattr(m, "tool_calls") and m.tool_calls:
            entry["tool_calls"] = [tc.model_dump() if hasattr(tc, "model_dump") else str(tc) for tc in m.tool_calls]
        if hasattr(m, "name") and m.name:
            entry["name"] = m.name
        result.append(entry)
    return result
