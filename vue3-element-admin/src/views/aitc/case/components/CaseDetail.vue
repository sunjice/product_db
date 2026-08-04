<template>
  <div>
    <div class="mb-2 flex items-center gap-2">
      <el-button text @click="$emit('back')">
        <el-icon><ArrowLeft /></el-icon> 返回列表
      </el-button>
      <span class="text-xs text-gray-500 flex-1">{{ viewingCase.project_prefix }}{{ viewingCase.external_id }}__{{ viewingCase.name }} — {{ viewingCase.purpose || viewingCase.name }}</span>
      <el-button type="primary" size="small" v-hasPerm="'aitc:case:update'" @click="$emit('startEdit', viewingCase)">编辑</el-button>
    </div>
    <el-descriptions :column="2" border size="small" label-width="80px">
      <el-descriptions-item label="用例编号" :span="2">{{ viewingCase.project_prefix }}{{ viewingCase.external_id }}__{{ viewingCase.name }}</el-descriptions-item>
      <el-descriptions-item label="测试目的" :span="2">{{ viewingCase.purpose || '—' }}</el-descriptions-item>
      <el-descriptions-item label="级别">
        <el-tag :type="importanceType(viewingCase.importance)" size="small">
          {{ importanceLabel(viewingCase.importance) }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="样本用例">
        <span v-if="viewingCase.is_sample" class="text-green-500">✓ 是</span>
        <span v-else>否</span>
      </el-descriptions-item>
      <el-descriptions-item label="核心用例">
        <span v-if="viewingCase.is_core" class="text-orange-500">★ 是</span>
        <span v-else>否</span>
      </el-descriptions-item>
      <el-descriptions-item label="核心来源">
        {{ coreSourceLabel(viewingCase.core_source) }}
      </el-descriptions-item>
      <el-descriptions-item label="核心理由" :span="2">{{ viewingCase.core_reason || '—' }}</el-descriptions-item>
      <el-descriptions-item label="测试思想" :span="2">{{ viewingCase.summary || '—' }}</el-descriptions-item>
      <el-descriptions-item label="测试Topo" :span="2">{{ viewingCase.topo || '—' }}</el-descriptions-item>
      <el-descriptions-item label="测试数据" :span="2">{{ viewingCase.test_data || '—' }}</el-descriptions-item>
      <el-descriptions-item label="前置条件" :span="2">{{ viewingCase.preconditions || '—' }}</el-descriptions-item>
    </el-descriptions>
    <div class="mt-3">
      <div class="font-bold mb-2 text-xs">测试步骤</div>
      <el-table :data="viewingCase.steps" border size="small">
        <el-table-column prop="step_no" label="序号" width="60" />
        <el-table-column prop="action" label="操作步骤" />
        <el-table-column prop="expected" label="预期结果" />
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft } from "@element-plus/icons-vue";
import type { CaseVO } from "@/api/aitc/case";
import { importanceLabel, importanceType, coreSourceLabel } from "../../constants";

defineProps<{
  viewingCase: CaseVO;
}>();

defineEmits<{
  back: [];
  startEdit: [row: CaseVO];
}>();
</script>
