<template>
  <div class="aitc-case-page">
    <!-- 顶部操作栏 -->
    <el-card body-style="padding: 4px 8px">
      <div class="flex gap-1 items-center flex-wrap">
        <el-select v-model="selectedProjectId" placeholder="请选择项目" size="small" style="width: 200px" @change="onProjectChange">
          <el-option v-for="p in projectOptions" :key="p.value" :label="p.label" :value="String(p.value)" />
        </el-select>
        <el-divider direction="vertical" />
        <el-button type="default" size="small" v-hasPerm="'aitc:case:import'" @click="downloadTemplate">
          下载模板
        </el-button>
        <el-upload
          :show-file-list="false"
          :before-upload="handleImport"
          accept=".xlsx,.xls"
          v-hasPerm="'aitc:case:import'"
        >
          <el-button type="primary" size="small" :disabled="!selectedProjectId">导入Excel</el-button>
        </el-upload>
      </div>
    </el-card>

    <!-- 主体：左树右表 -->
    <div class="flex gap-2 mt-2" style="height: calc(100vh - 130px)">
      <!-- 左侧套件树 -->
      <aside class="page-aside" :class="{ 'is-collapsed': sidebarCollapsed }" style="--page-aside-width: 260px">
        <div class="page-aside__inner" style="padding: 6px 8px; overflow-y: auto">
          <el-input v-model="treeFilter" placeholder="过滤模块" size="small" clearable class="mb-1" />
          <el-tree
            ref="treeRef"
            :load="loadTreeNode"
            :filter-node-method="filterTreeByText"
            lazy
            :props="treeProps"
            node-key="id"
            :key="selectedProjectId || 'empty'"
            highlight-current
            @node-click="onTreeClick"
            class="tree-compact"
          >
            <template #default="{ data }">
              <template v-if="data.node_type === 'case'">
                <span class="text-gray-400 mr-1" style="font-size: 10px">{{ data.external_id }}</span>
                <span class="flex-1 truncate" style="font-size: 11px">{{ data.name }}</span>
              </template>
              <template v-else>
                <span class="flex-1 truncate text-xs">{{ data.label }}</span>
                <span class="text-xs text-gray-400 ml-1" style="font-size: 10px">({{ data.case_count }})</span>
              </template>
            </template>
          </el-tree>
        </div>
        <button class="page-aside__toggle" @click="sidebarCollapsed = !sidebarCollapsed">
          <el-icon :size="14">
            <ArrowLeft v-if="!sidebarCollapsed" />
            <ArrowRight v-else />
          </el-icon>
        </button>
      </aside>

      <!-- 右侧：用例表格 / 用例详情 -->
      <el-card class="flex-1 case-content" style="overflow: hidden" body-style="padding: 6px 8px">
        <div>
          <!-- 用例详情视图 -->
          <template v-if="viewMode === 'detail' && viewingCase">
            <div class="mb-2 flex items-center gap-2">
              <el-button text @click="isEditing ? cancelEdit() : backToTable()">
                <el-icon><ArrowLeft /></el-icon> {{ isEditing ? '取消编辑' : '返回列表' }}
              </el-button>
              <span class="text-xs text-gray-500 flex-1">{{ viewingCase.external_id }} — {{ viewingCase.name }}</span>
              <template v-if="isEditing">
                <el-button type="primary" size="small" :loading="editSubmitting" @click="submitEdit">保存</el-button>
              </template>
              <template v-else>
                <el-button type="primary" size="small" v-hasPerm="'aitc:case:update'" @click="startEdit(viewingCase!)">编辑</el-button>
              </template>
            </div>

            <!-- 只读模式 -->
            <template v-if="!isEditing">
              <el-descriptions :column="2" border size="small" label-width="80px">
                <el-descriptions-item label="用例编号" :span="2">{{ viewingCase.external_id }}</el-descriptions-item>
                <el-descriptions-item label="用例名称" :span="2">{{ viewingCase.name }}</el-descriptions-item>
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
                  {{ viewingCase.core_source === 1 ? 'AI挑选' : viewingCase.core_source === 2 ? '人工标记' : '—' }}
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
            </template>

            <!-- 编辑模式（与只读布局完全一致，仅字段变为可编辑） -->
            <template v-else>
              <el-descriptions :column="2" border size="small" label-width="80px">
                <el-descriptions-item label="用例编号" :span="2">
                  <el-input v-model="editForm.external_id" size="small" placeholder="—" />
                </el-descriptions-item>
                <el-descriptions-item label="用例名称" :span="2">
                  <el-input v-model="editForm.name" size="small" placeholder="—" />
                </el-descriptions-item>
                <el-descriptions-item label="级别">
                  <el-select v-model="editForm.importance" size="small" style="width: 100%">
                    <el-option label="高" :value="3" />
                    <el-option label="中" :value="2" />
                    <el-option label="低" :value="1" />
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
                  {{ viewingCase!.core_source === 1 ? 'AI挑选' : viewingCase!.core_source === 2 ? '人工标记' : '—' }}
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
                      <el-button text type="danger" size="small" @click="removeStep($index)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <el-button class="mt-1" size="small" @click="addStep">+ 添加步骤</el-button>
              </div>
            </template>
          </template>

          <!-- 用例表格视图 -->
          <template v-else>
          <div class="mb-1 flex gap-1 items-center flex-wrap">
            <el-select v-model="queryParams.isCore" placeholder="核心状态" clearable size="small" style="width: 120px" @change="loadCases">
              <el-option label="核心用例" :value="1" />
              <el-option label="非核心" :value="0" />
            </el-select>
            <el-select v-model="queryParams.isSample" placeholder="样本状态" clearable size="small" style="width: 120px" @change="loadCases">
              <el-option label="样本用例" :value="1" />
              <el-option label="非样本" :value="0" />
            </el-select>
            <el-select v-model="queryParams.reviewStatus" placeholder="审核状态" clearable size="small" style="width: 120px" @change="loadCases">
              <el-option label="已审核" :value="1" />
              <el-option label="未审核" :value="0" />
            </el-select>
            <el-select v-model="queryParams.importance" placeholder="级别" clearable size="small" style="width: 100px" @change="loadCases">
              <el-option label="高" :value="3" />
              <el-option label="中" :value="2" />
              <el-option label="低" :value="1" />
            </el-select>
            <el-input
              v-model="queryParams.keywords" placeholder="搜索用例"
              size="small" style="width: 200px" clearable @keyup.enter="loadCases"
            />
            <el-button type="primary" size="small" @click="loadCases">搜索</el-button>
            <el-button size="small" @click="handleReset">重置</el-button>
          </div>
          <el-table ref="tableRef" :data="tableData" v-loading="loading" border stripe size="small" max-height="calc(100vh - 220px)" row-key="id" @sort-change="onSortChange" @selection-change="handleSelectionChange">
            <el-table-column type="selection" width="44" align="center" />
            <el-table-column prop="external_id" label="编号" width="100" sortable="custom" />
            <el-table-column prop="name" label="用例名称" min-width="200" show-overflow-tooltip />
            <el-table-column prop="importance" label="级别" width="70" align="center" sortable="custom">
              <template #default="{ row }">
                <el-tag :type="importanceType(row.importance)" size="small">
                  {{ importanceLabel(row.importance) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="is_core" label="核心" width="90" align="center" sortable="custom">
              <template #default="{ row }">
                <el-tooltip
                  v-if="row.is_core"
                  :content="row.core_reason || '无理由'"
                  placement="top"
                  :show-after="300"
                >
                  <span class="text-orange-500 cursor-pointer" style="font-size: 12px">★</span>
                </el-tooltip>
                <span v-else class="text-gray-300">—</span>
              </template>
            </el-table-column>
            <el-table-column prop="is_sample" label="样本" width="70" align="center">
              <template #default="{ row }">
                <span v-if="row.is_sample" class="text-green-500" style="font-size: 13px" title="样本用例">✓</span>
                <span v-else class="text-gray-300" style="font-size: 13px" title="非样本">—</span>
              </template>
            </el-table-column>
            <el-table-column prop="script_count" label="脚本" width="60" align="center" />
            <el-table-column label="操作" width="280" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click="showDetail(row)">详情</el-button>
                <el-button text type="primary" size="small" v-hasPerm="'aitc:case:update'" @click="openEdit(row)">编辑</el-button>
                <el-button text type="primary" size="small" v-hasPerm="'aitc:case:core'" @click="toggleCore(row)">
                  {{ row.is_core ? '取消核心' : '标记核心' }}
                </el-button>
                <el-button text type="primary" size="small" v-hasPerm="'aitc:case:sample'" @click="toggleSample(row)">
                  {{ row.is_sample ? '取消样本' : '标记样本' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!loading && tableData.length === 0" description="请选择项目或模块查看用例" />
          <div class="flex justify-end mt-1">
            <el-pagination
              v-model:current-page="queryParams.pageNum"
              v-model:page-size="queryParams.pageSize"
              :page-sizes="[100]"
              layout="total, prev, pager, next"
              :total="total"
              @size-change="loadCases"
              @current-change="loadCases"
              size="small"
            />
          </div>
        </template>
        </div>
      </el-card>
    </div>

    <!-- 导入结果弹窗 -->
    <el-dialog v-model="showImportResult" title="导入结果" width="500px">
      <div class="mb-2">新增 {{ importResult.created }} 条，更新 {{ importResult.updated }} 条</div>
      <div v-if="importResult.errors.length > 0" class="mt-2">
        <div class="text-red-500 mb-1">以下行导入失败：</div>
        <div v-for="e in importResult.errors" :key="e.row" class="text-xs text-gray-600">
          第 {{ e.row }} 行：{{ e.msg }}
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="showImportResult = false">确定</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch, nextTick } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadProps } from "element-plus";
import { ArrowLeft, ArrowRight } from "@element-plus/icons-vue";
import { ProjectAPI, SuiteAPI, CaseAPI } from "@/api/aitc/index";
import { useTableSelection } from "@/composables/useTableSelection";
import { useAiContextStore } from "@/stores/aiContext";
import type { OptionItem, PageResult } from "@/api/common";
import type {
  SuiteNode,
  CaseQueryParams, CaseVO, CaseForm, ImportResult,
} from "@/api/aitc/types";

// ── 项目 ──
const selectedProjectId = ref("");
const sidebarCollapsed = ref(false);
const projectOptions = ref<OptionItem[]>([]);

async function loadProjectOptions() {
  const res = await ProjectAPI.getOptions();
  projectOptions.value = res || [];
}

// ── 套件树 ──
const treeRef = ref();
const treeFilter = ref("");
const selectedSuiteId = ref("");
/** 当前查看的用例 ID（详情视图打开期间有效，离开后清空） */
const currentCaseId = ref<number | null>(null);
const treeProps = { children: "children", label: "label", isLeaf: (data: any) => data.node_type === "case" };

function filterTreeByText(value: string, data: any) {
  if (!value) return true;
  const v = value.toLowerCase();
  return (data.label || "").toLowerCase().includes(v)
    || (data.name || "").toLowerCase().includes(v)
    || (data.external_id || "").toLowerCase().includes(v);
}

watch(treeFilter, (val) => treeRef.value?.filter(val));

/** 懒加载树节点 */
function loadTreeNode(node: any, resolve: (data: SuiteNode[]) => void) {
  if (node.level === 0) {
    // 根节点：未选项目时返回空列表
    if (!selectedProjectId.value) {
      resolve([]);
      return;
    }
    SuiteAPI.getChildren(0, selectedProjectId.value).then((res) => {
      resolve(res || []);
    });
  } else if (node.data.node_type === "case") {
    // 用例节点：无子节点
    resolve([]);
  } else {
    // 套件节点：加载子套件 + 用例
    SuiteAPI.getChildren(node.data.id).then((res) => {
      resolve(res || []);
    });
  }
}

async function onProjectChange() {
  selectedSuiteId.value = "";
  queryParams.suiteId = undefined;
  viewMode.value = "table";
  viewingCase.value = null;
  tableData.value = [];
  total.value = 0;
  // 切换项目：勾选与查看状态全部失效
  selectedIds.value = [];
  currentCaseId.value = null;
}

function onTreeClick(node: SuiteNode) {
  if (node.node_type === "case") {
    _snapshotSelectedIds = [...selectedIds.value];
    const caseId = Number(-(node.id as number)); // 后端用负数 ID 避免冲突
    CaseAPI.getById(String(caseId)).then((res) => {
      viewingCase.value = res as CaseVO;
      viewMode.value = "detail";
    });
    if (node.parent_id != null) {
      selectedSuiteId.value = String(node.parent_id);
    }
    currentCaseId.value = caseId;
    return;
  }
  // 点击套件节点 → 切换模块上下文，勾选与查看状态全部清空
  selectedSuiteId.value = String(node.id);
  queryParams.suiteId = String(node.id) as any;
  viewMode.value = "table";
  selectedIds.value = [];
  currentCaseId.value = null;
  loadCases();
}

/** 从详情视图返回表格视图 */
async function backToTable() {
  viewMode.value = "table";
  viewingCase.value = null;
  currentCaseId.value = null;
  // 表格重新挂载后，用 toggleRowSelection 恢复勾选（会触发 selection-change → 同步 selectedIds）
  await nextTick();
  if (_snapshotSelectedIds.length && tableRef.value && tableData.value.length) {
    for (const row of tableData.value) {
      if (_snapshotSelectedIds.includes(row.id)) {
        tableRef.value.toggleRowSelection(row, true);
      }
    }
  }
}

// ── 用例列表 ──
const tableData = ref<CaseVO[]>([]);
const loading = ref(false);
const total = ref(0);
const tableRef = ref();
const { selectedIds, handleSelectionChange } = useTableSelection<CaseVO>();

// ── AI 上下文注册 ──
const aiContextStore = useAiContextStore();

// 监听页面选择变化，自动同步到 AI 上下文 Store
watch([selectedProjectId, selectedSuiteId, selectedIds, currentCaseId], () => {
  aiContextStore.update({
    projectId: selectedProjectId.value ? Number(selectedProjectId.value) : null,
    suiteId: selectedSuiteId.value ? Number(selectedSuiteId.value) : null,
    selectedCaseIds: selectedIds.value.map((id) => Number(id)),
    currentCaseId: currentCaseId.value != null ? Number(currentCaseId.value) : null,
  });
});

const queryParams = reactive<CaseQueryParams>({
  pageNum: 1, pageSize: 100,
  projectId: undefined, suiteId: undefined,
  isCore: undefined, reviewStatus: undefined,
  importance: undefined, keywords: undefined,
});

// ── 排序 ──
function onSortChange({ prop, order }: { prop: string; order: string | null }) {
  queryParams.sortField = order ? prop : undefined;
  queryParams.sortOrder = order || undefined;
  loadCases();
}

async function loadCases() {
  if (!selectedProjectId.value) return;
  loading.value = true;
  try {
    queryParams.projectId = selectedProjectId.value;
    const res = await CaseAPI.getPage(queryParams);
    const page = res as PageResult<CaseVO>;
    tableData.value = page?.list || (res as any)?.records || [];
    total.value = page?.total || (res as any)?.total || 0;
  } finally {
    loading.value = false;
  }
}

/** 重置所有筛选条件并重新加载 */
function handleReset() {
  queryParams.isCore = undefined;
  queryParams.isSample = undefined;
  queryParams.reviewStatus = undefined;
  queryParams.importance = undefined;
  queryParams.keywords = undefined;
  queryParams.pageNum = 1;
  treeFilter.value = "";
  viewMode.value = "table";
  viewingCase.value = null;
  loadCases();
}

function importanceLabel(v: number) {
  return { 1: "低", 2: "中", 3: "高" }[v] || "—";
}

function importanceType(v: number) {
  return { 1: "info", 2: "warning", 3: "danger" }[v] || "info";
}

// ── 核心标记 ──
async function toggleCore(row: CaseVO) {
  const newVal = row.is_core ? 0 : 1;
  const action = newVal ? "标记为核心用例" : "取消核心用例";
  try {
    await ElMessageBox.confirm(`确定${action}？`, "操作确认");
    const updated = await CaseAPI.markCore({ case_id: String(row.id), is_core: newVal });
    ElMessage.success("操作成功");
    // 只更新当前行，不重新加载整张表
    row.is_core = newVal;
    row.core_reason = (updated as any)?.core_reason ?? row.core_reason;
    row.core_source = (updated as any)?.core_source ?? (newVal ? 2 : undefined);
  } catch { /* cancelled */ }
}

// ── 样本标记 ──
async function toggleSample(row: CaseVO) {
  const newVal = row.is_sample ? 0 : 1;
  try {
    await CaseAPI.markSample({ case_id: String(row.id), is_sample: newVal });
    ElMessage.success(newVal ? "已标记为样本用例" : "已取消样本用例");
    row.is_sample = newVal;
  } catch { /* cancelled */ }
}

// ── 右侧视图模式：table | detail ──
const viewMode = ref<"table" | "detail">("table");
const viewingCase = ref<CaseVO | null>(null);
/** 进入详情前的勾选快照（表格 v-if 销毁会清空 selectedIds，返回时用它恢复） */
let _snapshotSelectedIds: (string | number)[] = [];

// ── 用例详情（表格内"详情"按钮 → 也在右侧区域展示）──

async function showDetail(row: CaseVO) {
  _snapshotSelectedIds = [...selectedIds.value];
  const res = await CaseAPI.getById(String(row.id));
  viewingCase.value = res as CaseVO;
  viewMode.value = "detail";
  currentCaseId.value = Number(row.id);
}

// ── 用例编辑 ──

const isEditing = ref(false);
const editSubmitting = ref(false);
const editingCaseId = ref<string>("");

interface StepForm {
  step_no: number;
  action: string;
  expected: string;
}

const editForm = reactive<{
  external_id: string;
  name: string;
  summary: string;
  preconditions: string;
  topo: string;
  test_data: string;
  steps: StepForm[];
  importance: number;
}>({
  external_id: "",
  name: "",
  summary: "",
  preconditions: "",
  topo: "",
  test_data: "",
  steps: [],
  importance: 2,
});

/** 表格行"编辑"按钮：跳转到详情页，并进入编辑模式 */
async function openEdit(row: CaseVO) {
  _snapshotSelectedIds = [...selectedIds.value];
  const res = await CaseAPI.getById(String(row.id));
  viewingCase.value = res as CaseVO;
  viewMode.value = "detail";
  currentCaseId.value = Number(row.id);
  populateEditForm(res as CaseVO);
  isEditing.value = true;
}

/** 详情页"编辑"按钮：在当前详情页进入编辑模式 */
function startEdit(row: CaseVO) {
  populateEditForm(row);
  isEditing.value = true;
}

/** 填充编辑表单 */
function populateEditForm(row: CaseVO) {
  editingCaseId.value = String(row.id);
  editForm.external_id = row.external_id || "";
  editForm.name = row.name;
  editForm.summary = row.summary || "";
  editForm.preconditions = row.preconditions || "";
  editForm.topo = row.topo || "";
  editForm.test_data = row.test_data || "";
  editForm.importance = row.importance;
  editForm.steps = (row.steps || []).map((s, i) => ({
    step_no: i + 1,
    action: s.action,
    expected: s.expected,
  }));
}

/** 取消编辑，回到只读详情 */
async function cancelEdit() {
  try {
    await ElMessageBox.confirm("取消后未保存的修改将丢失，确定取消？", "提示", {
      confirmButtonText: "确定取消",
      cancelButtonText: "继续编辑",
      type: "warning",
    });
    isEditing.value = false;
  } catch {
    /* 用户点击了"继续编辑"，不操作 */
  }
}

function addStep() {
  editForm.steps.push({
    step_no: editForm.steps.length + 1,
    action: "",
    expected: "",
  });
}

function removeStep(index: number) {
  editForm.steps.splice(index, 1);
  // 重新编号
  editForm.steps.forEach((s, i) => (s.step_no = i + 1));
}

async function submitEdit() {
  if (!editForm.name.trim()) {
    ElMessage.warning("请输入用例名称");
    return;
  }

  editSubmitting.value = true;
  try {
    const data: CaseForm = {
      external_id: editForm.external_id || undefined,
      name: editForm.name,
      summary: editForm.summary || undefined,
      preconditions: editForm.preconditions || undefined,
      topo: editForm.topo || undefined,
      test_data: editForm.test_data || undefined,
      steps: editForm.steps.map((s, i) => ({
        step_no: i + 1,
        action: s.action,
        expected: s.expected,
      })),
      importance: editForm.importance,
    };
    await CaseAPI.update(editingCaseId.value, data);
    ElMessage.success("保存成功");
    isEditing.value = false;

    // 刷新当前视图
    if (viewMode.value === "detail" && viewingCase.value) {
      const res = await CaseAPI.getById(editingCaseId.value);
      viewingCase.value = res as CaseVO;
    }
    loadCases();

    // 精准更新左侧树中对应节点（树中用例节点 id = -真实ID，用于区分套件/用例）
    const caseId = Number(editingCaseId.value);
    const treeNodeId = -caseId;
    const node = treeRef.value?.getNode(treeNodeId);
    if (node?.data) {
      node.data = {
        ...node.data,
        external_id: editForm.external_id || node.data.external_id,
        name: editForm.name,
      };
    }
  } finally {
    editSubmitting.value = false;
  }
}

// ── Excel 导入 ──
const showImportResult = ref(false);
const importResult = reactive<ImportResult>({ created: 0, updated: 0, errors: [] });

async function downloadTemplate() {
  const res = await CaseAPI.downloadTemplate();
  const blob = new Blob([res as any], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "用例导入模板.xlsx";
  a.click();
  URL.revokeObjectURL(url);
}

const handleImport: UploadProps["beforeUpload"] = async (file) => {
  if (!selectedProjectId.value) {
    ElMessage.warning("请先选择项目");
    return false;
  }
  try {
    const res = await CaseAPI.importExcel(selectedProjectId.value, file);
    Object.assign(importResult, res);
    showImportResult.value = true;
    loadCases();
    onProjectChange(); // 刷新树
  } catch (e: any) {
    ElMessage.error(e?.message || "导入失败");
  }
  return false; // 阻止默认上传
};

// ── 初始化 ──
onMounted(() => {
  aiContextStore.register("case");
  loadProjectOptions();
});

onUnmounted(() => {
  aiContextStore.unregister();
});
</script>

<style scoped>
.aitc-case-page {
  padding: 4px;
  font-family: Inter, sans-serif;
  font-size: 11px;
}

/* 紧凑树样式 */
.tree-compact {
  font-size: 11px;
}
.tree-compact :deep(.el-tree-node__content) {
  height: 24px;
  line-height: 24px;
}
.tree-compact :deep(.el-tree-node__label) {
  font-size: 11px;
}
.tree-compact :deep(.el-tree-node__expand-icon) {
  font-size: 11px;
  padding: 0 4px;
}

/* 右侧内容区字体与树保持一致（11px） */
.case-content {
  font-size: 11px;
}
.case-content :deep(.el-button) {
  font-size: 11px;
}
.case-content :deep(.el-input__inner) {
  font-size: 11px;
}
.case-content :deep(.el-select .el-input__inner) {
  font-size: 11px;
}
.case-content :deep(.el-pagination) {
  font-size: 11px;
}
.case-content :deep(.el-empty__description) {
  font-size: 11px;
}

/* 表格压缩到与树节点同高（24px） */
.case-content :deep(.el-table__row) {
  height: 24px;
}
.case-content :deep(.el-table .cell) {
  padding: 2px 4px;
  line-height: 1.2;
}
.case-content :deep(.el-table th.el-table__cell) {
  padding: 4px 0;
}
.case-content :deep(.el-table td.el-table__cell) {
  padding: 2px 0;
}

/* 详情描述列表压缩 */
.case-content :deep(.el-descriptions__cell) {
  padding: 4px 8px;
}

/* 编辑模式：显示细边框输入框，字体 12px 与只读对齐 */

/* ===== descriptions 中的输入控件 ===== */
.case-content :deep(.el-descriptions__cell .edit-inline-input) {
  width: 100%;
}
/* textarea */
.case-content :deep(.el-descriptions__cell .edit-inline-input .el-textarea__inner) {
  font-size: 12px;
  padding: 0 6px;
  min-height: 22px;
  line-height: 1.5;
  border-radius: 3px;
}
/* 普通 input（用例名称） */
.case-content :deep(.el-descriptions__cell .edit-inline-input .el-input__wrapper) {
  padding: 0 6px;
  border-radius: 3px;
  box-shadow: none;
}
.case-content :deep(.el-descriptions__cell .edit-inline-input .el-input__inner) {
  font-size: 12px;
  padding: 0;
  height: 24px;
  line-height: 24px;
}
/* select（级别） */
.case-content :deep(.el-descriptions__cell .el-select) {
  width: 100%;
}
.case-content :deep(.el-descriptions__cell .el-select .el-input__wrapper) {
  padding: 0 6px;
  border-radius: 3px;
  box-shadow: none;
}
.case-content :deep(.el-descriptions__cell .el-select .el-input__inner) {
  font-size: 12px;
  padding: 0;
  height: 24px;
  line-height: 24px;
}

/* ===== 步骤表格 ===== */
.edit-steps-table :deep(.el-table__row) {
  height: auto !important;
}
.edit-steps-table :deep(.el-table td.el-table__cell) .cell {
  padding: 2px 4px;
  line-height: 1.5;
}
.edit-steps-table :deep(.el-textarea) {
  width: 100%;
}
.edit-steps-table :deep(.el-textarea__inner) {
  font-size: 12px;
  padding: 0 6px;
  min-height: 22px;
  line-height: 1.5;
  border-radius: 3px;
}
</style>
