<template>
  <div>
    <div class="mb-2 flex items-center gap-2">
      <el-button text @click="$emit('cancelEdit')">
        <el-icon><ArrowLeft /></el-icon> 取消编辑
      </el-button>
      <span class="text-xs text-gray-500 flex-1">{{ viewingCase.project_prefix }}{{ viewingCase.external_id }}__{{ editForm.name }} — {{ editForm.purpose || editForm.name }}</span>
      <el-button type="primary" size="small" :loading="editSubmitting" @click="$emit('submitEdit')">保存</el-button>
    </div>

    <el-descriptions :column="2" border size="small" label-width="80px">
      <el-descriptions-item label="用例编号" :span="2">
        <span class="text-xs text-gray-700">{{ viewingCase.project_prefix }}{{ viewingCase.external_id }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="英文标识" :span="2">
        <el-input v-model="editForm.name" size="small" placeholder="英文标识名，如 user_login_test" />
      </el-descriptions-item>
      <el-descriptions-item label="测试目的" :span="2">
        <el-input v-model="editForm.purpose" size="small" placeholder="中文用例名称，如 SSID长度验证" />
      </el-descriptions-item>
      <el-descriptions-item label="级别">
        <el-select v-model="editForm.importance" size="small" style="width: 100%">
          <el-option label="高" :value="CaseImportanceEnum.HIGH" />
          <el-option label="中" :value="CaseImportanceEnum.MEDIUM" />
          <el-option label="低" :value="CaseImportanceEnum.LOW" />
        </el-select>
      </el-descriptions-item>
      <el-descriptions-item label="样本用例">
        <span v-if="viewingCase!.is_sample" class="text-green-500">✓ 是</span>
        <span v-else>否</span>
      </el-descriptions-item>
      <el-descriptions-item label="核心用例">
        <span v-if="viewingCase!.is_core" class="text-orange-500">★ 是</span>
        <span v-else>否</span>
      </el-descriptions-item>
      <el-descriptions-item label="核心来源">
        {{ coreSourceLabel(viewingCase!.core_source) }}
      </el-descriptions-item>
      <el-descriptions-item label="核心理由" :span="2">{{ viewingCase!.core_reason || '—' }}</el-descriptions-item>
      <el-descriptions-item label="测试思想" :span="2">
        <el-input v-model="editForm.summary" type="textarea" size="small" :autosize="{ minRows: 1, maxRows: 8 }" placeholder="—" />
      </el-descriptions-item>
      <el-descriptions-item label="测试Topo" :span="2">
        <el-input v-model="editForm.topo" type="textarea" size="small" :autosize="{ minRows: 1, maxRows: 8 }" placeholder="—" />
      </el-descriptions-item>
      <el-descriptions-item label="测试数据" :span="2">
        <el-input v-model="editForm.test_data" type="textarea" size="small" :autosize="{ minRows: 1, maxRows: 8 }" placeholder="—" />
      </el-descriptions-item>
      <el-descriptions-item label="前置条件" :span="2">
        <el-input v-model="editForm.preconditions" type="textarea" size="small" :autosize="{ minRows: 1, maxRows: 8 }" placeholder="—" />
      </el-descriptions-item>
    </el-descriptions>
    <div class="mt-3">
      <div class="font-bold mb-2 text-xs">测试步骤</div>
      <el-table :data="editForm.steps" border size="small" class="edit-steps-table">
        <el-table-column prop="step_no" label="序号" width="60" align="center" />
        <el-table-column label="操作步骤" min-width="200">
          <template #default="{ row: step }">
            <el-input v-model="step.action" type="textarea" size="small" :autosize="{ minRows: 3, maxRows: 8 }" placeholder="—" />
          </template>
        </el-table-column>
        <el-table-column label="预期结果" min-width="200">
          <template #default="{ row: step }">
            <el-input v-model="step.expected" type="textarea" size="small" :autosize="{ minRows: 3, maxRows: 8 }" placeholder="—" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70" align="center">
          <template #default="{ $index }">
            <el-button text type="danger" size="small" @click="$emit('removeStep', $index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-button class="mt-1" size="small" @click="$emit('addStep')">+ 添加步骤</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft } from "@element-plus/icons-vue";
import type { CaseVO } from "@/api/aitc/case";
import { coreSourceLabel } from "../../constants";
import { CaseImportanceEnum } from "@/enums/aitc";

interface StepForm {
  step_no: number;
  action: string;
  expected: string;
}

defineProps<{
  viewingCase: CaseVO;
  editForm: {
    external_id: string;
    name: string;
    summary: string;
    preconditions: string;
    topo: string;
    test_data: string;
    steps: StepForm[];
    importance: number;
  };
  editSubmitting: boolean;
}>();

defineEmits<{
  submitEdit: [];
  cancelEdit: [];
  addStep: [];
  removeStep: [index: number];
}>();
</script>
