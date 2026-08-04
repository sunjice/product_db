<template>
  <el-dialog v-model="visible" title="导入结果" width="500px">
    <div class="mb-2">新增 {{ importResult.created }} 条，更新 {{ importResult.updated }} 条</div>
    <div v-if="importResult.errors.length > 0" class="mt-2">
      <div class="text-red-500 mb-1">以下行导入失败：</div>
      <div v-for="e in importResult.errors" :key="e.row" class="text-xs text-gray-600">
        第 {{ e.row }} 行：{{ e.msg }}
      </div>
    </div>
    <template #footer>
      <el-button type="primary" @click="visible = false">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ImportResult } from "@/api/aitc/case";

const props = defineProps<{
  modelValue: boolean;
  importResult: ImportResult;
}>();

const emit = defineEmits<{
  "update:modelValue": [val: boolean];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});
</script>
