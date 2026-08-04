<template>
  <el-dialog
    v-model="localVisible"
    :title="isEdit ? '编辑产品' : '新增产品'"
    width="800px"
    @closed="handleClose"
    :close-on-click-modal="false"
  >
    <el-tabs v-model="activeTab">
      <el-tab-pane label="基础信息" name="basic">
        <el-form ref="basicFormRef" :model="form" :rules="basicRules" label-width="80px">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="分类" prop="category_id">
                <el-select v-model="form.category_id" placeholder="请选择分类" style="width: 100%" @change="onCategoryChange">
                  <el-option v-for="c in categoryOptions" :key="c.value" :label="c.label" :value="String(c.value)" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="品牌" prop="brand_id">
                <el-select v-model="form.brand_id" placeholder="请选择品牌" style="width: 100%">
                  <el-option v-for="b in brandOptions" :key="b.value" :label="b.label" :value="String(b.value)" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="名称" prop="name">
                <el-input v-model="form.name" maxlength="128" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="型号" prop="model">
                <el-input v-model="form.model" maxlength="64" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="描述">
            <el-input v-model="form.description" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="图片">
            <div class="flex gap-2 flex-wrap items-end">
              <div v-for="(url, idx) in form.image_urls" :key="idx" class="relative">
                <el-image :src="url" style="width: 100px; height: 80px" fit="cover" class="rounded border" />
                <el-button
                  class="absolute top-0 right-0"
                  circle size="small" type="danger"
                  @click="removeImage(idx)"
                  style="transform: translate(50%, -50%)"
                >
                  <i class="i-ep-close" />
                </el-button>
              </div>
              <el-input
                v-model="imageInput"
                placeholder="图片URL"
                style="width: 200px"
                @keyup.enter="addImage"
              >
                <template #append>
                  <el-button @click="addImage">添加</el-button>
                </template>
              </el-input>
            </div>
          </el-form-item>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="状态">
                <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="上架" inactive-text="下架" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="排序">
                <el-input-number v-model="form.sort_order" :min="0" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="规格编辑" name="specs">
        <div v-if="specGroups.length === 0 && !form.category_id" class="text-center text-gray-400 py-10">
          请先在基础信息中选择分类
        </div>
        <div v-if="specGroups.length === 0 && form.category_id" class="text-center text-gray-400 py-4">
          该分类暂无预定义规格分组，请点击下方按钮添加
        </div>
        <div v-for="(group, gi) in specGroups" :key="gi" class="mb-4 border rounded p-3 relative">
          <div class="flex items-center justify-between mb-2">
            <span class="font-semibold">{{ group.group_name }}</span>
            <el-button text type="danger" size="small" @click="removeSpecGroup(gi)">删除分组</el-button>
          </div>
          <el-table :data="group.items" border stripe size="small">
            <el-table-column label="规格名称" width="160">
              <template #default="{ row }">
                <el-input v-model="row.spec_name" size="small" placeholder="规格名称" />
              </template>
            </el-table-column>
            <el-table-column label="规格值" min-width="160">
              <template #default="{ row }">
                <el-input v-model="row.spec_value" size="small" placeholder="规格值" />
              </template>
            </el-table-column>
            <el-table-column label="单位" width="100">
              <template #default="{ row }">
                <el-input v-model="row.spec_unit" size="small" placeholder="单位" />
              </template>
            </el-table-column>
            <el-table-column label="排序" width="80">
              <template #default="{ row }">
                <el-input-number v-model="row.sort_order" :min="0" size="small" controls-position="right" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ $index }">
                <el-button text type="danger" size="small" @click="removeSpecRow(gi, $index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-button class="mt-2" size="small" @click="addSpecRow(group)">+ 添加规格项</el-button>
        </div>
        <el-button class="mt-2" size="small" type="primary" :disabled="!form.category_id" @click="addSpecGroup">
          + 添加规格分组
        </el-button>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="localVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitLoading" @click="handleSubmit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance } from "element-plus";
import { ProductAPI, CategoryAPI, BrandAPI, SpecGroupAPI } from "@/api/product/index";
import type { ProductForm, SpecGroupVO, SpecItem } from "@/api/product/types";
import type { OptionItem } from "@/api/common";

const props = defineProps<{ visible: boolean; productId?: string }>();
const emit = defineEmits<{ close: []; saved: [] }>();

const isEdit = ref(false);
const localVisible = ref(false);
const activeTab = ref("basic");
const submitLoading = ref(false);
const basicFormRef = ref<FormInstance>();

const categoryOptions = ref<OptionItem[]>([]);
const brandOptions = ref<OptionItem[]>([]);

const imageInput = ref("");

const form = reactive<ProductForm>({
  category_id: "", brand_id: "", name: "", model: "", description: "",
  image_urls: [], status: 1, sort_order: 0, specifications: [],
});

const specGroups = ref<SpecGroupVO[]>([]);

const basicRules = {
  category_id: [{ required: true, message: "请选择分类", trigger: "change" }],
  brand_id: [{ required: true, message: "请选择品牌", trigger: "change" }],
  name: [{ required: true, message: "请输入产品名称", trigger: "blur" }],
};

watch(() => props.visible, async (val) => {
  localVisible.value = val;
  if (val) {
    await loadOptions();
    if (props.productId) {
      await loadProduct(props.productId);
    } else {
      resetForm();
    }
  }
});

watch(localVisible, (val) => {
  if (!val) emit("close");
});

async function loadOptions() {
  const [cats, brands] = await Promise.all([
    CategoryAPI.getOptions(),
    BrandAPI.getOptions(),
  ]);
  categoryOptions.value = cats ?? [];
  brandOptions.value = brands ?? [];
}

async function loadProduct(id: string) {
  isEdit.value = true;
  const p = await ProductAPI.getById(id);
  if (p) {
    form.id = p.id;
    form.category_id = String(p.category_id);
    form.brand_id = String(p.brand_id);
    form.name = p.name;
    form.model = p.model ?? "";
    form.description = p.description ?? "";
    form.image_urls = p.image_urls ?? [];
    form.status = p.status;
    form.sort_order = p.sort_order;
    if (p.groups && p.groups.length > 0) {
      // 已有规格数据 → 直接渲染
      specGroups.value = p.groups.map(g => ({
        group_id: (g.items[0]?.group_id ?? g.group_id ?? ""),
        group_name: g.group_name,
        sort_order: g.sort_order,
        items: g.items.map(i => ({ ...i })),
      }));
    } else {
      // 无规格数据 → 按分类加载分组模板，每个分组预置一个空行
      try {
        const groups = await SpecGroupAPI.getOptions(form.category_id);
        specGroups.value = (groups ?? []).map(g => ({
          group_id: g.value as string,
          group_name: g.label,
          sort_order: 0,
          items: [{
            group_id: g.value as string,
            group_name: g.label,
            spec_name: "",
            spec_value: "",
            spec_unit: "",
            sort_order: 0,
          }],
        }));
      } catch {
        specGroups.value = [];
      }
    }
  }
}

function resetForm() {
  isEdit.value = false;
  form.id = "";
  form.category_id = "";
  form.brand_id = "";
  form.name = "";
  form.model = "";
  form.description = "";
  form.image_urls = [];
  form.status = 1;
  form.sort_order = 0;
  form.specifications = [];
  specGroups.value = [];
  imageInput.value = "";
  activeTab.value = "basic";
}

async function onCategoryChange() {
  if (!form.category_id) {
    specGroups.value = [];
    return;
  }
  try {
    const groups = await SpecGroupAPI.getOptions(form.category_id);
    // 每个分组预置一个空行，方便直接填写
    specGroups.value = (groups ?? []).map(g => ({
      group_id: g.value as string,
      group_name: g.label,
      sort_order: 0,
      items: [{
        group_id: g.value as string,
        group_name: g.label,
        spec_name: "",
        spec_value: "",
        spec_unit: "",
        sort_order: 0,
      }],
    }));
  } catch (e: any) {
    ElMessage.error("加载规格分组失败: " + (e?.message || e));
  }
}

function addImage() {
  const url = imageInput.value.trim();
  if (url && !form.image_urls.includes(url)) {
    form.image_urls.push(url);
    imageInput.value = "";
  }
}

function removeImage(idx: number) {
  form.image_urls.splice(idx, 1);
}

function addSpecRow(group: SpecGroupVO) {
  group.items.push({
    group_id: group.group_id,
    group_name: group.group_name,
    spec_name: "",
    spec_value: "",
    spec_unit: "",
    sort_order: group.items.length,
  });
}

function removeSpecRow(groupIdx: number, itemIdx: number) {
  specGroups.value[groupIdx]?.items.splice(itemIdx, 1);
}

async function addSpecGroup() {
  try {
    const { value } = await ElMessageBox.prompt("请输入规格分组名称", "添加分组", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      inputPattern: /\S+/,
      inputErrorMessage: "名称不能为空",
    });
    const name = value?.trim();
    if (name) {
      specGroups.value.push({
        group_id: 0,
        group_name: name,
        sort_order: specGroups.value.length,
        items: [],
      });
    }
  } catch {
    // 用户取消
  }
}

function removeSpecGroup(groupIdx: number) {
  specGroups.value.splice(groupIdx, 1);
}

function buildSpecifications(): SpecItem[] {
  const specs: SpecItem[] = [];
  specGroups.value.forEach(group => {
    group.items.forEach(item => {
      if (item.spec_name.trim()) {
        specs.push({
          group_id: group.group_id,
          group_name: group.group_name,
          spec_name: item.spec_name,
          spec_value: item.spec_value,
          spec_unit: item.spec_unit,
          sort_order: item.sort_order,
        });
      }
    });
  });
  return specs;
}

async function handleSubmit() {
  const valid = await basicFormRef.value?.validate().catch(() => false);
  if (!valid) {
    activeTab.value = "basic";
    return;
  }

  // 选了分类、加载了规格分组，但一条规格都没填 → 拦截提醒
  const specs = buildSpecifications();
  if (specGroups.value.length > 0 && specs.length === 0 && !props.productId) {
    try {
      await ElMessageBox.confirm("当前未填写任何规格数据，确定要保存吗？", "提示", {
        confirmButtonText: "继续保存",
        cancelButtonText: "去填写",
        type: "warning",
      });
    } catch {
      activeTab.value = "specs";
      return;
    }
  }

  submitLoading.value = true;
  try {
    const payload: ProductForm = {
      ...form,
      category_id: form.category_id,
      brand_id: form.brand_id,
      specifications: specs,
    };
    if (props.productId) {
      await ProductAPI.update(props.productId, payload);
      ElMessage.success("更新成功");
    } else {
      await ProductAPI.create(payload);
      ElMessage.success("创建成功");
    }
    emit("saved");
    emit("close");
  } finally {
    submitLoading.value = false;
  }
}

function handleClose() {
  resetForm();
}
</script>
