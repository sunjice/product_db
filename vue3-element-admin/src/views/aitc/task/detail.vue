<template>
  <div class="aitc-task-detail-page">
    <TaskProgress :task-id="taskId" :task="task" @go-review="goReview" @rerun="rerunTask">
      <template #header-left>
        <el-button @click="goBack" icon="ArrowLeft" size="small">返回</el-button>
      </template>
      <template #header-right>
        <el-switch v-model="autoRefresh" active-text="自动刷新" size="small" style="margin-left: 12px" />
      </template>
    </TaskProgress>

    <ReviewRecordList :records="reviewRecords" />

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
            <el-tag :type="itemStatusTag(row.item_status)" size="small">
              {{ itemStatusLabel(row.item_status) }}
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
              v-if="row.item_status === ItemStatusEnum.SUCCESS && (row.output?.rewritten || row.output?.fields || row.output?.script)"
              text type="primary" size="small"
              @click="goReviewItem(row)"
            >
              审核
            </el-button>
            <el-button
              v-if="row.item_status === ItemStatusEnum.SUCCESS && row.output"
              text type="info" size="small"
              @click="showRawOutput(row)"
              class="ml-1"
            >
              原始
            </el-button>
            <span v-else-if="row.item_status === ItemStatusEnum.PENDING" class="text-xs text-gray-400">等待中</span>
            <span v-else-if="row.item_status === ItemStatusEnum.FAILED" class="text-xs text-red-400">失败</span>
            <span v-else-if="row.confirm_status > ConfirmStatusEnum.PENDING" class="text-xs text-gray-400">已确认</span>
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
        <el-tag :type="rawOutputItemStatus === ItemStatusEnum.SUCCESS ? 'success' : 'danger'" size="small" class="ml-2">
          {{ rawOutputItemStatus === ItemStatusEnum.SUCCESS ? '成功' : '失败' }}
        </el-tag>
        <el-button size="small" text @click="copyRawOutput" class="ml-2">复制</el-button>
      </div>
      <pre class="raw-output-json">{{ rawOutputFormatted }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import TaskAPI from "@/api/aitc/task";
import type { TaskVO, TaskItemVO, ReviewRecordVO } from "@/api/aitc/task";
import { ItemStatusEnum, ConfirmStatusEnum } from "@/enums/aitc";
import {
  confirmLabel, confirmTag,
  itemStatusLabel, itemStatusTag,
} from "../constants";
import { useTaskPolling } from "./composables/useTaskPolling";

const route = useRoute();
const router = useRouter();
const taskId = String(route.params.taskId || "");

const task = ref<TaskVO | null>(null);
const items = ref<TaskItemVO[]>([]);
const reviewRecords = ref<ReviewRecordVO[]>([]);
const loading = ref(false);
const itemKeyword = ref("");
// 自动刷新
const { autoRefresh } = useTaskPolling(loadData);

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

onMounted(() => {
  loadData();
});
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
