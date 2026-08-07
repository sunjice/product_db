/** AI 对话 — 页面上下文共享 Store。
 *
 * 各页面在 onMounted 时调用 register() 注册当前页面类型，
 * 在项目/模块/用例选择变化时调用 update() 更新上下文数据。
 *
 * AI 对话框发消息前从此 Store 读取上下文，同步到后端会话。
 *
 * ======== 使用示例 ========
 *
 * // 用例管理页
 * aiContextStore.register("case")
 * aiContextStore.update({ projectId: 1, suiteId: 5, selectedCaseIds: [101,102], currentCaseId: 101 })
 *
 * // 脚本管理页
 * aiContextStore.register("script")
 * aiContextStore.update({ projectId: 1, scriptId: 42 })
 *
 * // 任务列表页
 * aiContextStore.register("task")
 * aiContextStore.update({ projectId: 1, taskId: 99 })
 *
 * // 任意页面离开时清理
 * onUnmounted(() => aiContextStore.unregister())
 */

import { ref, computed } from "vue";
import { defineStore } from "pinia";

/** 驼峰转下划线 */
function toSnake(key: string): string {
  return key.replace(/([A-Z])/g, "_$1").toLowerCase();
}

/** 判断值是否 "有内容"（非 null/undefined/空字符串/空数组） */
function isPresent(v: any): boolean {
  if (v == null) return false;
  if (v === "") return false;
  if (Array.isArray(v) && v.length === 0) return false;
  return true;
}

export interface AiPageContext {
  currentPage: string;
  projectId?: number | null;
  /** 以下为各页面按需设置的字段，驼峰自动转下划线 */
  [key: string]: any;
}

export const useAiContextStore = defineStore("aiContext", () => {
  const context = ref<AiPageContext>({
    currentPage: "",
    projectId: null,
  });

  /** 序列化为后端 context_json 格式（驼峰 → 下划线） */
  const contextJson = computed(() => {
    const result: Record<string, any> = {};
    // current_page 始终携带（空字符串也传，便于后端判断页面准入）
    result["current_page"] = context.value.currentPage || "";
    for (const [key, val] of Object.entries(context.value)) {
      if (key === "currentPage") continue;
      if (isPresent(val)) {
        result[toSnake(key)] = val;
      }
    }
    // 显式携带 selected_case_ids / current_case_id，即便为空也要通知后端清除旧值
    if (!("selected_case_ids" in result)) {
      result["selected_case_ids"] = [];
    }
    if (!("current_case_id" in result)) {
      result["current_case_id"] = null;
    }
    return result;
  });

  /** 注册当前页面 */
  function register(page: string) {
    context.value.currentPage = page;
  }

  /** 合并更新上下文数据（任意字段，驼峰命名，自动转下划线） */
  function update(data: Record<string, any>) {
    Object.assign(context.value, data);
  }

  /** 取消注册（页面 onUnmounted 时调用，只清页面数据保留 projectId） */
  function unregister() {
    const pid = context.value.projectId;
    context.value = { currentPage: "", projectId: pid } as AiPageContext;
  }

  /** 清空全部上下文（会话切换时调用） */
  function clear() {
    context.value = { currentPage: "", projectId: null } as AiPageContext;
  }

  return { context, contextJson, register, update, unregister, clear };
});
