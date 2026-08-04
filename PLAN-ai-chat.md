# AI 对话系统 — 详细实施计划

## 一、架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue 3)                          │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Sidebar  │  │ Chat Messages│  │ Draft/Detail     │  │
│  │ 会话列表  │  │ 消息列表     │  │ Panel 产出面板   │  │
│  └──────────┘  └──────────────┘  └──────────────────┘  │
│                      │ HTTP/SSE                         │
└──────────────────────┼──────────────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────────────┐
│               后端 (FastAPI + LangChain)                  │
│                      │                                   │
│  ┌───────────────────▼──────────────────────────────┐   │
│  │           Chat Orchestrator (编排层)              │   │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │   │
│  │  │ Intent   │  │ LangChain │  │ Session      │  │   │
│  │  │ Router   │  │ Tool Call │  │ Manager      │  │   │
│  │  └──────────┘  └───────────┘  └──────────────┘  │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
│  ┌──────────────────────▼───────────────────────────┐   │
│  │              Skill Layer (技能层)                  │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │   │
│  │  │core_   │ │case_   │ │script_ │ │field_  │ ... │   │
│  │  │select  │ │review  │ │gen     │ │complete│    │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘    │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
│  ┌──────────────────────▼───────────────────────────┐   │
│  │               Tool Layer (工具层)                  │   │
│  │  ┌────────────────┐  ┌────────────────────────┐  │   │
│  │  │ Domain Tools   │  │    ToolBus (跨域)       │  │   │
│  │  │ case/tools.py  │  │  tool_bus.py            │  │   │
│  │  └────────────────┘  └────────────────────────┘  │   │
│  └──────────────────────────────────────────────────┘   │
│                         │                                │
│  ┌──────────────────────▼───────────────────────────┐   │
│  │              Storage Layer (存储层)                │   │
│  │  MySQL: chat_sessions, chat_messages,             │   │
│  │         chat_drafts, ai_usage_logs                │   │
│  │  Milvus: 向量检索 (二期)                           │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### 核心设计原则

1. **Skill/Tool 分层** — Skill 面向用户意图，Tool 面向数据操作；Skill 调用 Tool 完成工作
2. **域插件隔离** — 每个业务域（case/bug/analytics）独立目录，互不干扰
3. **LangChain 仅编排** — LLM 调用 + Tool calling 由 LangChain 负责；Skill/Tool 内部是纯 Python
4. **执行双态** — SYNC（对话内同步，产出 Draft）和 ASYNC（批量异步，委托 TaskEngine）
5. **安全确认** — AI 产出必须人工确认后才入库

---

## 二、数据库设计（4 张新表）

### 2.1 chat_sessions — 对话会话

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 主键 |
| title | VARCHAR(200) | 会话标题（自动生成或用户编辑） |
| domain | VARCHAR(50) | 会话域 (case/bug/analytics)，默认 case |
| context_json | JSON | 页面上下文快照 (project_id, suite_id, filters 等) |
| message_count | INT | 消息数量 |
| is_pinned | TINYINT | 是否置顶 |
| user_id | INT FK | 所属用户 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |
| is_deleted | TINYINT | 软删除 |

### 2.2 chat_messages — 消息记录

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 主键 |
| session_id | BIGINT FK | 所属会话 |
| role | VARCHAR(20) | user / assistant / system |
| msg_type | VARCHAR(30) | text / action_card / task_card / draft_card / clarify_card / help_card |
| content | TEXT | 消息正文（Markdown） |
| metadata_json | JSON | 附加数据 (skill_name, tool_calls, tokens, execution_time 等) |
| draft_id | BIGINT | 关联的 Draft（如有产出） |
| created_at | DATETIME | 创建时间 |

### 2.3 chat_drafts — AI 产出草稿

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 主键 |
| session_id | BIGINT FK | 所属会话 |
| message_id | BIGINT FK | 关联消息 |
| draft_type | VARCHAR(30) | core_select / case_review / script_gen / field_complete / steps_complete / case_design |
| title | VARCHAR(200) | 草稿标题 |
| content_json | JSON | 草稿内容 |
| status | VARCHAR(20) | pending / confirmed / applied / discarded |
| confirmed_by | INT | 确认人 |
| confirmed_at | DATETIME | 确认时间 |
| created_at | DATETIME | 创建时间 |

### 2.4 ai_usage_logs — Token 用量统计

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 主键 |
| module | VARCHAR(50) | chat / task_engine |
| session_id | BIGINT | 会话 ID |
| task_id | BIGINT | 任务 ID |
| model | VARCHAR(100) | 模型名称 |
| prompt_tokens | INT | 输入 token |
| completion_tokens | INT | 输出 token |
| total_tokens | INT | 总 token |
| duration_ms | INT | 耗时(毫秒) |
| created_at | DATETIME | 创建时间 |

---

## 三、消息协议

| msg_type | 说明 | 前端渲染 |
|----------|------|----------|
| text | 普通文本（Markdown） | Markdown 渲染器 |
| action_card | 操作卡片（Skill 执行结果摘要） | 卡片组件 + 按钮 |
| task_card | 异步任务卡片 | 进度条 + 跳转链接 |
| draft_card | 草稿产出卡片 | 可折叠预览 + 确认/拒绝按钮 |
| clarify_card | 澄清卡片（AI 需要更多信息） | 选项按钮 |
| help_card | 帮助卡片（展示可用技能） | 技能列表 |

---

## 四、后端目录结构

```
app/system/aitc/chat/
├── __init__.py
├── models.py              # chat_sessions, chat_messages, chat_drafts, ai_usage_logs
├── schemas.py             # Pydantic 请求/响应 Schema
├── service.py             # 会话/消息/草稿 CRUD
├── router.py              # /api/v1/aitc/chat/* 路由
├── orchestrator.py        # LangChain 编排器（Tool calling + 路由）
├── session_manager.py     # 会话上下文管理
├── skill_base.py          # Skill 基类 + 注册表
├── tool_bus.py            # 跨域工具总线
├── intent_router.py       # 意图路由（一期规则匹配，二期 LLM）
├── usage_logger.py        # Token 用量记录（LangChain Callback）
└── domains/
    └── case/
        ├── __init__.py
        ├── tools.py               # case 域工具（查用例/获取详情/统计等）
        ├── core_select_skill.py   # 挑选核心用例
        ├── case_review_skill.py   # 审核用例
        ├── script_gen_skill.py    # 生成测试脚本
        ├── field_complete_skill.py # 补全字段
        ├── steps_complete_skill.py # 补写测试步骤
        └── case_design_skill.py   # 设计测试用例
```

---

## 五、前端目录结构

```
src/views/aitc/chat/
├── index.vue                   # 主页面（三栏布局）
├── components/
│   ├── ChatSidebar.vue         # 左侧会话列表
│   ├── ChatHeader.vue          # 顶部标题栏
│   ├── ChatMessageList.vue     # 消息列表容器
│   ├── ChatMessage.vue         # 单条消息渲染
│   ├── ChatInput.vue           # 底部输入区
│   ├── DraftPanel.vue          # 右侧草稿详情面板
│   ├── cards/
│   │   ├── TextCard.vue        # text 类型
│   │   ├── ActionCard.vue      # action_card 类型
│   │   ├── TaskCard.vue        # task_card 类型
│   │   ├── DraftCard.vue       # draft_card 类型
│   │   ├── ClarifyCard.vue     # clarify_card 类型
│   │   └── HelpCard.vue        # help_card 类型
│   └── SkillPicker.vue         # 技能选择器
├── composables/
│   └── useChat.ts              # 聊天核心逻辑
└── types.ts                    # 前端类型定义

src/api/aitc/chat/
├── index.ts                    # Chat API 封装
└── types.ts                    # API 类型
```

---

## 六、API 设计

### 会话管理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/aitc/chat/sessions | 创建会话 |
| GET | /api/v1/aitc/chat/sessions | 会话列表 |
| GET | /api/v1/aitc/chat/sessions/{id} | 会话详情 |
| PUT | /api/v1/aitc/chat/sessions/{id} | 更新（标题/置顶） |
| DELETE | /api/v1/aitc/chat/sessions/{id} | 删除会话 |

### 消息
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/aitc/chat/sessions/{id}/messages | 消息列表 |
| POST | /api/v1/aitc/chat/sessions/{id}/messages | 发送消息 (SSE 流式响应) |

### 草稿
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/aitc/chat/drafts/{id} | 草稿详情 |
| POST | /api/v1/aitc/chat/drafts/{id}/confirm | 确认草稿（写入正式表） |
| POST | /api/v1/aitc/chat/drafts/{id}/discard | 丢弃草稿 |

### 上下文
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/aitc/chat/context | 设置会话上下文（页面切换时） |
| GET | /api/v1/aitc/chat/skills | 获取可用技能列表 |

---

## 七、Skill 基类协议

```python
class BaseSkill:
    name: str              # 技能标识 (core_select, case_review, ...)
    description: str       # 技能描述（给 LLM 看）
    domain: str            # 所属域 (case, bug, ...)
    mode: str              # SYNC / ASYNC
    keywords: list[str]    # 触发关键词
    
    def parameters_schema(self) -> dict:
        """返回 OpenAI function calling 格式的参数定义"""
        
    async def resolve(self, message: str, context: dict) -> dict:
        """解析用户消息，提取参数（一期用规则，二期用 LLM）"""
        
    async def execute(self, params: dict, context: dict) -> SkillResult:
        """执行技能，返回结果"""
```

---

## 八、一期 Skill 清单（case 域）

| 序号 | Skill | 模式 | 触发词 | 说明 |
|------|-------|------|--------|------|
| 1 | core_select | ASYNC | 挑选核心/重要用例/核心用例 | 从项目中挑选核心用例 |
| 2 | case_review | ASYNC | 审核/检查/评审用例 | 审核用例质量 |
| 3 | script_gen | ASYNC | 生成脚本/自动化脚本 | 为用例生成测试脚本 |
| 4 | field_complete | SYNC | 补全字段/完善信息 | AI 补全用例字段 |
| 5 | steps_complete | SYNC | 补写步骤/补充步骤 | 根据标题/目的补写步骤 |
| 6 | case_design | SYNC | 设计用例/新增用例/写用例 | 根据需求设计测试用例 |

---

## 九、实施顺序（Phase 1）

| 步骤 | 内容 | 文件 |
|------|------|------|
| 1 | 数据库模型 | `chat/models.py` |
| 2 | Pydantic Schema | `chat/schemas.py` |
| 3 | 注册模型 + Alembic 迁移 | `registry.py` + migration |
| 4 | Skill 基类 + 注册表 + Tool Bus | `chat/skill_base.py`, `chat/tool_bus.py` |
| 5 | case 域 Tools | `chat/domains/case/tools.py` |
| 6 | 6 个 case Skill 文件 | `chat/domains/case/*_skill.py` |
| 7 | 意图路由器 | `chat/intent_router.py` |
| 8 | 用量记录器 | `chat/usage_logger.py` |
| 9 | Orchestrator（LangChain 编排） | `chat/orchestrator.py` |
| 10 | 会话管理器 | `chat/session_manager.py` |
| 11 | Service 层 | `chat/service.py` |
| 12 | Router + SSE | `chat/router.py` |
| 13 | 注册路由 | `main.py` |
| 14 | 前端 API 层 | `src/api/aitc/chat/` |
| 15 | 前端 Chat 页面 + 组件 | `src/views/aitc/chat/` |
| 16 | 前端路由注册 | `src/router/index.ts` |

---

## 十、二期/三期规划

| 期数 | 内容 |
|------|------|
| 二期 | bug 域插件 + Milvus 向量检索 + LLM 意图路由 |
| 三期 | LangGraph 多步 Agent + analytics 域 (Text-to-SQL) |

---

## 十一、关键设计决策

1. **复用现有 AiClient** — Skill 的 ASYNC 模式委托给现有 `TaskEngine`/`AiClient`
2. **SYNC 模式新建 AI 调用** — 轻量同步 Skill 直接创建 LLM 调用，不走 TaskEngine
3. **会话不隔离** — 跨页面共享会话列表，通过 context 切换页面上下文
4. **一期规则路由** — 关键词匹配 + 参数正则提取，二期升级为 LangChain function calling
5. **SSE 流式** — 消息回应用 SSE 推送，前端逐字渲染
