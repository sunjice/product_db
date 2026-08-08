/**
 * Chat 组件共享工具函数
 */

import MarkdownIt from "markdown-it"
import hljs from "highlight.js/lib/core"
// 按需注册常用语言
import javascript from "highlight.js/lib/languages/javascript"
import typescript from "highlight.js/lib/languages/typescript"
import python from "highlight.js/lib/languages/python"
import json from "highlight.js/lib/languages/json"
import xml from "highlight.js/lib/languages/xml"
import bash from "highlight.js/lib/languages/bash"
import sql from "highlight.js/lib/languages/sql"
import yaml from "highlight.js/lib/languages/yaml"
import css from "highlight.js/lib/languages/css"
import plaintext from "highlight.js/lib/languages/plaintext"

hljs.registerLanguage("javascript", javascript)
hljs.registerLanguage("js", javascript)
hljs.registerLanguage("typescript", typescript)
hljs.registerLanguage("ts", typescript)
hljs.registerLanguage("python", python)
hljs.registerLanguage("py", python)
hljs.registerLanguage("json", json)
hljs.registerLanguage("xml", xml)
hljs.registerLanguage("html", xml)
hljs.registerLanguage("bash", bash)
hljs.registerLanguage("sh", bash)
hljs.registerLanguage("shell", bash)
hljs.registerLanguage("sql", sql)
hljs.registerLanguage("yaml", yaml)
hljs.registerLanguage("yml", yaml)
hljs.registerLanguage("css", css)
hljs.registerLanguage("plaintext", plaintext)
hljs.registerLanguage("text", plaintext)

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight(str: string, lang: string): string {
    const code = str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;")
    const langLabel = lang || "text"
    if (lang && hljs.getLanguage(lang)) {
      try {
        const highlighted = hljs.highlight(str, { language: lang, ignoreIllegals: true }).value
        return (
          `<pre class="md-code-block"><div class="md-code-header">` +
          `<span class="md-code-lang">${langLabel}</span>` +
          `<button class="md-code-copy" data-code="${code}">复制</button></div>` +
          `<code class="hljs language-${lang}">${highlighted}</code></pre>`
        )
      } catch {
        // fallback
      }
    }
    return (
      `<pre class="md-code-block"><div class="md-code-header">` +
      `<span class="md-code-lang">${langLabel}</span>` +
      `<button class="md-code-copy" data-code="${code}">复制</button></div>` +
      `<code class="hljs">${md.utils.escapeHtml(str)}</code></pre>`
    )
  },
})

/** 完整 Markdown 渲染，自动为表格添加下载按钮 */
export function renderMarkdown(text: string): string {
  if (!text) return ""
  let html = md.render(text)
  // 检测是否有表格，若有则给每个表格包一层工具栏容器
  if (html.includes("<table>")) {
    html = html.replace(
      /<table>/g,
      '<div class="md-table-wrapper"><div class="md-table-toolbar"><span class="md-table-label">表格</span><button class="md-table-download" data-action="download-table">下载 Excel</button></div><table>'
    )
    html = html.replace(/<\/table>/g, "</table></div>")
  }
  return html
}

/**
 * 从 HTML table 元素提取数据并导出为 Excel
 */
export async function exportTableToExcel(tableEl: HTMLTableElement, filename?: string) {
  const rows: string[][] = []
  for (const tr of tableEl.rows) {
    const row: string[] = []
    for (const cell of tr.cells) {
      row.push(cell.textContent?.trim() || "")
    }
    rows.push(row)
  }

  if (rows.length === 0) return

  // exceljs 在浏览器端必须动态 import
  const ExcelJS = await import("exceljs")
  const workbook = new ExcelJS.Workbook()
  const sheet = workbook.addWorksheet("Sheet1")

  // 表头行（第一行）加粗 + 浅灰背景
  const headerRow = sheet.addRow(rows[0])
  if (rows.length > 1) {
    headerRow.font = { bold: true }
    headerRow.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: "F0F0F0" },
    }
  }

  // 剩余数据行
  for (let i = 1; i < rows.length; i++) {
    sheet.addRow(rows[i])
  }

  // 自适应列宽
  sheet.columns = rows[0].map((_, colIdx) => {
    const maxLen = Math.min(
      Math.max(...rows.map((r) => (r[colIdx] || "").length), rows[0][colIdx]?.length || 8),
      50
    )
    return { width: maxLen + 4 }
  })

  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `${filename || "表格数据"}.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

/**
 * 截掉末尾未闭合的 Markdown 标记，适配流式渲染。
 * 业界常见做法：渲染前检测末尾的 **、``` 等待闭合标记，
 * 只渲染"已闭合"的部分，未闭合尾部暂不渲染。
 */
function stripIncompleteTail(text: string): string {
  let result = text

  // 去掉末尾未闭合的围栏代码块 ```
  {
    const parts = result.split("```")
    if (parts.length % 2 === 0) {
      // 偶数段 → ``` 出现奇数次 → 最后一个未闭合
      result = parts.slice(0, -1).join("```")
    }
  }

  // 去掉末尾未闭合的加粗 **
  {
    const parts = result.split("**")
    if (parts.length % 2 === 0) {
      result = parts.slice(0, -1).join("**")
    }
  }

  return result
}

/** 流式 Markdown 渲染：先截掉未闭合标记，再渲染 */
export function renderStreamingMarkdown(text: string): string {
  if (!text) return ""
  const safe = stripIncompleteTail(text)
  if (!safe) return ""
  return md.render(safe)
}

/** 设置代码块复制按钮的事件委托（在消息容器上调用一次即可） */
export function setupCodeCopy(container: HTMLElement) {
  container.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest(".md-code-copy") as HTMLElement | null
    if (!btn) return
    const code = btn.getAttribute("data-code")
    if (!code) return
    navigator.clipboard.writeText(code).then(() => {
      btn.textContent = "已复制"
      setTimeout(() => {
        btn.textContent = "复制"
      }, 2000)
    })
  })
}

/** 格式化时间为 HH:mm */
export function formatTimeHM(time: string | null): string {
  if (!time) return ""
  const d = new Date(time)
  const h = String(d.getHours()).padStart(2, "0")
  const m = String(d.getMinutes()).padStart(2, "0")
  return `${h}:${m}`
}

/** 格式化完整时间 */
export function formatFullTime(time: string | null): string {
  if (!time) return ""
  const d = new Date(time)
  const y = d.getFullYear()
  const M = String(d.getMonth() + 1).padStart(2, "0")
  const day = String(d.getDate()).padStart(2, "0")
  const h = String(d.getHours()).padStart(2, "0")
  const m = String(d.getMinutes()).padStart(2, "0")
  const s = String(d.getSeconds()).padStart(2, "0")
  return `${y}-${M}-${day} ${h}:${m}:${s}`
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
