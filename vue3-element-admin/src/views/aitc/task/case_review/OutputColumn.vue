<template>
  <div class="text-sm">
    <div v-if="output.score !== undefined">
      评分: <b>{{ output.score }}</b>
      <div v-if="output.fields?.length" class="mt-1">
        <span class="text-green-600 text-xs">{{ passedCount }} 合格</span>
        <span v-if="failedCount > 0" class="text-red-500 text-xs ml-1">{{ failedCount }} 不合格</span>
      </div>
      <div v-if="output.issues" class="text-red-500 text-xs">
        {{ Array.isArray(output.issues) ? output.issues.join('; ') : output.issues }}
      </div>
    </div>
    <div v-else class="text-xs text-gray-400">无评分</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue"

const props = defineProps<{
  output: Record<string, any>
}>()

const passedCount = computed(() => {
  if (!Array.isArray(props.output.fields)) return 0
  return props.output.fields.filter((f: any) => f.conclusion === "pass").length
})

const failedCount = computed(() => {
  if (!Array.isArray(props.output.fields)) return 0
  return props.output.fields.filter((f: any) => f.conclusion === "fail").length
})
</script>
