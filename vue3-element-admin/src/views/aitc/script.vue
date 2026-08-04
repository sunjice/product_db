<template>
  <div class="aitc-script-page">
    <el-card>
      <!-- 筛选区 -->
      <div class="flex gap-2 items-center mb-4 flex-wrap">
        <el-select v-model="queryParams.projectId" placeholder="项目" clearable style="width: 160px" @change="loadData">
          <el-option v-for="p in projectOptions" :key="p.value" :label="p.label" :value="String(p.value)" />
        </el-select>
        <el-select v-model="queryParams.status" placeholder="状态" clearable style="width: 120px" @change="loadData">
          <el-option label="草稿" :value="1" />
          <el-option label="已入库" :value="2" />
        </el-select>
        <el-select v-model="queryParams.source" placeholder="来源" clearable style="width: 120px" @change="loadData">
          <el-option label="AI生成" :value="1" />
          <el-option label="人工编写" :value="2" />
        </el-select>
        <el-button type="primary" @click="loadData">查询</el-button>
        <el-button v-if="selectedIds.length" type="danger" plain @click="handleBatchDelete" v-hasPerm="'aitc:script:update'">
          批量删除 ({{ selectedIds.length }})
        </el-button>
      </div>

      <!-- 脚本列表 -->
      <el-table
        :data="tableData" v-loading="loading" border stripe size="small"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="case_name" label="关联用例" min-width="200" show-overflow-tooltip />
        <el-table-column label="语言/框架" width="140" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.language || 'python' }}</el-tag>
            <span class="mx-1">/</span>
            <el-tag type="warning" size="small">{{ row.framework || 'pytest' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.source === 1 ? 'primary' : ''" size="small">
              {{ row.source === 1 ? 'AI' : '人工' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 2 ? 'success' : 'info'" size="small">
              {{ row.status === 2 ? '已入库' : '草稿' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="70" align="center">
          <template #default="{ row }">v{{ row.version }}</template>
        </el-table-column>
        <el-table-column prop="update_time" label="更新时间" width="160" />
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="showEditor(row)">查看/编辑</el-button>
            <el-button
              v-if="row.status === 1" text type="success" size="small"
              v-hasPerm="'aitc:script:update'" @click="handlePublish(row)"
            >
              入库
            </el-button>
            <el-button text type="warning" size="small" @click="handleExport(row)">导出</el-button>
            <el-button text type="danger" size="small" v-hasPerm="'aitc:script:update'" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && tableData.length === 0" description="暂无脚本" />
      <div class="flex justify-end mt-4">
        <el-pagination
          v-model:current-page="queryParams.pageNum" v-model:page-size="queryParams.pageSize"
          :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" :total="total"
          @size-change="loadData" @current-change="loadData"
        />
      </div>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="showEditorDialog" :title="`编辑脚本 — ${editingItem?.case_name || ''}`" width="80%" top="3vh">
      <el-tag size="small" type="primary" class="mb-2">{{ editingItem?.language || 'python' }} / {{ editingItem?.framework || 'pytest' }}</el-tag>
      <el-input
        v-model="editingContent"
        type="textarea"
        :rows="20"
        placeholder="脚本内容"
        style="font-family: 'Courier New', Consolas, monospace; font-size: 13px;"
      />
      <template #footer>
        <el-button @click="showEditorDialog = false">取消</el-button>
        <el-button type="primary" @click="submitEdit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { ProjectAPI, ScriptAPI } from "@/api/aitc/index";
import type { OptionItem, PageResult } from "@/api/common";
import type { ScriptItem, ScriptQueryParams } from "@/api/aitc/types";

// ── 项目选项 ──
const projectOptions = ref<OptionItem[]>([]);

// ── 脚本列表 ──
const tableData = ref<ScriptItem[]>([]);
const loading = ref(false);
const total = ref(0);
const selectedIds = ref<string[]>([]);
const queryParams = reactive<ScriptQueryParams>({ pageNum: 1, pageSize: 20 });

function onSelectionChange(rows: ScriptItem[]) {
  selectedIds.value = rows.map(r => String(r.id));
}

async function loadData() {
  loading.value = true;
  try {
    const res = await ScriptAPI.getPage(queryParams);
    const page = res as PageResult<ScriptItem>;
    tableData.value = page?.list || (res as any)?.records || [];
    total.value = page?.total || (res as any)?.total || 0;
  } finally { loading.value = false; }
}

// ── 编辑 ──
const showEditorDialog = ref(false);
const editingItem = ref<ScriptItem | null>(null);
const editingContent = ref("");
const submitting = ref(false);

function showEditor(row: ScriptItem) {
  editingItem.value = row;
  editingContent.value = row.content;
  showEditorDialog.value = true;
}

async function submitEdit() {
  if (!editingItem.value) return;
  submitting.value = true;
  try {
    await ScriptAPI.update(String(editingItem.value.id), {
      content: editingContent.value,
      version: editingItem.value.version,
    });
    ElMessage.success("保存成功");
    showEditorDialog.value = false;
    loadData();
  } finally { submitting.value = false; }
}

// ── 入库 ──
async function handlePublish(row: ScriptItem) {
  try {
    await ElMessageBox.confirm("确定将此脚本入库为正式版本？", "确认入库");
    await ScriptAPI.publish(String(row.id));
    ElMessage.success("已入库");
    loadData();
  } catch { /* cancelled */ }
}

// ── 导出 ──
function handleExport(row: ScriptItem) {
  const ext = row.language === "python" ? "py" : row.language === "javascript" ? "js" : "txt";
  const filename = `${row.case_name.replace(/[\\\\/:*?"<>|]/g, "_")}.${ext}`;
  const blob = new Blob([row.content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  ElMessage.success("导出成功");
}

// ── 删除 ──
async function handleDelete(row: ScriptItem) {
  try {
    await ElMessageBox.confirm("确定删除此脚本？", "删除确认");
    await ScriptAPI.delete(String(row.id));
    ElMessage.success("删除成功");
    loadData();
  } catch { /* cancelled */ }
}

async function handleBatchDelete() {
  if (!selectedIds.value.length) return;
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 个脚本？`, "批量删除确认");
    await ScriptAPI.delete(selectedIds.value.join(","));
    ElMessage.success("删除成功");
    loadData();
  } catch { /* cancelled */ }
}

// ── 初始化 ──
onMounted(async () => {
  const res = await ProjectAPI.getOptions();
  projectOptions.value = res || [];
  loadData();
});
</script>

<style scoped>
.aitc-script-page {
  padding: 4px;
}
</style>
