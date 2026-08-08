/** Chat 聊天核心逻辑 composable */

import { ref, reactive, computed, nextTick, onUnmounted } from "vue"
import { ElMessage } from "element-plus"
import { ChatSessionAPI, ChatMessageAPI, ChatDraftAPI, ChatSkillAPI, ChatContextAPI, ChatTaskAPI } from "@/api/chat/index"
import TaskAPI from "@/api/aitc/task"
import { TASK_TYPE_MAP } from "@/views/aitc/constants"
import type {
  ChatSession,
  ChatMessage,
  ChatDraft,
  SkillInfo,
  MessageSendReq,
} from "@/api/chat/types"

export function useChat() {
  // ── 状态 ──
  const sessions = ref<ChatSession[]>([])
  const activeSessionId = ref<number | null>(null)
  const messages = ref<ChatMessage[]>([])
  const skills = ref<SkillInfo[]>([])
  const loading = ref(false)
  const streaming = ref(false)
  const streamingText = ref("")
  const thinkingStep = ref("")       // 当前正在执行的工具名称（Agent 模式）
  const toolSteps = ref<string[]>([]) // 已完成工具调用记录
  const activeDraft = ref<ChatDraft | null>(null)
  const showDraftPanel = ref(false)
  const loadingSessions = ref(false)
  const loadingMessages = ref(false)
  const pageContext = ref<Record<string, any>>({})  // 页面上下文（projectId/suiteId 等）
  let abortController: AbortController | null = null  // 用于中断流式请求

  // ── 计算属性 ──
  const activeSession = computed(() =>
    sessions.value.find((s) => s.id === activeSessionId.value) || null
  )

  const pinnedSessions = computed(() =>
    sessions.value.filter((s) => s.is_pinned === 1)
  )

  const normalSessions = computed(() =>
    sessions.value.filter((s) => s.is_pinned !== 1)
  )

  // ── 会话 ──
  async function loadSessions() {
    loadingSessions.value = true
    try {
      sessions.value = await ChatSessionAPI.list()
    } catch {
      // 静默处理
    } finally {
      loadingSessions.value = false
    }
  }

  async function createSession(title?: string, contextJson?: Record<string, any>) {
    const session = await ChatSessionAPI.create({
      title: title || "新对话",
      domain: "case",
      context_json: contextJson,
    })
    sessions.value.unshift(session)
    return session
  }

  async function selectSession(sessionId: number) {
    activeSessionId.value = sessionId
    await loadMessages(sessionId)
  }

  async function updateSession(sessionId: number, data: { title?: string; is_pinned?: number }) {
    await ChatSessionAPI.update(sessionId, data)
    await loadSessions()
  }

  async function deleteSession(sessionId: number) {
    await ChatSessionAPI.delete(sessionId)
    sessions.value = sessions.value.filter((s) => s.id !== sessionId)
    if (activeSessionId.value === sessionId) {
      activeSessionId.value = null
      messages.value = []
    }
  }

  // ── 消息 ──
  async function loadMessages(sessionId: number) {
    loadingMessages.value = true
    try {
      messages.value = await ChatMessageAPI.list(sessionId)

      // 为未完成的 task_card 启动状态监控
      await nextTick()
      await monitorIncompleteTasks()
    } catch {
      messages.value = []
    } finally {
      loadingMessages.value = false
    }
  }

  function addLocalMessage(msg: ChatMessage) {
    messages.value.push(msg)
  }

  /** 停止当前生成 */
  function stopGeneration() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    streaming.value = false
    streamingText.value = ""
    thinkingStep.value = ""
    toolSteps.value = []
  }

  /** 重试最后一条消息（发送最后一条用户消息） */
  async function retryLastMessage() {
    // 找到最后一条用户消息
    let lastUserContent = ""
    for (let i = messages.value.length - 1; i >= 0; i--) {
      if (messages.value[i].role === "user") {
        lastUserContent = messages.value[i].content || ""
        break
      }
    }
    if (!lastUserContent) return

    // 移除最后的 assistant 和 error 消息
    while (
      messages.value.length > 0 &&
      messages.value[messages.value.length - 1].role !== "user"
    ) {
      messages.value.pop()
    }

    await sendMessage(lastUserContent)
  }

  async function sendMessage(content: string): Promise<void> {
    if (!activeSessionId.value) {
      // 自动创建会话，带上页面上下文
      const session = await createSession(undefined, { ...pageContext.value })
      activeSessionId.value = session.id!
    }

    // 同步当前页面上下文到后端会话（用户可能切换了项目/模块）
    const ctx = pageContext.value
    if (ctx && Object.keys(ctx).length > 0 && activeSessionId.value) {
      await ChatContextAPI.set(activeSessionId.value, { context_json: ctx }).catch(() => {})
    }

    const sessionId = activeSessionId.value!

    // 添加用户消息到本地
    const userMsg: ChatMessage = {
      id: null,
      session_id: sessionId,
      role: "user",
      msg_type: "text",
      content,
      metadata_json: null,
      draft_id: null,
      create_time: new Date().toISOString(),
    }
    addLocalMessage(userMsg)

    streaming.value = true
    streamingText.value = ""
    thinkingStep.value = ""
    toolSteps.value = []

    // 创建新的 AbortController
    abortController = new AbortController()

    try {
      const req: MessageSendReq = { content }
      const response = await ChatMessageAPI.send(sessionId, req, abortController.signal)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error("No response body")

      const decoder = new TextDecoder()
      let buffer = ""
      let assistantContent = ""
      let assistantMsgType = "text" as ChatMessage["msg_type"]
      let draftType: string | undefined
      let draftData: Record<string, any> | undefined
      let skillName: string | undefined
      let messageMetadata: Record<string, any> = {}
      let draftId: number | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""

        let eventType = ""
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6).trim())

              switch (eventType) {
                case "thinking":
                  // Agent 初始心跳，仅表示模型正在思考，不写入 thinkingStep
                  // 由 StreamingBubble 默认显示「思考中...」
                  break

                case "chunk":
                  streamingText.value += data.content || ""
                  break

                case "skill_start":
                  skillName = data.skill_name
                  break

                case "tool_start":
                  // Agent 模式：工具开始执行，更新 thinking 状态
                  // 不再拼接到 streamingText，保持正文干净
                  thinkingStep.value = data.name || "处理中"
                  break

                case "tool_end":
                  // Agent 模式：工具执行完成
                  if (data.name) toolSteps.value.push(data.name)
                  thinkingStep.value = ""
                  // 不再把工具摘要拼入 streamingText
                  break

                case "message":
                  assistantContent = data.content || ""
                  assistantMsgType = data.msg_type || "text"
                  if (data.draft_type) draftType = data.draft_type
                  if (data.draft_data) draftData = data.draft_data
                  if (data.skill_name) skillName = data.skill_name
                  if (data.metadata) messageMetadata = data.metadata
                  break

                case "error":
                  // 不再只弹 toast，后续会作为错误消息插入列表
                  throw new Error(data.message || "服务端处理出错")
              }
            } catch (parseErr: any) {
              // 如果是主动抛出的错误，继续向上传播
              if (parseErr.message && !parseErr.message.includes("JSON")) {
                throw parseErr
              }
              // JSON 解析失败，跳过
            }
          }
        }
      }

      // SSE 流已结束，先关闭 streaming 占位符，再 push 真消息
      streaming.value = false

      // 把本次 Agent 调用的工具列表合并进 metadata，不依赖 message 事件
      if (toolSteps.value.length) {
        messageMetadata = {
          ...messageMetadata,
          tool_names: [...toolSteps.value],
          tool_calls: toolSteps.value.length,
        }
        // 如果还没有 skill_name 但有技能，补充进来
        if (!messageMetadata.skill_name && skillName) {
          messageMetadata.skill_name = skillName
        }
      }

      // 添加助手消息
      if (assistantContent || streamingText.value) {
        const assistantMsg: ChatMessage = {
          id: null,
          session_id: sessionId,
          role: "assistant",
          msg_type: assistantMsgType,
          content: assistantContent || streamingText.value,
          metadata_json: Object.keys(messageMetadata).length > 0
            ? messageMetadata
            : skillName
              ? { skill_name: skillName }
              : null,
          draft_id: draftId,
          create_time: new Date().toISOString(),
        }
        addLocalMessage(assistantMsg)

        // 如果有草稿数据，打开草稿面板
        if (draftType && draftData) {
          activeDraft.value = {
            id: null,
            session_id: sessionId,
            message_id: null,
            draft_type: draftType,
            title: draftType,
            content_json: draftData,
            status: "pending",
            confirmed_by: null,
            confirmed_at: null,
            create_time: null,
          }
          showDraftPanel.value = true
        }
      }

      // 刷新会话列表（更新消息计数和时间）
      await loadSessions()
    } catch (e: any) {
      // 如果是用户主动中断，不显示错误
      if (e.name === "AbortError") {
        // 保留已输出的部分内容作为消息
        if (streamingText.value) {
          const md: Record<string, any> = {}
          if (toolSteps.value.length) {
            md.tool_names = [...toolSteps.value]
            md.tool_calls = toolSteps.value.length
          }
          const partialMsg: ChatMessage = {
            id: null,
            session_id: sessionId,
            role: "assistant",
            msg_type: "text",
            content: streamingText.value + "\n\n*[已停止生成]*",
            metadata_json: Object.keys(md).length > 0 ? md : null,
            draft_id: null,
            create_time: new Date().toISOString(),
          }
          addLocalMessage(partialMsg)
        }
      } else {
        // 推送错误消息到列表
        const errMsg: ChatMessage = {
          id: null,
          session_id: sessionId,
          role: "system",
          msg_type: "error",
          content: e.message || "请求失败，请重试",
          metadata_json: {
            error: true,
            last_user_message: content,
          } as any,
          draft_id: null,
          create_time: new Date().toISOString(),
        }
        addLocalMessage(errMsg)
      }
    } finally {
      streaming.value = false
      streamingText.value = ""
      thinkingStep.value = ""
      abortController = null
    }
  }

  // ── 草稿 ──
  async function confirmDraft(action: "confirm" | "discard", editedContent?: Record<string, any>) {
    if (!activeDraft.value?.id) return
    try {
      await ChatDraftAPI.confirm(activeDraft.value.id, {
        action,
        edited_content: editedContent,
      })
      // 回写本地 draft_card 消息的 metadata_json
      const draftId = activeDraft.value.id
      for (let i = messages.value.length - 1; i >= 0; i--) {
        const m = messages.value[i]
        if (m.msg_type === "draft_card" && m.draft_id === draftId) {
          messages.value[i] = {
            ...m,
            metadata_json: { ...(m.metadata_json || {}), draft_status: action },
          }
          break
        }
      }
      if (action === "confirm") {
        ElMessage.success("草稿已确认")
      } else {
        ElMessage.info("草稿已丢弃")
      }
      showDraftPanel.value = false
      activeDraft.value = null
    } catch (e: any) {
      ElMessage.error(`操作失败: ${e.message}`)
    }
  }

  async function viewDraft(draftId: number) {
    try {
      activeDraft.value = await ChatDraftAPI.get(draftId)
      showDraftPanel.value = true
    } catch {
      ElMessage.error("加载草稿失败")
    }
  }

  function closeDraftPanel() {
    showDraftPanel.value = false
    activeDraft.value = null
  }

  // ── 任务确认 ──

  /** 活跃的任务状态轮询器: task_id → intervalId */
  const taskMonitors = new Map<number, ReturnType<typeof setInterval>>()

  onUnmounted(() => {
    taskMonitors.forEach((id) => clearInterval(id))
    taskMonitors.clear()
  })

  /** 创建/查找进度消息并轮询任务状态，完成后更新消息内容 */
  /** 更新确认创建的消息中的任务状态 */
  function updateConfirmCardTaskStatus(taskId: number, status: number, done: number, total: number) {
    const idx = messages.value.findIndex(
      m => m.msg_type === "task_card"
        && m.metadata_json?.task_id === taskId
        && !m.metadata_json?._task_progress
    )
    if (idx === -1) return
    const msg = messages.value[idx]
    messages.value[idx] = {
      ...msg,
      metadata_json: {
        ...(msg.metadata_json || {}),
        task_status: status,
        done_count: done,
        total_count: total,
      },
    }
  }

  function startTaskMonitor(taskId: number, skillName: string) {
    if (taskMonitors.has(taskId)) return

    const intervalId = setInterval(async () => {
      try {
        const detail = await TaskAPI.getDetail(String(taskId))
        const task = detail.task

        // 更新确认消息中的任务状态（不创建进度消息）
        updateConfirmCardTaskStatus(taskId, task.status, task.done_count ?? 0, task.total_count ?? 0)

        if (task.status >= 2) {
          // COMPLETED(2) 或 FAILED(3) — 停止轮询
          clearInterval(intervalId)
          taskMonitors.delete(taskId)
        }
      } catch {
        // 静默处理轮询错误
      }
    }, 2000)

    taskMonitors.set(taskId, intervalId)
  }

  /** 为已加载的历史消息中未完成任务启动监控，同时补齐已完成/失败任务的计数 */
  async function monitorIncompleteTasks() {
    for (let i = 0; i < messages.value.length; i++) {
      const msg = messages.value[i]
      if (msg.msg_type !== "task_card") continue
      const taskId = msg.metadata_json?.task_id
      if (!taskId) continue

      // 消息中已有明确的完成/失败状态
      const ts = msg.metadata_json?.task_status
      if (ts != null && ts >= 2) {
        // 已完成/失败但缺少计数，从服务端补齐
        if ((msg.metadata_json?.done_count ?? 0) === 0 && (msg.metadata_json?.total_count ?? 0) === 0) {
          try {
            const detail = await TaskAPI.getDetail(String(taskId))
            const task = detail.task
            messages.value[i] = {
              ...msg,
              metadata_json: {
                ...(msg.metadata_json || {}),
                task_id: taskId,
                task_status: task.status,
                done_count: task.done_count,
                total_count: task.total_count,
              },
            }
          } catch { /* 静默 */ }
        }
        continue
      }

      // 未完成任务，先查询任务实际状态
      if (taskMonitors.has(taskId)) continue

      try {
        const detail = await TaskAPI.getDetail(String(taskId))
        const task = detail.task
        // 先更新当前消息的计数
        messages.value[i] = {
          ...msg,
          metadata_json: {
            ...(msg.metadata_json || {}),
            task_id: taskId,
            task_status: task.status,
            done_count: task.done_count,
            total_count: task.total_count,
          },
        }
        if (task.status >= 2) continue
        const skillName = msg.metadata_json?.skill_name || ""
        startTaskMonitor(taskId, skillName)
      } catch {
        // 静默处理
      }
    }
  }

  async function confirmCreateTask(metadata: Record<string, any>) {
    if (!activeSessionId.value) return

    const sessionId = activeSessionId.value
    const skillName = metadata.skill_name || ""
    const projectId = metadata.project_id
    const suiteId = metadata.suite_id
    const caseIds: number[] | undefined = metadata.case_ids ?? undefined
    const selectedOption = metadata._selected_option as string | undefined

    try {
      const res = await ChatTaskAPI.confirmCreate(sessionId, {
        skill_name: skillName,
        project_id: projectId,
        suite_id: suiteId,
        case_ids: caseIds ?? null,
        selected_option: selectedOption ?? null,
      })

      const taskId = res.task_id
      const total = res.total_count ?? metadata.total ?? 0
      const label = TASK_TYPE_MAP[skillName]?.label || skillName
      const scopeDesc = caseIds?.length ? `已选中的 ${caseIds.length} 条` : '当前模块下的'
      const content = `已创建${label}任务，将对${scopeDesc}用例逐条处理。完成后可点击查看。`

      // 本地追加 task_card 消息（不调用 loadMessages，避免数组替换闪烁）
      const taskMsg: ChatMessage = {
        id: null,
        session_id: sessionId,
        role: "assistant",
        msg_type: "task_card",
        content,
        metadata_json: {
          skill_name: skillName,
          task_id: taskId,
          project_id: projectId,
          suite_id: suiteId,
          total,
          task_status: 0,
          done_count: 0,
          total_count: total,
        },
        draft_id: null,
        create_time: new Date().toISOString(),
      }
      messages.value.push(taskMsg)

      // 回写本地 confirm_card 消息的 metadata_json，标记已确认
      updateLastUnconfirmedCardInMessages("confirmed", selectedOption)

      await loadSessions()

      // 启动任务状态轮询
      if (taskId) {
        startTaskMonitor(taskId, skillName)
      }

      ElMessage.success("任务已创建")
    } catch (e: any) {
      ElMessage.error(`创建任务失败: ${e.message || e}`)
      throw e
    }
  }

  async function cancelTask(_metadata: Record<string, any>) {
    if (!activeSessionId.value) return
    try {
      await ChatMessageAPI.cancelConfirm(activeSessionId.value)
      updateLastUnconfirmedCardInMessages("cancelled")
    } catch {
      // 静默处理
    }
    ElMessage.info("已取消创建")
  }

  /** 找到 messages 中最后一条未处理的 confirm_card，更新其 metadata_json */
  function updateLastUnconfirmedCardInMessages(status: string, selectedOption?: string) {
    for (let i = messages.value.length - 1; i >= 0; i--) {
      const m = messages.value[i]
      if (m.msg_type === "confirm_card" && !m.metadata_json?.confirm_status) {
        const meta: Record<string, any> = { ...(m.metadata_json || {}), confirm_status: status }
        if (selectedOption) meta._selected_option = selectedOption
        messages.value[i] = { ...m, metadata_json: meta }
        break
      }
    }
  }

  /** 将最后一条 clarify_card 标记为已提交，并将答案持久化 */
  async function submitClarifyAnswers(answers: Record<string, string>) {
    // 本地更新
    for (let i = messages.value.length - 1; i >= 0; i--) {
      const m = messages.value[i]
      if (m.msg_type === "clarify_card" && !m.metadata_json?.clarify_status) {
        messages.value[i] = {
          ...m,
          metadata_json: {
            ...(m.metadata_json || {}),
            clarify_status: "submitted",
            clarify_answers: answers,
          },
        }
        break
      }
    }
    // 持久化到后端
    if (activeSessionId.value) {
      ChatMessageAPI.updateCardStatus(activeSessionId.value, {
        msg_type: "clarify_card",
        metadata: { clarify_status: "submitted", clarify_answers: answers },
      }).catch(() => {})
    }
  }

  // ── 技能 ──
  async function loadSkills() {
    try {
      skills.value = await ChatSkillAPI.list()
    } catch {
      skills.value = []
    }
  }

  // ── 初始化 ──
  async function init() {
    await Promise.all([loadSessions(), loadSkills()])
  }

  return {
    // 状态
    sessions,
    activeSessionId,
    activeSession,
    pinnedSessions,
    normalSessions,
    messages,
    skills,
    loading,
    loadingSessions,
    loadingMessages,
    streaming,
    streamingText,
    thinkingStep,
    toolSteps,
    activeDraft,
    showDraftPanel,
    pageContext,

    // 方法
    loadSessions,
    createSession,
    selectSession,
    updateSession,
    deleteSession,
    loadMessages,
    sendMessage,
    stopGeneration,
    retryLastMessage,
    confirmDraft,
    viewDraft,
    closeDraftPanel,
    confirmCreateTask,
    cancelTask,
    submitClarifyAnswers,
    loadSkills,
    monitorIncompleteTasks,
    init,
  }
}
