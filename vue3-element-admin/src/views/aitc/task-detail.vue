<template>
  <div class="aitc-task-detail-page">
    <el-card class="mb-3">
      <div class="flex items-center gap-2 mb-4">
        <el-button @click="goBack" icon="ArrowLeft" size="small">返回</el-button>
        <span class="text-lg font-bold">任务 #{{ taskId }} 明细</span>
        <el-switch v-model="autoRefresh" active-text="自动刷新" size="small" style="margin-left: 12px" />
      </div>

      <!-- 任务基本信息 -->
      <el-descriptions v-if="task" :column="4" border size="small" class="mb-4">
        <el-descriptions-item label="任务类型">
          <el-tag :type="taskTypeTag(task.task_type)" size="small">{{ taskTypeLabel(task.task_type) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="项目">{{ task.project_name }}</el-descriptions-item>
        <el-descriptions-item label="套件" :span="2">{{ task.suite_name }}</el-descriptions-item>
        <el-descriptions-item label="模型">{{ task.model || '—' }}</el-descriptions-item>
        <el-descriptions-item label="创建人">{{ task.create_by || '—' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ task.create_time || '—' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTag(task.status)" size="small">{{ statusLabel(task.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="进度">
          <el-progress
            :percentage="task.total_count ? Math.round(task.done_count / task.total_count * 100) : 0"
            :status="task.status === 3 ? 'exception' : task.status === 2 ? 'success' : undefined"
            :stroke-width="14"
          />
          <span class="text-xs text-gray-500">{{ task.done_count }} / {{ task.total_count }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="Token 入">{{ task.input_tokens }}</el-descriptions-item>
        <el-descriptions-item label="Token 出">{{ task.output_tokens }}</el-descriptions-item>
        <el-descriptions-item v-if="task.error_msg" label="错误信息" :span="4">
          <span class="text-red-500">{{ task.error_msg }}</span>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 操作按钮 -->
      <div class="flex gap-2">
        <el-button
          v-if="task?.status === 2"
          type="warning"
          v-hasPerm="'aitc:task:confirm'"
          @click="goReview"
        >
          审核任务结果
        </el-button>
        <el-button
          v-if="task?.status === 2 || task?.status === 3 || task?.status === 4"
          type="danger"
          v-hasPerm="'aitc:task:create'"
          @click="rerunTask"
        >
          重跑任务
        </el-button>
      </div>
    </el-card>

    <!-- 审核记录 -->
    <el-card v-if="reviewRecords.length > 0" class="mb-3">
      <template #header><span class="font-bold">审核记录</span></template>
      <el-table :data="reviewRecords" border stripe size="small" max-height="300">
        <el-table-column prop="reviewer" label="审核人" width="100" />
        <el-table-column prop="reviewer_ip" label="IP" width="140" />
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="reviewActionTag(row.review_action)" size="small">
              {{ reviewActionLabel(row.review_action) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="field_name" label="字段" width="120">
          <template #default="{ row }">{{ row.field_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="审核前" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="text-xs text-gray-500">{{ formatRecordValue(row.before_value) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="审核后" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="text-xs text-green-600">{{ formatRecordValue(row.after_value) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="review_time" label="审核时间" width="160" />
      </el-table>
    </el-card>

    <!-- 明细列表 -->
    <el-card>
      <template #header>
        <div class="flex justify-between items-center">
          <span class="font-bold">任务明细（{{ items.length }} 条）</span>
          <div class="flex gap-2">
            <el-input v-model="itemKeyword" placeholder="搜索用例名" clearable size="small" style="width: 200px" />
          </div>
        </div>
      </template>
      <el-table :data="filteredItems" v-loading="loading" border stripe size="small">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="case_name" label="用例名称" min-width="200" show-overflow-tooltip />
        <el-table-column label="明细状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.item_status === 1 ? 'success' : row.item_status === 2 ? 'danger' : 'info'" size="small">
              {{ row.item_status === 0 ? '排队' : row.item_status === 1 ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="确认状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="confirmTag(row.confirm_status)" size="small">
              {{ confirmLabel(row.confirm_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="AI输出" min-width="220">
          <template #default="{ row }">
            <template v-if="row.output">
              <div v-if="row.output.selected !== undefined" class="text-sm">
                <span :class="row.output.selected ? 'text-green-600' : 'text-gray-400'">
                  {{ row.output.selected ? '★ 核心' : '非核心' }}
                </span>
                <span class="ml-2 text-gray-500">— {{ row.output.reason || '' }}</span>
              </div>
              <div v-else-if="row.output.score !== undefined" class="text-sm">
                评分: <b>{{ row.output.score }}</b>
                <div v-if="row.output.fields?.length" class="mt-1">
                  <span class="text-green-600 text-xs">{{ passedFieldCount(row.output.fields) }} 合格</span>
                  <span v-if="failedFieldCount(row.output.fields) > 0" class="text-red-500 text-xs ml-1">
                    {{ failedFieldCount(row.output.fields) }} 不合格
                  </span>
                </div>
                <div v-if="row.output.issues" class="text-red-500 text-xs">
                  {{ Array.isArray(row.output.issues) ? row.output.issues.join('; ') : row.output.issues }}
                </div>
              </div>
              <div v-else-if="row.output.script" class="text-sm text-gray-500">
                {{ row.output.language || 'python' }} / {{ row.output.framework || 'pytest' }}
              </div>
              <div v-else class="text-xs text-gray-400">{{ JSON.stringify(row.output).slice(0, 80) }}</div>
            </template>
            <span v-else class="text-gray-300">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.item_status === 1 && (row.output?.rewritten || row.output?.fields || row.output?.script)"
              text type="primary" size="small"
              @click="goReviewItem(row)"
            >
              审核
            </el-button>
            <el-button
              v-if="row.item_status === 1 && row.output"
              text type="info" size="small"
              @click="showRawOutput(row)"
              class="ml-1"
            >
              原始
            </el-button>
            <span v-else-if="row.item_status === 0" class="text-xs text-gray-400">等待中</span>
            <span v-else-if="row.item_status === 2" class="text-xs text-red-400">失败</span>
            <span v-else-if="row.confirm_status > 0" class="text-xs text-gray-400">已确认</span>
            <span v-else class="text-xs text-gray-300">—</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && items.length === 0" description="暂无明细" />
    </el-card>

    <!-- 原始 AI 输出查看弹窗 -->
    <el-dialog v-model="rawOutputVisible" title="AI 原始输出" width="700px" destroy-on-close>
      <div class="raw-output-header">
        <span class="text-sm font-bold">{{ rawOutputCaseName }}</span>
        <el-tag :type="rawOutputItemStatus === 1 ? 'success' : 'danger'" size="small" class="ml-2">
          {{ rawOutputItemStatus === 1 ? '成功' : '失败' }}
        </el-tag>
        <el-button size="small" text @click="copyRawOutput" class="ml-2">复制</el-button>
      </div>
      <pre class="raw-output-json">{{ rawOutputFormatted }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { TaskAPI } from "@/api/aitc/index";
import type { TaskVO, TaskItemVO, ReviewRecordVO } from "@/api/aitc/types";

const route = useRoute();
const router = useRouter();
const taskId = String(route.params.taskId || "");

const task = ref<TaskVO | null>(null);
const items = ref<TaskItemVO[]>([]);
const reviewRecords = ref<ReviewRecordVO[]>([]);
const loading = ref(false);
const itemKeyword = ref("");
const autoRefresh = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;

// 原始输出弹窗
const rawOutputVisible = ref(false);
const rawOutputContent = ref<Record<string, any> | null>(null);
const rawOutputCaseName = ref("");
const rawOutputItemStatus = ref(0);

const rawOutputFormatted = computed(() => {
  if (!rawOutputContent.value) return "";
  try {
    return JSON.stringify(rawOutputContent.value, null, 2);
  } catch {
    return String(rawOutputContent.value);
  }
});

const filteredItems = computed(() => {
  if (!itemKeyword.value) return items.value;
  const kw = itemKeyword.value.toLowerCase();
  return items.value.filter(it => it.case_name.toLowerCase().includes(kw));
});

// 标签映射
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
function confirmLabel(v: number) {
  return { 0: "待确认", 1: "已采纳", 2: "已忽略", 3: "编辑采纳" }[v] || "—";
}
function confirmTag(v: number) {
  return { 0: "info", 1: "success", 2: "warning", 3: "primary" }[v] || "info";
}
function reviewActionLabel(v: string) {
  return { accept: "整体采纳", ignore: "忽略", edit_accept: "编辑采纳", field_accept: "字段采纳" }[v] || v;
}
function reviewActionTag(v: string) {
  return { accept: "success", ignore: "warning", edit_accept: "primary", field_accept: "success" }[v] || "info";
}
function formatRecordValue(val?: string) {
  if (!val) return "—";
  try {
    const obj = JSON.parse(val);
    if (typeof obj === "object" && obj !== null) {
      if (Array.isArray(obj)) return `[${obj.length} 项]`;
      const keys = Object.keys(obj);
      if (keys.length <= 2) return keys.map(k => `${k}: ${String(obj[k]).slice(0, 40)}`).join(", ");
      return `{${keys.length} 个字段}`;
    }
    return String(obj).slice(0, 80);
  } catch {
    return val.slice(0, 80);
  }
}

// fields 统计（新格式）
function passedFieldCount(fields: any[]) {
  if (!Array.isArray(fields)) return 0;
  return fields.filter((f: any) => f.conclusion === "pass").length;
}
function failedFieldCount(fields: any[]) {
  if (!Array.isArray(fields)) return 0;
  return fields.filter((f: any) => f.conclusion === "fail").length;
}

// 原材料输出弹窗
function showRawOutput(row: TaskItemVO) {
  rawOutputContent.value = row.output || null;
  rawOutputCaseName.value = row.case_name;
  rawOutputItemStatus.value = row.item_status;
  rawOutputVisible.value = true;
}

async function copyRawOutput() {
  try {
    await navigator.clipboard.writeText(rawOutputFormatted.value);
    ElMessage.success("已复制到剪贴板");
  } catch {
    ElMessage.warning("复制失败，请手动复制");
  }
}

// 数据加载
async function loadData(silent = false) {
  if (!silent) loading.value = true;
  try {
    const res = await TaskAPI.getDetail(taskId);
    const detail = res as any;
    task.value = detail?.task || null;
    items.value = detail?.items || [];

    // 加载审核记录
    try {
      const records = await TaskAPI.getReviewRecords(taskId);
      reviewRecords.value = records || [];
    } catch { /* ignore */ }
  } finally {
    loading.value = false;
  }
}

// 路由跳转
function goBack() {
  router.push("/aitc/tasks");
}

function goReview() {
  // 根据任务类型跳转，默认从第一条开始审核
  if (items.value.length > 0) {
    const firstItem = items.value[0];
    if (task.value?.task_type === "case_review") {
      router.push(`/aitc/tasks/${taskId}/case-review/${firstItem.id}`);
    } else if (task.value?.task_type === "script_gen") {
      router.push(`/aitc/tasks/${taskId}/script-review/${firstItem.id}`);
    }
  }
}

function goReviewItem(row: TaskItemVO) {
  const taskType = task.value?.task_type;
  if (taskType === "case_review") {
    router.push(`/aitc/tasks/${taskId}/case-review/${row.id}`);
  } else if (taskType === "script_gen") {
    router.push(`/aitc/tasks/${taskId}/script-review/${row.id}`);
  } else {
    router.push(`/aitc/tasks/${taskId}/review?itemId=${row.id}`);
  }
}

async function rerunTask() {
  try {
    await ElMessageBox.confirm("确认重新执行？所有结果将被清空。", "重跑确认", { type: "warning" });
  } catch {
    return;
  }
  try {
    await TaskAPI.rerun(taskId);
    ElMessage.success("任务已重新启动");
    loadData();
  } catch (e: any) {
    ElMessage.error(e?.message || "重跑失败");
  }
}

// 自动刷新
function startPolling() {
  stopPolling();
  if (autoRefresh.value) {
    pollTimer = setInterval(() => loadData(true), 5000);
  }
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

import { watch } from "vue";
watch(autoRefresh, startPolling);

onMounted(() => {
  loadData();
  startPolling();
});

onUnmounted(() => stopPolling());
</script>

<style scoped>
.aitc-task-detail-page {
  padding: 4px;
}

.raw-output-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.raw-output-json {
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
</style>
