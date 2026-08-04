<template>
  <el-card v-if="records.length > 0" class="mb-3">
    <template #header><span class="font-bold">审核记录</span></template>
    <el-table :data="records" border stripe size="small" max-height="300">
      <el-table-column prop="reviewer" label="审核人" width="100" />
      <el-table-column prop="reviewer_ip" label="IP" width="140" />
      <el-table-column label="操作" width="120" align="center">
        <template #default="{ row }">
          <el-tag :type="reviewActionTag(row.review_action)" size="small">
            {{ reviewActionLabel(row.review_action) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="field_name" label="字段" width="120">
        <template #default="{ row }">{{ row.field_name || '—' }}</template>
      </el-table-column>
      <el-table-column label="审核前" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="text-xs text-gray-500">{{ formatRecordValue(row.before_value) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="审核后" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="text-xs text-green-600">{{ formatRecordValue(row.after_value) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="review_time" label="审核时间" width="160" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import type { ReviewRecordVO } from "@/api/aitc/task";
import { reviewActionLabel, reviewActionTag } from "../../constants";

defineProps<{
  records: ReviewRecordVO[];
}>();

function formatRecordValue(val?: string) {
  if (!val) return "—";
  try {
    const obj = JSON.parse(val);
    if (typeof obj === "object" && obj !== null) {
      if (Array.isArray(obj)) return `[${obj.length} 项]`;
      const keys = Object.keys(obj);
      if (keys.length <= 2) return keys.map(k => `${k}: ${String(obj[k]).slice(0, 40)}`).join(", ");
      return `{${keys.length} 个字段}`;
    }
    return String(obj).slice(0, 80);
  } catch {
    return val.slice(0, 80);
  }
}
</script>
