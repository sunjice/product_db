/** AI 对话 — Chat 模块类型定义 */

// ═══════════════ 会话 ═══════════════

export interface ChatSession {
  id: number | null
  title: string
  domain: string
  context_json: Record<string, any> | null
  message_count: number
  is_pinned: number
  user_id: number | null
  create_time: string | null
  update_time: string | null
}

export interface SessionCreateForm {
  title?: string
  domain?: string
  context_json?: Record<string, any>
}

export interface SessionUpdateForm {
  title?: string
  is_pinned?: number
}

// ═══════════════ 消息 ═══════════════

export interface ChatMessage {
  id: number | null
  session_id: number | null
  role: 'user' | 'assistant' | 'system'
  msg_type: 'text' | 'action_card' | 'task_card' | 'draft_card' | 'clarify_card' | 'help_card' | 'confirm_card' | 'error'
  content: string
  metadata_json: Record<string, any> | null
  draft_id: number | null
  create_time: string | null
}

export interface MessageSendReq {
  content: string
  skill_name?: string
}

// ═══════════════ 草稿 ═══════════════

export interface ChatDraft {
  id: number | null
  session_id: number | null
  message_id: number | null
  draft_type: string
  title: string
  content_json: Record<string, any> | null
  status: 'pending' | 'confirmed' | 'applied' | 'discarded'
  confirmed_by: string | null
  confirmed_at: string | null
  create_time: string | null
}

export interface DraftConfirmReq {
  action: 'confirm' | 'discard'
  edited_content?: Record<string, any>
}

// ═══════════════ 上下文 ═══════════════

export interface ContextSetReq {
  domain?: string
  context_json: Record<string, any>
}

// ═══════════════ 技能 ═══════════════

export interface SkillInfo {
  name: string
  domain: string
  description: string
  mode: 'SYNC' | 'ASYNC'
  keywords: string[]
}

// ═══════════════ 任务确认 ═══════════════

export interface ConfirmCreateTaskReq {
  skill_name: string
  project_id: number
  suite_id: number
  case_ids?: number[] | null
  selected_option?: string | null
}

/** 更新卡片状态 */
export interface UpdateCardStatusReq {
  msg_type: string
  metadata: Record<string, any>
}

// ═══════════════ SSE 事件 ═══════════════

export interface SseEvent {
  event: string
  data: Record<string, any>
}
