/**
 * useTaskPolling — 任务 5s 轮询器
 *
 * 同时服务于：
 *   - task/index.vue（任务列表页）
 *   - task/detail.vue（任务详情页）
 */
import { ref, watch, onUnmounted } from "vue";

export function useTaskPolling(fetchFn: (silent: boolean) => void, interval = 5000) {
  const autoRefresh = ref(false);
  let pollTimer: ReturnType<typeof setInterval> | null = null;

  function startPolling() {
    stopPolling();
    if (autoRefresh.value) {
      pollTimer = setInterval(() => fetchFn(true), interval);
    }
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  watch(autoRefresh, () => {
    startPolling();
  });

  onUnmounted(() => stopPolling());

  return { autoRefresh, startPolling, stopPolling };
}
