<template>
  <div class="aitc-case-page">
    <!-- 顶部操作栏 -->
    <el-card body-style="padding: 4px 8px">
      <div class="flex gap-1 items-center flex-wrap">
        <el-select v-model="selectedProjectId" placeholder="请选择项目" size="small" style="width: 200px" @change="onProjectChange">
          <el-option v-for="p in projectOptions" :key="p.value" :label="p.label" :value="String(p.value)" />
        </el-select>
        <el-divider direction="vertical" />
        <!-- <el-button type="default" size="small" v-hasPerm="'aitc:case:import'" @click="downloadTemplate">下载模板</el-button>
        <el-upload :show-file-list="false" :before-upload="handleImport" accept=".xlsx,.xls" v-hasPerm="'aitc:case:import'">
          <el-button type="primary" size="small" :disabled="!selectedProjectId">导入Excel</el-button>
        </el-upload> -->
      </div>
    </el-card>

    <!-- 主体：左树右表 -->
    <div class="flex gap-2 mt-2" style="height: calc(100vh - 130px)">
      <!-- 左侧套件树 -->
      <aside
        class="page-aside"
        :class="{ 'is-collapsed': sidebarCollapsed, 'is-resizing': isResizing }"
        :style="{ '--page-aside-width': sidebarWidth + 'px' }"
      >
        <SuiteTree ref="treeCmp" :project-id="selectedProjectId" @node-click="onTreeClick" />
        <button class="page-aside__toggle" @click="sidebarCollapsed = !sidebarCollapsed">
          <el-icon :size="14">
            <ArrowLeft v-if="!sidebarCollapsed" />
            <ArrowRight v-else />
          </el-icon>
        </button>
        <!-- 拖拽手柄 -->
        <div
          class="sidebar-resize-handle"
          @mousedown="startResize"
        />
      </aside>

      <!-- 右侧内容 -->
      <el-card class="flex-1 case-content" style="overflow: hidden" body-style="padding: 6px 8px">
        <!-- 详情 / 编辑视图 -->
        <template v-if="viewMode === 'detail' && viewingCase">
          <CaseEditForm
            v-if="isEditing"
            :viewing-case="viewingCase"
            :edit-form="editForm"
            :edit-submitting="editSubmitting"
            @submit-edit="() => submitEdit(treeCmp)"
            @cancel-edit="cancelEdit"
            @add-step="addStep"
            @remove-step="removeStep"
          />
          <CaseDetail
            v-else
            :viewing-case="viewingCase"
            @back="backToTable"
            @start-edit="startEdit"
          />
        </template>

        <!-- 表格视图 -->
        <template v-else>
          <CaseTable
            :table-data="tableData"
            :loading="loading"
            :total="total"
            :query-params="queryParams"
            @load-cases="loadCases"
            @sort-change="onSortChange"
            @selection-change="handleSelectionChange"
            @show-detail="showDetail"
            @open-edit="openEdit"
            @toggle-core="toggleCore"
            @toggle-sample="toggleSample"
            @handle-reset="handleReset"
          />
        </template>
      </el-card>
    </div>

    <!-- 导入结果弹窗 -->
    <CaseImportDialog v-model="showImportResult" :import-result="importResult" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { ArrowLeft, ArrowRight } from "@element-plus/icons-vue";
import { useCasePage } from "./composables/useCasePage";

const {
  selectedProjectId, sidebarCollapsed, projectOptions, loadProjectOptions,
  onProjectChange, onTreeClick, backToTable,
  tableData, loading, total, queryParams,
  handleSelectionChange, onSortChange, loadCases, handleReset,
  toggleCore, toggleSample,
  viewMode, viewingCase, showDetail,
  isEditing, editSubmitting, editForm,
  openEdit, startEdit, cancelEdit, addStep, removeStep, submitEdit,
  showImportResult, importResult, downloadTemplate, handleImport,
  initAiContext, mountAiContext, unmountAiContext,
} = useCasePage();

// 树组件引用（传给 submitEdit 用于更新树节点）
const treeCmp = ref<any>(null);

/** ── 侧边栏拖拽调整宽度 ── */
const sidebarWidth = ref(260);
const SIDEBAR_MIN = 200;
const SIDEBAR_MAX = 500;
const isResizing = ref(false);
let startX = 0;
let startWidth = 0;

function startResize(e: MouseEvent) {
  isResizing.value = true;
  startX = e.clientX;
  startWidth = sidebarWidth.value;
  document.addEventListener("mousemove", onResize);
  document.addEventListener("mouseup", stopResize);
  document.body.style.cursor = "col-resize";
  document.body.style.userSelect = "none";
  e.preventDefault();
}

function onResize(e: MouseEvent) {
  if (!isResizing.value) return;
  const delta = e.clientX - startX;
  const w = Math.max(SIDEBAR_MIN, Math.min(SIDEBAR_MAX, startWidth + delta));
  sidebarWidth.value = w;
}

function stopResize() {
  isResizing.value = false;
  document.removeEventListener("mousemove", onResize);
  document.removeEventListener("mouseup", stopResize);
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
}

// 初始化
initAiContext();
onMounted(() => {
  mountAiContext();
  loadProjectOptions();
});
onUnmounted(() => unmountAiContext());
</script>

<style scoped>
.aitc-case-page {
  padding: 4px;
  font-family: Inter, sans-serif;
  font-size: 11px;
}

/* ── 侧边栏拖拽手柄 ── */
.sidebar-resize-handle {
  position: absolute;
  top: 0;
  right: -4px;
  bottom: 0;
  width: 8px;
  cursor: col-resize;
  z-index: 10;
}
.sidebar-resize-handle:hover {
  border-right: 1px solid #333;
}
/* 拖拽时关闭 page.scss 里 0.2s 的过渡动画，让侧边紧跟鼠标 */
.page-aside.is-resizing {
  transition: none !important;
}

/* 右侧内容区字体 */
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

/* 表格压缩 */
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

/* 编辑模式 input/select */
.case-content :deep(.el-descriptions__cell .el-input__wrapper) {
  padding: 0 6px;
  border-radius: 3px;
  box-shadow: none;
}
.case-content :deep(.el-descriptions__cell .el-input__inner) {
  font-size: 12px;
  padding: 0;
  height: 24px;
  line-height: 24px;
}
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

/* textarea */
.case-content :deep(.el-descriptions__cell .el-textarea__inner) {
  font-size: 12px;
  padding: 0 6px;
  min-height: 22px;
  line-height: 1.5;
  border-radius: 3px;
}

/* 步骤编辑表格 */
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
