<template>
  <div class="aitc-spec-page">
    <el-card>
      <!-- 搜索区域 -->
      <div class="flex gap-2 items-center mb-4 flex-wrap">
        <el-select v-model="queryParams.projectId" placeholder="项目" clearable style="width: 160px" @change="handleProjectChange">
          <el-option v-for="p in projectOptions" :key="p.value" :label="p.label" :value="p.value" />
        </el-select>
        <el-select v-model="queryParams.taskType" placeholder="任务类型" clearable style="width: 140px" @change="loadData">
          <el-option v-for="(label, key) in taskTypeLabels" :key="key" :label="label" :value="key" />
        </el-select>
        <el-select v-model="queryParams.specType" placeholder="规范类型" clearable style="width: 140px" @change="loadData">
          <el-option v-for="(label, key) in specTypeLabels" :key="key" :label="label" :value="key" />
        </el-select>
        <el-input v-model="queryParams.keywords" placeholder="搜索内容关键词" style="width: 200px" clearable @keyup.enter="loadData" />
        <el-button type="primary" @click="loadData">搜索</el-button>
        <el-button @click="resetQuery">重置</el-button>
        <el-button type="primary" v-hasPerm="'aitc:spec:create'" @click="openCreate">新增规范</el-button>
      </div>

      <!-- 表格 -->
      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="80" sortable />
        <el-table-column prop="project_name" label="所属项目" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.project_name" size="small">{{ row.project_name }}</el-tag>
            <el-tag v-else type="info" size="small">全局通用</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="suite_name" label="所属模块" width="120">
          <template #default="{ row }">
            <span v-if="row.suite_name">{{ row.suite_name }}</span>
            <span v-else class="text-gray-400">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="task_type" label="任务类型" width="100">
          <template #default="{ row }">
            <el-tag :type="taskTypeTag(row.task_type)" size="small">
              {{ taskTypeLabels[row.task_type] || row.task_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="spec_type" label="规范类型" width="100">
          <template #default="{ row }">
            <el-tag :type="specTypeTag(row.spec_type)" size="small">
              {{ specTypeLabels[row.spec_type] || row.spec_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="规范内容" min-width="250" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.content">{{ truncateContent(row.content) }}</span>
            <span v-else class="text-gray-400">（待填写）</span>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" width="80" align="center" sortable>
          <template #header>
            <el-tooltip content="数值越小，规范在 AI 提示词中越靠前" placement="top">
              <span>优先级</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'" size="small">{{ row.status ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" v-hasPerm="'aitc:spec:update'" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" size="small" v-hasPerm="'aitc:spec:delete'" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && tableData.length === 0" description="暂无数据" />
      <div class="flex justify-end mt-4">
        <el-pagination
          v-model:current-page="queryParams.pageNum" v-model:page-size="queryParams.pageSize"
          :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" :total="total"
          @size-change="loadData" @current-change="loadData"
        />
      </div>
    </el-card>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="showDialog" :title="isEdit ? '编辑规范' : '新增规范'" width="800px" @closed="resetForm">
      <el-form :model="form" label-width="90px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="所属项目">
              <el-select v-model="form.project_id" placeholder="不选则为全局通用" clearable style="width: 100%" @change="handleFormProjectChange">
                <el-option v-for="p in projectOptions" :key="p.value" :label="p.label" :value="p.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属模块">
                <el-select v-model="form.suite_id" placeholder="不选则不限定模块" clearable style="width: 100%" :disabled="!form.project_id">
                  <el-option
                    v-for="s in flatSuiteOptions"
                    :key="s.value"
                    :label="s.label"
                    :value="s.value"
                    :disabled="s.disabled"
                  />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="任务类型" required>
              <el-select v-model="form.task_type" style="width: 100%">
                <el-option v-for="(label, key) in taskTypeLabels" :key="key" :label="label" :value="key" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="规范类型" required>
              <el-select v-model="form.spec_type" style="width: 100%">
                <el-option v-for="(label, key) in specTypeLabels" :key="key" :label="label" :value="key" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="优先级">
              <el-input-number v-model="form.sort_order" :min="0" :max="9999" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="规范内容">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="16"
            placeholder="支持 Markdown 格式，如：# 标题、## 二级标题、- 列表项等"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import ProjectAPI from "@/api/aitc/project";
import SpecAPI from "@/api/aitc/spec";
import SuiteAPI from "@/api/aitc/suite";
import type { OptionItem } from "@/api/common";
import type { SpecItem, SpecForm, SpecQueryParams } from "@/api/aitc/spec";

import { TASK_TYPE_MAP, SPEC_TYPE_LABELS, specTypeTag } from "../constants";

defineOptions({ name: "AitcSpec" });

// 标签映射（统一来源：views/aitc/constants.ts）
const taskTypeLabels = Object.fromEntries(
  Object.entries(TASK_TYPE_MAP).map(([k, v]) => [k, v.label])
);
const specTypeLabels = SPEC_TYPE_LABELS;
function taskTypeTag(t: string) { return TASK_TYPE_MAP[t]?.tag ?? ''; }
function truncateContent(text: string, max = 80) {
  if (!text) return "";
  const stripped = text.replace(/^#+ /gm, "");
  return stripped.length > max ? stripped.substring(0, max) + "..." : stripped;
}

// ── 数据 ──

const projectOptions = ref<OptionItem[]>([]);
const flatSuiteOptions = ref<(OptionItem & { disabled?: boolean })[]>([]);
const tableData = ref<SpecItem[]>([]);
const loading = ref(false);
const total = ref(0);
const queryParams = reactive<SpecQueryParams>({ pageNum: 1, pageSize: 10 });

// ── 加载数据 ──

async function loadData() {
  loading.value = true;
  try {
    const res = await SpecAPI.getPage(queryParams) as any;
    tableData.value = res.records ?? res.list ?? [];
    total.value = res.total ?? 0;
  } finally {
    loading.value = false;
  }
}

function resetQuery() {
  queryParams.projectId = undefined;
  queryParams.suiteId = undefined;
  queryParams.taskType = undefined;
  queryParams.specType = undefined;
  queryParams.keywords = undefined;
  loadData();
}

async function handleProjectChange() {
  queryParams.suiteId = undefined;
  loadData();
}

// ── 套件树拉取 ──

async function loadSuiteTree(projectId?: string) {
  if (!projectId) { flatSuiteOptions.value = []; return; }
  try {
    const tree = await SuiteAPI.getTree(projectId);
    flatSuiteOptions.value = flattenSuiteTree(tree || []);
  } catch {
    flatSuiteOptions.value = [];
  }
}

function flattenSuiteTree(nodes: any[], level = 0): (OptionItem & { disabled?: boolean })[] {
  const result: (OptionItem & { disabled?: boolean })[] = [];
  for (const node of nodes) {
    result.push({
      value: node.id,
      label: "—".repeat(level) + (level > 0 ? " " : "") + node.label,
    });
    if (node.children?.length) {
      result.push(...flattenSuiteTree(node.children, level + 1));
    }
  }
  return result;
}

// ── CRUD 弹窗 ──

const showDialog = ref(false);
const isEdit = ref(false);
const submitting = ref(false);
const editingId = ref("");

const DEFAULT_FORM: SpecForm = {
  project_id: undefined, suite_id: undefined,
  task_type: "", spec_type: "", content: "",
  sort_order: 0, status: 1,
};

const form = reactive<SpecForm>({ ...DEFAULT_FORM });

function openCreate() {
  isEdit.value = false;
  editingId.value = "";
  resetForm();
  showDialog.value = true;
}

function openEdit(row: SpecItem) {
  isEdit.value = true;
  editingId.value = String(row.id);
  Object.assign(form, {
    project_id: row.project_id || undefined,
    suite_id: row.suite_id || undefined,
    task_type: row.task_type,
    spec_type: row.spec_type,
    content: row.content,
    sort_order: row.sort_order,
    status: row.status,
  });
  if (row.project_id) {
    loadSuiteTree(String(row.project_id));
  }
  showDialog.value = true;
}

function resetForm() {
  Object.assign(form, DEFAULT_FORM);
  flatSuiteOptions.value = [];
}

async function handleFormProjectChange(projectId?: string) {
  form.suite_id = undefined;
  await loadSuiteTree(projectId);
}

async function submit() {
  if (!form.task_type || !form.spec_type) {
    ElMessage.warning("请选择任务类型和规范类型");
    return;
  }
  submitting.value = true;
  try {
    if (isEdit.value) {
      await SpecAPI.update(editingId.value, { ...form });
      ElMessage.success("更新成功");
    } else {
      await SpecAPI.create({ ...form });
      ElMessage.success("创建成功");
    }
    showDialog.value = false;
    loadData();
  } finally {
    submitting.value = false;
  }
}

async function handleDelete(row: SpecItem) {
  try {
    await ElMessageBox.confirm("确定删除此规范？", "删除确认", { type: "warning" });
    await SpecAPI.delete(String(row.id));
    ElMessage.success("删除成功");
    loadData();
  } catch {
    /* cancelled */
  }
}

// ── 初始化 ──

onMounted(async () => {
  const res = await ProjectAPI.getOptions();
  projectOptions.value = res || [];
  loadData();
});
</script>
