<template>
  <div class="text-sm text-gray-500">
    {{ output.language || 'python' }} / {{ output.framework || 'pytest' }}
  </div>
</template>

<script setup lang="ts">
defineProps<{
  output: Record<string, any>
}>()
</script>
