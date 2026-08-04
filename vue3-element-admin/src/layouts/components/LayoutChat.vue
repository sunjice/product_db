<template>
  <!-- 收起状态：只显示一个悬浮按钮 -->
  <div v-if="!isOpen" class="layout-chat-collapsed" @click="toggle">
    <el-icon :size="20"><ChatDotRound /></el-icon>
    <span class="collapsed-label">AI</span>
  </div>

  <!-- 展开状态：可拖动浮窗 -->
  <div
    v-else
    class="layout-chat-float"
    :style="floatStyle"
  >
    <!-- 顶部（可拖拽标题栏） -->
    <div class="chat-panel-header" @mousedown="startDrag">
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
      <!-- 消息列表 -->
      <div class="chat-panel-messages" ref="msgListRef">
        <div v-if="!messages.length && !streaming" class="welcome">
          <p class="welcome-title">有什么我能帮你的吗？</p>
          <div class="quick-tags">
            <div
              v-for="q in quickPrompts"
              :key="q"
              class="quick-tag"
              @click="onQuickSend(q)"
            >
              {{ q }}
            </div>
          </div>
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

      <!-- 任务列表（有任务时才显示） -->
      <TaskListPanel v-if="hasTasks" :messages="messages" />

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
            :placeholder="pageAgent.isRunning.value ? 'Agent 执行中...' : '输入消息，Enter 发送'"
            :disabled="streaming || pageAgent.isRunning.value"
            @keydown="onKeydown"
            class="fill-textarea"
          />
          <el-button
            class="send-btn"
            type="primary"
            :disabled="!text.trim() || streaming || pageAgent.isRunning.value"
            @click="send"
            circle
            size="small"
          >
            <el-icon><Promotion /></el-icon>
          </el-button>
        </div>
      </div>
    </template>

    <!-- 四边 + 四角隐形缩放区域 -->
    <div v-for="d in RESIZE_DIRS" :key="d" :class="['resize-handle', d]" @mousedown.stop="startResize($event, d)" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed } from "vue"
import { useRoute } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import { ChatDotRound, Plus, DArrowRight, Promotion, ArrowLeft, Clock, Delete, Search, Edit } from "@element-plus/icons-vue"
import ChatMessage from "./chat/ChatMessage.vue"
import TaskListPanel from "./chat/TaskListPanel.vue"
import { useChat } from "./chat/useChat"
import { useAiContextStore } from "@/stores/aiContext"
import { usePageAgent } from "./chat/usePageAgent"
import { useChatResize, useInputResize, RESIZE_DIRS } from "./chat/useChatResize"
import { renderSimpleMd, formatHistoryTime } from "./chat/utils"
import type { ChatSession, ChatMessage as ChatMessageType } from "@/api/chat/types"

// ── 全局状态（组件实例不会被销毁，因为 LayoutMain 不会切换） ──
const isOpen = ref(false)
const panelWidth = ref(320)
const panelHeight = ref(580)
const floatX = ref(window.innerWidth - panelWidth.value - 20)
const floatY = ref(window.innerHeight - panelHeight.value - 20)
const text = ref("")
const msgListRef = ref<HTMLElement>()

const floatStyle = computed(() => ({
  width: panelWidth.value + "px",
  height: panelHeight.value + "px",
  left: floatX.value + "px",
  top: floatY.value + "px",
}))

const route = useRoute()
const aiContextStore = useAiContextStore()

const {
  sessions,
  activeSessionId,
  messages,
  streaming,
  streamingText,
  pageContext,
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

// ── PageAgent Spike ──
const pageAgent = usePageAgent()

// 是否有任务消息
const hasTasks = computed(() =>
  messages.value.some((m) => m.msg_type === "task_card")
)

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

// ── 危险确认弹窗（复用） ──
async function confirmDanger(message: string): Promise<boolean> {
  try {
    await ElMessageBox.confirm(message, "确认删除", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    })
    return true
  } catch {
    return false
  }
}

async function onDeleteSession(s: ChatSession) {
  if (!(await confirmDanger(`确定删除"${s.title}"？此操作不可恢复。`))) return
  if (activeSessionId.value === s.id) {
    const rest = sessions.value.filter((x) => x.id !== s.id)
    if (rest.length) await selectSession(rest[0].id!)
  }
  await deleteSession(s.id!)
  ElMessage.success("已删除")
}

async function onDeleteAll() {
  if (!sessions.value.length) return
  if (!(await confirmDanger("确定删除所有历史对话？此操作不可恢复。"))) return
  const ids = sessions.value.map((s) => s.id).filter((id): id is number => !!id)
  await Promise.all(ids.map((id) => deleteSession(id)))
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

// ── 监听路由/Store，同步页面上下文（route query 优先） ──
watch(
  [() => route.fullPath, () => aiContextStore.contextJson],
  ([, storeCtx]) => {
    const ctx: Record<string, any> = {}
    const { projectId, suiteId } = route.query
    if (projectId) ctx.project_id = Number(projectId)
    if (suiteId) ctx.suite_id = Number(suiteId)
    if (route.meta?.projectId) ctx.project_id = Number(route.meta.projectId)
    // route 无上下文时，fallback 到 Store
    if (!Object.keys(ctx).length && storeCtx && Object.keys(storeCtx).length) {
      Object.assign(ctx, storeCtx)
    }
    if (Object.keys(ctx).length) {
      pageContext.value = ctx
    }
  },
  { deep: true, immediate: true }
)

// ── 发送消息 ──
async function send() {
  const val = text.value.trim()
  if (!val || streaming.value) return
  text.value = ""

  // PageAgent Spike: 以 /agent 开头则调用页面操作
  if (val.startsWith("/agent ")) {
    const task = val.slice(7).trim()
    if (!task) return

    // 在聊天区插入一条用户指令
    const agentMsg: ChatMessageType = {
      id: Date.now(),
      session_id: activeSessionId.value,
      role: "user",
      msg_type: "text",
      content: `[Agent] ${task}`,
      metadata_json: null,
      draft_id: null,
      create_time: new Date().toISOString(),
    }
    messages.value.push(agentMsg)

    // 执行 agent 任务
    try {
      const result = await pageAgent.execute(task)
      const summary = result.success
        ? `PageAgent 执行完成 | 步骤: ${result.steps} | 耗时: ${(result.durationMs / 1000).toFixed(1)}s\n\n${result.data}`
        : `PageAgent 执行失败 | 耗时: ${(result.durationMs / 1000).toFixed(1)}s\n\n${result.data}`

      const resultMsg: ChatMessageType = {
        id: Date.now() + 1,
        session_id: activeSessionId.value,
        role: "system",
        msg_type: "text",
        content: summary,
        metadata_json: { agent_result: result, type: "page_agent" },
        draft_id: null,
        create_time: new Date().toISOString(),
      }
      messages.value.push(resultMsg)

      if (result.success) {
        ElMessage.success(`Agent: ${result.steps} 步完成 (${(result.durationMs / 1000).toFixed(1)}s)`)
      } else {
        ElMessage.error(`Agent 失败: ${result.data.slice(0, 100)}`)
      }
    } catch (e: any) {
      const errorMsg: ChatMessageType = {
        id: Date.now() + 1,
        session_id: activeSessionId.value,
        role: "system",
        msg_type: "text",
        content: `PageAgent 初始化失败: ${e?.message || String(e)}`,
        metadata_json: { type: "page_agent_error" },
        draft_id: null,
        create_time: new Date().toISOString(),
      }
      messages.value.push(errorMsg)
      ElMessage.error("Agent 初始化失败，请检查 .env.development.local 配置")
    }
    return
  }

  await sendMessage(val)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

// ── 快捷提问 ──
const quickPrompts = [
  "帮我挑选核心用例",
  "审核用例质量",
  "生成测试脚本",
  "补全用例字段",
  "补写测试步骤",
  "设计测试用例",
]

async function onQuickSend(prompt: string) {
  if (streaming.value) return
  await sendMessage(prompt)
}

// ── 会话操作 ──
async function newSession() {
  const s = await createSession()
  await selectSession(s.id!)
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
  return renderSimpleMd(t)
}

// ── 浮窗拖拽 + 缩放 ──
const { startDrag, startResize } = useChatResize(panelWidth, panelHeight, floatX, floatY)
const { inputHeight, onInputMouseDown } = useInputResize()

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

/* 展开态：可拖动浮窗 */
.layout-chat-float {
  position: fixed;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  z-index: 2000;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  transition: box-shadow 0.2s;
}

.layout-chat-float:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}

/* 缩放热区 */
.resize-handle { position: absolute; }

.resize-handle.top, .resize-handle.bottom { height: 6px; left: 12px; right: 12px; cursor: ns-resize; }
.resize-handle.left, .resize-handle.right { width: 6px; top: 12px; bottom: 12px; cursor: ew-resize; }
.resize-handle.top { top: 0; }
.resize-handle.bottom { bottom: 0; z-index: 9; }
.resize-handle.left { left: 0; z-index: 9; }
.resize-handle.right { right: 0; z-index: 9; }

.resize-handle.tl, .resize-handle.tr, .resize-handle.bl, .resize-handle.br { width: 12px; height: 12px; z-index: 10; }
.resize-handle.tl { top: 0; left: 0; cursor: nwse-resize; }
.resize-handle.tr { top: 0; right: 0; cursor: nesw-resize; }
.resize-handle.bl { bottom: 0; left: 0; cursor: nesw-resize; }
.resize-handle.br { bottom: 0; right: 0; cursor: nwse-resize; }

.chat-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 3px 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-color-primary-light-9);
  flex-shrink: 0;
  cursor: move;
  user-select: none;
  min-height: 28px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
  font-size: 12px;
}

.header-actions {
  display: flex;
  gap: 0;
}

.header-actions :deep(.el-button) {
  height: 26px;
  padding: 0;
  margin: 0;
  border: none;
}

.header-actions :deep(.el-button.is-circle) {
  width: 26px;
  min-width: 26px;
}

.header-actions :deep(.el-button .el-icon) {
  font-size: 14px;
  margin: 0;
}

.header-actions :deep(.el-button--small) {
  font-size: 11px;
  height: 24px;
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
  gap: 16px;
}

.welcome-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0;
}

.quick-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  max-width: 420px;
}

.quick-tag {
  padding: 8px 14px;
  border-radius: 18px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  color: var(--el-text-color-regular);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.quick-tag:hover {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
  color: var(--el-color-primary);
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
  padding: 6px 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.history-group {
  margin-bottom: 2px;
}

.history-group-label {
  padding: 4px 10px;
  font-size: 10px;
  color: var(--el-text-color-secondary);
}

.history-item {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 10px;
  cursor: pointer;
  transition: background 0.15s;
}

.history-item:hover {
  background: var(--el-fill-color-light);
}

.history-item-icon {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
}

.history-item-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.history-item-time {
  font-size: 10px;
  color: var(--el-text-color-placeholder);
  flex-shrink: 0;
}

.history-item-action {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  cursor: pointer;
  flex-shrink: 0;
  padding: 1px;
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