<template>
  <div class="product-detail-page">
    <div class="mb-4 flex items-center gap-4">
      <el-button @click="goBack">返回列表</el-button>
      <h2 class="text-xl font-bold">{{ product.name }}</h2>
    </div>

    <!-- 基本信息 -->
    <el-card class="mb-4">
      <template #header><span class="font-semibold">基本信息</span></template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="名称">{{ product.name }}</el-descriptions-item>
        <el-descriptions-item label="型号">{{ product.model || '—' }}</el-descriptions-item>
        <el-descriptions-item label="品牌">{{ product.brand_name || '—' }}</el-descriptions-item>
        <el-descriptions-item label="分类">{{ product.category_name || '—' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="product.status === 1 ? 'success' : 'info'">{{ product.status === 1 ? '上架' : '下架' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ product.create_time || '—' }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ product.update_time || '—' }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="3">{{ product.description || '—' }}</el-descriptions-item>
        <el-descriptions-item label="图片" :span="3">
          <div class="flex gap-2 flex-wrap">
            <el-image
              v-for="(url, idx) in product.image_urls"
              :key="idx"
              :src="url"
              :preview-src-list="product.image_urls"
              style="width: 120px; height: 100px"
              fit="cover"
              class="rounded border"
            />
            <span v-if="!product.image_urls.length" class="text-gray-400">暂无图片</span>
          </div>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 规格参数 -->
    <div v-for="group in product.groups" :key="group.group_name" class="mb-4">
      <el-card>
        <template #header><span class="font-semibold">{{ group.group_name }}</span></template>
        <el-table :data="group.items" border stripe size="small">
          <el-table-column prop="spec_name" label="规格名称" width="180" />
          <el-table-column prop="spec_value" label="规格值">
            <template #default="{ row }">{{ row.spec_value || '—' }}</template>
          </el-table-column>
          <el-table-column prop="spec_unit" label="单位" width="100">
            <template #default="{ row }">{{ row.spec_unit || '—' }}</template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <el-empty v-if="loading" description="加载中..." />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ProductAPI } from "@/api/product/index";
import type { ProductVO } from "@/api/product/types";

const route = useRoute();
const router = useRouter();
const loading = ref(true);
const product = ref<ProductVO>({
  id: "", category_id: "", brand_id: "", name: "",
  image_urls: [], groups: [], status: 1, sort_order: 0,
});

function goBack() {
  router.back();
}

onMounted(async () => {
  try {
    const id = route.params.id as string;
    const res = await ProductAPI.getById(id);
    product.value = res ?? product.value;
  } finally {
    loading.value = false;
  }
});
</script>
