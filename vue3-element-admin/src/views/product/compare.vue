<template>
  <div class="product-compare-page">
    <div class="mb-4 flex items-center justify-between">
      <div class="flex items-center gap-4">
        <el-button @click="goBack">返回列表</el-button>
        <h2 class="text-xl font-bold">产品对比</h2>
      </div>
      <div v-if="data?.products?.length" class="flex items-center gap-3">
        <span v-if="!showAll" class="text-gray-400 text-sm">相同项已自动隐藏</span>
        <el-button type="warning" :icon="showAll ? 'Hide' : 'View'" @click="showAll = !showAll">
          {{ showAll ? '隐藏相同项' : '显示全部规格' }}
        </el-button>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-20">
      <el-icon class="is-loading" :size="40"><Loading /></el-icon>
    </div>

    <template v-if="!loading && data">
      <!-- 基本信息对比 — 与规格表格结构完全一致 -->
      <el-card class="mb-4">
        <template #header>
          <span class="font-semibold">基本信息</span>
        </template>
        <el-table
          :data="basicInfoRows"
          border
          stripe
          size="small"
          :row-class-name="rowClassName"
          style="width: 100%"
        >
          <el-table-column prop="spec_name" label="规格名称" width="160" fixed="left" />
          <el-table-column
            v-for="(p, idx) in data.products"
            :key="p.id"
            :label="p.name"
            min-width="180"
          >
            <template #default="{ row }">
              <span :class="{ 'font-semibold text-warning': isRowDiff(row) }">
                {{ row[`product_${idx}`] || '—' }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 规格对比 -->
      <el-card v-for="groupName in data.common_groups" :key="groupName" class="mb-4">
        <template #header>
          <span class="font-semibold">{{ groupName }}</span>
          <span class="text-gray-400 text-sm ml-2">
            {{ getDisplaySpecs(groupName).length }} / {{ getMergedSpecs(groupName).length }} 项
          </span>
        </template>
        <div v-if="getMergedSpecs(groupName).length === 0" class="text-gray-400 text-center py-4">该分组无规格数据</div>
        <div v-else-if="getDisplaySpecs(groupName).length === 0" class="text-gray-400 text-center py-4">
          该分组下所有规格项均相同，已自动隐藏
        </div>
        <el-table
          v-else
          :data="getDisplaySpecs(groupName)"
          border
          stripe
          size="small"
          :row-class-name="rowClassName"
          style="width: 100%"
        >
          <el-table-column prop="spec_name" label="规格名称" width="160" fixed="left" />
          <el-table-column
            v-for="(p, idx) in data.products"
            :key="p.id"
            :label="p.name"
            min-width="180"
          >
            <template #default="{ row }">
              <span :class="{ 'font-semibold text-warning': isRowDiff(row) }">
                {{ row[`product_${idx}`] || '—' }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ProductAPI } from "@/api/product/index";
import type { ProductCompareVO } from "@/api/product/types";

const route = useRoute();
const router = useRouter();
const loading = ref(true);
const data = ref<ProductCompareVO | null>(null);
const showAll = ref(false);

/** 基本信息表数据：名称、品牌、型号各一行 */
const basicInfoRows = computed<SpecRow[]>(() => {
  if (!data.value) return [];
  const rows: SpecRow[] = [
    { spec_name: "名称" },
    { spec_name: "品牌" },
    { spec_name: "型号" },
  ];
  data.value.products.forEach((p, idx) => {
    rows[0][`product_${idx}`] = p.name || "—";
    rows[1][`product_${idx}`] = p.brand_name || "—";
    rows[2][`product_${idx}`] = p.model || "—";
  });
  return rows;
});

function goBack() {
  router.push("/product/list");
}

interface SpecRow {
  spec_name: string;
  [key: string]: string;
}

/** 判断某行是否所有产品的值都相同 */
function isRowAllSame(row: SpecRow): boolean {
  if (!data.value || data.value.products.length < 2) return true;
  const values = data.value.products.map((_, idx) => row[`product_${idx}`] || "");
  return new Set(values).size <= 1;
}

/** 判断某行是否存在差异 */
function isRowDiff(row: SpecRow): boolean {
  return !isRowAllSame(row);
}

function getMergedSpecs(groupName: string): SpecRow[] {
  if (!data.value) return [];
  const specMap = new Map<string, SpecRow>();

  data.value.products.forEach((p, idx) => {
    const group = p.groups.find(g => g.group_name === groupName);
    if (group) {
      group.items.forEach(item => {
        if (!specMap.has(item.spec_name)) {
          specMap.set(item.spec_name, { spec_name: item.spec_name });
        }
        const row = specMap.get(item.spec_name)!;
        const displayValue = [item.spec_value, item.spec_unit].filter(Boolean).join(" ");
        row[`product_${idx}`] = displayValue;
      });
    }
  });

  return Array.from(specMap.values());
}

/** 根据 showAll 状态过滤：默认隐藏所有值相同的行 */
function getDisplaySpecs(groupName: string): SpecRow[] {
  const all = getMergedSpecs(groupName);
  if (showAll.value) return all;
  return all.filter(row => isRowDiff(row));
}

/** 给差异行加背景色（仅在显示全部时生效） */
function rowClassName({ row }: { row: SpecRow }) {
  if (showAll.value && isRowDiff(row)) {
    return "compare-diff-row";
  }
  return "";
}

onMounted(async () => {
  try {
    const ids = route.query.ids as string;
    if (!ids) {
      router.replace("/product");
      return;
    }
    const res = await ProductAPI.compare(ids);
    data.value = res ?? null;
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.compare-diff-row {
  background-color: #fff7e6 !important;
}

.compare-diff-row td {
  background-color: #fff7e6 !important;
}
</style>
