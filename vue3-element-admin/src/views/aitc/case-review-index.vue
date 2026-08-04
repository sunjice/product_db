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
                <el-tag v-if="data.type === 'case' && data.importance" :type="impType(data.importance)" size="small" class="ml-1">
                  {{ impLabel(data.importance) }}
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
                  <el-tag :type="impType(currentDetail.case.importance)" size="small">{{ impLabel(currentDetail.case.importance) }}</el-tag>
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

              <!-- 审核结论 -->
              <el-table-column label="审核结论" width="110" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.conclusion === 'pass'" type="success" effect="plain" size="small">
                    ✓ 合格
                  </el-tag>
                  <el-tag v-else type="danger" effect="plain" size="small">
                    ✗ 不合格
                  </el-tag>
                </template>
              </el-table-column>

              <!-- 违反的规范 -->
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

              <!-- AI修改建议 -->
              <el-table-column label="AI修改建议" min-width="220">
                <template #default="{ row }">
                  <template v-if="row.conclusion === 'fail' && row.hasSuggestion">
                    <!-- 未处理：显示建议 -->
                    <template v-if="!fieldStates[row.field_name]">
                      <div class="cell-text suggested">{{ displayVal(row.suggested) }}</div>
                    </template>
                    <!-- 已采纳：确认标记 -->
                    <template v-else-if="fieldStates[row.field_name] === 'accept'">
                      <span class="text-green-500 text-xs">✓ 已采纳</span>
                    </template>
                    <!-- 已忽略 -->
                    <template v-else-if="fieldStates[row.field_name] === 'ignore'">
                      <span class="text-orange-500 text-xs">已忽略</span>
                    </template>
                    <!-- 已手动修改 -->
                    <template v-else-if="fieldStates[row.field_name] === 'manual'">
                      <span class="text-blue-500 text-xs">已手动修改</span>
                    </template>
                  </template>
                  <template v-else>
                    <span class="text-gray-400 text-xs">—</span>
                  </template>
                </template>
              </el-table-column>

              <!-- 值（当前/最终） -->
              <el-table-column label="值" min-width="180">
                <template #default="{ row }">
                  <!-- 合格/无建议：显示原始值 -->
                  <template v-if="!fieldStates[row.field_name] && editingField !== row.field_name">
                    <div class="cell-text muted">{{ displayVal(row.original) }}</div>
                  </template>
                  <!-- 已采纳：显示AI值 -->
                  <template v-else-if="fieldStates[row.field_name] === 'accept'">
                    <div class="cell-text accepted">{{ displayVal(row.suggested) }}</div>
                  </template>
                  <!-- 已手动修改 -->
                  <template v-else-if="fieldStates[row.field_name] === 'manual'">
                    <div class="cell-text edited">{{ manualValues[row.field_name] }}</div>
                  </template>
                  <!-- 已忽略 -->
                  <template v-else-if="fieldStates[row.field_name] === 'ignore'">
                    <div class="cell-text ignored">{{ displayVal(row.original) }}</div>
                  </template>
                  <!-- 编辑中 -->
                  <template v-else-if="editingField === row.field_name">
                    <el-input
                      v-model="editDraft[row.field_name]"
                      type="textarea"
                      :rows="4"
                      size="small"
                      placeholder="请输入修改后的内容..."
                    />
                    <div class="inline-actions">
                      <el-button size="small" type="primary" @click="saveManualEdit(row.field_name)">保存</el-button>
                      <el-button size="small" @click="cancelEdit">取消</el-button>
                    </div>
                  </template>
                </template>
              </el-table-column>

              <!-- 操作 -->
              <el-table-column label="操作" width="200" fixed="right" align="center">
                <template #default="{ row }">
                  <!-- 合格 → 无需操作 -->
                  <template v-if="row.conclusion === 'pass'">
                    <span class="text-gray-400 text-xs">—</span>
                  </template>
                  <!-- 不合格 → 三态操作 -->
                  <template v-else>
                    <!-- 未处理 -->
                    <template v-if="!fieldStates[row.field_name]">
                      <template v-if="row.hasSuggestion">
                        <el-button size="small" type="success" @click="acceptField(row.field_name)">采纳</el-button>
                        <el-button size="small" type="primary" plain @click="startEdit(row)">修改</el-button>
                        <el-button size="small" type="warning" plain @click="ignoreField(row.field_name)">忽略</el-button>
                      </template>
                    </template>
                    <!-- 已处理 -->
                    <template v-else>
                      <el-tag v-if="fieldStates[row.field_name] === 'accept'" type="success" size="small">✓ 已采纳</el-tag>
                      <el-tag v-else-if="fieldStates[row.field_name] === 'manual'" type="primary" size="small">✎ 已修改</el-tag>
                      <el-tag v-else-if="fieldStates[row.field_name] === 'ignore'" type="warning" size="small">已忽略</el-tag>
                      <el-button size="small" link type="primary" class="ml-2" @click="resetField(row.field_name)">重置</el-button>
                    </template>
                  </template>
                </template>
              </el-table-column>
            </el-table>
          </div>

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
import { ProjectAPI, ReviewAPI } from "@/api/aitc/index";
import type { OptionItem } from "@/api/common";
import type {
  PendingSuiteNode, PendingCaseVO,
  CaseReviewDetailVO, FieldSuggestionVO,
} from "@/api/aitc/types";

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

const fieldLabelMap: Record<string, string> = {
  name: "用例名称",
  summary: "测试思想",
  preconditions: "前置条件",
  test_data: "测试数据",
  topo: "测试Topo",
  steps: "测试步骤",
};

// 字段处理状态: null=未处理, 'accept'=采纳AI, 'ignore'=保持原样, 'manual'=人工编辑
const fieldStates = reactive<Record<string, string | null>>({});
const manualValues = reactive<Record<string, any>>({});
const editingField = ref<string | null>(null);
const editDraft = reactive<Record<string, string>>({});
const editSteps = ref<any[]>([]);

function clearFieldStates() {
  Object.keys(fieldStates).forEach(k => { fieldStates[k] = null; });
  Object.keys(manualValues).forEach(k => { manualValues[k] = null; });
}

// 文本字段表格行（排除 steps）
interface TextFieldRow {
  field_name: string;
  label: string;
  conclusion: string;
  rule_violated: string;
  hasSuggestion: boolean;
  original: any;
  suggested: any;
}

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

function textRowClassName({ row }: { row: TextFieldRow }) {
  if (row.conclusion === "pass") return "";
  const st = fieldStates[row.field_name];
  if (st === "accept") return "row-accept";
  if (st === "manual") return "row-edit";
  if (st === "ignore") return "row-ignore";
  return "row-pending";
}

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

// 统计
const passCount = computed(() => {
  return (currentDetail.value?.suggestions || []).filter(s => s.conclusion === "pass").length;
});

const failCount = computed(() => {
  return (currentDetail.value?.suggestions || []).filter(s => s.conclusion === "fail").length;
});

const processedCount = computed(() => {
  return Object.entries(fieldStates).filter(
    ([k, v]) => v && currentDetail.value?.suggestions?.some(s => s.field_name === k && s.conclusion === "fail")
  ).length;
});

const canSubmit = computed(() => {
  if (!currentDetail.value?.suggestions) return false;
  const fails = currentDetail.value.suggestions.filter(s => s.conclusion === "fail");
  return fails.length === 0 || processedCount.value >= fails.length;
});

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

function displayVal(v: any) {
  if (v === null || v === undefined || v === "") return "（空）";
  return String(v);
}

// ── 三态操作 ──
function acceptField(fieldName: string) {
  fieldStates[fieldName] = "accept";
  cancelEdit();
}

function ignoreField(fieldName: string) {
  fieldStates[fieldName] = "ignore";
  cancelEdit();
}

function resetField(fieldName: string) {
  fieldStates[fieldName] = null;
  manualValues[fieldName] = undefined;
  cancelEdit();
}

function startEdit(sug: FieldSuggestionVO) {
  cancelEdit();
  editingField.value = sug.field_name;
  if (sug.field_name === "steps") {
    const base = (sug.has_suggestion && sug.suggested?.length) ? sug.suggested : sug.original || [];
    editSteps.value = JSON.parse(JSON.stringify(base));
  } else {
    editDraft[sug.field_name] = sug.has_suggestion ? displayVal(sug.suggested) : displayVal(sug.original);
  }
}

function cancelEdit() {
  editingField.value = null;
  editSteps.value = [];
}

function addStepRow() {
  const no = editSteps.value.length + 1;
  editSteps.value = [...editSteps.value, { step_no: no, action: "", expected: "" }];
}

function removeStepRow() {
  if (editSteps.value.length <= 1) return;
  editSteps.value = editSteps.value.slice(0, -1);
}

function saveManualEdit(fieldName: string) {
  if (fieldName === "steps") {
    const steps = editSteps.value.map((s: any, i: number) => ({ ...s, step_no: i + 1 }));
    manualValues.steps = steps;
  } else {
    manualValues[fieldName] = editDraft[fieldName] || "";
  }
  fieldStates[fieldName] = "manual";
  cancelEdit();
}

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
    const fields = fails.map(s => {
      const action = fieldStates[s.field_name] || "ignore";
      const item: any = { field_name: s.field_name, action };
      if (action === "manual") {
        item.action = "edit_accept";
        item.edited_value = manualValues[s.field_name];
      }
      return item;
    });

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
function impLabel(v: number) { return { 1: "低", 2: "中", 3: "高" }[v] || "—"; }
function impType(v: number) { return { 1: "info", 2: "warning", 3: "danger" }[v] || "info"; }
function scoreTag(s: number) { return s >= 80 ? "success" : s >= 60 ? "warning" : "danger"; }

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

/* ==================== 统一表格 ==================== */
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

/* 行高亮 */
::deep(.row-accept)  { background-color: #f0f9eb !important; }
::deep(.row-edit)    { background-color: #ecf5ff !important; }
::deep(.row-ignore)  { background-color: #fdf6ec !important; opacity: 0.7; }
::deep(.row-pending) { background-color: #fef0f0 !important; }

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
