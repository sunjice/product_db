<template>
  <div class="product-specgroup-page">
    <el-card>
      <el-form :inline="true" :model="queryParams" @submit.prevent="handleSearch">
        <el-form-item label="所属分类">
          <el-select v-model="queryParams.category_id" placeholder="全部" clearable style="width: 160px">
            <el-option v-for="c in categoryOptions" :key="c.value" :label="c.label" :value="String(c.value)" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="queryParams.keywords" placeholder="分组名称" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="mt-4">
      <div class="mb-4">
        <el-button type="primary" v-hasPerm="'specgroup:create'" @click="openDialog()">新增分组</el-button>
      </div>
      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="分组名称" />
        <el-table-column prop="category_name" label="所属分类" />
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column prop="create_time" label="创建时间" width="180" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" v-hasPerm="'specgroup:update'" @click="openDialog(row)">编辑</el-button>
            <el-button text type="danger" v-hasPerm="'specgroup:delete'" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="flex justify-end mt-4">
        <el-pagination
          v-model:current-page="queryParams.pageNum"
          v-model:page-size="queryParams.pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @change="fetchData"
        />
      </div>
    </el-card>

    <!-- 表单弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑规格分组' : '新增规格分组'" width="500px" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="所属分类" prop="category_id">
          <el-select v-model="form.category_id" placeholder="请选择分类" style="width: 100%">
            <el-option v-for="c in categoryOptions" :key="c.value" :label="c.label" :value="String(c.value)" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="64" />
        </el-form-item>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance } from "element-plus";
import { SpecGroupAPI, CategoryAPI } from "@/api/product/index";
import type { SpecGroupItem, SpecGroupForm } from "@/api/product/types";
import type { OptionItem } from "@/api/common";

const loading = ref(false);
const submitLoading = ref(false);
const dialogVisible = ref(false);
const isEdit = ref(false);
const formRef = ref<FormInstance>();
const tableData = ref<SpecGroupItem[]>([]);
const total = ref(0);
const categoryOptions = ref<OptionItem[]>([]);

const queryParams = reactive({ pageNum: 1, pageSize: 10, category_id: "" as string | undefined, keywords: "" });

const form = reactive<SpecGroupForm>({ id: "", category_id: "", name: "", sort_order: 0 });
const editId = ref("");

const rules = {
  category_id: [{ required: true, message: "请选择分类", trigger: "change" }],
  name: [{ required: true, message: "请输入分组名称", trigger: "blur" }],
};

async function fetchCategories() {
  const res = await CategoryAPI.getOptions();
  categoryOptions.value = res ?? [];
}

async function fetchData() {
  loading.value = true;
  try {
    const params: any = { pageNum: queryParams.pageNum, pageSize: queryParams.pageSize, keywords: queryParams.keywords };
    if (queryParams.category_id) params.category_id = queryParams.category_id;
    const res = await SpecGroupAPI.getPage(params);
    tableData.value = res.list ?? [];
    total.value = res.total ?? 0;
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  queryParams.pageNum = 1;
  fetchData();
}

function handleReset() {
  queryParams.category_id = undefined;
  queryParams.keywords = "";
  handleSearch();
}

function openDialog(row?: SpecGroupItem) {
  if (row) {
    isEdit.value = true;
    editId.value = row.id;
    form.id = row.id;
    form.category_id = String(row.category_id);
    form.name = row.name;
    form.sort_order = row.sort_order;
  } else {
    isEdit.value = false;
    editId.value = "";
    form.id = "";
  }
  dialogVisible.value = true;
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  submitLoading.value = true;
  try {
    if (isEdit.value) {
      await SpecGroupAPI.update(editId.value, form);
      ElMessage.success("更新成功");
    } else {
      await SpecGroupAPI.create(form);
      ElMessage.success("创建成功");
    }
    dialogVisible.value = false;
    fetchData();
  } finally {
    submitLoading.value = false;
  }
}

async function handleDelete(row: SpecGroupItem) {
  await ElMessageBox.confirm(`确认删除规格分组「${row.name}」？`, "提示", { type: "warning" });
  await SpecGroupAPI.delete(row.id);
  ElMessage.success("删除成功");
  fetchData();
}

function resetForm() {
  form.id = "";
  form.category_id = "";
  form.name = "";
  form.sort_order = 0;
  formRef.value?.resetFields();
}

onMounted(() => {
  fetchCategories();
  fetchData();
});
</script>
