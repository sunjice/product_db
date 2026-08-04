# TODO

> 最后更新：2026-08-04
> 范围：`vue3-element-admin` + `youlai-fastapi-master`

---

## 一、前端（vue3-element-admin）

### 页面能力补齐

- [ ] 1. sample/script/spec 接入 `usePageTable`（或 `useAitcPageTable`），去掉手写分页兜底
- [ ] 2. aiContext 接入 task/script/sample 页面

### 收尾验证

- [ ] 3. `vue-tsc` 类型检查 + 页面冒烟（用例树、审核提交、SSE 聊天、任务轮询）

---

## 二、后端（youlai-fastapi-master）

### TestLink 集成（用例同步）

- [ ] 4. 阶段 0：TestLink 连通验证（需提供 URL + devKey + 样例用例编号）
  - `config.py`/`.env` 加 `TESTLINK_URL`、`TESTLINK_DEVKEY`
  - `scripts/verify_testlink.py`：拉真实用例，确认「测试目的」字段位置、`updater_login`/`modification_ts` 可用性 → 定稿 FIELD_MAP
- [ ] 5. 新建 `app/aitc/testlink/` 包
  - `client.py`（XML-RPC 封装）
  - `field_map.py`（字段映射表 + `full_external_id()` 组装）
  - `hashing.py`（canonical 序列化 + SHA256，字段范围: purpose/name/summary/preconditions/steps/importance）
  - `models.py`（`ai_tc_sync_logs` 审计表）
  - `sync_service.py`（拉取幂等 / 反写乐观锁+降级链 / 三方合并 / 回声抑制）
  - `router.py`（`POST /pull`、`POST /push`、`GET /conflicts`、`POST /conflicts/{id}/resolve`、`GET /logs`）
  - 注册进 `aitc/router.py`
- [ ] 6. `service.py`：内容字段变更自动置 `sync_status=2`（`topo`/`test_data`/AI 字段除外）
- [ ] 7. 巡检定时任务：比对 version/modification_ts，标记 `sync_status=3`（只标记不自动拉）
- [ ] 8. 前端：同步状态列、拉取/反写按钮、待反写筛选、冲突三栏处理页
- [ ] 9. Excel 导入功能下线（`import_cases` 去掉 Excel 格式解析，`CaseImportDialog.vue` + 入口按钮移除）
- [ ] 10. `开发指导手册.md` 补 testlink 域、字段映射表、同步状态机、降级链章节

### LangGraph 二期

- [ ] 11. 新建 `agent/graphs/`：base + core_select/case_review/script_gen 三张作业图，handler 改为薄适配层
- [ ] 12. 新建 `chat/graph.py`：LangGraph 重写 orchestrator 内部实现，保留关键词 fast path

**说明**：两层图各司其职 — 作业图编排单次任务内多节点 LLM 流程；会话图替换 orchestrator 的意图路由 + 自由对话，SSE 事件协议不变。

---

## 三、共享

- [ ] 13. 权限控制补齐（前端 `v-hasPerm` + 后端端点 `Depends(require_perm(...))`）
- [ ] 14. 测试覆盖补充（aitc/ai 域）

---

## 变更记录

| 日期 | 内容 |
|------|------|
| 2026-08-04 | 合并两份 TODO 为一份，删除已完成项和背景/目标/注意事项等非 TODO 内容 |
