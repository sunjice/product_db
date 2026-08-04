<template>
  <div class="product-list-page">
    <!-- 搜索区 -->
    <el-card>
      <el-form :inline="true" :model="queryParams" @submit.prevent="handleSearch">
        <el-form-item label="分类">
          <el-select v-model="queryParams.categoryId" placeholder="全部" clearable style="width: 150px">
            <el-option v-for="c in categoryOptions" :key="c.value" :label="c.label" :value="String(c.value)" />
          </el-select>
        </el-form-item>
        <el-form-item label="品牌">
          <el-select v-model="queryParams.brandId" placeholder="全部" clearable style="width: 150px">
            <el-option v-for="b in brandOptions" :key="b.value" :label="b.label" :value="String(b.value)" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="queryParams.keywords" placeholder="名称/型号" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格区 -->
    <el-card class="mt-4">
      <div class="mb-4 flex gap-2 items-center">
        <el-button type="primary" v-hasPerm="'product:create'" @click="openCreateDialog">新增产品</el-button>
        <el-button
          type="warning"
          :disabled="compareList.length < 2"
          @click="goComparePage"
        >
          产品对比{{ compareList.length > 0 ? ` (${compareList.length})` : '' }}
        </el-button>
        <span v-if="compareList.length > 0" class="text-gray-500 text-sm">
          已选 {{ compareList.length }} 个产品
          <el-button text type="danger" size="small" @click="clearCompare">清空</el-button>
        </span>
      </div>
      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="model" label="型号" width="120" />
        <el-table-column prop="brand_name" label="品牌" width="100" />
        <el-table-column prop="category_name" label="分类" width="100" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '上架' : '下架' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="170" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" v-hasPerm="'product:list'" @click="goDetail(row.id)">详情</el-button>
            <el-button text type="primary" v-hasPerm="'product:update'" @click="openEditDialog(row)">编辑</el-button>
            <el-button text type="danger" v-hasPerm="'product:delete'" @click="handleDelete(row)">删除</el-button>
            <el-button
              v-if="!isInCompare(row.id)"
              text
              type="warning"
              @click="toggleCompare(row)"
            >
              加入对比
            </el-button>
            <el-button
              v-else
              text
              type="info"
              @click="toggleCompare(row)"
            >
              取消对比
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && tableData.length === 0" description="暂无产品数据" />
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
    <ProductFormDialog :visible="formDialogVisible" :product-id="editProductId" @close="formDialogVisible = false" @saved="fetchData" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { ProductAPI, CategoryAPI, BrandAPI } from "@/api/product/index";
import type { ProductVO } from "@/api/product/types";
import type { OptionItem } from "@/api/common";
import ProductFormDialog from "./components/ProductFormDialog.vue";

const router = useRouter();
const loading = ref(false);
const tableData = ref<ProductVO[]>([]);
const total = ref(0);
const categoryOptions = ref<OptionItem[]>([]);
const brandOptions = ref<OptionItem[]>([]);

const queryParams = reactive({
  pageNum: 1, pageSize: 10,
  categoryId: undefined as string | undefined,
  brandId: undefined as string | undefined,
  keywords: "",
});

// 表单弹窗
const formDialogVisible = ref(false);
const editProductId = ref("");

function openCreateDialog() {
  editProductId.value = "";
  formDialogVisible.value = true;
}

function openEditDialog(row: ProductVO) {
  editProductId.value = row.id;
  formDialogVisible.value = true;
}

// 对比
const compareList = ref<ProductVO[]>([]);

function isInCompare(productId: string) {
  return compareList.value.some(p => p.id === productId);
}

function toggleCompare(row: ProductVO) {
  const idx = compareList.value.findIndex(p => p.id === row.id);
  if (idx > -1) {
    // 已加入 → 移除
    compareList.value.splice(idx, 1);
    return;
  }
  // 未加入 → 先校验
  if (compareList.value.length >= 4) {
    ElMessage.warning("最多选择4个产品进行对比");
    return;
  }
  if (compareList.value.length >= 1 && row.category_id !== compareList.value[0].category_id) {
    ElMessage.warning("只能对比同一分类下的产品");
    return;
  }
  compareList.value.push(row);
}

function clearCompare() {
  compareList.value = [];
}

function goComparePage() {
  if (compareList.value.length < 2) return;
  const ids = compareList.value.map(p => p.id).join(",");
  router.push({ path: "/product/compare", query: { ids } });
}

async function fetchData() {
  loading.value = true;
  try {
    const params: any = { pageNum: queryParams.pageNum, pageSize: queryParams.pageSize };
    if (queryParams.categoryId) params.categoryId = queryParams.categoryId;
    if (queryParams.brandId) params.brandId = queryParams.brandId;
    if (queryParams.keywords) params.keywords = queryParams.keywords;
    const res = await ProductAPI.getPage(params);
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
  queryParams.categoryId = undefined;
  queryParams.brandId = undefined;
  queryParams.keywords = "";
  handleSearch();
}

function goDetail(id: string) {
  router.push(`/product/detail/${id}`);
}

async function handleDelete(row: ProductVO) {
  await ElMessageBox.confirm(`确认删除产品「${row.name}」？`, "提示", { type: "warning" });
  await ProductAPI.delete(row.id);
  ElMessage.success("删除成功");
  fetchData();
}

onMounted(async () => {
  const [cats, brands] = await Promise.all([
    CategoryAPI.getOptions(),
    BrandAPI.getOptions(),
  ]);
  categoryOptions.value = cats ?? [];
  brandOptions.value = brands ?? [];
  fetchData();
});
</script>
