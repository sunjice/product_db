-- ============================================================
-- AITC 前端架构重构 → 数据库菜单 component 字段迁移
-- 执行前请备份 sys_menu 表！
-- ============================================================

-- 1. 用例管理：aitc/index → aitc/case
UPDATE sys_menu SET component = 'aitc/case'
WHERE id = 3010 AND component = 'aitc/index';

-- 2. 审核工作台：aitc/review → aitc/task/review-index
UPDATE sys_menu SET component = 'aitc/task/review-index'
WHERE id = 3060 AND component = 'aitc/review';

-- 3. 删除 AI 配置菜单 + 按钮权限（前端已移除 aiconfig.vue）
DELETE FROM sys_role_menu WHERE menu_id >= 3050 AND menu_id <= 3054;
DELETE FROM sys_menu WHERE id >= 3050 AND id <= 3054;

-- 验证：以下页面的 component 应保持不变
--   aitc/task → 任务管理 (3020)
--   aitc/sample → 样本库 (3040)
--   aitc/script → 脚本库 (3070)
--   aitc/spec  → 规范管理 (3080)
SELECT id, name, component FROM sys_menu
WHERE id BETWEEN 3000 AND 3084
ORDER BY id;
