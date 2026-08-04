/**
 * useCaseReview — 用例审核共享 composable
 *
 * 同时服务于：
 *   - case-review.vue（任务内逐条审核——左/右分栏）
 *   - case-review-index.vue（审核工作台——树+列表+字段表格）
 *
 * 提取的共享逻辑：
 *   - 字段三态状态机（accept / ignore / manual）
 *   - 手动编辑流程（文本 + 步骤）
 *   - 完成度统计 + canSubmit 判定
 */

import { ref, reactive, computed } from 'vue'

// ── 工具 ──

export function displayVal(v: any): string {
  if (v === null || v === undefined || v === '') return '（空）'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

// ── 字段名中文映射 ──

export const FIELD_LABEL_MAP: Record<string, string> = {
  name: '用例名称',
  summary: '测试思想',
  preconditions: '前置条件',
  test_data: '测试数据',
  topo: '测试Topo',
  steps: '测试步骤',
}

export interface FieldItem {
  field_name: string
  conclusion: string       // 'pass' | 'fail'
  rule_violated?: string
  original?: any
  suggested?: any
  has_suggestion?: boolean
}

// ── composable ──

export function useCaseReview() {
  // 字段处理状态: null=未处理, 'accept'=采纳AI, 'ignore'=保持原样, 'manual'=人工编辑
  const fieldStates = reactive<Record<string, string | null>>({})
  const manualValues = reactive<Record<string, any>>({})
  const editingField = ref<string | null>(null)
  const editDraft = reactive<Record<string, string>>({})
  const editSteps = ref<any[]>([])

  /** 清空所有状态 */
  function clearFieldStates() {
    Object.keys(fieldStates).forEach(k => { fieldStates[k] = null })
    Object.keys(manualValues).forEach(k => { manualValues[k] = null })
    editingField.value = null
    editSteps.value = []
  }

  /** 统计字段列表中的已处理数和未处理数 */
  function useFieldStats(failFields: () => FieldItem[]) {
    const failCount = computed(() => failFields().length)
    const processedCount = computed(() =>
      failFields().filter(f => !!fieldStates[f.field_name]).length
    )
    const canSubmit = computed(() =>
      failCount.value === 0 || processedCount.value >= failCount.value
    )
    return { failCount, processedCount, canSubmit }
  }

  // ── 三态操作 ──
  function acceptField(fieldName: string) {
    fieldStates[fieldName] = 'accept'
    cancelEdit()
  }

  function ignoreField(fieldName: string) {
    fieldStates[fieldName] = 'ignore'
    cancelEdit()
  }

  function resetField(fieldName: string) {
    fieldStates[fieldName] = null
    manualValues[fieldName] = undefined
    cancelEdit()
  }

  function acceptAll(failFields: FieldItem[]) {
    failFields.forEach(f => {
      if (!fieldStates[f.field_name]) fieldStates[f.field_name] = 'accept'
    })
  }

  function ignoreAll(failFields: FieldItem[]) {
    failFields.forEach(f => {
      if (!fieldStates[f.field_name]) fieldStates[f.field_name] = 'ignore'
    })
  }

  // ── 编辑流程 ──
  function startEdit(sug: FieldItem, stepsOriginal?: any[]) {
    cancelEdit()
    editingField.value = sug.field_name
    if (sug.field_name === 'steps') {
      const base = (sug.has_suggestion && Array.isArray(sug.suggested) && sug.suggested.length)
        ? sug.suggested
        : (Array.isArray(stepsOriginal) ? stepsOriginal : sug.original || [])
      editSteps.value = JSON.parse(JSON.stringify(base.length ? base : [{ step_no: 1, action: '', expected: '' }]))
    } else {
      editDraft[sug.field_name] = sug.has_suggestion
        ? displayVal(sug.suggested)
        : displayVal(sug.original)
    }
  }

  function cancelEdit() {
    editingField.value = null
  }

  function saveManualEdit(fieldName: string) {
    if (fieldName === 'steps') {
      const steps = editSteps.value.map((s: any, i: number) => ({ ...s, step_no: i + 1 }))
      manualValues.steps = steps
    } else {
      manualValues[fieldName] = editDraft[fieldName] || ''
    }
    fieldStates[fieldName] = 'manual'
    cancelEdit()
  }

  // ── 步骤行操作 ──
  function addStepRow() {
    const no = editSteps.value.length + 1
    editSteps.value = [...editSteps.value, { step_no: no, action: '', expected: '' }]
  }

  function removeStepRow() {
    if (editSteps.value.length <= 1) return
    editSteps.value = editSteps.value.slice(0, -1)
  }

  /** 构建提交字段列表 */
  function buildFields(failFields: FieldItem[]) {
    return failFields.map(s => {
      const action = fieldStates[s.field_name] || 'ignore'
      const item: any = { field_name: s.field_name, action }
      if (action === 'manual') {
        item.action = 'edit_accept'
        item.edited_value = manualValues[s.field_name]
      }
      return item
    })
  }

  return {
    fieldStates,
    manualValues,
    editingField,
    editDraft,
    editSteps,
    clearFieldStates,
    useFieldStats,
    acceptField,
    ignoreField,
    resetField,
    acceptAll,
    ignoreAll,
    startEdit,
    cancelEdit,
    saveManualEdit,
    addStepRow,
    removeStepRow,
    buildFields,
  }
}
