<template>
  <!-- 等待模型响应 -->
  <div v-if="!streamingText && !thinkingStep && !doneToolSteps.length" class="streaming waiting-state">
    <span class="waiting-cursor"></span>
  </div>

  <!-- 工具执行中 / 已完成工具历史 -->
  <div v-else-if="thinkingStep || doneToolSteps.length" class="streaming tool-state">
    <div class="tool-info">
      <!-- 已完成工具列表 -->
      <div v-for="(name, i) in doneToolSteps" :key="'done-' + i" class="tool-badge done">
        <el-icon class="tool-check"><Check /></el-icon>
        <span>{{ toolLabel(name) }}</span>
      </div>
      <!-- 当前正在执行的工具 -->
      <div v-if="thinkingStep" class="tool-badge active">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>{{ toolLabel(thinkingStep) }}</span>
      </div>
      <!-- 有文字流时同时展示 -->
      <div v-if="streamingText" class="streaming-text" v-html="renderedText" />
    </div>
  </div>

  <!-- 流式输出：有 chunk 但无工具活动 -->
  <div v-else class="streaming text-state">
    <div class="streaming-text" v-html="renderedText" />
    <span class="cursor">|</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { Loading, Check } from "@element-plus/icons-vue"
import { toolLabel } from "./constants"
import { renderStreamingMarkdown } from "./utils"

const props = defineProps<{
  streamingText: string
  thinkingStep: string
  toolSteps: string[]
}>()

/**
 * 流式 Markdown 渲染：先截掉末尾未闭合的 **、``` 等标记，
 * 其余部分正常走 markdown-it 渲染。效果接近 ChatGPT 的渐进格式。
 */
const renderedText = computed(() => {
  return renderStreamingMarkdown(props.streamingText || "")
})

/** 已完成工具去重，并过滤空名称 */
const doneToolSteps = computed(() => {
  if (!Array.isArray(props.toolSteps)) return []
  return [...new Set(props.toolSteps.filter((n: string) => !!n))]
})
</script>

<style scoped>
.streaming {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 4px 12px;
}

.streaming-text {
  flex: 1;
  line-height: 1.55;
  font-size: 12.5px;
  color: var(--el-text-color-primary);
  word-break: break-word;
}

/* ── 流式 Markdown 样式（与 ChatMessage .msg-text 保持一致）── */
.streaming-text :deep(p) {
  margin: 0 0 3px;
}
.streaming-text :deep(p:last-child) {
  margin-bottom: 0;
}
.streaming-text :deep(ul),
.streaming-text :deep(ol) {
  margin: 3px 0;
  padding-left: 18px;
}
.streaming-text :deep(li) {
  margin-bottom: 1px;
}
.streaming-text :deep(h1),
.streaming-text :deep(h2),
.streaming-text :deep(h3),
.streaming-text :deep(h4) {
  margin: 6px 0 3px;
  font-weight: 600;
  line-height: 1.3;
}
.streaming-text :deep(h1) { font-size: 15px; }
.streaming-text :deep(h2) { font-size: 14px; }
.streaming-text :deep(h3) { font-size: 13px; }
.streaming-text :deep(h4) { font-size: 12.5px; }
.streaming-text :deep(strong) {
  font-weight: 500;
  color: var(--el-text-color-primary);
}
.streaming-text :deep(code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 0 3px;
  border-radius: 3px;
  font-size: 11px;
  font-family: "SF Mono", "Fira Code", Consolas, monospace;
}
.streaming-text :deep(blockquote) {
  margin: 3px 0;
  padding: 2px 10px;
  border-left: 3px solid var(--el-color-primary-light-5);
  background: var(--el-fill-color-light);
  color: var(--el-text-color-secondary);
  border-radius: 0 6px 6px 0;
}
.streaming-text :deep(a) {
  color: var(--el-color-primary);
  text-decoration: underline;
}
.streaming-text :deep(.md-code-block) {
  background: #1e1e2e;
  border-radius: 6px;
  margin: 3px 0;
  overflow: hidden;
}
.streaming-text :deep(.md-code-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 3px 10px;
  background: rgba(255, 255, 255, 0.06);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.streaming-text :deep(.md-code-lang) {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.55);
  text-transform: uppercase;
}
.streaming-text :deep(.md-code-copy) {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.65);
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10px;
  cursor: pointer;
}
.streaming-text :deep(.hljs) {
  display: block;
  padding: 7px 10px;
  overflow-x: auto;
  font-size: 11px;
  line-height: 1.45;
  font-family: "SF Mono", "Fira Code", Consolas, monospace;
  color: #cdd6f4;
}
.streaming-text :deep(.hljs-keyword) { color: #cba6f7; }
.streaming-text :deep(.hljs-string) { color: #a6e3a1; }
.streaming-text :deep(.hljs-number) { color: #fab387; }
.streaming-text :deep(.hljs-comment) { color: #6c7086; font-style: italic; }
.streaming-text :deep(.hljs-function) { color: #89b4fa; }
.streaming-text :deep(.hljs-title) { color: #89b4fa; }
.streaming-text :deep(.hljs-type) { color: #f9e2af; }
.streaming-text :deep(.hljs-literal) { color: #fab387; }
.streaming-text :deep(.hljs-built_in) { color: #f38ba8; }
.streaming-text :deep(.hljs-attr) { color: #89b4fa; }
.streaming-text :deep(.hljs-params) { color: #f2cdcd; }
.streaming-text :deep(.hljs-meta) { color: #f5c2e7; }
.streaming-text :deep(.hljs-property) { color: #89b4fa; }
.streaming-text :deep(.hljs-variable) { color: #f38ba8; }

.waiting-state {
  padding: 7px 12px 4px;
}

.waiting-cursor {
  display: inline-block;
  width: 5px;
  height: 14px;
  background: var(--el-color-primary);
  border-radius: 2px;
  animation: waitPulse 0.8s ease-in-out infinite;
}

@keyframes waitPulse {
  0%, 100% { opacity: 0.25; }
  50% { opacity: 1; }
}

.cursor {
  animation: blink 1s infinite;
  color: var(--el-color-primary);
  font-weight: bold;
  font-size: 12.5px;
  line-height: 1.55;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.tool-state {
  align-items: flex-start;
}

.tool-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tool-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-5);
  color: var(--el-color-primary);
  font-size: 11px;
  line-height: 1.35;
  width: fit-content;
}

.tool-badge.active {
  animation: toolEntry 0.3s ease-out;
}

.tool-badge.done {
  opacity: 0.7;
  background: var(--el-fill-color);
  border-color: var(--el-border-color-lighter);
  color: var(--el-text-color-secondary);
}

.tool-badge .el-icon {
  font-size: 12px;
}

.tool-check {
  color: var(--el-color-success);
}

@keyframes toolEntry {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.text-state {
  padding: 4px 12px;
}
</style>
