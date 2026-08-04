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

        <!-- 确认卡片（任务创建前确认） -->
        <div v-else-if="msg.msg_type === 'confirm_card'" class="msg-card">
          <div class="msg-text" v-html="renderedContent" />
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
        <div class="msg-time">{{ formatTime(msg.create_time) }}</div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import { useRouter } from "vue-router"
import { User, ChatDotRound } from "@element-plus/icons-vue"
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
}>()

const router = useRouter()
const confirming = ref(false)
const confirmState = computed<'idle' | 'confirmed' | 'cancelled'>(() => {
  const status = props.msg.metadata_json?.confirm_status
  if (status === 'confirmed') return 'confirmed'
  if (status === 'cancelled') return 'cancelled'
  return 'idle'
})

async function handleConfirm() {
  confirming.value = true
  try {
    emit('confirmTask', props.msg.metadata_json || {})
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

.msg-text {
  white-space: pre-wrap;
}

.msg-text :deep(code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
}

.user-bubble .msg-text :deep(code) {
  background: rgba(0, 0, 0, 0.1);
  color: var(--el-text-color-primary);
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
