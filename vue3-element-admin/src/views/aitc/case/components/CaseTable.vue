<template>
  <div>
    <div class="mb-1 flex gap-1 items-center flex-wrap">
      <el-select v-model="localQuery.isCore" placeholder="核心状态" clearable size="small" style="width: 120px" @change="$emit('loadCases')">
        <el-option label="核心用例" :value="1" />
        <el-option label="非核心" :value="0" />
      </el-select>
      <el-select v-model="localQuery.isSample" placeholder="样本状态" clearable size="small" style="width: 120px" @change="$emit('loadCases')">
        <el-option label="样本用例" :value="1" />
        <el-option label="非样本" :value="0" />
      </el-select>
      <el-select v-model="localQuery.reviewStatus" placeholder="审核状态" clearable size="small" style="width: 120px" @change="$emit('loadCases')">
        <el-option label="已审核" :value="ReviewStatusEnum.REVIEWED" />
        <el-option label="未审核" :value="ReviewStatusEnum.UNREVIEWED" />
      </el-select>
      <el-select v-model="localQuery.importance" placeholder="级别" clearable size="small" style="width: 100px" @change="$emit('loadCases')">
        <el-option label="高" :value="CaseImportanceEnum.HIGH" />
        <el-option label="中" :value="CaseImportanceEnum.MEDIUM" />
        <el-option label="低" :value="CaseImportanceEnum.LOW" />
      </el-select>
      <el-input
        v-model="localQuery.keywords" placeholder="搜索用例"
        size="small" style="width: 200px" clearable @keyup.enter="$emit('loadCases')"
      />
      <el-button type="primary" size="small" @click="$emit('loadCases')">搜索</el-button>
      <el-button size="small" @click="$emit('handleReset')">重置</el-button>
    </div>
    <el-table
      ref="tableRef"
      :data="tableData"
      v-loading="loading"
      border stripe size="small"
      max-height="calc(100vh - 220px)"
      row-key="id"
      @sort-change="(s: any) => $emit('sortChange', s)"
      @selection-change="(rows: CaseVO[]) => $emit('selectionChange', rows.map(r => r.id))"
    >
      <el-table-column type="selection" width="44" align="center" />
      <el-table-column label="编号" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <span>{{ row.project_prefix }}{{ row.external_id }}__{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="purpose" label="测试目的" min-width="200" show-overflow-tooltip />
      <el-table-column prop="importance" label="级别" width="70" align="center" sortable="custom">
        <template #default="{ row }">
          <el-tag :type="importanceType(row.importance)" size="small">
            {{ importanceLabel(row.importance) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_core" label="核心" width="90" align="center" sortable="custom">
        <template #default="{ row }">
          <el-tooltip v-if="row.is_core" :content="row.core_reason || '无理由'" placement="top" :show-after="300">
            <span class="text-orange-500 cursor-pointer" style="font-size: 12px">★</span>
          </el-tooltip>
          <span v-else class="text-gray-300">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="is_sample" label="样本" width="70" align="center">
        <template #default="{ row }">
          <span v-if="row.is_sample" class="text-green-500" style="font-size: 13px" title="样本用例">✓</span>
          <span v-else class="text-gray-300" style="font-size: 13px" title="非样本">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="script_count" label="脚本" width="60" align="center" />
      <el-table-column label="操作" width="180" fixed="right" class-name="col-ops">
        <template #default="{ row }">
          <div class="ops-cell">
            <el-button text type="primary" size="small" @click="$emit('showDetail', row)">详情</el-button>
            <el-button text type="primary" size="small" v-hasPerm="'aitc:case:update'" @click="$emit('openEdit', row)">编辑</el-button>
            <el-button text type="primary" size="small" v-hasPerm="'aitc:case:core'" @click="$emit('toggleCore', row)">
              {{ row.is_core ? '取消核心' : '标记核心' }}
            </el-button>
            <el-button text type="primary" size="small" v-hasPerm="'aitc:case:sample'" @click="$emit('toggleSample', row)">
              {{ row.is_sample ? '取消样本' : '标记样本' }}
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && tableData.length === 0" description="请选择项目或模块查看用例" />
    <div class="flex justify-end mt-1">
      <el-pagination
        v-model:current-page="localQuery.pageNum"
        v-model:page-size="localQuery.pageSize"
        :page-sizes="[100]"
        layout="total, prev, pager, next"
        :total="total"
        @size-change="$emit('loadCases')"
        @current-change="$emit('loadCases')"
        size="small"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { CaseVO, CaseQueryParams } from "@/api/aitc/case";
import { importanceLabel, importanceType } from "../../constants";
import { CaseImportanceEnum, ReviewStatusEnum } from "@/enums/aitc";

const props = defineProps<{
  tableData: CaseVO[];
  loading: boolean;
  total: number;
  queryParams: CaseQueryParams;
}>();

defineEmits<{
  loadCases: [];
  sortChange: [data: { prop: string; order: string | null }];
  selectionChange: [ids: (string | number)[]];
  showDetail: [row: CaseVO];
  openEdit: [row: CaseVO];
  toggleCore: [row: CaseVO];
  toggleSample: [row: CaseVO];
  handleReset: [];
}>();

/** 双向绑定 queryParams 的各字段，变更时 emit loadCases */
const localQuery = computed({
  get: () => props.queryParams,
  set: () => {}, // 父组件通过 v-model:query-params 绑定
});
</script>

<style scoped>
.ops-cell {
  display: flex;
  gap: 0;
  align-items: center;
}
.ops-cell .el-button {
  padding: 0 6px;
  height: 22px;
  font-size: 11px;
}
</style>
