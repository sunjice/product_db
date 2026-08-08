<template>
  <div class="text-sm">
    <span :class="output.selected ? 'text-green-600' : 'text-gray-400'">
      {{ output.selected ? '★ 核心' : '非核心' }}
    </span>
    <span class="ml-2 text-gray-500">— {{ output.reason || '' }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  output: Record<string, any>;
}>();
</script>
