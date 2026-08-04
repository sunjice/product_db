/**
 * Chat 组件共享工具函数
 */

/** 简单 Markdown 渲染：转义 HTML、粗体、行内代码、换行 */
export function renderSimpleMd(t: string): string {
  if (!t) return ""
  let s = t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>")
  s = s.replace(/\n/g, "<br>")
  return s
}

/** 格式化时间为 HH:mm */
export function formatTimeHM(time: string | null): string {
  if (!time) return ""
  const d = new Date(time)
  const h = String(d.getHours()).padStart(2, "0")
  const m = String(d.getMinutes()).padStart(2, "0")
  return `${h}:${m}`
}

/** 格式化历史时间：今天→HH:mm，否则→M/D */
export function formatHistoryTime(time: string | null): string {
  if (!time) return ""
  const d = new Date(time)
  const now = new Date()
  if (d.toDateString() === now.toDateString())
    return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })
  return d.toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" })
}
