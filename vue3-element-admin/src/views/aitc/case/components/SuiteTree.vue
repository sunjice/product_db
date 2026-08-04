<template>
  <div class="page-aside__inner" style="padding: 6px 8px; overflow-y: auto">
    <el-input v-model="filterText" placeholder="过滤模块" size="small" clearable class="mb-1" @input="onFilterChange" />
    <el-tree
      ref="treeRef"
      :load="loadTreeNode"
      :filter-node-method="filterTreeByText"
      lazy
      :props="treeProps"
      node-key="id"
      :key="projectId || 'empty'"
      highlight-current
      @node-click="$emit('nodeClick', $event)"
      class="tree-compact"
    >
      <template #default="{ data }">
        <template v-if="data.node_type === 'case'">
          <span class="flex-1 truncate" style="font-size: 11px">{{ data.project_prefix }}{{ data.external_id }}__{{ data.name }}</span>
        </template>
        <template v-else>
          <span class="flex-1 truncate text-xs">{{ data.label }}</span>
          <span class="text-xs text-gray-400 ml-1" style="font-size: 10px">({{ data.case_count }})</span>
        </template>
      </template>
    </el-tree>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import type { SuiteNode } from "@/api/aitc/suite";
import SuiteAPI from "@/api/aitc/suite";

const props = defineProps<{
  projectId: string;
}>();

defineEmits<{
  nodeClick: [node: SuiteNode];
}>();

const treeRef = ref();
const filterText = ref("");
const treeProps = { children: "children", label: "label", isLeaf: (data: any) => data.node_type === "case" };

function filterTreeByText(value: string, data: any) {
  if (!value) return true;
  const v = value.toLowerCase();
  return (data.label || "").toLowerCase().includes(v)
    || (data.name || "").toLowerCase().includes(v)
    || (data.external_id || "").toLowerCase().includes(v);
}

function onFilterChange() {
  treeRef.value?.filter(filterText.value);
}

function loadTreeNode(node: any, resolve: (data: SuiteNode[]) => void) {
  if (node.level === 0) {
    if (!props.projectId) { resolve([]); return; }
    SuiteAPI.getChildren(0, props.projectId).then((res) => resolve(res || []));
  } else if (node.data.node_type === "case") {
    resolve([]);
  } else {
    SuiteAPI.getChildren(node.data.id).then((res) => resolve(res || []));
  }
}

/** 刷新树中单个节点数据（编辑保存后调用） */
function updateCaseNode(caseId: number, data: Partial<SuiteNode>) {
  const nodeId = -caseId;
  const node = treeRef.value?.getNode(nodeId);
  if (node?.data) {
    node.data = { ...node.data, ...data };
  }
}

/** 暴露树实例和过滤文本，供父组件控制 */
defineExpose({ treeRef, filterText, updateCaseNode });
</script>

<style scoped>
.tree-compact {
  font-size: 11px;
}
.tree-compact :deep(.el-tree-node__content) {
  height: 24px;
  line-height: 24px;
}
.tree-compact :deep(.el-tree-node__label) {
  font-size: 11px;
}
.tree-compact :deep(.el-tree-node__expand-icon) {
  font-size: 11px;
  padding: 0 4px;
}
</style>
