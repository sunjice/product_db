/**
 * PageAgent 封装层（Spike 阶段）
 *
 * 用法:
 *   const { isReady, isRunning, execute, dispose } = usePageAgent()
 *   const result = await execute('点击项目选择器，选择 XX 项目')
 *
 * 配置: 在 .env.development.local 中设置，变量名 VITE_AGENT_* 前缀
 *       （.gitignore 已排除 *.local，不会提交到仓库）
 */
import { PageAgent } from 'page-agent'
import type { PageAgentCore } from 'page-agent'
import { ref } from 'vue'

// ═══════ Spike 阶段：直连 LLM（之后切回后端代理时删除） ═══════
const AGENT_BASE_URL = import.meta.env.VITE_AGENT_BASE_URL || ''
const AGENT_API_KEY  = import.meta.env.VITE_AGENT_API_KEY || ''
const AGENT_MODEL    = import.meta.env.VITE_AGENT_MODEL || ''

// 内部使用 PageAgent（含 Panel），但通过 dispose 掉 panel 后，行为和 PageAgentCore 一致
let agentInstance: PageAgent | null = null

export interface AgentExecutionResult {
  success: boolean
  data: string
  steps: number
  durationMs: number
  history: any[]
}

export function usePageAgent() {
  const isReady = ref(false)
  const isRunning = ref(false)

  function getOrCreateAgent(): PageAgentCore {
    if (!agentInstance) {
      const baseURL = AGENT_BASE_URL
      const apiKey  = AGENT_API_KEY
      const model    = AGENT_MODEL

      if (!baseURL || !apiKey || !model) {
        throw new Error(
          'PageAgent 配置缺失，请修改 usePageAgent.ts 顶部的 AGENT_* 常量'
        )
      }

      console.debug('[PageAgent] 初始化', { baseURL, model })

      agentInstance = new PageAgent({
        baseURL,
        apiKey,
        model,
        language: 'zh-CN',
        maxSteps: 20,
        // 关闭所有视觉反馈：遮罩、高亮、标签
        enableMask: false,
        highlightOpacity: 0,
        highlightLabelOpacity: 0,
        // Azure OpenAI 不兼容 thinking 参数，请求发出前删掉它
        transformRequestBody: (body: Record<string, unknown>) => {
          if ('thinking' in body) {
            const { thinking, ...rest } = body
            return rest
          }
          return undefined
        },
      })

      // 彻底销毁 Panel UI（PageAgentCore 本就无 UI，这里通过 dispose 等效实现）
      agentInstance.panel.dispose()

      // 监听事件用于调试
      agentInstance.addEventListener('statuschange', () => {
        console.debug(`[PageAgent] status: ${agentInstance!.status}`)
      })

      agentInstance.addEventListener('activity', ((e: CustomEvent) => {
        const activity = e.detail
        if (activity) {
          console.debug(`[PageAgent] ${activity.type}`, activity)
        }
      }) as EventListener)

      isReady.value = true
    }
    return agentInstance
  }

  /**
   * 执行一个页面操作任务
   * @param task 自然语言指令，例如 "点击项目选择器，选择【XX 项目】"
   * @returns 执行结果
   */
  async function execute(task: string): Promise<AgentExecutionResult> {
    const startTime = performance.now()
    isRunning.value = true

    try {
      const agent = getOrCreateAgent()
      const result = await agent.execute(task)

      const durationMs = Math.round(performance.now() - startTime)
      isRunning.value = false

      return {
        success: result.success,
        data: result.data,
        steps: result.history.filter((e: any) => e.type === 'step').length,
        durationMs,
        history: result.history,
      }
    } catch (e: any) {
      isRunning.value = false
      const durationMs = Math.round(performance.now() - startTime)
      return {
        success: false,
        data: e?.message || String(e),
        steps: 0,
        durationMs,
        history: [],
      }
    }
  }

  /** 停止当前任务 */
  async function stop() {
    if (agentInstance) {
      await agentInstance.stop()
      isRunning.value = false
    }
  }

  /** 销毁 agent 实例 */
  function dispose() {
    if (agentInstance) {
      agentInstance.dispose()
      agentInstance = null
      isReady.value = false
      isRunning.value = false
    }
  }

  return { isReady, isRunning, execute, stop, dispose }
}
