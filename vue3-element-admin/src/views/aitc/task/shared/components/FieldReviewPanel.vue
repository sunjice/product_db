<template>
  <div class="section-card">
    <div class="section-header">
      <span class="text-sm font-bold">字段审核</span>
      <span class="text-xs text-gray-400">{{ processedCount }} / {{ failCount }} 不合格字段已处理</span>
    </div>

    <table class="rt-table">
      <thead>
        <tr>
          <th style="width:100px">字段</th>
          <th style="width:auto">当前值</th>
          <th style="width:auto">AI 建议值</th>
          <th style="width:auto">评审意见</th>
          <th style="width:80px;text-align:center">结论</th>
          <th style="width:180px;text-align:center">操作</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="row in textFieldRows" :key="row.field_name">
          <tr>
            <!-- 字段 -->
            <td>
              <div class="font-semibold text-xs">{{ row.label }}</div>
              <span v-if="fieldStates[row.field_name] === 'accept'" class="text-xs text-gray-400">（已采纳）</span>
              <span v-if="fieldStates[row.field_name] === 'manual'" class="text-xs text-gray-400">（已修改）</span>
              <span v-if="fieldStates[row.field_name] === 'ignore'" class="text-xs text-gray-400">（已忽略）</span>
            </td>

            <!-- 当前值 -->
            <td>
              <span :class="fieldStates[row.field_name] === 'ignore' ? 'text-gray-400 line-through' : ''">{{ displayVal(row.original) }}</span>
            </td>

            <!-- AI 建议值 -->
            <td>
              <template v-if="row.conclusion === 'pass' || fieldStates[row.field_name] === 'ignore'">
                —
              </template>
              <template v-else-if="fieldStates[row.field_name] === 'accept'">
                {{ displayVal(row.suggested) }}
              </template>
              <template v-else-if="fieldStates[row.field_name] === 'manual'">
                {{ manualValues[row.field_name] }}
              </template>
              <template v-else>
                <template v-if="row.hasSuggestion">{{ displayVal(row.suggested) }}</template>
                <span v-else class="text-gray-400">—</span>
              </template>
            </td>

            <!-- 评审意见 -->
            <td>
              <span v-if="row.conclusion === 'fail' && row.rule_violated" class="text-xs">{{ row.rule_violated }}</span>
              <span v-else class="text-gray-400">—</span>
            </td>

            <!-- 结论 -->
            <td class="text-center">
              <span v-if="row.conclusion === 'pass'" class="text-green-600">合格</span>
              <span v-else class="text-red-500">不合格</span>
            </td>

            <!-- 操作 -->
            <td class="text-center">
              <template v-if="row.conclusion === 'fail' && row.hasSuggestion && !fieldStates[row.field_name]">
                <el-button size="small" type="primary" link @click="$emit('acceptField', row.field_name)">接受</el-button>
                <el-button size="small" link type="primary" @click="$emit('startEdit', row)">修改</el-button>
                <el-button size="small" link type="primary" @click="$emit('ignoreField', row.field_name)">忽略</el-button>
              </template>
              <template v-if="fieldStates[row.field_name]">
                <el-button size="small" link type="primary" @click="$emit('resetField', row.field_name)">重置</el-button>
              </template>
            </td>
          </tr>

          <!-- 编辑行 -->
          <tr v-if="editingField === row.field_name" class="editor-row">
            <td colspan="6">
              <div class="py-3 px-2">
                <div class="text-xs font-semibold mb-2 text-gray-500">编辑内容</div>
                <el-input
                  v-model="editDraft[row.field_name]"
                  type="textarea"
                  :rows="4"
                  size="small"
                  placeholder="请输入修改后的内容..."
                />
                <div class="flex gap-2 mt-2">
                  <el-button size="small" type="primary" @click="$emit('saveManualEdit', row.field_name)">保存</el-button>
                  <el-button size="small" @click="$emit('cancelEdit')">取消</el-button>
                </div>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
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

defineProps<{
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
</script>

<style scoped>
.section-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  margin-bottom: 14px;
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: #fafafa;
  border-bottom: 1px solid #ebeef5;
}

/* ==================== 字段对比表格 ==================== */
.rt-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  color: #303133;
}

.rt-table th {
  background: #f5f7fa;
  color: #606266;
  font-weight: 600;
  font-size: 13px;
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #ebeef5;
  border-right: 1px solid #ebeef5;
}

.rt-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #ebeef5;
  border-right: 1px solid #ebeef5;
  vertical-align: top;
  background: #fff;
  word-break: break-all;
}

.rt-table tbody tr:nth-child(even) td {
  background: #fafafa;
}

.rt-table tr.editor-row td {
  background: #fafafa;
  padding: 0;
}

.text-green-600 {
  color: #67c23a;
}

.text-red-500 {
  color: #f56c6c;
}

.text-gray-400 {
  color: #c0c4cc;
}

.line-through {
  text-decoration: line-through;
}
</style>
