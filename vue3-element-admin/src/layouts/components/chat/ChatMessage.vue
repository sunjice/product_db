<template>
  <div class="chat-message" :class="msg.role">
    <!-- 用户消息：右侧气泡 -->
    <template v-if="msg.role === 'user'">
      <div class="msg-bubble user-bubble">
        <div class="msg-text">{{ msg.content }}</div>
        <div class="msg-time">{{ formatTime(msg.create_time) }}</div>
      </div>
      <div class="msg-avatar">
        <el-avatar :size="26"><el-icon><User /></el-icon></el-avatar>
      </div>
    </template>

    <!-- AI 消息：左侧气泡 -->
    <template v-else>
      <div class="msg-avatar">
        <el-avatar :size="26" style="background: var(--el-color-primary)">
          <el-icon><ChatDotRound /></el-icon>
        </el-avatar>
      </div>
      <div class="msg-bubble ai-bubble">
        <!-- 文本 -->
        <div v-if="msg.msg_type === 'text'" class="msg-text" v-html="renderedContent" />

        <!-- 操作卡片（核心挑选/审核/脚本生成结果） -->
        <div v-else-if="msg.msg_type === 'action_card'" class="msg-card">
          <div class="msg-text" v-html="renderedContent" />
          <div v-if="msg.metadata_json?.skill_name" class="card-meta">
            技能：{{ msg.metadata_json.skill_name }}
          </div>
          <div v-if="msg.draft_id" class="card-actions">
            <el-button size="small" type="primary" @click="$emit('viewDraft', msg.draft_id!)">
              查看详情
            </el-button>
          </div>
        </div>

        <!-- 草稿卡片 -->
        <div v-else-if="msg.msg_type === 'draft_card'" class="msg-card">
          <div class="msg-text" v-html="renderedContent" />
          <div v-if="msg.metadata_json?.skill_name" class="card-meta">
            草稿类型：{{ msg.metadata_json.skill_name }}
          </div>
          <div v-if="!msg.metadata_json?.draft_status" class="card-actions">
            <el-button size="small" type="primary" @click="$emit('viewDraft', msg.draft_id!)">
              查看草稿
            </el-button>
            <el-button size="small" type="danger" plain @click="$emit('confirmDraft', 'discard')">
              丢弃
            </el-button>
            <el-button size="small" type="success" @click="$emit('confirmDraft', 'confirm')">
              确认采纳
            </el-button>
          </div>
          <div v-else class="card-result" :class="msg.metadata_json.draft_status === 'confirm' ? 'success' : 'muted'">
            {{ msg.metadata_json.draft_status === 'confirm' ? '已采纳' : '已丢弃' }}
          </div>
        </div>

        <!-- 任务卡片 -->
        <div v-else-if="msg.msg_type === 'task_card'" class="msg-card">
          <div class="msg-text" v-html="renderedContent" />
          <div class="card-actions">
            <el-button size="small" type="primary" @click="goTaskDetail">
              {{ taskButtonText }}
            </el-button>
          </div>
        </div>

        <!-- 澄清卡片（LLM 向用户提问收集信息） -->
        <div v-else-if="msg.msg_type === 'clarify_card'" class="msg-card">
          <div class="msg-text" v-html="renderedContent" />
          <div class="clarify-form">
            <div v-for="q in clarifyQuestions" :key="q.id" class="clarify-field">
              <label class="clarify-label">
                {{ q.label }}
                <span v-if="q.required" class="clarify-required">*</span>
              </label>
              <el-input
                v-if="q.type === 'text'"
                v-model="clarifyAnswers[q.id]"
                :placeholder="q.placeholder || '请输入'"
                size="small"
              />
              <el-select
                v-else-if="q.type === 'select'"
                v-model="clarifyAnswers[q.id]"
                :placeholder="q.placeholder || '请选择'"
                size="small"
                class="clarify-select"
              >
                <el-option
                  v-for="opt in (q.options || [])"
                  :key="opt.id"
                  :label="opt.label"
                  :value="opt.id"
                />
              </el-select>
            </div>
          </div>
          <div v-if="!clarifySubmitted" class="card-actions">
            <el-button size="small" type="primary" :loading="clarifySubmitting" @click="handleClarifySubmit">
              提交
            </el-button>
          </div>
          <div v-else class="card-result muted">
            {{ clarifySubmitText || '已提交' }}
          </div>
        </div>

        <!-- 确认卡片（任务创建前确认，支持多选项） -->
        <div v-else-if="msg.msg_type === 'confirm_card'" class="msg-card">
          <div class="msg-text" v-html="renderedContent" />

          <!-- 多选项（如审核范围选择） -->
          <div v-if="confirmOptions.length > 0 && confirmState === 'idle'" class="confirm-options">
            <div
              v-for="opt in confirmOptions"
              :key="opt.id"
              class="confirm-option"
              :class="{ selected: selectedOptionId === opt.id }"
              @click="selectedOptionId = opt.id"
            >
              <span class="option-radio">
                <span v-if="selectedOptionId === opt.id" class="radio-dot" />
              </span>
              <span class="option-label">{{ opt.label }}</span>
              <span v-if="opt.description" class="option-desc">{{ opt.description }}</span>
            </div>
          </div>

          <div v-if="confirmState === 'idle'" class="card-actions">
            <el-button size="small" type="primary" :loading="confirming" @click="handleConfirm">
              确认创建
            </el-button>
            <el-button size="small" plain @click="handleCancel">
              取消
            </el-button>
          </div>
          <div v-else-if="confirmState === 'confirmed'" class="card-result success">
            任务已创建
          </div>
          <div v-else class="card-result muted">
            已取消
          </div>
        </div>

        <!-- 其他类型直接渲染文本 -->
        <div v-else class="msg-text" v-html="renderedContent" />

        <!-- Agent 工具调用记录 -->
        <!-- <div v-if="toolNames.length" class="msg-tool-steps">
          <el-icon><Tools /></el-icon>
          <span>已调用：{{ toolNames.join("、") }}</span>
        </div> -->

        <div class="msg-time">{{ formatTime(msg.create_time) }}</div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import { useRouter } from "vue-router"
import { User, ChatDotRound, Tools } from "@element-plus/icons-vue"
import { renderSimpleMd, formatTimeHM } from "./utils"
import type { ChatMessage } from "@/api/chat/types"

const props = defineProps<{
  msg: ChatMessage
}>()

const emit = defineEmits<{
  viewDraft: [id: number]
  confirmDraft: [action: string]
  confirmTask: [metadata: Record<string, any>]
  cancelTask: [metadata: Record<string, any>]
  submitClarify: [text: string]
}>()

const router = useRouter()
const confirming = ref(false)

// ── 澄清卡片（clarify_card）逻辑 ──

interface ClarifyQuestion {
  id: string
  label: string
  type: string
  placeholder: string
  options: { id: string; label: string }[]
  required: boolean
}

const clarifyQuestions = computed<ClarifyQuestion[]>(() => {
  return props.msg.metadata_json?.questions || []
})

const clarifyAnswers = ref<Record<string, string>>({})
const clarifySubmitted = ref(false)
const clarifySubmitting = ref(false)
const clarifySubmitText = ref("")

function handleClarifySubmit() {
  // 收集答案，格式化为文本发送给 LLM
  const qs = clarifyQuestions.value
  const answers = clarifyAnswers.value
  const lines = qs.map((q) => {
    const a = answers[q.id] || "（未填写）"
    return `- ${q.label}：${a}`
  })
  const text = "以下是我的回答：\n" + lines.join("\n")
  clarifySubmitText.value = "已提交"
  clarifySubmitted.value = true
  emit("submitClarify", text)
}

/** 确认卡片中的多选项（如审核范围选择） */
interface ConfirmOption {
  id: string
  label: string
  description?: string
}

const selectedOptionId = ref("")

const confirmOptions = computed<ConfirmOption[]>(() => {
  const raw = props.msg.metadata_json?.options
  if (Array.isArray(raw) && raw.length > 0) {
    // 默认选中第一个
    if (!selectedOptionId.value) {
      selectedOptionId.value = raw[0]?.id || ""
    }
    return raw
  }
  return []
})
const confirmState = computed<'idle' | 'confirmed' | 'cancelled'>(() => {
  const status = props.msg.metadata_json?.confirm_status
  if (status === 'confirmed') return 'confirmed'
  if (status === 'cancelled') return 'cancelled'
  return 'idle'
})

async function handleConfirm() {
  confirming.value = true
  try {
    const meta = { ...(props.msg.metadata_json || {}) }
    if (selectedOptionId.value) {
      meta._selected_option = selectedOptionId.value
    }
    emit('confirmTask', meta)
  } finally {
    confirming.value = false
  }
}

function handleCancel() {
  emit('cancelTask', props.msg.metadata_json || {})
}

const taskButtonText = computed(() => {
  const status = props.msg.metadata_json?.task_status
  if (status === 2) return "查看审核结果"
  if (status === 3) return "查看详情"
  return "查看任务进度"
})

function goTaskDetail() {
  const taskId = props.msg.metadata_json?.task_id
  if (taskId) {
    router.push(`/aitc/tasks/${taskId}`)
  } else {
    router.push("/aitc/tasks")
  }
}

// 简单 Markdown 渲染（粗体 + 行内代码 + 换行）
const renderedContent = computed(() => renderSimpleMd(props.msg.content || ""))

/** 已调用的 Agent 工具名称列表（去重） */
const toolNames = computed(() => {
  const raw = props.msg.metadata_json?.tool_names
  if (!Array.isArray(raw) || raw.length === 0) return []
  const labels = new Map<string, string>([
    ["list_projects", "列出项目"],
    ["get_suite_tree", "查看模块树"],
    ["search_cases", "搜索用例"],
    ["get_case_detail", "查看用例详情"],
    ["get_suite_samples", "查看样本用例"],
    ["ask_question", "询问用户"],
    ["create_core_select_task", "创建核心挑选任务"],
    ["create_case_review_task", "创建审核任务"],
    ["create_script_gen_task", "创建脚本生成任务"],
    ["complete_case_steps", "补写测试步骤"],
    ["complete_case_fields", "补全用例字段"],
    ["design_test_case", "设计测试用例"],
  ])
  return [...new Set(raw.map((n: string) => labels.get(n) || n))]
})

function formatTime(time: string | null) {
  return formatTimeHM(time)
}
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 6px;
  padding: 5px 10px;
  margin-bottom: 1px;
}

.chat-message.user {
  justify-content: flex-end;
}

.msg-avatar {
  flex-shrink: 0;
  align-self: flex-end;
}

.msg-bubble {
  position: relative;
  max-width: 78%;
  padding: 6px 10px 16px;
  border-radius: 8px;
  line-height: 1.55;
  font-size: 12px;
  word-break: break-word;
}

.user-bubble {
  background: var(--el-color-primary-light-8);
  color: var(--el-text-color-primary);
  border: 1px solid var(--el-color-primary-light-5);
}

.ai-bubble {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}

.ai-bubble .msg-text {
  color: var(--el-text-color-primary) !important;
}

.msg-text {
  white-space: pre-wrap;
  color: var(--el-text-color-primary);
}

/* 强制 v-html 子元素继承文字颜色，避免 strong/a/span 等被全局或 Element Plus 默认色影响 */
.ai-bubble .msg-text :deep(*),
.user-bubble .msg-text :deep(*) {
  color: inherit !important;
}

.msg-text :deep(code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
}

.user-bubble .msg-text :deep(code) {
  background: rgba(0, 0, 0, 0.1);
}

.msg-tool-steps {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  padding: 3px 8px;
  background: var(--el-fill-color);
  border-radius: 4px;
  font-size: 10px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}

.msg-tool-steps .el-icon {
  font-size: 11px;
}

.msg-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-meta {
  font-size: 10px;
  color: var(--el-text-color-secondary);
  padding-top: 3px;
  border-top: 1px dashed var(--el-border-color-lighter);
}

.card-actions {
  display: flex;
  gap: 4px;
  padding-top: 2px;
}

.card-result {
  font-size: 11px;
  padding: 3px 6px;
  border-radius: 4px;
  margin-top: 2px;
}

.card-result.success {
  color: var(--el-color-success);
  background: var(--el-color-success-light-9);
}

.card-result.muted {
  color: var(--el-text-color-placeholder);
  background: var(--el-fill-color);
}

/* confirm_card 多选项 */
.confirm-options {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px 0;
}

.confirm-option {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  border-radius: 6px;
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  transition: all 0.15s;
  font-size: 11px;
}

.confirm-option:hover {
  border-color: var(--el-color-primary-light-5);
  background: var(--el-color-primary-light-9);
}

.confirm-option.selected {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.option-radio {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--el-border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: border-color 0.15s;
}

.confirm-option.selected .option-radio {
  border-color: var(--el-color-primary);
}

.radio-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--el-color-primary);
}

.option-label {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.option-desc {
  color: var(--el-text-color-secondary);
  font-size: 10px;
}

/* clarify_card 问答表单 */
.clarify-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 4px 0;
}

.clarify-field {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.clarify-label {
  font-size: 11px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.clarify-required {
  color: var(--el-color-danger);
  margin-left: 1px;
}

.clarify-select {
  width: 100%;
}

.msg-time {
  position: absolute;
  bottom: 2px;
  right: 8px;
  font-size: 9px;
  color: var(--el-text-color-placeholder);
  line-height: 1;
  pointer-events: none;
}
</style>
