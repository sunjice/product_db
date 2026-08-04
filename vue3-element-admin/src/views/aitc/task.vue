<template>
  <div class="aitc-task-page">
    <el-card>
      <div class="flex gap-2 items-center flex-wrap mb-4">
        <el-select v-model="queryParams.projectId" placeholder="项目" clearable style="width: 160px" @change="loadTasks">
          <el-option v-for="p in projectOptions" :key="p.value" :label="p.label" :value="String(p.value)" />
        </el-select>
        <el-select v-model="queryParams.taskType" placeholder="任务类型" clearable style="width: 140px" @change="loadTasks">
          <el-option label="挑选核心" value="core_select" />
          <el-option label="用例审核" value="case_review" />
          <el-option label="生成脚本" value="script_gen" />
        </el-select>
        <el-select v-model="queryParams.status" placeholder="状态" clearable style="width: 120px" @change="loadTasks">
          <el-option label="排队" :value="0" />
          <el-option label="运行中" :value="1" />
          <el-option label="已完成" :value="2" />
          <el-option label="失败" :value="3" />
          <el-option label="已确认" :value="4" />
        </el-select>
        <el-button type="primary" @click="loadTasks">查询</el-button>
        <el-switch v-model="autoRefresh" active-text="自动刷新" size="small" style="margin-left: 8px" />
      </div>

      <el-table :data="tableData" v-loading="loading" border stripe size="small">
        <el-table-column prop="id" label="任务ID" width="80" />
        <el-table-column prop="task_type" label="任务类型" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="taskTypeTag(row.task_type)" size="small">
              {{ taskTypeLabel(row.task_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="project_name" label="项目" width="140" show-overflow-tooltip />
        <el-table-column prop="suite_name" label="套件" min-width="180" show-overflow-tooltip />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="150" align="center">
          <template #default="{ row }">
            <el-progress
              :percentage="row.total_count ? Math.round(row.done_count / row.total_count * 100) : 0"
              :status="row.status === 3 ? 'exception' : row.status === 2 ? 'success' : undefined"
              :stroke-width="16"
            />
            <span class="text-xs text-gray-500">{{ row.done_count }} / {{ row.total_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="create_by" label="创建人" width="90" />
        <el-table-column prop="create_time" label="创建时间" width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="goDetail(row)">详情</el-button>
            <el-button
              v-if="row.status === 2 || row.status === 3 || row.status === 4"
              text type="danger" size="small"
              v-hasPerm="'aitc:task:create'" @click="rerunTask(row)"
            >
              重跑
            </el-button>
            <el-button
              v-if="row.status === 2" text type="warning" size="small"
              v-hasPerm="'aitc:task:confirm'" @click="goReview(row)"
            >
              审核结果
            </el-button>
            <el-button text type="primary" size="small" @click="refreshProgress(row)">
              刷新
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && tableData.length === 0" description="暂无AI任务记录" />
      <div class="flex justify-end mt-4">
        <el-pagination
          v-model:current-page="queryParams.pageNum"
          v-model:page-size="queryParams.pageSize"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          :total="total"
          @size-change="loadTasks"
          @current-change="loadTasks"
        />
      </div>
    </el-card>


  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { ProjectAPI, TaskAPI } from "@/api/aitc/index";
import type { OptionItem, PageResult } from "@/api/common";
import type { TaskVO, TaskQueryParams, TaskItemVO } from "@/api/aitc/types";

const router = useRouter();

// ── 项目选项 ──
const projectOptions = ref<OptionItem[]>([]);

async function loadProjectOptions() {
  const res = await ProjectAPI.getOptions();
  projectOptions.value = res || [];
}

// ── 自动刷新 ──
const autoRefresh = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;
const POLL_INTERVAL = 5000; // 5 秒轮询

function startPolling() {
  stopPolling();
  if (autoRefresh.value) {
    pollTimer = setInterval(() => {
      loadTasks(true);
    }, POLL_INTERVAL);
  }
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

watch(autoRefresh, () => {
  startPolling();
});

// ── 任务列表 ──
const tableData = ref<TaskVO[]>([]);
const loading = ref(false);
const total = ref(0);
const queryParams = reactive<TaskQueryParams>({
  pageNum: 1, pageSize: 20,
  projectId: undefined, taskType: undefined, status: undefined,
});

async function loadTasks(silent = false) {
  if (!silent) loading.value = true;
  try {
    const res = await TaskAPI.getPage(queryParams);
    const page = res as PageResult<TaskVO>;
    tableData.value = page?.list || (res as any)?.records || [];
    total.value = page?.total || (res as any)?.total || 0;
  } finally {
    loading.value = false;
  }
}

async function refreshProgress(row: TaskVO) {
  const res = await TaskAPI.getItems(String(row.id));
  const items = res as TaskItemVO[];
  const done = items?.filter(i => i.item_status !== 0).length || 0;
  row.done_count = done;
  const allDone = items?.every(i => i.item_status !== 0);
  if (allDone) {
    row.status = items?.every(i => i.item_status === 1) ? 2 : 3;
  } else {
    row.status = 1;
  }
}

async function rerunTask(row: TaskVO) {
  try {
    await ElMessageBox.confirm(
      `确认重新执行任务 #${row.id}？所有已有结果将被清空。`,
      "重跑确认",
      { type: "warning" }
    );
  } catch {
    return;
  }
  try {
    await TaskAPI.rerun(String(row.id));
    ElMessage.success("任务已重新启动");
    row.status = 0;
    row.done_count = 0;
    loadTasks();
  } catch (e: any) {
    ElMessage.error(e?.message || "重跑失败");
  }
}

// 路由跳转
function goDetail(row: TaskVO) {
  router.push(`/aitc/tasks/${row.id}`);
}

function goReview(row: TaskVO) {
  router.push(`/aitc/tasks/${row.id}`);
}

// ── 标签映射 ──
function taskTypeLabel(v: string) {
  return { core_select: "挑选核心", case_review: "用例审核", script_gen: "生成脚本" }[v] || v;
}
function taskTypeTag(v: string) {
  return { core_select: "warning", case_review: "primary", script_gen: "success" }[v] || "info";
}
function statusLabel(v: number) {
  return { 0: "排队", 1: "运行中", 2: "已完成", 3: "失败", 4: "已确认" }[v] || "—";
}
function statusTag(v: number) {
  return { 0: "info", 1: "warning", 2: "success", 3: "danger", 4: "" }[v] || "info";
}

// ── 初始化 ──
onMounted(async () => {
  await loadProjectOptions();
  loadTasks();
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped>
.aitc-task-page {
  padding: 4px;
}
</style>
