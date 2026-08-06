<template>
  <div class="llm-log-page">
    <el-card>
      <!-- 查询条件 -->
      <div class="flex gap-2 items-center flex-wrap mb-4">
        <el-select
          v-model="queryParams.session_id"
          placeholder="选择会话"
          clearable
          filterable
          style="width: 260px"
          @change="handleSearch"
        >
          <el-option
            v-for="s in sessionOptions"
            :key="s.session_id"
            :label="`会话 #${s.session_id}（${s.log_count} 条日志）`"
            :value="s.session_id"
          />
        </el-select>
        <el-input
          v-model="queryParams.trace_id"
          placeholder="Trace ID"
          clearable
          style="width: 200px"
          @clear="handleSearch"
          @keyup.enter="handleSearch"
        />
        <el-select
          v-model="queryParams.status"
          placeholder="状态"
          clearable
          style="width: 100px"
          @change="handleSearch"
        >
          <el-option label="成功" value="success" />
          <el-option label="失败" value="error" />
        </el-select>
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button @click="handleExport('json')">导出 JSON</el-button>
        <el-button @click="handleExport('txt')">导出 TXT</el-button>
      </div>

      <!-- 日志表格 -->
      <el-table :data="tableData" v-loading="loading" border stripe size="small">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="session_id" label="会话ID" width="80" />
        <el-table-column prop="action" label="动作" width="140" show-overflow-tooltip />
        <el-table-column prop="model" label="模型" width="120" />
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Tokens" width="110" align="center">
          <template #default="{ row }">
            <span class="text-xs">
              {{ row.prompt_tokens }} + {{ row.completion_tokens }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="80" align="center">
          <template #default="{ row }">
            {{ row.duration_ms }}ms
          </template>
        </el-table-column>
        <el-table-column prop="trace_id" label="Trace ID" width="200" show-overflow-tooltip />
        <el-table-column prop="create_time" label="时间" width="170" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="handleCopy(row)">
              复制
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && tableData.length === 0" description="暂无日志记录" />

      <div class="flex justify-end mt-4">
        <el-pagination
          v-model:current-page="queryParams.pageNum"
          v-model:page-size="queryParams.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          :total="total"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue"
import { ElMessage } from "element-plus"
import { LlmLogAPI, type LlmLogItem, type LlmLogSession } from "@/api/chat/llm-log"

// ── 会话下拉 ──
const sessionOptions = ref<LlmLogSession[]>([])

async function loadSessions() {
  try {
    const res = await LlmLogAPI.getSessions()
    sessionOptions.value = res || []
  } catch {
    // 静默
  }
}

// ── 列表数据 ──
const tableData = ref<LlmLogItem[]>([])
const loading = ref(false)
const total = ref(0)

const queryParams = reactive({
  pageNum: 1,
  pageSize: 20,
  session_id: null as number | null,
  trace_id: "",
  action: "",
  status: "",
  module: "",
})

async function loadData() {
  loading.value = true
  try {
    const res = await LlmLogAPI.getPage({ ...queryParams })
    tableData.value = res?.list || []
    total.value = res?.total || 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  queryParams.pageNum = 1
  loadData()
}

// ── 复制 ──
async function handleCopy(row: LlmLogItem) {
  try {
    const detail = await LlmLogAPI.getDetail(row.id)
    const text = JSON.stringify(detail, null, 2)
    await navigator.clipboard.writeText(text)
    ElMessage.success("已复制到剪贴板")
  } catch (e: any) {
    // 降级：复制基础字段
    const text = JSON.stringify(row, null, 2)
    try {
      await navigator.clipboard.writeText(text)
      ElMessage.success("已复制（仅基础信息）")
    } catch {
      ElMessage.error("复制失败，请手动复制")
    }
  }
}

// ── 导出 ──
async function handleExport(format: "json" | "txt") {
  try {
    await LlmLogAPI.export({
      format,
      session_id: queryParams.session_id,
      trace_id: queryParams.trace_id || undefined,
      action: queryParams.action || undefined,
      status: queryParams.status || undefined,
      module: queryParams.module || undefined,
    })
    ElMessage.success(`导出 ${format.toUpperCase()} 成功`)
  } catch (e: any) {
    ElMessage.error(e?.message || "导出失败")
  }
}

// ── 初始化 ──
onMounted(async () => {
  await loadSessions()
  loadData()
})
</script>

<style scoped>
.llm-log-page {
  padding: 4px;
}
</style>
