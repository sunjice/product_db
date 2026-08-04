<template>
  <div class="case-review-page">
    <!-- 顶部导航 -->
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2">
        <el-button @click="goBack" icon="ArrowLeft" size="small">返回</el-button>
        <span class="text-lg font-bold">用例审核 — 任务 #{{ taskId }}</span>
        <el-tag v-if="caseData" type="info" size="small">{{ caseData.name }}</el-tag>
      </div>
      <div class="flex gap-2 items-center">
        <span class="text-sm text-gray-500">{{ currentIndex + 1 }} / {{ allItems.length }}</span>
        <el-button @click="prevItem" :disabled="!hasPrev" size="small">上一条</el-button>
        <el-button @click="nextItem" :disabled="!hasNext" size="small">下一条</el-button>
        <el-button size="small" type="info" text @click="showRawDialog" v-if="rawOutput">查看原始输出</el-button>
      </div>
    </div>

    <!-- 分值 + 整体评价 -->
    <div v-if="aiOutput" class="score-bar mb-3" v-loading="loading">
      <div class="flex items-center gap-4 flex-wrap">
        <div class="flex items-center gap-2">
          <span class="text-sm text-gray-600">AI 评分：</span>
          <el-tag v-if="aiOutput.score !== undefined" :type="scoreTag(aiOutput.score)" effect="dark" size="small">
            {{ aiOutput.score }} 分
          </el-tag>
          <span v-else class="text-gray-400 text-xs">—</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-sm text-gray-600">字段：</span>
          <span class="text-green-600 text-xs font-semibold">{{ passCount }} 合格</span>
          <span v-if="failCount > 0" class="text-red-500 text-xs font-semibold">{{ failCount }} 不合格</span>
          <span v-if="failCount > 0" class="text-gray-400 text-xs">
            （{{ processedCount }} / {{ failCount }} 已处理）
          </span>
        </div>
        <div v-if="aiOutput.overall_assessment" class="text-xs text-gray-500 flex-1 min-w-0">
          <span class="font-semibold">评价：</span>{{ aiOutput.overall_assessment }}
        </div>
      </div>
    </div>

    <!-- 左右分栏 -->
    <div class="review-split">
      <!-- 左侧：原用例 -->
      <div class="review-panel review-left">
        <div class="panel-header">
          <span class="panel-title">原始用例</span>
          <el-tag size="small" type="info">当前用例</el-tag>
        </div>
        <div class="panel-body">
          <div class="field-block">
            <div class="field-label">用例名称</div>
            <div class="field-value">{{ caseData?.name || '—' }}</div>
          </div>
          <div class="field-block">
            <div class="field-label">测试思想</div>
            <div class="field-value pre-wrap">{{ caseData?.summary || '—' }}</div>
          </div>
          <div class="field-block">
            <div class="field-label">前置条件</div>
            <div class="field-value pre-wrap">{{ caseData?.preconditions || '—' }}</div>
          </div>
          <div class="field-block">
            <div class="field-label">测试数据</div>
            <div class="field-value pre-wrap">{{ caseData?.test_data || '—' }}</div>
          </div>
          <div class="field-block">
            <div class="field-label">测试Topo</div>
            <div class="field-value pre-wrap">{{ caseData?.topo || '—' }}</div>
          </div>
          <div class="field-block">
            <div class="field-label">测试步骤</div>
            <el-table v-if="caseData?.steps?.length" :data="caseData.steps" border size="small" class="step-table">
              <el-table-column prop="step_no" label="序号" width="55" />
              <el-table-column prop="action" label="操作步骤" />
              <el-table-column prop="expected" label="预期结果" />
            </el-table>
            <div v-else class="text-gray-400 text-sm">—</div>
          </div>
          <div class="field-block">
            <div class="field-label">级别</div>
            <div class="field-value">{{ importanceLabel(caseData?.importance) }}</div>
          </div>
        </div>
      </div>

      <!-- 右侧：逐字段审核结果 -->
      <div class="review-panel review-right">
        <div class="panel-header">
          <span class="panel-title">AI 逐字段审核</span>
          <div class="flex gap-2">
            <el-button v-if="failCount > 0" size="small" type="success" @click="acceptAll">全部采纳</el-button>
            <el-button v-if="failCount > 0" size="small" type="warning" @click="ignoreAll">全部忽略</el-button>
          </div>
        </div>
        <div class="panel-body">
          <!-- 无 fields -->
          <div v-if="!allFields.length" class="text-center text-gray-400 py-10">
            <el-empty description="AI 未返回字段审核结果" :image-size="80" />
          </div>

          <!-- fields 表格 -->
          <div v-else class="field-review-list">
            <div
              v-for="f in allFields"
              :key="f.field_name"
              class="field-review-card"
              :class="{
                'conclusion-pass': f.conclusion === 'pass',
                'conclusion-fail': f.conclusion === 'fail',
                'state-accepted': fieldStates[f.field_name] === 'accept',
                'state-ignored': fieldStates[f.field_name] === 'ignore',
                'state-manual': fieldStates[f.field_name] === 'manual',
              }"
            >
              <!-- 字段名 + 结论 -->
              <div class="frc-header">
                <div class="flex items-center gap-2">
                  <span class="frc-field-name">{{ fieldLabelMap[f.field_name] || f.field_name }}</span>
                  <el-tag v-if="f.conclusion === 'pass'" type="success" effect="plain" size="small">✓ 合格</el-tag>
                  <el-tag v-else type="danger" effect="plain" size="small">✗ 不合格</el-tag>
                  <el-tag v-if="fieldStates[f.field_name] === 'accept'" type="success" size="small">已采纳</el-tag>
                  <el-tag v-if="fieldStates[f.field_name] === 'manual'" type="primary" size="small">已修改</el-tag>
                  <el-tag v-if="fieldStates[f.field_name] === 'ignore'" type="warning" size="small">已忽略</el-tag>
                </div>
                <!-- 操作按钮（仅 fail 且有建议） -->
                <div v-if="f.conclusion === 'fail' && f.has_suggestion && !fieldStates[f.field_name]" class="flex gap-1">
                  <el-button size="small" type="success" plain @click="acceptField(f.field_name)">采纳</el-button>
                  <el-button size="small" type="primary" plain @click="startEdit(f)">修改</el-button>
                  <el-button size="small" type="warning" plain @click="ignoreField(f.field_name)">忽略</el-button>
                </div>
                <div v-if="fieldStates[f.field_name] && fieldStates[f.field_name] !== 'edit'" class="flex gap-1">
                  <el-button size="small" link type="primary" @click="resetField(f.field_name)">重置</el-button>
                </div>
              </div>

              <!-- 违反的规范 -->
              <div v-if="f.conclusion === 'fail' && f.rule_violated" class="frc-rule">
                <span class="rule-badge">违反规范</span>
                <span>{{ f.rule_violated }}</span>
              </div>

              <!-- 值对比 -->
              <div class="frc-values">
                <!-- 合格 / 无建议 / 已忽略 → 显示原始值 -->
                <template v-if="f.conclusion === 'pass' || (!f.has_suggestion && !fieldStates[f.field_name]) || fieldStates[f.field_name] === 'ignore'">
                  <div class="frc-value-row">
                    <span class="frc-value-label">内容：</span>
                    <span v-if="f.field_name === 'steps'" class="text-xs text-gray-600">{{ (f.original || []).length }} 个步骤</span>
                    <div v-else class="cell-text muted">{{ displayVal(f.original) }}</div>
                  </div>
                </template>

                <!-- 已采纳 → 显示 AI 建议值 -->
                <template v-else-if="fieldStates[f.field_name] === 'accept'">
                  <div class="frc-value-row">
                    <span class="frc-value-label accepted">最终值：</span>
                    <span v-if="f.field_name === 'steps'" class="text-xs text-green-600">
                      采纳了 {{ (f.suggested || []).length }} 个步骤（AI建议）
                    </span>
                    <div v-else class="cell-text accepted">{{ displayVal(f.suggested) }}</div>
                  </div>
                </template>

                <!-- 已手动修改 → 显示自定义值 -->
                <template v-else-if="fieldStates[f.field_name] === 'manual'">
                  <div class="frc-value-row">
                    <span class="frc-value-label edited">最终值：</span>
                    <span v-if="f.field_name === 'steps'" class="text-xs text-blue-600">
                      {{ (manualSteps.length) }} 个步骤（手动修改）
                    </span>
                    <div v-else class="cell-text edited">{{ manualValues[f.field_name] }}</div>
                  </div>
                </template>

                <!-- 编辑中 -->
                <template v-else-if="editingField === f.field_name">
                  <template v-if="f.field_name === 'steps'">
                    <div class="step-editor">
                      <div class="edit-toolbar">
                        <el-button size="small" @click="addStepRow">+ 添加行</el-button>
                        <el-button size="small" type="danger" plain :disabled="editSteps.length <= 1" @click="removeStepRow">删除末行</el-button>
                      </div>
                      <el-table :data="editSteps" border size="small" class="mini-step-table mb-2">
                        <el-table-column prop="step_no" label="#" width="40" />
                        <el-table-column label="操作步骤" min-width="140">
                          <template #default="{ row, $index }">
                            <el-input v-model="editSteps[$index].action" size="small" placeholder="操作步骤" />
                          </template>
                        </el-table-column>
                        <el-table-column label="预期结果" min-width="140">
                          <template #default="{ row, $index }">
                            <el-input v-model="editSteps[$index].expected" size="small" placeholder="预期结果" />
                          </template>
                        </el-table-column>
                      </el-table>
                      <div class="flex gap-2">
                        <el-button size="small" type="primary" @click="saveManualEdit(f.field_name)">保存</el-button>
                        <el-button size="small" @click="cancelEdit">取消</el-button>
                      </div>
                    </div>
                  </template>
                  <template v-else>
                    <el-input
                      v-model="editDraft[f.field_name]"
                      type="textarea"
                      :rows="4"
                      size="small"
                      placeholder="请输入修改后的内容..."
                    />
                    <div class="flex gap-2 mt-1">
                      <el-button size="small" type="primary" @click="saveManualEdit(f.field_name)">保存</el-button>
                      <el-button size="small" @click="cancelEdit">取消</el-button>
                    </div>
                  </template>
                </template>

                <!-- 有建议且未处理：显示原始 vs AI 建议 -->
                <template v-else>
                  <div class="compare-pair">
                    <div class="compare-half">
                      <span class="compare-tag">原始</span>
                      <span v-if="f.field_name === 'steps'" class="text-xs text-gray-500">{{ (f.original || []).length }} 个步骤</span>
                      <div v-else class="cell-text original">{{ displayVal(f.original) }}</div>
                    </div>
                    <div class="compare-arrow">→</div>
                    <div class="compare-half">
                      <span class="compare-tag ai">AI建议</span>
                      <span v-if="f.field_name === 'steps'" class="text-xs text-green-500">{{ (f.suggested || []).length }} 个步骤</span>
                      <div v-else class="cell-text suggested">{{ displayVal(f.suggested) }}</div>
                    </div>
                  </div>
                </template>
              </div>

              <!-- 步骤详情（单独展示 steps diff） -->
              <div v-if="f.field_name === 'steps' && f.conclusion === 'fail' && !fieldStates.steps && f.has_suggestion && editingField !== 'steps'" class="steps-detail mt-2">
                <div class="flex gap-2">
                  <div class="steps-half">
                    <div class="steps-half-title">原始步骤</div>
                    <el-table v-if="(f.original || []).length" :data="f.original" border size="small" class="mini-step-table">
                      <el-table-column prop="step_no" label="#" width="35" />
                      <el-table-column prop="action" label="操作" min-width="120" />
                      <el-table-column prop="expected" label="预期" min-width="120" />
                    </el-table>
                    <div v-else class="text-gray-400 text-xs p-3">（空）</div>
                  </div>
                  <div class="steps-half">
                    <div class="steps-half-title ai">AI建议步骤</div>
                    <el-table v-if="(f.suggested || []).length" :data="f.suggested" border size="small" class="mini-step-table">
                      <el-table-column prop="step_no" label="#" width="35" />
                      <el-table-column prop="action" label="操作" min-width="120" />
                      <el-table-column prop="expected" label="预期" min-width="120" />
                    </el-table>
                    <div v-else class="text-gray-400 text-xs p-3">（空）</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部提交 -->
    <div class="review-footer mt-4 flex justify-center gap-3">
      <el-button size="large" @click="goBack">返回</el-button>
      <el-button size="large" type="primary" @click="submitReview" :loading="submitting" :disabled="!canSubmit">
        提交审核（不合格字段 {{ processedCount }}/{{ failCount }}）
      </el-button>
    </div>

    <!-- 原始输出弹窗 -->
    <el-dialog v-model="rawVisible" title="AI 原始输出" width="700px" destroy-on-close>
      <div class="raw-header">
        <span class="text-sm font-bold">{{ caseData?.name }}</span>
        <el-button size="small" text @click="copyRawOutput">复制</el-button>
      </div>
      <pre class="raw-json">{{ rawFormatted }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { TaskAPI } from "@/api/aitc/index";
import type { CaseVO, TaskItemVO, FieldSuggestionVO } from "@/api/aitc/types";

const route = useRoute();
const router = useRouter();
const taskId = String(route.params.taskId || "");
const itemId = String(route.params.itemId || "");

const loading = ref(false);
const submitting = ref(false);
const caseData = ref<CaseVO | null>(null);
const itemData = ref<TaskItemVO | null>(null);
const allItems = ref<TaskItemVO[]>([]);

// 原始输出弹窗
const rawVisible = ref(false);

// 字段名映射
const fieldLabelMap: Record<string, string> = {
  name: "用例名称",
  summary: "测试思想",
  preconditions: "前置条件",
  test_data: "测试数据",
  topo: "测试Topo",
  steps: "测试步骤",
};

const aiOutput = computed(() => itemData.value?.output as Record<string, any> | null);

// 从 output.fields 构建字段审核列表（新格式）
const allFields = computed(() => {
  const raw = aiOutput.value?.fields;
  if (!Array.isArray(raw)) return [];
  return raw.map((f: any) => {
    const fn = f.field_name || "";
    const conclusion = f.conclusion || "pass";
    const has = conclusion === "fail" && f.suggested_value != null && String(f.suggested_value) !== "null" && String(f.suggested_value) !== "";
    const original = getOriginalValue(fn);
    return {
      field_name: fn,
      conclusion,
      rule_violated: f.rule_violated || "",
      suggested: f.suggested_value ?? null,
      original,
      has_suggestion: has,
    };
  });
});

// 仅为 fail 的字段
const failFields = computed(() => allFields.value.filter(f => f.conclusion === "fail"));
const passCount = computed(() => allFields.value.filter(f => f.conclusion === "pass").length);
const failCount = computed(() => failFields.value.length);

function getOriginalValue(fieldName: string): any {
  if (!caseData.value) return "";
  if (fieldName === "steps") return caseData.value.steps || [];
  return (caseData.value as any)[fieldName] || "";
}

// 字段处理状态：null=未处理, accept=采纳, ignore=忽略, manual=手动修改
const fieldStates = reactive<Record<string, string | null>>({});
const manualValues = reactive<Record<string, string>>({});
const manualSteps = ref<any[]>([]);
const editingField = ref<string | null>(null);
const editDraft = reactive<Record<string, string>>({});
const editSteps = ref<any[]>([]);

const processedCount = computed(() => {
  return failFields.value.filter(f => !!fieldStates[f.field_name]).length;
});

const canSubmit = computed(() => failCount.value === 0 || processedCount.value === failCount.value);

const currentIndex = computed(() => allItems.value.findIndex(it => String(it.id) === itemId));
const hasPrev = computed(() => currentIndex.value > 0);
const hasNext = computed(() => currentIndex.value < allItems.value.length - 1);

// 原始输出
const rawOutput = computed(() => itemData.value?.output);
const rawFormatted = computed(() => {
  try {
    return JSON.stringify(rawOutput.value, null, 2);
  } catch {
    return "";
  }
});

function displayVal(val: any): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

function importanceLabel(v?: number) {
  return { 1: "低", 2: "中", 3: "高" }[v ?? 2] || "—";
}

function scoreTag(s: number) {
  return s >= 80 ? "success" : s >= 60 ? "warning" : "danger";
}

// 逐字段操作
function acceptField(field: string) {
  fieldStates[field] = "accept";
}

function ignoreField(field: string) {
  fieldStates[field] = "ignore";
}

function acceptAll() {
  failFields.value.forEach(f => {
    if (!fieldStates[f.field_name]) fieldStates[f.field_name] = "accept";
  });
}

function ignoreAll() {
  failFields.value.forEach(f => {
    if (!fieldStates[f.field_name]) fieldStates[f.field_name] = "ignore";
  });
}

function resetField(field: string) {
  fieldStates[field] = null;
  delete manualValues[field];
}

// 手动编辑
function startEdit(f: any) {
  editingField.value = f.field_name;
  if (f.field_name === "steps") {
    const src = f.original || f.suggested || [];
    editSteps.value = src.length ? JSON.parse(JSON.stringify(src)) : [{ step_no: 1, action: "", expected: "" }];
  } else {
    editDraft[f.field_name] = manualValues[f.field_name] || displayVal(f.original);
  }
}

function addStepRow() {
  const no = editSteps.value.length > 0 ? Math.max(...editSteps.value.map((s: any) => s.step_no || 0)) + 1 : 1;
  editSteps.value.push({ step_no: no, action: "", expected: "" });
}

function removeStepRow() {
  if (editSteps.value.length > 1) editSteps.value.pop();
}

function saveManualEdit(fieldName: string) {
  if (fieldName === "steps") {
    manualSteps.value = [...editSteps.value];
    fieldStates[fieldName] = "manual";
  } else {
    manualValues[fieldName] = editDraft[fieldName] || "";
    fieldStates[fieldName] = "manual";
  }
  editingField.value = null;
}

function cancelEdit() {
  editingField.value = null;
}

// 导航
function goBack() {
  router.push(`/aitc/tasks/${taskId}`);
}

function prevItem() {
  if (!hasPrev.value) return;
  const prev = allItems.value[currentIndex.value - 1];
  router.push(`/aitc/tasks/${taskId}/case-review/${prev.id}`);
  loadItem(String(prev.id));
}

function nextItem() {
  if (!hasNext.value) return;
  const next = allItems.value[currentIndex.value + 1];
  router.push(`/aitc/tasks/${taskId}/case-review/${next.id}`);
  loadItem(String(next.id));
}

// 数据加载
async function loadItem(id?: string) {
  const targetId = id || itemId;
  loading.value = true;
  try {
    const itemsRes = await TaskAPI.getItems(taskId);
    allItems.value = (itemsRes as TaskItemVO[]) || [];

    const res = await TaskAPI.getItemWithCase(taskId, targetId);
    const data = res as any;
    itemData.value = data?.item || null;
    caseData.value = data?.case || null;

    // 重置所有状态
    Object.keys(fieldStates).forEach(k => { fieldStates[k] = null; });
    Object.keys(manualValues).forEach(k => { delete manualValues[k]; });
    manualSteps.value = [];
    editingField.value = null;
  } finally {
    loading.value = false;
  }
}

// 提交审核
async function submitReview() {
  if (failCount.value > 0 && processedCount.value < failCount.value) {
    ElMessage.warning(`还有 ${failCount.value - processedCount.value} 个不合格字段未处理`);
    return;
  }
  if (!itemData.value) {
    ElMessage.warning("没有可审核的内容");
    return;
  }

  submitting.value = true;
  try {
    // 构建审核字段列表
    const fields = failFields.value
      .filter(f => !!fieldStates[f.field_name])
      .map(f => ({
        field_name: f.field_name,
        action: fieldStates[f.field_name] as string,
        edited_value: fieldStates[f.field_name] === "manual"
          ? (f.field_name === "steps" ? JSON.stringify(manualSteps.value) : manualValues[f.field_name])
          : undefined,
      }));

    const hasAccepted = fields.some(f => f.action === "accept");
    await TaskAPI.reviewItem(taskId, String(itemData.value.id), {
      task_id: taskId,
      item_id: String(itemData.value.id),
      confirm_status: hasAccepted ? 1 : 2,
      fields,
    });

    ElMessage.success("审核成功，结果已保存");
    if (hasNext.value) {
      nextItem();
    } else {
      goBack();
    }
  } catch (e: any) {
    ElMessage.error(e?.message || "审核失败");
  } finally {
    submitting.value = false;
  }
}

// 原始输出
function showRawDialog() {
  rawVisible.value = true;
}

async function copyRawOutput() {
  try {
    await navigator.clipboard.writeText(rawFormatted.value);
    ElMessage.success("已复制到剪贴板");
  } catch {
    ElMessage.warning("复制失败，请手动复制");
  }
}

// 监听路由参数变化
import { watch } from "vue";
watch(() => route.params.itemId, (newId) => {
  if (newId) loadItem(String(newId));
});

onMounted(() => loadItem());
</script>

<style scoped>
.case-review-page {
  padding: 4px;
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
}

.score-bar {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 10px 16px;
  flex-shrink: 0;
}

.review-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.review-panel {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.review-left {
  background: #fafafa;
}

.review-right {
  background: #fff;
}

.panel-header {
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-shrink: 0;
}

.panel-title {
  font-weight: 700;
  font-size: 14px;
}

.panel-body {
  padding: 12px 16px;
  overflow-y: auto;
  flex: 1;
}

.field-block {
  margin-bottom: 14px;
}

.field-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 3px;
  font-weight: 600;
}

.field-value {
  font-size: 13px;
  color: #303133;
  line-height: 1.6;
}

.pre-wrap {
  white-space: pre-wrap;
  margin: 0;
}

.step-table {
  width: 100%;
}

/* 字段审核卡片 */
.field-review-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field-review-card {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 10px 12px;
  transition: border-color 0.2s;
}

.field-review-card.conclusion-pass {
  border-left: 3px solid #67c23a;
  background: #f6fdf3;
}

.field-review-card.conclusion-fail {
  border-left: 3px solid #f56c6c;
  background: #fefbfb;
}

.field-review-card.state-accepted {
  opacity: 0.7;
  border-left-color: #67c23a;
}

.field-review-card.state-ignored {
  opacity: 0.5;
  border-left-color: #e6a23c;
}

.field-review-card.state-manual {
  border-left-color: #409eff;
}

.frc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.frc-field-name {
  font-weight: 700;
  font-size: 13px;
}

.frc-rule {
  background: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 4px;
  padding: 6px 10px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #f56c6c;
  display: flex;
  gap: 6px;
  align-items: flex-start;
}

.rule-badge {
  background: #f56c6c;
  color: #fff;
  padding: 0 5px;
  border-radius: 3px;
  font-size: 10px;
  white-space: nowrap;
  flex-shrink: 0;
  line-height: 1.6;
}

.frc-values {
  font-size: 12px;
}

.frc-value-row {
  display: flex;
  gap: 6px;
}

.frc-value-label {
  font-weight: 600;
  flex-shrink: 0;
}

.frc-value-label.accepted {
  color: #67c23a;
}

.frc-value-label.edited {
  color: #409eff;
}

.cell-text {
  line-height: 1.6;
  word-break: break-all;
}

.cell-text.muted {
  color: #909399;
}

.cell-text.original {
  color: #909399;
}

.cell-text.suggested {
  color: #67c23a;
}

.cell-text.accepted {
  color: #67c23a;
}

.cell-text.edited {
  color: #409eff;
}

.compare-pair {
  display: grid;
  grid-template-columns: 1fr 28px 1fr;
  gap: 6px;
  align-items: flex-start;
}

.compare-half {
  min-width: 0;
}

.compare-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
  font-weight: bold;
  font-size: 16px;
}

.compare-tag {
  display: inline-block;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  margin-bottom: 3px;
  background: #f0f0f0;
  color: #909399;
  font-weight: 600;
}

.compare-tag.ai {
  background: #e1f3d8;
  color: #67c23a;
}

/* 步骤编辑器 */
.step-editor {
  margin-top: 4px;
}

.edit-toolbar {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}

.mini-step-table {
  width: 100%;
}

.steps-detail {
  border-top: 1px dashed #e4e7ed;
  padding-top: 8px;
}

.steps-half {
  flex: 1;
  min-width: 0;
}

.steps-half-title {
  font-size: 11px;
  color: #909399;
  margin-bottom: 4px;
  font-weight: 600;
}

.steps-half-title.ai {
  color: #67c23a;
}

/* 原始输出弹窗 */
.raw-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.raw-json {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.7;
  max-height: 500px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

.review-footer {
  flex-shrink: 0;
}
</style>
