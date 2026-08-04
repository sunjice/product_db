<template>
  <div class="aitc-sample-page">
    <el-card>
      <div class="flex gap-2 items-center mb-4 flex-wrap">
        <el-select v-model="queryParams.projectId" placeholder="项目" clearable style="width: 180px" @change="loadData">
          <el-option v-for="p in projectOptions" :key="p.value" :label="p.label" :value="String(p.value)" />
        </el-select>
        <el-select v-model="queryParams.sampleType" placeholder="类型" clearable style="width: 140px" @change="loadData">
          <el-option label="用例样本" value="case" />
          <el-option label="脚本样本" value="script" />
        </el-select>
        <el-input v-model="queryParams.keywords" placeholder="搜索样本名" style="width: 200px" clearable @keyup.enter="loadData" />
        <el-button type="primary" @click="loadData">搜索</el-button>
        <el-button type="primary" v-hasPerm="'aitc:sample:create'" @click="openCreate">新增样本</el-button>
      </div>

      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="project_name" label="所属项目" width="140">
          <template #default="{ row }">
            <el-tag v-if="row.project_name" size="small">{{ row.project_name }}</el-tag>
            <el-tag v-else type="info" size="small">通用</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sample_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.sample_type === 'case' ? 'success' : 'warning'" size="small">
              {{ row.sample_type === 'case' ? '用例样本' : '脚本样本' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="language" label="语言" width="80">
          <template #default="{ row }">{{ row.language || '—' }}</template>
        </el-table-column>
        <el-table-column prop="framework" label="框架" width="80" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'" size="small">{{ row.status ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" v-hasPerm="'aitc:sample:update'" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" size="small" v-hasPerm="'aitc:sample:delete'" @click="handleDelete(row)">删除</el-button>
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
    <el-dialog v-model="showDialog" :title="isEdit ? '编辑样本' : '新增样本'" width="700px" @closed="resetForm">
      <el-form :model="form" label-width="80px">
        <el-form-item label="所属项目">
          <el-select v-model="form.project_id" placeholder="不选则为通用样本" clearable style="width: 100%">
            <el-option v-for="p in projectOptions" :key="p.value" :label="p.label" :value="String(p.value)" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="form.sample_type" style="width: 100%">
            <el-option label="用例样本" value="case" />
            <el-option label="脚本样本" value="script" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如：pytest标准脚本样本" />
        </el-form-item>
        <el-form-item label="语言" v-if="form.sample_type === 'script'">
          <el-input v-model="form.language" placeholder="如 python" />
        </el-form-item>
        <el-form-item label="框架" v-if="form.sample_type === 'script'">
          <el-input v-model="form.framework" placeholder="如 pytest" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" placeholder="简要描述样本用途" />
        </el-form-item>
        <el-form-item label="样本内容" required>
          <el-input v-model="form.content" type="textarea" :rows="14" placeholder="样本内容..." />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
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
import { ProjectAPI, SampleAPI } from "@/api/aitc/index";
import type { OptionItem, PageResult } from "@/api/common";
import type { SampleItem, SampleForm, SampleQueryParams } from "@/api/aitc/types";

const projectOptions = ref<OptionItem[]>([]);
const tableData = ref<SampleItem[]>([]);
const loading = ref(false);
const total = ref(0);
const queryParams = reactive<SampleQueryParams>({ pageNum: 1, pageSize: 10 });

async function loadData() {
  loading.value = true;
  try {
    const res = await SampleAPI.getPage(queryParams);
    const page = res as PageResult<SampleItem>;
    tableData.value = page?.list || (res as any)?.records || [];
    total.value = page?.total || (res as any)?.total || 0;
  } finally { loading.value = false; }
}

// ── CRUD ──
const showDialog = ref(false);
const isEdit = ref(false);
const submitting = ref(false);
const editingId = ref("");
const form = reactive<SampleForm>({
  project_id: undefined, sample_type: "", name: "",
  language: undefined, framework: undefined,
  content: "", description: "", status: 1,
});

function openCreate() {
  isEdit.value = false;
  editingId.value = "";
  resetForm();
  showDialog.value = true;
}

function openEdit(row: SampleItem) {
  isEdit.value = true;
  editingId.value = String(row.id);
  Object.assign(form, {
    project_id: row.project_id || undefined,
    sample_type: row.sample_type,
    name: row.name,
    language: row.language,
    framework: row.framework,
    content: row.content,
    description: row.description,
    status: row.status,
  });
  showDialog.value = true;
}

function resetForm() {
  form.project_id = undefined;
  form.sample_type = "";
  form.name = "";
  form.language = undefined;
  form.framework = undefined;
  form.content = "";
  form.description = "";
  form.status = 1;
}

async function submit() {
  submitting.value = true;
  try {
    if (isEdit.value) {
      await SampleAPI.update(editingId.value, { ...form });
      ElMessage.success("更新成功");
    } else {
      await SampleAPI.create({ ...form });
      ElMessage.success("创建成功");
    }
    showDialog.value = false;
    loadData();
  } finally { submitting.value = false; }
}

async function handleDelete(row: SampleItem) {
  try {
    await ElMessageBox.confirm("确定删除此样本？", "删除确认");
    await SampleAPI.delete(String(row.id));
    ElMessage.success("删除成功");
    loadData();
  } catch { /* cancelled */ }
}

onMounted(async () => {
  const res = await ProjectAPI.getOptions();
  projectOptions.value = res || [];
  loadData();
});
</script>
