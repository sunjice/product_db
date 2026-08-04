/**
 * useChatResize — 聊天浮窗拖拽 + 八向缩放
 *
 * 从 LayoutChat.vue 提取，约 130 行 DOM 交互逻辑。
 */
import { ref, computed, type Ref, type ComputedRef } from "vue"

type ResizeDir = "top" | "bottom" | "left" | "right" | "tl" | "tr" | "bl" | "br"

const DIR_COEF: Record<ResizeDir, { fx: number; fy: number }> = {
  left: { fx: -1, fy: 0 }, right: { fx: 1, fy: 0 },
  top: { fx: 0, fy: -1 }, bottom: { fx: 0, fy: 1 },
  tl: { fx: -1, fy: -1 }, tr: { fx: 1, fy: -1 },
  bl: { fx: -1, fy: 1 }, br: { fx: 1, fy: 1 },
}

const MIN_W = 320, MAX_W = 900, MIN_H = 360, MAX_H = 800

export const RESIZE_DIRS: ResizeDir[] = ["top", "bottom", "left", "right", "tl", "tr", "bl", "br"]

export function useChatResize(
  panelWidth: Ref<number>,
  panelHeight: Ref<number>,
  floatX: Ref<number>,
  floatY: Ref<number>,
) {
  const isDragging = ref(false)
  const isResizing = ref(false)
  let dragStartX = 0, dragStartY = 0
  let dragStartFloatX = 0, dragStartFloatY = 0

  // ── 拖拽 ──
  function startDrag(e: MouseEvent) {
    const target = e.target as HTMLElement
    if (target.closest("button")) return
    isDragging.value = true
    dragStartX = e.clientX; dragStartY = e.clientY
    dragStartFloatX = floatX.value; dragStartFloatY = floatY.value
    document.addEventListener("mousemove", onDragMove)
    document.addEventListener("mouseup", onDragEnd)
  }

  function onDragMove(e: MouseEvent) {
    if (!isDragging.value) return
    const dx = e.clientX - dragStartX
    const dy = e.clientY - dragStartY
    floatX.value = Math.min(Math.max(dragStartFloatX + dx, -panelWidth.value + 60), window.innerWidth - 60)
    floatY.value = Math.min(Math.max(dragStartFloatY + dy, 0), window.innerHeight - 40)
  }

  function onDragEnd() {
    isDragging.value = false
    document.removeEventListener("mousemove", onDragMove)
    document.removeEventListener("mouseup", onDragEnd)
  }

  // ── 窗口八向缩放 ──
  let resizeCorner = "" as ResizeDir
  let resizeStartX = 0, resizeStartY = 0
  let resizeStartW = 0, resizeStartH = 0
  let resizeStartLeft = 0, resizeStartTop = 0

  function startResize(e: MouseEvent, corner: ResizeDir) {
    e.preventDefault()
    isResizing.value = true
    resizeCorner = corner
    resizeStartX = e.clientX; resizeStartY = e.clientY
    resizeStartW = panelWidth.value; resizeStartH = panelHeight.value
    resizeStartLeft = floatX.value; resizeStartTop = floatY.value
    document.addEventListener("mousemove", onResizeMove)
    document.addEventListener("mouseup", onResizeEnd)
  }

  function onResizeMove(e: MouseEvent) {
    if (!isResizing.value) return
    const dx = e.clientX - resizeStartX
    const dy = e.clientY - resizeStartY
    const { fx, fy } = DIR_COEF[resizeCorner]

    let newW = resizeStartW + fx * dx
    let newL = resizeStartLeft
    if (fx < 0) {
      newW = Math.min(Math.max(newW, MIN_W), MAX_W)
      newL = resizeStartLeft + resizeStartW - newW
    } else {
      newW = Math.min(Math.max(newW, MIN_W), MAX_W)
    }

    let newH = resizeStartH + fy * dy
    let newT = resizeStartTop
    if (fy < 0) {
      newH = Math.min(Math.max(newH, MIN_H), MAX_H)
      newT = resizeStartTop + resizeStartH - newH
    } else {
      newH = Math.min(Math.max(newH, MIN_H), MAX_H)
    }

    panelWidth.value = newW
    panelHeight.value = newH
    floatX.value = newL
    floatY.value = newT
  }

  function onResizeEnd() {
    isResizing.value = false
    document.removeEventListener("mousemove", onResizeMove)
    document.removeEventListener("mouseup", onResizeEnd)
  }

  return { isDragging, isResizing, startDrag, startResize }
}

/** 输入区高度拖拽逻辑 */
export function useInputResize() {
  const inputHeight = ref(100)
  const isInputResizing = ref(false)

  function onInputMouseDown(e: MouseEvent) {
    if (e.offsetY > 5) return
    startInputResize(e)
  }

  function startInputResize(e: MouseEvent) {
    isInputResizing.value = true
    const startY = e.clientY
    const startHeight = inputHeight.value

    function onMouseMove(ev: MouseEvent) {
      const delta = startY - ev.clientY
      inputHeight.value = Math.min(Math.max(startHeight + delta, 60), 320)
    }

    function onMouseUp() {
      isInputResizing.value = false
      document.removeEventListener("mousemove", onMouseMove)
      document.removeEventListener("mouseup", onMouseUp)
    }

    document.addEventListener("mousemove", onMouseMove)
    document.addEventListener("mouseup", onMouseUp)
  }

  return { inputHeight, isInputResizing, onInputMouseDown }
}
