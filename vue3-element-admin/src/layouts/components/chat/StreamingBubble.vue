<template>
  <!-- 思考中：模型正在推理，尚未输出文字 -->
  <div v-if="!streamingText && !thinkingStep" class="streaming thinking-state">
    <el-avatar :size="28" style="background: var(--el-color-primary)">
      <el-icon><ChatDotRound /></el-icon>
    </el-avatar>
    <div class="thinking-text">
      Thinking
      <span class="thinking-dots"><i>.</i><i>.</i><i>.</i></span>
    </div>
  </div>

  <!-- 工具执行中：显示调用什么工具 -->
  <div v-else-if="thinkingStep" class="streaming tool-state">
    <el-avatar :size="28" style="background: var(--el-color-primary)">
      <el-icon><ChatDotRound /></el-icon>
    </el-avatar>
    <div class="tool-info">
      <div class="tool-badge">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>{{ label }}</span>
      </div>
      <div v-if="streamingText" class="streaming-text" v-html="renderedText" />
    </div>
  </div>

  <!-- 流式输出：有 chunk 文字流时显示打字效果 -->
  <div v-else class="streaming">
    <el-avatar :size="28" style="background: var(--el-color-primary)">
      <el-icon><ChatDotRound /></el-icon>
    </el-avatar>
    <div class="streaming-text" v-html="renderedText" />
    <span class="cursor">|</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { ChatDotRound, Loading } from "@element-plus/icons-vue"
import { toolLabel } from "./constants"
import { renderSimpleMd } from "./utils"

const props = defineProps<{
  streamingText: string
  thinkingStep: string
}>()

const label = computed(() => toolLabel(props.thinkingStep))
const renderedText = computed(() => renderSimpleMd(props.streamingText))
</script>

<style scoped>
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
  color: var(--el-text-color-primary) !important;
}

.streaming-text :deep(*) {
  color: inherit !important;
}

.streaming-text :deep(code) {
  background: var(--el-fill-color);
  padding: 1px 4px;
  border-radius: 3px;
}

.streaming.thinking-state {
  padding: 10px 10px 6px;
}

.thinking-text {
  font-size: 12px;
  line-height: 1.55;
  color: var(--el-text-color-primary);
  display: flex;
  align-items: center;
}

.thinking-dots i {
  font-style: normal;
  animation: dotPulse 1.4s infinite ease-in-out both;
  display: inline-block;
}

.thinking-dots i:nth-child(1) { animation-delay: -0.32s; }
.thinking-dots i:nth-child(2) { animation-delay: -0.16s; }
.thinking-dots i:nth-child(3) { animation-delay: 0s; }

@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.2; }
  40% { opacity: 1; }
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

.tool-state { align-items: flex-start; }

.tool-info {
  flex: 1;
  min-width: 0;
}

.tool-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  margin-bottom: 6px;
  border-radius: 12px;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-5);
  color: var(--el-color-primary);
  font-size: 11px;
  line-height: 1.4;
}

.tool-badge .el-icon {
  font-size: 13px;
}
</style>
