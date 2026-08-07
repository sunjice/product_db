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
        <div class="header-logo">
          <el-icon><ChatDotRound /></el-icon>
        </div>
        <span>AI 助手</span>
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
          <div class="welcome-brand">
            <el-icon :size="26" color="var(--el-color-primary)"><ChatDotRound /></el-icon>
          </div>
          <h2 class="welcome-title">{{ welcomeTitle }}</h2>
          <p class="welcome-subtitle">我可以帮你挑选核心用例、审核质量、生成脚本、补全字段等</p>

          <div class="quick-actions">
            <div
              v-for="q in quickActions"
              :key="q.title"
              class="quick-action-card"
              @click="onQuickSend(q.prompt)"
            >
              <div class="quick-action-icon" :style="{ background: q.bg }">
                <el-icon :size="18"><component :is="q.icon" /></el-icon>
              </div>
              <div class="quick-action-text">
                <div class="quick-action-title">{{ q.title }}</div>
                <div class="quick-action-desc">{{ q.desc }}</div>
              </div>
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
          @submitClarify="onSubmitClarify"
        />

        <StreamingBubble
          v-if="streaming"
          :streaming-text="streamingText"
          :thinking-step="thinkingStep"
        />
      </div>

      <!-- 任务列表（有任务时才显示） -->
      <TaskListPanel v-if="hasTasks" :messages="messages" />

      <!-- 上下文显示行 -->
      <div v-if="showContextBar && contextBarItems.length" class="context-bar">
        <div class="context-bar-inner">
          <div class="context-info">
            <el-icon class="context-pin"><Location /></el-icon>
            <span class="context-label">上下文</span>
            <span class="context-divider">·</span>
            <span class="context-items">
              <span
                v-for="(item, idx) in contextBarItems"
                :key="idx"
                class="context-item"
              >
                <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
                <span>{{ item.label }}</span>
              </span>
            </span>
          </div>
          <el-button
            text
            circle
            size="small"
            class="context-close"
            @click="showContextBar = false"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- 输入区（上边缘可拖拽调整高度） -->
      <div
        class="chat-panel-input"
        :style="{ height: inputHeight + 'px' }"
        @mousedown="onInputMouseDown"
      >
        <div class="input-box">
          <el-input
            v-model="text"
            type="textarea"
            :placeholder="inputPlaceholder"
            :disabled="streaming"
            @keydown="onKeydown"
            class="fill-textarea"
          />
          <el-button
            class="send-btn-float"
            type="primary"
            :disabled="!text.trim() || streaming"
            @click="send"
            circle
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
import {
  ChatDotRound, Plus, DArrowRight, Promotion, ArrowLeft, Clock, Delete, Search, Edit,
  FolderChecked, DocumentChecked, EditPen, CircleCheck,
  Grid, Opportunity, Collection, Location, Close,
} from "@element-plus/icons-vue"
import ChatMessage from "./chat/ChatMessage.vue"
import TaskListPanel from "./chat/TaskListPanel.vue"
import StreamingBubble from "./chat/StreamingBubble.vue"
import { useChat } from "./chat/useChat"
import { useAiContextStore } from "@/stores/aiContext"
import { useChatResize, useInputResize, RESIZE_DIRS } from "./chat/useChatResize"
import { formatHistoryTime } from "./chat/utils"
import type { ChatSession } from "@/api/chat/types"

// ── 全局状态（组件实例不会被销毁，因为 LayoutMain 不会切换） ──
const isOpen = ref(false)
const panelWidth = ref(480)
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
  thinkingStep,
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
    // Store 里的 current_page / project_id / suite_id 等始终合并进来
    // route.query 优先级更高（已设置过的字段不再被 Store 覆盖）
    if (storeCtx && Object.keys(storeCtx).length) {
      Object.assign(ctx, storeCtx, ctx)
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

  await sendMessage(val)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

// ── 上下文显示行 ──
const showContextBar = ref(true)

const welcomeTitle = computed(() => {
  const hour = new Date().getHours()
  let greet: string
  if (hour < 12) greet = "早上好"
  else if (hour < 18) greet = "下午好"
  else greet = "晚上好"
  return `${greet}，有什么我能帮你的吗？`
})

interface ContextItem {
  label: string
  icon?: any
}

const contextBarItems = computed<ContextItem[]>(() => {
  const ctx = pageContext.value || {}
  const page = ctx.current_page || ""
  if (!page) return []

  const items: ContextItem[] = []

  // 公共字段：项目、模块、用例
  if (ctx.project_name || ctx.project_id) {
    items.push({ label: ctx.project_name || `项目 #${ctx.project_id}`, icon: FolderChecked })
  }
  if (ctx.suite_name || ctx.suite_id) {
    items.push({ label: ctx.suite_name || `模块 #${ctx.suite_id}`, icon: Collection })
  }
  if (ctx.current_case_id) {
    items.push({ label: `用例 #${ctx.current_case_id}`, icon: DocumentChecked })
  }

  // 页面特有字段
  if (page === "case") {
    if (ctx.selected_case_ids?.length) {
      items.push({ label: `已选 ${ctx.selected_case_ids.length} 条用例`, icon: Grid })
    }
  } else {
    if (ctx.task_id) items.push({ label: `任务 #${ctx.task_id}`, icon: Opportunity })
    if (ctx.script_id) items.push({ label: `脚本 #${ctx.script_id}`, icon: DocumentChecked })
  }

  return items
})

const inputPlaceholder = computed(() => {
  const page = pageContext.value?.current_page
  if (page === "case") return "提问、@（提及）或使用“/”进行操作"
  return "有什么我可以帮你的？"
})

// ── 快捷提问（Rovo 风格卡片） ──
interface QuickAction {
  title: string
  desc: string
  prompt: string
  icon: any
  bg: string
}

const quickActions = ref<QuickAction[]>([
  {
    title: "挑选核心用例",
    desc: "从当前模块智能挑选最重要的用例",
    prompt: "帮我挑选核心用例",
    icon: CircleCheck,
    bg: "linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%)",
  },
  {
    title: "审核用例质量",
    desc: "检查字段完整性和步骤规范性",
    prompt: "审核用例质量",
    icon: CircleCheck,
    bg: "linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)",
  },
  {
    title: "补写测试步骤",
    desc: "AI 自动补全用例的测试步骤",
    prompt: "补写测试步骤",
    icon: EditPen,
    bg: "linear-gradient(135deg, #ffedd5 0%, #fed7aa 100%)",
  },
])

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

// ── 澄清卡片提交：将答案作为新消息发送给 LLM ──
async function onSubmitClarify(text: string) {
  await sendMessage(text)
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
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  z-index: 2000;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.1), 0 4px 12px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  transition: box-shadow 0.2s;
}

.layout-chat-float:hover {
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.12), 0 6px 16px rgba(0, 0, 0, 0.05);
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
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
  flex-shrink: 0;
  cursor: move;
  user-select: none;
  min-height: 44px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.header-logo {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--el-color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-logo .el-icon {
  font-size: 16px;
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
  justify-content: flex-start;
  padding: 28px 16px 16px;
  text-align: center;
  gap: 8px;
}

.welcome-brand {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: linear-gradient(135deg, var(--el-color-primary-light-8) 0%, var(--el-color-primary-light-9) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 2px;
  box-shadow: 0 4px 16px rgba(var(--el-color-primary-rgb), 0.12);
}

.welcome-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0;
  line-height: 1.35;
}

.welcome-subtitle {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin: 0 0 8px;
  line-height: 1.45;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  max-width: 420px;
  padding: 0 4px;
}

.quick-action-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
  text-align: left;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}

.quick-action-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.quick-action-icon {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--el-text-color-primary);
}

.quick-action-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.quick-action-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.quick-action-desc {
  font-size: 10px;
  color: var(--el-text-color-secondary);
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.context-item .el-icon {
  font-size: 11px;
}

.context-close {
  padding: 6px 12px 0;
  flex-shrink: 0;
}

.context-bar {
  padding: 6px 12px 0;
  flex-shrink: 0;
}

.context-bar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 10px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
}

.context-info {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

.context-pin {
  font-size: 13px;
  color: var(--el-color-primary);
  flex-shrink: 0;
}

.context-label {
  font-size: 11px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  flex-shrink: 0;
}

.context-divider {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  flex-shrink: 0;
}

.context-items {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
  overflow: hidden;
}

.context-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: var(--el-text-color-regular);
  background: var(--el-bg-color);
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid var(--el-border-color-lighter);
  white-space: nowrap;
  flex-shrink: 0;
}

.context-item .el-icon {
  font-size: 11px;
}

.context-close {
  flex-shrink: 0;
}

.context-close :deep(.el-icon) {
  font-size: 12px;
}

.chat-panel-input {
  padding: 10px 12px 12px;
  flex-shrink: 0;
  overflow: visible;
  display: flex;
  flex-direction: column;
  min-height: 62px;
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

.input-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  border-radius: 18px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  padding: 8px 46px 8px 14px;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  min-height: 0;
  overflow: hidden;
}

.input-box:focus-within {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 0 0 3px var(--el-color-primary-light-8), 0 1px 3px rgba(0, 0, 0, 0.04);
}

.send-btn-float {
  position: absolute;
  right: 8px;
  bottom: 8px;
  width: 32px;
  height: 32px;
  z-index: 2;
  transition: all 0.2s;
}

.send-btn-float :deep(.el-icon) {
  font-size: 15px;
}

.send-btn-float.is-disabled {
  opacity: 0.5;
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

.fill-textarea {
  flex: 1;
  min-height: 0;
  display: flex;
}

.fill-textarea :deep(.el-textarea) {
  flex: 1;
  min-height: 0;
  display: flex;
}

.fill-textarea :deep(.el-textarea__inner) {
  border: none;
  border-radius: 0;
  padding: 0;
  font-size: 13px;
  line-height: 1.55;
  resize: none;
  height: 100%;
  min-height: 20px;
  background: transparent;
  box-shadow: none;
}

.fill-textarea :deep(.el-textarea__inner::placeholder) {
  color: var(--el-text-color-placeholder);
}
</style>