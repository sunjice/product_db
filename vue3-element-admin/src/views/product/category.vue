<template>
  <div class="product-category-page">
    <el-card>
      <el-form :inline="true" :model="queryParams" @submit.prevent="handleSearch">
        <el-form-item label="关键词">
          <el-input v-model="queryParams.keywords" placeholder="分类名称" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="mt-4">
      <div class="mb-4">
        <el-button type="primary" v-hasPerm="'category:create'" @click="openDialog()">新增分类</el-button>
      </div>
      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="分类名称" />
        <el-table-column prop="slug" label="标识" />
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column prop="create_time" label="创建时间" width="180" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" v-hasPerm="'category:update'" @click="openDialog(row)">编辑</el-button>
            <el-button text type="danger" v-hasPerm="'category:delete'" @click="handleDelete(row)">删除</el-button>
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
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑分类' : '新增分类'" width="500px" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="64" />
        </el-form-item>
        <el-form-item label="标识" prop="slug">
          <el-input v-model="form.slug" maxlength="64" />
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
import { CategoryAPI } from "@/api/product/index";
import type { CategoryItem, CategoryForm } from "@/api/product/types";

const loading = ref(false);
const submitLoading = ref(false);
const dialogVisible = ref(false);
const isEdit = ref(false);
const formRef = ref<FormInstance>();
const tableData = ref<CategoryItem[]>([]);
const total = ref(0);

const queryParams = reactive({ pageNum: 1, pageSize: 10, keywords: "" });

const form = reactive<CategoryForm>({ id: "", name: "", slug: "", sort_order: 0 });
const editId = ref("");

const rules = {
  name: [{ required: true, message: "请输入分类名称", trigger: "blur" }],
  slug: [{ required: true, message: "请输入分类标识", trigger: "blur" }],
};

async function fetchData() {
  loading.value = true;
  try {
    const res = await CategoryAPI.getPage(queryParams);
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
  queryParams.keywords = "";
  handleSearch();
}

function openDialog(row?: CategoryItem) {
  if (row) {
    isEdit.value = true;
    editId.value = row.id;
    form.id = row.id;
    form.name = row.name;
    form.slug = row.slug;
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
      await CategoryAPI.update(editId.value, form);
      ElMessage.success("更新成功");
    } else {
      await CategoryAPI.create(form);
      ElMessage.success("创建成功");
    }
    dialogVisible.value = false;
    fetchData();
  } finally {
    submitLoading.value = false;
  }
}

async function handleDelete(row: CategoryItem) {
  await ElMessageBox.confirm(`确认删除分类「${row.name}」？`, "提示", { type: "warning" });
  await CategoryAPI.delete(row.id);
  ElMessage.success("删除成功");
  fetchData();
}

function resetForm() {
  form.id = "";
  form.name = "";
  form.slug = "";
  form.sort_order = 0;
  formRef.value?.resetFields();
}

onMounted(() => fetchData());
</script>
