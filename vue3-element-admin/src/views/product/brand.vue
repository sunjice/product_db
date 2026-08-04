<template>
  <div class="product-brand-page">
    <el-card>
      <el-form :inline="true" :model="queryParams" @submit.prevent="handleSearch">
        <el-form-item label="关键词">
          <el-input v-model="queryParams.keywords" placeholder="品牌名称" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="mt-4">
      <div class="mb-4">
        <el-button type="primary" v-hasPerm="'brand:create'" @click="openDialog()">新增品牌</el-button>
      </div>
      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="品牌名称" />
        <el-table-column prop="logo_url" label="Logo" width="120">
          <template #default="{ row }">
            <el-image v-if="row.logo_url" :src="row.logo_url" style="width: 48px; height: 48px" fit="contain" />
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column prop="create_time" label="创建时间" width="180" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" v-hasPerm="'brand:update'" @click="openDialog(row)">编辑</el-button>
            <el-button text type="danger" v-hasPerm="'brand:delete'" @click="handleDelete(row)">删除</el-button>
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
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑品牌' : '新增品牌'" width="500px" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="64" />
        </el-form-item>
        <el-form-item label="Logo URL">
          <el-input v-model="form.logo_url" placeholder="Logo图片地址" />
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
import { BrandAPI } from "@/api/product/index";
import type { BrandItem, BrandForm } from "@/api/product/types";

const loading = ref(false);
const submitLoading = ref(false);
const dialogVisible = ref(false);
const isEdit = ref(false);
const formRef = ref<FormInstance>();
const tableData = ref<BrandItem[]>([]);
const total = ref(0);

const queryParams = reactive({ pageNum: 1, pageSize: 10, keywords: "" });

const form = reactive<BrandForm>({ id: "", name: "", logo_url: "", sort_order: 0 });
const editId = ref("");

const rules = {
  name: [{ required: true, message: "请输入品牌名称", trigger: "blur" }],
};

async function fetchData() {
  loading.value = true;
  try {
    const res = await BrandAPI.getPage(queryParams);
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

function openDialog(row?: BrandItem) {
  if (row) {
    isEdit.value = true;
    editId.value = row.id;
    form.id = row.id;
    form.name = row.name;
    form.logo_url = row.logo_url ?? "";
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
      await BrandAPI.update(editId.value, form);
      ElMessage.success("更新成功");
    } else {
      await BrandAPI.create(form);
      ElMessage.success("创建成功");
    }
    dialogVisible.value = false;
    fetchData();
  } finally {
    submitLoading.value = false;
  }
}

async function handleDelete(row: BrandItem) {
  await ElMessageBox.confirm(`确认删除品牌「${row.name}」？`, "提示", { type: "warning" });
  await BrandAPI.delete(row.id);
  ElMessage.success("删除成功");
  fetchData();
}

function resetForm() {
  form.id = "";
  form.name = "";
  form.logo_url = "";
  form.sort_order = 0;
  formRef.value?.resetFields();
}

onMounted(() => fetchData());
</script>
