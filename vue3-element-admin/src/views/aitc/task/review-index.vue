<template>
  <div class="case-review-index">
    <!-- 顶部项目选择 -->
    <div class="top-bar">
      <div class="flex items-center gap-3">
        <span class="text-sm font-semibold text-gray-700">项目：</span>
        <el-select v-model="projectId" placeholder="请选择项目" size="default" style="width: 240px" @change="onProjectChange">
          <el-option v-for="p in projectOptions" :key="p.value" :label="p.label" :value="String(p.value)" />
        </el-select>
        <el-tag v-if="rawTree.length > 0" type="danger" effect="dark" round>
          {{ totalPending }} 个用例待审核
        </el-tag>
      </div>
    </div>

    <!-- 主体：左树 + 右详情 -->
    <div class="review-body">
      <!-- 左侧：待审核树 -->
      <div class="review-left-panel">
        <div class="panel-header">
          <span class="panel-title">用例模块</span>
        </div>
        <div class="panel-body">
          <el-input v-model="treeFilter" placeholder="搜索模块或用例" size="small" clearable class="mb-3" />
          <el-tree
            ref="treeRef"
            :data="treeData"
            :props="treeProps"
            node-key="nodeKey"
            highlight-current
            :expand-on-click-node="false"
            :filter-node-method="filterTreeNode"
            :default-expand-all="false"
            @node-click="onNodeClick"
          >
            <template #default="{ data }">
              <div class="tree-node-row" :class="{ 'is-case': data.type === 'case' }">
                <span class="truncate flex-1">{{ data.label }}</span>
                <el-badge v-if="data.pending_count > 0" :value="data.pending_count" :max="999" class="tree-badge" />
                <el-tag v-if="data.type === 'case' && data.importance" :type="importanceType(data.importance)" size="small" class="ml-1">
                  {{ importanceLabel(data.importance) }}
                </el-tag>
              </div>
            </template>
          </el-tree>
        </div>
      </div>

      <!-- 右侧：审核详情 -->
      <div class="review-right-panel">
        <el-empty v-if="!currentDetail" description="请在左侧点击待审核用例编号" :image-size="100" />

        <div v-if="currentDetail?.case" class="detail-container" v-loading="loading">
          <!-- 用例信息头部 -->
          <div class="case-header">
            <div class="flex items-center justify-between flex-wrap gap-3">
              <div>
                <span class="case-name">{{ currentDetail.case.name }}</span>
                <div class="case-meta">
                  <el-tag type="info" size="small">{{ currentDetail.case.external_id || '无编号' }}</el-tag>
                  <el-tag :type="importanceType(currentDetail.case.importance)" size="small">{{ importanceLabel(currentDetail.case.importance) }}</el-tag>
                  <el-tag v-if="currentDetail.score !== null && currentDetail.score !== undefined"
                    :type="scoreTag(currentDetail.score)" effect="dark" size="small">
                    AI {{ currentDetail.score }}分
                  </el-tag>
                  <span class="field-stats">{{ passCount }} 合格 / {{ failCount }} 不合格</span>
                </div>
              </div>
            </div>
            <!-- 整体评价 -->
            <div v-if="currentDetail.overall_assessment" class="overall-assessment">
              <span class="oa-label">整体评价：</span>{{ currentDetail.overall_assessment }}
            </div>
            <div v-if="currentDetail.issues?.length" class="case-issues">
              <el-tag v-for="(issue, i) in currentDetail.issues" :key="i" type="danger" size="small" class="mr-1 mb-1">{{ issue }}</el-tag>
            </div>
          </div>

          <!-- ============ 文本字段统一表格 ============ -->
          <FieldReviewPanel
            :text-field-rows="textFieldRows"
            :field-states="fieldStates"
            :editing-field="editingField"
            :edit-draft="editDraft"
            :manual-values="manualValues"
            :pass-count="passCount"
            :fail-count="failCount"
            :processed-count="processedCount"
            @accept-field="acceptField"
            @ignore-field="ignoreField"
            @reset-field="resetField"
            @start-edit="(row: any) => startEdit(row)"
            @cancel-edit="cancelEdit"
            @save-manual-edit="saveManualEdit"
          />

          <!-- ============ 测试步骤 ============ -->
          <div v-if="stepsSug" class="section-card">
            <div class="section-header">
              <span class="section-title">测试步骤</span>
              <div class="flex items-center gap-2">
                <el-tag v-if="stepsSug.conclusion === 'pass'" type="success" effect="plain" size="small">✓ 合格</el-tag>
                <el-tag v-else type="danger" effect="plain" size="small">✗ 不合格</el-tag>
              </div>
            </div>

            <!-- 违反规范说明 -->
            <div v-if="stepsSug.conclusion === 'fail' && stepsSug.rule_violated" class="steps-rule-notice">
              <span class="rule-badge">违反规范</span>
              <span>{{ stepsSug.rule_violated }}</span>
            </div>

            <!-- 未处理/忽略 → 原始 vs AI 对比 -->
            <template v-if="!fieldStates.steps || fieldStates.steps === 'ignore'">
              <div class="steps-compare">
                <div class="steps-half">
                  <div class="steps-half-title">原始</div>
                  <el-table v-if="origSteps.length" :data="origSteps" border size="small" class="mini-step-table">
                    <el-table-column prop="step_no" label="#" width="40" />
                    <el-table-column prop="action" label="操作步骤" min-width="150" />
                    <el-table-column prop="expected" label="预期结果" min-width="150" />
                  </el-table>
                  <div v-else class="text-gray-400 text-xs p-2">（空）</div>
                </div>
                <div class="steps-divider" v-if="stepsSug.conclusion === 'fail' && stepsSug.has_suggestion && fieldStates.steps !== 'ignore'">→</div>
                <div class="steps-half" v-if="stepsSug.conclusion === 'fail' && stepsSug.has_suggestion && fieldStates.steps !== 'ignore'">
                  <div class="steps-half-title ai">AI建议</div>
                  <el-table v-if="aiSteps.length" :data="aiSteps" border size="small" class="mini-step-table ai-table">
                    <el-table-column prop="step_no" label="#" width="40" />
                    <el-table-column prop="action" label="操作步骤" min-width="150" />
                    <el-table-column prop="expected" label="预期结果" min-width="150" />
                  </el-table>
                </div>
              </div>

              <!-- 步骤操作按钮 -->
              <div v-if="!fieldStates.steps && stepsSug.conclusion === 'fail'" class="steps-actions">
                <template v-if="stepsSug.has_suggestion">
                  <el-button size="small" type="success" @click="acceptField('steps')">采纳 AI</el-button>
                  <el-button size="small" type="primary" plain @click="startEdit(stepsSug)">手动修改</el-button>
                  <el-button size="small" type="warning" plain @click="ignoreField('steps')">保持原样</el-button>
                </template>
              </div>
              <div v-if="fieldStates.steps === 'ignore'" class="steps-actions">
                <el-tag type="warning" size="small">已忽略</el-tag>
                <el-button size="small" link type="primary" class="ml-2" @click="resetField('steps')">重置</el-button>
              </div>
            </template>

            <!-- 已采纳 → 显示AI建议 -->
            <template v-if="fieldStates.steps === 'accept'">
              <div class="steps-half px-4">
                <div class="steps-half-title accepted">最终步骤（AI建议）</div>
                <el-table v-if="aiSteps.length" :data="aiSteps" border size="small" class="mini-step-table accepted-table">
                  <el-table-column prop="step_no" label="#" width="40" />
                  <el-table-column prop="action" label="操作步骤" min-width="150" />
                  <el-table-column prop="expected" label="预期结果" min-width="150" />
                </el-table>
              </div>
              <div class="steps-actions mt-2">
                <el-tag type="success" size="small">✓ 已采纳</el-tag>
                <el-button size="small" link type="primary" class="ml-2" @click="resetField('steps')">重置</el-button>
              </div>
            </template>

            <!-- 已编辑 → 显示手动步骤 -->
            <template v-if="fieldStates.steps === 'manual'">
              <div class="steps-half px-4">
                <div class="steps-half-title edited">最终步骤（手动修改）</div>
                <el-table v-if="manualSteps.length" :data="manualSteps" border size="small" class="mini-step-table edited-table">
                  <el-table-column prop="step_no" label="#" width="40" />
                  <el-table-column prop="action" label="操作步骤" min-width="150" />
                  <el-table-column prop="expected" label="预期结果" min-width="150" />
                </el-table>
              </div>
              <div class="steps-actions mt-2">
                <el-tag type="primary" size="small">✎ 已修改</el-tag>
                <el-button size="small" link type="primary" class="ml-2" @click="resetField('steps')">重置</el-button>
              </div>
            </template>

            <!-- 步骤编辑区域 -->
            <template v-if="editingField === 'steps'">
              <div class="step-edit-area">
                <div class="edit-toolbar">
                  <el-button size="small" @click="addStepRow">+ 添加行</el-button>
                  <el-button size="small" type="danger" plain :disabled="editSteps.length <= 1" @click="removeStepRow">删除末行</el-button>
                </div>
                <el-table :data="editSteps" border size="small" class="mini-step-table">
                  <el-table-column prop="step_no" label="#" width="40" />
                  <el-table-column label="操作步骤" min-width="150">
                    <template #default="{ row, $index }">
                      <el-input v-model="editSteps[$index].action" size="small" placeholder="操作步骤" />
                    </template>
                  </el-table-column>
                  <el-table-column label="预期结果" min-width="150">
                    <template #default="{ row, $index }">
                      <el-input v-model="editSteps[$index].expected" size="small" placeholder="预期结果" />
                    </template>
                  </el-table-column>
                </el-table>
                <div class="inline-actions">
                  <el-button size="small" type="primary" @click="saveManualEdit('steps')">保存</el-button>
                  <el-button size="small" @click="cancelEdit">取消</el-button>
                </div>
              </div>
            </template>
          </div>

          <!-- 底部提交 -->
          <div v-if="currentDetail?.suggestions?.length" class="review-footer">
            <div class="footer-bar">
              <div class="flex items-center gap-3">
                <el-progress
                  :percentage="failCount ? Math.round(processedCount / failCount * 100) : 100"
                  :stroke-width="6"
                  :color="progressColor"
                  style="width: 140px"
                />
                <span class="progress-text">
                  不合格字段 {{ processedCount }}/{{ failCount }}
                  <span v-if="passCount > 0" class="text-gray-400">（{{ passCount }} 个合格）</span>
                </span>
              </div>
              <el-button type="primary" size="large" :loading="submitting" @click="submitReview" :disabled="!canSubmit">
                审核完成，保存用例
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick } from "vue";
import { ElMessage } from "element-plus";
import ProjectAPI from "@/api/aitc/project";
import { ReviewAPI } from "@/api/aitc/task";
import type { OptionItem } from "@/api/common";
import type {
  PendingSuiteNode, PendingCaseVO,
  CaseReviewDetailVO, FieldSuggestionVO,
} from "@/api/aitc/task";
import { importanceLabel, importanceType, scoreTag } from "../constants";
import { useCaseReview, FIELD_LABEL_MAP, displayVal } from "./shared/composables/useCaseReview";
import FieldReviewPanel from "./shared/components/FieldReviewPanel.vue";
import type { TextFieldRow } from "./shared/components/FieldReviewPanel.vue";

// ── 项目 ──
const projectId = ref("");
const projectOptions = ref<OptionItem[]>([]);

async function loadProjectOptions() {
  const res = await ProjectAPI.getOptions();
  projectOptions.value = res || [];
}

// ── 待审核树 ──
const treeRef = ref();
const treeFilter = ref("");
const rawTree = ref<any[]>([]);
const loadedCaseMap = ref<Record<string, PendingCaseVO[]>>({});
const treeProps = { children: "children", label: "label" };

const totalPending = computed(() => {
  let count = 0;
  const walk = (nodes: any[]) => {
    for (const n of nodes) {
      if (n.headCount !== undefined) count += n.headCount;
      walk(n.children || []);
    }
  };
  walk(rawTree.value);
  return count;
});

const treeData = computed(() => buildTree(rawTree.value, loadedCaseMap.value));

function buildTree(nodes: any[], caseMap: Record<string, PendingCaseVO[]>): any[] {
  return nodes.map(n => {
    const cases = caseMap[`suite_${n.id}`] || [];
    const caseNodes = cases.map((c: PendingCaseVO) => ({
      nodeKey: `case_${c.id}`,
      label: c.external_id || `#${c.id}`,
      type: "case",
      caseId: c.id,
      caseName: c.name,
      externalId: c.external_id,
      importance: c.importance,
      isLeaf: true,
      children: [],
    }));
    return {
      ...n,
      nodeKey: `suite_${n.id}`,
      headCount: n.pending_count,
      children: [
        ...buildTree(n.children || [], caseMap),
        ...caseNodes,
      ],
    };
  });
}

function filterTreeNode(value: string, data: any) {
  if (!value) return true;
  const v = value.toLowerCase();
  return (data.label || "").toLowerCase().includes(v)
    || (data.externalId || "").toLowerCase().includes(v)
    || (data.caseName || "").toLowerCase().includes(v);
}

watch(treeFilter, (val) => treeRef.value?.filter(val));

async function onProjectChange() {
  rawTree.value = [];
  loadedCaseMap.value = {};
  currentDetail.value = null;
  selectedCaseId.value = null;
  cancelEdit();
  clearFieldStates();
  if (!projectId.value) return;
  const suites = await ReviewAPI.getPendingTree(projectId.value);
  rawTree.value = (suites as PendingSuiteNode[]) || [];
}

async function onNodeClick(data: any) {
  if (data.type !== "case" && data.pending_count > 0) {
    const key = `suite_${data.id}`;
    if (!loadedCaseMap.value[key]) {
      try {
        const cases = await ReviewAPI.getPendingList(String(data.id));
        loadedCaseMap.value = { ...loadedCaseMap.value, [key]: cases as PendingCaseVO[] };
      } catch { /* ignore */ }
    }
    nextTick(() => {
      treeRef.value?.setExpandedKeys?.(
        Array.from(new Set([
          ...(treeRef.value?.getExpandedKeys?.() || []),
          data.nodeKey as string,
        ]))
      );
    });
  }
  if (data.type === "case") {
    await loadDetail(data.caseId);
  }
}

// ── 审核详情 ──
const loading = ref(false);
const submitting = ref(false);
const currentDetail = ref<CaseReviewDetailVO | null>(null);
const selectedCaseId = ref<string | null>(null);

// 共享审核逻辑
const {
  fieldStates, manualValues, editingField, editDraft, editSteps,
  clearFieldStates, useFieldStats,
  acceptField, ignoreField, resetField,
  startEdit, cancelEdit, saveManualEdit,
  addStepRow, removeStepRow, buildFields,
} = useCaseReview();

// 字段名映射（统一来源）
const fieldLabelMap = FIELD_LABEL_MAP;

// 文本字段表格行（排除 steps）
const textFieldRows = computed<TextFieldRow[]>(() => {
  if (!currentDetail.value?.suggestions) return [];
  return currentDetail.value.suggestions
    .filter(s => s.field_name !== "steps")
    .map(s => ({
      field_name: s.field_name,
      label: fieldLabelMap[s.field_name] || s.field_name,
      conclusion: s.conclusion || "pass",
      rule_violated: s.rule_violated || "",
      hasSuggestion: s.has_suggestion,
      original: s.original,
      suggested: s.suggested,
    }));
});

// 步骤相关
const stepsSug = computed(() => {
  return currentDetail.value?.suggestions?.find(s => s.field_name === "steps") ?? null;
});

const origSteps = computed(() => {
  if (!stepsSug.value) return [];
  return stepsSug.value.original || [];
});

const aiSteps = computed(() => stepsSug.value?.suggested || []);

const manualSteps = computed(() => manualValues.steps || []);

// 统计 — 使用 composable 统一口径
const failFields = computed(() =>
  (currentDetail.value?.suggestions || []).filter(s => s.conclusion === "fail")
);
const passCount = computed(() =>
  (currentDetail.value?.suggestions || []).filter(s => s.conclusion === "pass").length
);
const { failCount, processedCount, canSubmit } = useFieldStats(() =>
  failFields.value.map(f => ({ field_name: f.field_name, conclusion: f.conclusion }))
);

const progressColor = computed(() => {
  if (!failCount.value) return "#67c23a";
  const pct = processedCount.value / failCount.value;
  if (pct >= 1) return "#67c23a";
  if (pct >= 0.5) return "#e6a23c";
  return "#409eff";
});

// ── 加载 ──
async function loadDetail(caseId: string | number) {
  selectedCaseId.value = String(caseId);
  loading.value = true;
  try {
    const res = await ReviewAPI.getReviewDetail(String(caseId));
    currentDetail.value = res as CaseReviewDetailVO;
    clearFieldStates();
  } catch (e: any) {
    ElMessage.error(e?.message || "加载失败");
  } finally {
    loading.value = false;
  }
}

// ── 三态操作 ──
// （acceptField / ignoreField / resetField / startEdit / cancelEdit / saveManualEdit
//  addStepRow / removeStepRow / displayVal 已由 useCaseReview() 提供）

// ── 提交审核 ──
async function submitReview() {
  if (!currentDetail.value || !selectedCaseId.value) {
    ElMessage.warning("请先选择用例");
    return;
  }

  const suggs = currentDetail.value.suggestions || [];
  const fails = suggs.filter(s => s.conclusion === "fail");
  const pending = fails.filter(s => !fieldStates[s.field_name]);
  if (pending.length > 0) {
    ElMessage.warning(
      `还有 ${pending.length} 个不合格字段未处理：${pending.map(s => fieldLabelMap[s.field_name] || s.field_name).join("、")}`
    );
    return;
  }

  if (!currentDetail.value.task_item_id) {
    ElMessage.warning("没有可审核的 AI 建议");
    return;
  }

  submitting.value = true;
  try {
    const fields = buildFields(fails);

    await ReviewAPI.submitReview(String(selectedCaseId.value), {
      case_id: String(selectedCaseId.value),
      task_item_id: String(currentDetail.value.task_item_id),
      fields,
    });

    ElMessage.success("审核完成，用例已更新");

    if (projectId.value) {
      const suites = await ReviewAPI.getPendingTree(projectId.value);
      rawTree.value = (suites as PendingSuiteNode[]) || [];
    }

    for (const key of Object.keys(loadedCaseMap.value)) {
      loadedCaseMap.value[key] = loadedCaseMap.value[key].filter(
        c => String(c.id) !== String(selectedCaseId.value)
      );
    }

    const nextCase = findNextCase();
    if (nextCase) {
      await loadDetail(nextCase.caseId);
    } else {
      currentDetail.value = null;
      selectedCaseId.value = null;
      ElMessage.info("当前模块全部审核完毕");
    }
  } catch (e: any) {
    ElMessage.error(e?.message || "审核失败");
  } finally {
    submitting.value = false;
  }
}

function findNextCase(): any {
  for (const key of Object.keys(loadedCaseMap.value)) {
    const list = loadedCaseMap.value[key];
    if (list.length > 0) return { caseId: list[0].id };
  }
  const walkTree = (nodes: any[]): any => {
    for (const n of nodes) {
      if (n.type === "case") return { caseId: n.caseId };
      const found = walkTree(n.children || []);
      if (found) return found;
    }
    return null;
  };
  return walkTree(treeData.value);
}

// ── 工具函数 ──
loadProjectOptions();
</script>

<style scoped>
/* ==================== 整体布局 ==================== */
.case-review-index {
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
  padding: 0;
}

.top-bar {
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.review-body {
  display: flex;
  gap: 0;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ==================== 左侧 ==================== */
.review-left-panel {
  width: 300px;
  flex-shrink: 0;
  border-right: 1px solid #ebeef5;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid #ebeef5;
  background: #fff;
}

.panel-title {
  font-size: 14px;
  font-weight: 700;
  color: #303133;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.tree-node-row {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 4px;
  font-size: 13px;
}

.tree-node-row.is-case {
  font-size: 12px;
  color: #606266;
}

.tree-badge { flex-shrink: 0; }

/* ==================== 右侧 ==================== */
.review-right-panel {
  flex: 1;
  overflow-y: auto;
  background: #f0f2f5;
  min-width: 0;
}

.detail-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 16px 16px 60px;
}

/* ==================== 头部 ==================== */
.case-header {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 14px 18px;
  margin-bottom: 14px;
}

.case-name {
  font-size: 16px;
  font-weight: 700;
  color: #1d2129;
  line-height: 1.3;
}

.case-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}

.field-stats {
  font-size: 12px;
  color: #909399;
  margin-left: 4px;
}

.overall-assessment {
  margin-top: 8px;
  padding: 8px 12px;
  background: #f0f9ff;
  border-left: 3px solid #409eff;
  border-radius: 4px;
  font-size: 13px;
  color: #303133;
  line-height: 1.5;
}

.oa-label {
  font-weight: 600;
  color: #409eff;
}

.case-issues {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #fde2e2;
}

/* ==================== 区块卡片 ==================== */
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

/* ==================== 步骤 ==================== */
.steps-rule-notice {
  margin: 8px 16px;
  padding: 8px 12px;
  background: #fdf6ec;
  border-left: 3px solid #e6a23c;
  border-radius: 4px;
  font-size: 12px;
  color: #303133;
  line-height: 1.5;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.rule-badge {
  flex-shrink: 0;
  background: #e6a23c;
  color: #fff;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 600;
  white-space: nowrap;
}

.steps-compare {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  align-items: flex-start;
}

.steps-half {
  flex: 1;
  min-width: 0;
}

.steps-divider {
  display: flex;
  align-items: center;
  font-size: 22px;
  color: #c0c4cc;
  font-weight: 700;
  padding-top: 30px;
  flex-shrink: 0;
}

.steps-half-title {
  font-size: 11px;
  font-weight: 600;
  color: #909399;
  padding: 2px 8px;
  background: #f0f0f0;
  border-radius: 3px;
  display: inline-block;
  margin-bottom: 8px;
}

.steps-half-title.ai       { background: #e1f0ff; color: #409eff; }
.steps-half-title.accepted { background: #e1f3d8; color: #67c23a; }
.steps-half-title.edited   { background: #d9ecff; color: #409eff; }

.mini-step-table {
  font-size: 12px;
}

.mini-step-table :deep(th) {
  font-size: 11px;
  padding: 5px 4px !important;
  background: #f5f7fa !important;
}

.mini-step-table :deep(td) {
  font-size: 12px;
  padding: 4px 4px !important;
}

.ai-table :deep(th)       { background: #e1f0ff !important; }
.accepted-table :deep(th) { background: #e1f3d8 !important; }
.edited-table :deep(th)   { background: #d9ecff !important; }

.steps-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px 14px;
  border-top: 1px solid #f0f0f0;
}

.step-edit-area {
  padding: 14px 16px;
  border-top: 1px solid #ebeef5;
  background: #f9fafb;
}

.edit-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

/* ==================== 底部提交 ==================== */
.review-footer {
  margin-top: 8px;
}

.footer-bar {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 14px 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 36px;
}

.progress-text {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}
</style>
