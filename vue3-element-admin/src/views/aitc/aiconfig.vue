<template>
  <div class="aitc-aiconfig-page">
    <el-card>
      <div class="flex gap-2 items-center mb-4 flex-wrap">
        <el-select v-model="queryParams.provider" placeholder="提供方" clearable style="width: 160px" @change="loadData">
          <el-option label="OpenAI兼容" value="openai_compat" />
          <el-option label="DeepSeek" value="deepseek" />
        </el-select>
        <el-select v-model="queryParams.status" placeholder="状态" clearable style="width: 100px" @change="loadData">
          <el-option label="启用" :value="1" />
          <el-option label="停用" :value="0" />
        </el-select>
        <el-input v-model="queryParams.keywords" placeholder="搜索配置名" style="width: 200px" clearable @keyup.enter="loadData" />
        <el-button type="primary" @click="loadData">搜索</el-button>
        <el-button type="primary" v-hasPerm="'aitc:aiconfig:create'" @click="openCreate">新增配置</el-button>
      </div>

      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="配置名称" min-width="160" />
        <el-table-column prop="provider" label="提供方" width="120" />
        <el-table-column prop="model" label="模型" width="160" show-overflow-tooltip />
        <el-table-column prop="scenes" label="适用场景" width="240">
          <template #default="{ row }">
            <el-tag v-for="s in row.scenes" :key="s" size="small" class="mr-1">{{ sceneLabel(s) }}</el-tag>
            <span v-if="!row.scenes?.length">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_default" label="全局默认" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="success" size="small">是</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'" size="small">{{ row.status ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" v-hasPerm="'aitc:aiconfig:update'" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" size="small" v-hasPerm="'aitc:aiconfig:delete'" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && tableData.length === 0" description="暂无AI配置，请先新增" />
      <div class="flex justify-end mt-4">
        <el-pagination
          v-model:current-page="queryParams.pageNum" v-model:page-size="queryParams.pageSize"
          :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" :total="total"
          @size-change="loadData" @current-change="loadData"
        />
      </div>
    </el-card>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="showDialog" :title="isEdit ? '编辑AI配置' : '新增AI配置'" width="650px" @closed="resetForm">
      <el-form :model="form" label-width="100px">
        <el-form-item label="配置名称" required>
          <el-input v-model="form.name" placeholder="如 DeepSeek-V3" />
        </el-form-item>
        <el-form-item label="提供方" required>
          <el-select v-model="form.provider" style="width: 100%">
            <el-option label="OpenAI兼容" value="openai_compat" />
            <el-option label="DeepSeek" value="deepseek" />
          </el-select>
        </el-form-item>
        <el-form-item label="API地址" required>
          <el-input v-model="form.api_base" placeholder="如 https://api.deepseek.com" />
        </el-form-item>
        <el-form-item label="API密钥" required>
          <el-input v-model="form.api_key" type="password" placeholder="sk-xxx" show-password />
        </el-form-item>
        <el-form-item label="模型名" required>
          <el-input v-model="form.model" placeholder="如 deepseek-chat" />
        </el-form-item>
        <el-form-item label="采样温度">
          <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" show-input />
        </el-form-item>
        <el-form-item label="最大输出Token">
          <el-input-number v-model="form.max_tokens" :min="1" :max="32768" :step="1024" />
        </el-form-item>
        <el-form-item label="适用场景">
          <el-checkbox-group v-model="form.scenes">
            <el-checkbox value="core_select">挑选核心用例</el-checkbox>
            <el-checkbox value="case_review">用例审核</el-checkbox>
            <el-checkbox value="script_gen">生成测试脚本</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="全局默认">
          <el-switch v-model="form.is_default" :active-value="1" :inactive-value="0" />
          <span class="text-gray-400 text-sm ml-2">设为全局兜底默认配置</span>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="可选备注" />
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
import { AiConfigAPI } from "@/api/aitc/index";
import type { PageResult } from "@/api/common";
import type { AiConfigItem, AiConfigForm, AiConfigQueryParams } from "@/api/aitc/types";

const tableData = ref<AiConfigItem[]>([]);
const loading = ref(false);
const total = ref(0);
const queryParams = reactive<AiConfigQueryParams>({ pageNum: 1, pageSize: 10 });

function sceneLabel(s: string) {
  return { core_select: "挑选核心用例", case_review: "用例审核", script_gen: "生成测试脚本" }[s] || s;
}

async function loadData() {
  loading.value = true;
  try {
    const res = await AiConfigAPI.getPage(queryParams);
    const page = res as PageResult<AiConfigItem>;
    tableData.value = page?.list || (res as any)?.records || [];
    total.value = page?.total || (res as any)?.total || 0;
  } finally { loading.value = false; }
}

// ── CRUD ──
const showDialog = ref(false);
const isEdit = ref(false);
const submitting = ref(false);
const editingId = ref("");
const form = reactive<AiConfigForm>({
  name: "", provider: "openai_compat", api_base: "", api_key: "",
  model: "", temperature: 0.3, max_tokens: 4096,
  scenes: [], is_default: 0, status: 1, remark: "",
});

function openCreate() {
  isEdit.value = false;
  editingId.value = "";
  resetForm();
  showDialog.value = true;
}

function openEdit(row: AiConfigItem) {
  isEdit.value = true;
  editingId.value = String(row.id);
  Object.assign(form, {
    name: row.name, provider: row.provider,
    api_base: row.api_base, api_key: row.api_key,
    model: row.model, temperature: row.temperature,
    max_tokens: row.max_tokens, scenes: [...(row.scenes || [])],
    is_default: row.is_default, status: row.status, remark: row.remark,
  });
  showDialog.value = true;
}

function resetForm() {
  form.name = ""; form.provider = "openai_compat"; form.api_base = "";
  form.api_key = ""; form.model = ""; form.temperature = 0.3;
  form.max_tokens = 4096; form.scenes = []; form.is_default = 0;
  form.status = 1; form.remark = "";
}

async function submit() {
  if (!form.name || !form.api_base || !form.api_key || !form.model) {
    ElMessage.warning("请填写必填项");
    return;
  }
  submitting.value = true;
  try {
    if (isEdit.value) {
      await AiConfigAPI.update(editingId.value, { ...form });
      ElMessage.success("更新成功");
    } else {
      await AiConfigAPI.create({ ...form });
      ElMessage.success("创建成功");
    }
    showDialog.value = false;
    loadData();
  } finally { submitting.value = false; }
}

async function handleDelete(row: AiConfigItem) {
  try {
    await ElMessageBox.confirm("确定删除此配置？", "删除确认");
    await AiConfigAPI.delete(String(row.id));
    ElMessage.success("删除成功");
    loadData();
  } catch { /* cancelled */ }
}

onMounted(() => {
  loadData();
});
</script>
