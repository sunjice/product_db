<template>
  <!-- 收起状态：只显示一个悬浮按钮 -->
  <div v-if="!isOpen" class="layout-chat-collapsed" @click="toggle">
    <el-icon :size="20"><ChatDotRound /></el-icon>
    <span class="collapsed-label">AI</span>
  </div>

  <!-- 展开状态：右侧面板 -->
  <div v-else class="layout-chat-panel" :style="{ width: panelWidth + 'px' }">
    <!-- 宽度拖拽条 -->
    <div class="panel-resize-handle" @mousedown="startResize" />

    <!-- 顶部 -->
    <div class="chat-panel-header">
      <div v-if="showHistory" class="header-title">
        <el-button text @click="showHistory = false">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <span>历史对话</span>
      </div>
      <div v-else class="header-title">
        <el-icon><ChatDotRound /></el-icon>
        <span>AI 对话</span>
      </div>
      <div class="header-actions">
        <el-button v-if="showHistory" type="danger" text size="small" @click="onDeleteAll">
          <el-icon><Delete /></el-icon>
          删除所有
        </el-button>
        <el-button v-if="!showHistory" text circle @click="showHistory = true" title="历史对话">
          <el-icon><Clock /></el-icon>
        </el-button>
        <el-button v-if="!showHistory" text circle @click="newSession" title="新对话">
          <el-icon><Plus /></el-icon>
        </el-button>
        <el-button text circle @click="toggle" title="收起">
          <el-icon><DArrowRight /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 历史会话面板 -->
    <template v-if="showHistory">
      <div class="history-search-bar">
        <el-input
          v-model="historyKeyword"
          placeholder="搜索历史对话"
          clearable
          :prefix-icon="Search"
          size="small"
        />
      </div>
      <div class="history-list">
        <template v-if="groupedSessions.length">
          <div v-for="group in groupedSessions" :key="group.label" class="history-group">
            <div class="history-group-label">{{ group.label }}</div>
            <div
              v-for="s in group.sessions"
              :key="s.id"
              class="history-item"
              @click="onHistorySelect(s.id!)"
            >
              <el-icon class="history-item-icon"><ChatDotRound /></el-icon>
              <span class="history-item-title" :title="s.title">{{ s.title }}</span>
              <span class="history-item-time">{{ formatHistoryTime(s.update_time) }}</span>
              <el-icon class="history-item-action" @click.stop="onRenameSession(s)" title="重命名"><Edit /></el-icon>
              <el-icon class="history-item-action" @click.stop="onDeleteSession(s)" title="删除"><Delete /></el-icon>
            </div>
          </div>
        </template>
        <el-empty v-else description="暂无历史对话" :image-size="50" />
      </div>
    </template>

    <!-- 正常聊天区域 -->
    <template v-else>
      <!-- 会话选择条 -->
      <!-- <div v-if="sessions.length > 1" class="chat-session-bar">
        <el-select
          v-model="activeSessionId"
          placeholder="选择对话"
          size="small"
          @change="onSessionChange"
          style="width: 100%"
        >
          <el-option
            v-for="s in sessions"
            :key="s.id"
            :label="s.title"
            :value="s.id"
          />
        </el-select>
      </div> -->

      <!-- 消息列表 -->
      <div class="chat-panel-messages" ref="msgListRef">
        <div v-if="!messages.length && !streaming" class="welcome">
          <el-icon :size="32" color="var(--el-color-primary)"><ChatDotRound /></el-icon>
          <p>AI 测试助手</p>
          <span>输入消息开始对话</span>
        </div>

        <ChatMessage
          v-for="msg in messages"
          :key="msg.id || msg.create_time"
          :msg="msg"
          @viewDraft="onViewDraft"
          @confirmDraft="onConfirmDraft"
          @confirmTask="onConfirmTask"
          @cancelTask="onCancelTask"
        />

        <!-- 流式输出：只有 chunk 流内容时显示打字效果 -->
        <div v-if="streaming && streamingText" class="streaming">
          <el-avatar :size="28" style="background: var(--el-color-primary)">
            <el-icon><ChatDotRound /></el-icon>
          </el-avatar>
          <div class="streaming-text" v-html="renderMd(streamingText)" />
          <span class="cursor">|</span>
        </div>

        <!-- 非流式的处理中（如 skill 匹配、任务生成等）用轻量指示 -->
        <div v-else-if="streaming && !streamingText" class="streaming thinking">
          <el-avatar :size="28" style="background: var(--el-color-primary)">
            <el-icon><ChatDotRound /></el-icon>
          </el-avatar>
          <div class="thinking-dots">
            <span /><span /><span />
          </div>
        </div>
      </div>

      <!-- 任务列表 -->
      <TaskListPanel :messages="messages" />

      <!-- 输入区（上边缘可拖拽调整高度） -->
      <div
        class="chat-panel-input"
        :style="{ height: inputHeight + 'px' }"
        @mousedown="onInputMouseDown"
      >
        <div class="input-row">
          <el-input
            v-model="text"
            type="textarea"
            placeholder="输入消息，Enter 发送"
            :disabled="streaming"
            @keydown="onKeydown"
            resize="none"
            class="fill-textarea"
          />
          <el-button
            class="send-btn"
            type="primary"
            :disabled="!text.trim() || streaming"
            @click="send"
            circle
            size="small"
          >
            <el-icon><Promotion /></el-icon>
          </el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed } from "vue"
import { useRoute } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import { ChatDotRound, Plus, DArrowRight, Promotion, ArrowLeft, Clock, Delete, Search, Edit } from "@element-plus/icons-vue"
import ChatMessage from "@/views/aitc/chat/components/ChatMessage.vue"
import TaskListPanel from "@/views/aitc/chat/components/TaskListPanel.vue"
import { useChat } from "@/views/aitc/chat/composables/useChat"
import { useAiContextStore } from "@/stores/aiContext"
import type { ChatSession } from "@/api/aitc/chat/types"

// ── 全局状态（组件实例不会被销毁，因为 LayoutMain 不会切换） ──
const isOpen = ref(false)
const panelWidth = ref(480)
const text = ref("")
const msgListRef = ref<HTMLElement>()

const route = useRoute()
const aiContextStore = useAiContextStore()

const {
  sessions,
  activeSessionId,
  messages,
  streaming,
  streamingText,
  pageContext,
  loadSessions,
  createSession,
  selectSession,
  updateSession,
  deleteSession,
  sendMessage,
  confirmDraft,
  confirmCreateTask,
  cancelTask,
  viewDraft,
  init,
} = useChat()

// ── 初始化（只执行一次） ──
const inited = ref(false)
function ensureInit() {
  if (inited.value) return
  inited.value = true
  init()
}

// ── 历史面板 ──
const showHistory = ref(false)
const historyKeyword = ref("")

const filteredSessions = computed(() => {
  if (!historyKeyword.value.trim()) return sessions.value
  const k = historyKeyword.value.trim().toLowerCase()
  return sessions.value.filter((s) => s.title?.toLowerCase().includes(k))
})

const groupedSessions = computed(() => {
  const groups: { label: string; sessions: ChatSession[] }[] = []
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  const weekAgo = new Date(now)
  weekAgo.setDate(weekAgo.getDate() - 7)
  const monthAgo = new Date(now)
  monthAgo.setMonth(monthAgo.getMonth() - 1)

  const today: ChatSession[] = []
  const yday: ChatSession[] = []
  const week: ChatSession[] = []
  const month: ChatSession[] = []
  const earlier: ChatSession[] = []

  for (const s of filteredSessions.value) {
    const t = s.update_time ? new Date(s.update_time) : null
    if (!t) { earlier.push(s); continue }
    const d = new Date(t); d.setHours(0, 0, 0, 0)
    if (d.getTime() === now.getTime()) today.push(s)
    else if (d.getTime() === yesterday.getTime()) yday.push(s)
    else if (d.getTime() > weekAgo.getTime()) week.push(s)
    else if (d.getTime() > monthAgo.getTime()) month.push(s)
    else earlier.push(s)
  }

  if (today.length) groups.push({ label: "今天", sessions: today })
  if (yday.length) groups.push({ label: "昨天", sessions: yday })
  if (week.length) groups.push({ label: "最近7天", sessions: week })
  if (month.length) groups.push({ label: "最近30天", sessions: month })
  if (earlier.length) groups.push({ label: "更早", sessions: earlier })
  return groups
})

function formatHistoryTime(time: string | null): string {
  if (!time) return ""
  const d = new Date(time)
  const now = new Date()
  if (d.toDateString() === now.toDateString())
    return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })
  return d.toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" })
}

function onHistorySelect(sessionId: number) {
  showHistory.value = false
  selectSession(sessionId)
}

async function onRenameSession(s: ChatSession) {
  try {
    const { value } = await ElMessageBox.prompt("请输入新名称", "重命名对话", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      inputValue: s.title,
      inputPlaceholder: "对话名称",
    })
    if (value && value.trim() && value.trim() !== s.title) {
      await updateSession(s.id!, { title: value.trim() })
    }
  } catch {
    // 取消
  }
}

async function onDeleteSession(s: ChatSession) {
  try {
    await ElMessageBox.confirm(`确定删除"${s.title}"？此操作不可恢复。`, "确认删除", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    })
  } catch {
    return
  }
  // 如果删除的是当前激活的会话，先切换到其他会话
  if (activeSessionId.value === s.id) {
    const rest = sessions.value.filter((x) => x.id !== s.id)
    if (rest.length) await selectSession(rest[0].id!)
  }
  await deleteSession(s.id!)
  ElMessage.success("已删除")
}

async function onDeleteAll() {
  if (!sessions.value.length) return
  try {
    await ElMessageBox.confirm("确定删除所有历史对话？此操作不可恢复。", "确认删除", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    })
  } catch {
    return
  }
  const ids = sessions.value.map((s) => s.id!).filter(Boolean)
  for (const id of ids) {
    await deleteSession(id)
  }
  ElMessage.success("已删除所有历史对话")
  showHistory.value = false
}

// ── 控制开关 ──
function toggle() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    ensureInit()
    if (!activeSessionId.value && sessions.value.length > 0) {
      selectSession(sessions.value[0].id!)
    }
  }
}

// ── 监听路由，自动提取页面上下文 ──
watch(
  () => route.fullPath,
  () => {
    // 从 URL query 参数或 route meta 中提取上下文
    const ctx: Record<string, any> = {}
    const { projectId, suiteId } = route.query
    if (projectId) ctx.project_id = Number(projectId)
    if (suiteId) ctx.suite_id = Number(suiteId)
    if (route.meta?.projectId) ctx.project_id = Number(route.meta.projectId)

    // 更新到 pageContext（影响后续 sendMessage 自动创建会话时的上下文）
    if (Object.keys(ctx).length) {
      pageContext.value = ctx
    }
  },
  { immediate: true }
)

// ── 监听 Pinia Store，同步页面上下文（各页面通过 Store 注册） ──
watch(
  () => aiContextStore.contextJson,
  (ctx) => {
    if (ctx && Object.keys(ctx).length) {
      pageContext.value = { ...ctx }
    }
  },
  { deep: true, immediate: true }
)

// ── 发送消息 ──
async function send() {
  const val = text.value.trim()
  if (!val || streaming.value) return
  text.value = ""
  await sendMessage(val)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

// ── 会话操作 ──
async function newSession() {
  const s = await createSession()
  await selectSession(s.id!)
}

function onSessionChange(id: number) {
  selectSession(id)
}

// ── 草稿操作 ──
function onViewDraft(id: number) {
  viewDraft(id)
}

async function onConfirmDraft(action: string) {
  await confirmDraft(action as "confirm" | "discard")
}

function onConfirmTask(metadata: Record<string, any>) {
  confirmCreateTask(metadata)
}

function onCancelTask(metadata: Record<string, any>) {
  cancelTask(metadata)
}

// ── 自动滚动 ──
watch(
  () => [messages.value.length, streamingText.value],
  async () => {
    await nextTick()
    if (msgListRef.value) {
      msgListRef.value.scrollTop = msgListRef.value.scrollHeight
    }
  }
)

// ── 简易 Markdown ──
function renderMd(t: string): string {
  if (!t) return ""
  let s = t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>")
  s = s.replace(/\n/g, "<br>")
  return s
}

// ── 面板宽度拖拽 ──
const isResizing = ref(false)

function startResize(e: MouseEvent) {
  isResizing.value = true
  const startX = e.clientX
  const startWidth = panelWidth.value

  function onMouseMove(ev: MouseEvent) {
    const delta = startX - ev.clientX
    const newWidth = Math.min(Math.max(startWidth + delta, 320), 800)
    panelWidth.value = newWidth
  }

  function onMouseUp() {
    isResizing.value = false
    document.removeEventListener("mousemove", onMouseMove)
    document.removeEventListener("mouseup", onMouseUp)
  }

  document.addEventListener("mousemove", onMouseMove)
  document.addEventListener("mouseup", onMouseUp)
}

// ── 输入区高度拖拽 ──
const inputHeight = ref(100)
const isInputResizing = ref(false)

function onInputMouseDown(e: MouseEvent) {
  // 只有鼠标在输入区上边缘 5px 范围内才触发拖拽
  if (e.offsetY > 5) return
  startInputResize(e)
}

function startInputResize(e: MouseEvent) {
  isInputResizing.value = true
  const startY = e.clientY
  const startHeight = inputHeight.value

  function onMouseMove(ev: MouseEvent) {
    const delta = startY - ev.clientY
    const newHeight = Math.min(Math.max(startHeight + delta, 60), 320)
    inputHeight.value = newHeight
  }

  function onMouseUp() {
    isInputResizing.value = false
    document.removeEventListener("mousemove", onMouseMove)
    document.removeEventListener("mouseup", onMouseUp)
  }

  document.addEventListener("mousemove", onMouseMove)
  document.addEventListener("mouseup", onMouseUp)
}

// ── 对外暴露开关方法（给 LayoutToolbar 用） ──
defineExpose({ toggle, isOpen })
</script>

<style scoped>
/* 收起态：右侧悬浮按钮 */
.layout-chat-collapsed {
  position: fixed;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 36px;
  padding: 12px 0;
  background: var(--el-color-primary);
  color: #fff;
  border-radius: 8px 0 0 8px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  z-index: 2000;
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.15);
  transition: all 0.2s;
}

.layout-chat-collapsed:hover {
  width: 40px;
  box-shadow: -2px 0 12px rgba(0, 0, 0, 0.25);
}

.collapsed-label {
  font-size: 11px;
  writing-mode: vertical-rl;
  letter-spacing: 2px;
}

/* 展开态：右侧固定面板 */
.layout-chat-panel {
  position: fixed;
  right: 0;
  top: 0;
  bottom: 0;
  background: var(--el-bg-color);
  border-left: 1px solid var(--el-border-color-lighter);
  display: flex;
  flex-direction: column;
  z-index: 2000;
  box-shadow: -4px 0 16px rgba(0, 0, 0, 0.08);
}

.panel-resize-handle {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  cursor: col-resize;
  z-index: 2001;
  transition: background 0.2s;
}

.panel-resize-handle:hover {
  background: var(--el-color-primary-light-7);
}

.chat-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 2px;
}

.header-actions :deep(.el-button) {
  width: 34px;
  height: 34px;
}

.header-actions :deep(.el-button .el-icon) {
  font-size: 16px;
}

.chat-session-bar {
  padding: 6px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
}

.chat-panel-messages {
  flex: 1;
  overflow-y: auto;
  padding: 2px 0;
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.welcome p {
  margin: 10px 0 4px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.streaming {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 10px;
}

.streaming-text {
  flex: 1;
  line-height: 1.55;
  font-size: 12px;
}

.streaming-text :deep(code) {
  background: var(--el-fill-color);
  padding: 1px 4px;
  border-radius: 3px;
}

.streaming.thinking {
  padding: 10px 10px 6px;
}

.thinking-dots {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 4px 0;
}

.thinking-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--el-color-primary);
  animation: dotPulse 1.4s infinite ease-in-out both;
}

.thinking-dots span:nth-child(1) { animation-delay: -0.32s; }
.thinking-dots span:nth-child(2) { animation-delay: -0.16s; }
.thinking-dots span:nth-child(3) { animation-delay: 0s; }

@keyframes dotPulse {
  0%, 80%, 100% { transform: scale(0.4); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

.cursor {
  animation: blink 1s infinite;
  color: var(--el-color-primary);
  font-weight: bold;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.chat-panel-input {
  padding: 8px 10px;
  border-top: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 60px;
  position: relative;
}

.chat-panel-input::before {
  content: "";
  position: absolute;
  top: -3px;
  left: 0;
  right: 0;
  height: 7px;
  cursor: row-resize;
  z-index: 1;
}

.chat-panel-input::after {
  content: "";
  position: absolute;
  top: 1px;
  left: 50%;
  transform: translateX(-50%);
  width: 28px;
  height: 3px;
  border-radius: 2px;
  background: var(--el-border-color);
  transition: background 0.2s;
}

.chat-panel-input:hover::after {
  background: var(--el-color-primary-light-5);
}

/* 历史面板 */
.history-search-bar {
  padding: 10px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.history-group {
  margin-bottom: 4px;
}

.history-group-label {
  padding: 6px 14px;
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  cursor: pointer;
  transition: background 0.15s;
}

.history-item:hover {
  background: var(--el-fill-color-light);
}

.history-item-icon {
  font-size: 15px;
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
}

.history-item-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.history-item-time {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  flex-shrink: 0;
}

.history-item-action {
  font-size: 14px;
  color: var(--el-text-color-placeholder);
  cursor: pointer;
  flex-shrink: 0;
  padding: 2px;
  border-radius: 3px;
  transition: color 0.15s, background 0.15s;
  display: none;
}

.history-item:hover .history-item-action {
  display: inline-flex;
}

.history-item-action:hover {
  color: var(--el-color-primary);
  background: var(--el-fill-color);
}

.input-row {
  position: relative;
  flex: 1;
  min-height: 0;
}

.send-btn {
  position: absolute;
  right: 6px;
  bottom: 6px;
  z-index: 2;
}

.input-row :deep(.el-textarea) {
  height: 100%;
  display: flex;
}

.input-row :deep(.el-textarea__inner) {
  border-radius: 8px;
  padding: 8px 40px 8px 12px;
  font-size: 13px;
  line-height: 1.5;
  resize: none;
  height: 100%;
}
</style>