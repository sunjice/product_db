/** AI 调用日志 — API 封装 + 类型定义 */

import request from "@/utils/request"
import type { PageResult } from "@/api/common"

// ── 类型 ──

export interface LlmLogItem {
  id: number
  trace_id: string
  span_seq: number
  attempt: number
  module: string
  action: string
  session_id: number | null
  task_id: number | null
  message_id: number | null
  model: string
  status: string
  error_msg: string | null
  prompt_tokens: number
  completion_tokens: number
  duration_ms: number
  create_time: string | null
}

export interface LlmLogDetail extends LlmLogItem {
  messages: Record<string, any> | null
  response_raw: string | null
  response_json: Record<string, any> | null
}

export interface LlmLogSession {
  session_id: number
  last_time: string | null
  log_count: number
}

export interface LlmLogQuery {
  pageNum: number
  pageSize: number
  session_id?: number | null
  trace_id?: string
  action?: string
  status?: string
  module?: string
}

// ── API ──

export const LlmLogAPI = {
  /** 分页列表 */
  getPage(params: LlmLogQuery) {
    // 过滤掉 null/undefined/"" 避免后端 422
    const clean: Record<string, any> = {}
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== "") clean[k] = v
    })
    return request<unknown, PageResult<LlmLogItem>>({
      url: "/api/v1/llm-logs",
      method: "get",
      params: clean,
    })
  },

  /** 单条详情（含 messages / response） */
  getDetail(logId: number) {
    return request<unknown, LlmLogDetail>({
      url: `/api/v1/llm-logs/${logId}`,
      method: "get",
    })
  },

  /** 有日志的会话列表 */
  getSessions() {
    return request<unknown, LlmLogSession[]>({
      url: "/api/v1/llm-logs/sessions/list",
      method: "get",
    })
  },

  /** 导出日志文件（返回 blob 下载） */
  async export(params: {
    format: "json" | "txt"
    session_id?: number | null
    trace_id?: string
    action?: string
    status?: string
    module?: string
  }) {
    const baseURL = import.meta.env.VITE_APP_BASE_API || ""
    const token = localStorage.getItem("accessToken") || ""
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        searchParams.set(k, String(v))
      }
    })
    const resp = await fetch(
      `${baseURL}/api/v1/llm-logs/export?${searchParams.toString()}`,
      {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      }
    )
    if (!resp.ok) throw new Error("导出失败")
    const blob = await resp.blob()
    const filename = params.format === "txt" ? "llm_logs.txt" : "llm_logs.json"
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  },
}
