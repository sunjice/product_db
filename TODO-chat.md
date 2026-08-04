# AI Chat 待办

## 快捷提问可配置化

当前 `quickPrompts` 硬编码在 `src/layouts/components/LayoutChat.vue`，生产环境修改需重新构建部署。

目标：从后端读取，改配置无需发版。

### 方案

1. **后端**：`prompts/chat_quick.txt` 一行一条，加接口 `GET /api/v1/aitc/chat/quick-prompts` 返回数组
2. **前端**：`LayoutChat.vue` 在 `ensureInit()` 时调接口获取，替代硬编码数组

### 文件

| 位置 | 文件 |
|------|------|
| 模板 | `youlai-fastapi-master/app/system/aitc/prompts/chat_quick.txt` |
| 接口 | `youlai-fastapi-master/app/system/aitc/chat/router.py` |
| API | `vue3-element-admin/src/api/chat/index.ts` |
| UI | `vue3-element-admin/src/layouts/components/LayoutChat.vue` |
