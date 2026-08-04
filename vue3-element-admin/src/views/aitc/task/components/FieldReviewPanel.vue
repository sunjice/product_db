<template>
  <div class="section-card">
    <div class="section-header">
      <span class="section-title">字段审核</span>
      <span class="section-hint">
        {{ processedCount }} / {{ failCount }} 不合格字段已处理
      </span>
    </div>
    <el-table
      :data="textFieldRows"
      border
      size="small"
      :row-class-name="textRowClassName"
      style="width: 100%"
    >
      <el-table-column prop="label" label="字段" width="100" fixed="left" />

      <el-table-column label="审核结论" width="110" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.conclusion === 'pass'" type="success" effect="plain" size="small">✓ 合格</el-tag>
          <el-tag v-else type="danger" effect="plain" size="small">✗ 不合格</el-tag>
        </template>
      </el-table-column>

      <el-table-column label="违反的规范" min-width="200">
        <template #default="{ row }">
          <template v-if="row.conclusion === 'fail' && row.rule_violated">
            <div class="rule-text">{{ row.rule_violated }}</div>
          </template>
          <template v-else>
            <span class="text-gray-400 text-xs">—</span>
          </template>
        </template>
      </el-table-column>

      <el-table-column label="AI修改建议" min-width="220">
        <template #default="{ row }">
          <template v-if="row.conclusion === 'fail' && row.hasSuggestion">
            <template v-if="!fieldStates[row.field_name]">
              <div class="cell-text suggested">{{ displayVal(row.suggested) }}</div>
            </template>
            <template v-else-if="fieldStates[row.field_name] === 'accept'">
              <span class="text-green-500 text-xs">✓ 已采纳</span>
            </template>
            <template v-else-if="fieldStates[row.field_name] === 'ignore'">
              <span class="text-orange-500 text-xs">已忽略</span>
            </template>
            <template v-else-if="fieldStates[row.field_name] === 'manual'">
              <span class="text-blue-500 text-xs">已手动修改</span>
            </template>
          </template>
          <template v-else>
            <span class="text-gray-400 text-xs">—</span>
          </template>
        </template>
      </el-table-column>

      <el-table-column label="值" min-width="180">
        <template #default="{ row }">
          <template v-if="!fieldStates[row.field_name] && editingField !== row.field_name">
            <div class="cell-text muted">{{ displayVal(row.original) }}</div>
          </template>
          <template v-else-if="fieldStates[row.field_name] === 'accept'">
            <div class="cell-text accepted">{{ displayVal(row.suggested) }}</div>
          </template>
          <template v-else-if="fieldStates[row.field_name] === 'manual'">
            <div class="cell-text edited">{{ manualValues[row.field_name] }}</div>
          </template>
          <template v-else-if="fieldStates[row.field_name] === 'ignore'">
            <div class="cell-text ignored">{{ displayVal(row.original) }}</div>
          </template>
          <template v-else-if="editingField === row.field_name">
            <el-input
              v-model="editDraft[row.field_name]"
              type="textarea"
              :rows="4"
              size="small"
              placeholder="请输入修改后的内容..."
            />
            <div class="inline-actions">
              <el-button size="small" type="primary" @click="$emit('saveManualEdit', row.field_name)">保存</el-button>
              <el-button size="small" @click="$emit('cancelEdit')">取消</el-button>
            </div>
          </template>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="200" fixed="right" align="center">
        <template #default="{ row }">
          <template v-if="row.conclusion === 'pass'">
            <span class="text-gray-400 text-xs">—</span>
          </template>
          <template v-else>
            <template v-if="!fieldStates[row.field_name]">
              <template v-if="row.hasSuggestion">
                <el-button size="small" type="success" @click="$emit('acceptField', row.field_name)">采纳</el-button>
                <el-button size="small" type="primary" plain @click="$emit('startEdit', row)">修改</el-button>
                <el-button size="small" type="warning" plain @click="$emit('ignoreField', row.field_name)">忽略</el-button>
              </template>
            </template>
            <template v-else>
              <el-tag v-if="fieldStates[row.field_name] === 'accept'" type="success" size="small">✓ 已采纳</el-tag>
              <el-tag v-else-if="fieldStates[row.field_name] === 'manual'" type="primary" size="small">✎ 已修改</el-tag>
              <el-tag v-else-if="fieldStates[row.field_name] === 'ignore'" type="warning" size="small">已忽略</el-tag>
              <el-button size="small" link type="primary" class="ml-2" @click="$emit('resetField', row.field_name)">重置</el-button>
            </template>
          </template>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import type { FieldSuggestionVO } from "@/api/aitc/task";
import { displayVal } from "../composables/useCaseReview";

export interface TextFieldRow {
  field_name: string;
  label: string;
  conclusion: string;
  rule_violated: string;
  hasSuggestion: boolean;
  original: any;
  suggested: any;
}

const props = defineProps<{
  textFieldRows: TextFieldRow[];
  fieldStates: Record<string, string>;
  editingField: string | null;
  editDraft: Record<string, string>;
  manualValues: Record<string, any>;
  passCount: number;
  failCount: number;
  processedCount: number;
}>();

defineEmits<{
  acceptField: [fieldName: string];
  ignoreField: [fieldName: string];
  resetField: [fieldName: string];
  startEdit: [row: TextFieldRow];
  cancelEdit: [];
  saveManualEdit: [fieldName: string];
}>();

function textRowClassName({ row }: { row: TextFieldRow }) {
  if (row.conclusion === "pass") return "";
  const st = props.fieldStates[row.field_name];
  if (st === "accept") return "row-accept";
  if (st === "manual") return "row-edit";
  if (st === "ignore") return "row-ignore";
  return "row-pending";
}
</script>

<style scoped>
.section-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  margin-bottom: 14px;
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fafafa;
  border-bottom: 1px solid #ebeef5;
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: #303133;
}

.section-hint {
  font-size: 12px;
  color: #909399;
}

.cell-text {
  white-space: pre-wrap;
  font-size: 12px;
  line-height: 1.55;
  max-height: 160px;
  overflow-y: auto;
  padding: 2px 0;
}

.cell-text.muted     { color: #909399; }
.cell-text.suggested { color: #409eff; background: #f0f7ff; padding: 4px 6px; border-radius: 4px; }
.cell-text.accepted  { color: #67c23a; background: #f0f9eb; padding: 4px 6px; border-radius: 4px; }
.cell-text.edited    { color: #409eff; background: #ecf5ff; padding: 4px 6px; border-radius: 4px; }
.cell-text.ignored   { color: #c0c4cc; text-decoration: line-through; }

.rule-text {
  font-size: 12px;
  color: #e6a23c;
  line-height: 1.55;
  padding: 4px 6px;
  background: #fdf6ec;
  border-radius: 4px;
}

.inline-actions {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

:deep(.row-accept)  { background-color: #f0f9eb !important; }
:deep(.row-edit)    { background-color: #ecf5ff !important; }
:deep(.row-ignore)  { background-color: #fdf6ec !important; opacity: 0.7; }
:deep(.row-pending) { background-color: #fef0f0 !important; }
</style>
