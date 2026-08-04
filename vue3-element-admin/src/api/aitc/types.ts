/**
 * 测试部 AI 助手 - TypeScript 类型定义
 */

import type { BaseQueryParams } from "@/api/common";

// ── 项目 ──

export interface ProjectQueryParams extends BaseQueryParams {
  keywords?: string;
}

export interface ProjectItem {
  id: string;
  name: string;
  prefix: string;
  description?: string;
  last_sync_time?: string;
  create_time?: string;
  update_time?: string;
}

export interface ProjectForm {
  id?: string;
  name: string;
  prefix: string;
  description?: string;
}

// ── 套件树 ──

export interface SuiteNode {
  id: string | number;
  label: string;
  name: string;
  project_id: string | number;
  parent_id: string | number;
  sort_order: number;
  case_count: number;
  node_type: string;   // "suite" | "case"
  external_id?: string; // 用例编号（仅 node_type="case" 时有值）
  children: SuiteNode[];
}

// ── 用例 ──

export interface CaseStep {
  step_no: number;
  action: string;
  expected: string;
}

export interface CaseQueryParams extends BaseQueryParams {
  projectId?: string;
  suiteId?: string;
  isCore?: number;
  isSample?: number;
  reviewStatus?: number;
  importance?: number;
  keywords?: string;
  sortField?: string;
  sortOrder?: string;
}

export interface CaseVO {
  id: string;
  project_id: string;
  suite_id: string;
  suite_name: string;
  external_id?: string;
  name: string;
  summary?: string;
  preconditions?: string;
  topo?: string;
  test_data?: string;
  steps: CaseStep[];
  importance: number;
  is_core: number;
  core_reason?: string;
  core_source?: number;
  is_sample: number;
  review_status: number;
  script_count: number;
  create_time?: string;
  update_time?: string;
}

export interface CaseForm {
  external_id?: string;
  name: string;
  summary?: string;
  preconditions?: string;
  topo?: string;
  test_data?: string;
  steps: CaseStep[];
  importance: number;
}

export interface CaseCoreMark {
  case_id: string;
  is_core: number;
  reason?: string;
}

export interface CaseSampleMark {
  case_id: string;
  is_sample: number;
}


// ── 导入结果 ──

export interface ImportResult {
  created: number;
  updated: number;
  errors: { row: number; msg: string }[];
}

// ── 样本库 ──

export interface SampleQueryParams extends BaseQueryParams {
  projectId?: string;
  sampleType?: string;
  keywords?: string;
}

export interface SampleItem {
  id: string;
  project_id?: string;
  project_name?: string;
  sample_type: string;
  name: string;
  language?: string;
  framework?: string;
  content: string;
  description?: string;
  status: number;
  create_time?: string;
  update_time?: string;
}

export interface SampleForm {
  id?: string;
  project_id?: string;
  sample_type: string;
  name: string;
  language?: string;
  framework?: string;
  content: string;
  description?: string;
  status: number;
}

// ── AI 配置 ──

export interface AiConfigQueryParams extends BaseQueryParams {
  keywords?: string;
  provider?: string;
  status?: number;
}

export interface AiConfigItem {
  id: string;
  name: string;
  provider: string;
  api_base: string;
  api_key: string;
  model: string;
  temperature: number;
  max_tokens: number;
  scenes: string[];
  is_default: number;
  status: number;
  remark?: string;
  create_time?: string;
  update_time?: string;
}

export interface AiConfigForm {
  id?: string;
  name: string;
  provider: string;
  api_base: string;
  api_key: string;
  model: string;
  temperature: number;
  max_tokens: number;
  scenes: string[];
  is_default: number;
  status: number;
  remark?: string;
}

// ── 脚本库 ──

export interface ScriptQueryParams extends BaseQueryParams {
  caseId?: string;
  projectId?: string;
  status?: number;
  source?: number;
}

export interface ScriptItem {
  id: string;
  case_id: string;
  case_name: string;
  language: string;
  framework: string;
  content: string;
  source: number;
  task_item_id?: string;
  version: number;
  status: number;
  reviewed_by?: string;
  create_time?: string;
  update_time?: string;
}

export interface ScriptForm {
  content: string;
  version: number;
}

// ── AI 任务 ──

export interface TaskCreateForm {
  task_type: string;
  project_id: string;
  suite_id?: string;
  spec_ids?: string[];
  ai_config_id?: string;
  case_ids?: string[];
}

export interface TaskQueryParams extends BaseQueryParams {
  projectId?: string;
  taskType?: string;
  status?: number;
}

export interface TaskVO {
  id: string;
  task_type: string;
  project_id: string;
  project_name: string;
  suite_id: string;
  suite_name: string;
  prompt_id?: string;
  sample_ids: string[];
  ai_config_id?: string;
  model?: string;
  status: number;
  total_count: number;
  done_count: number;
  input_tokens: number;
  output_tokens: number;
  error_msg?: string;
  create_by?: string;
  create_time?: string;
}

export interface TaskItemVO {
  id: string;
  task_id: string;
  case_id: string;
  case_name: string;
  output?: Record<string, any>;
  item_status: number;
  confirm_status: number;
  final_content?: string;
  reviewed_by?: string;
  review_time?: string;
}

export interface TaskConfirmItem {
  item_id: string;
  confirm_status: number; // 1-采纳 2-忽略 3-编辑采纳
  final_content?: string;
}

export interface TaskConfirmReq {
  items: TaskConfirmItem[];
}

export interface TaskDetail {
  task: TaskVO;
  items: TaskItemVO[];
}

// ── 审核记录 ──

export interface ReviewRecordVO {
  id: string;
  task_id: string;
  task_item_id: string;
  case_id: string;
  review_action: string;
  field_name?: string;
  before_value?: string;
  after_value?: string;
  reviewer?: string;
  reviewer_ip?: string;
  review_time?: string;
  memo?: string;
  create_time?: string;
}

// ── 规范管理 ──

export interface SpecQueryParams extends BaseQueryParams {
  projectId?: string;
  suiteId?: string;
  taskType?: string;
  specType?: string;
  keywords?: string;
}

export interface SpecItem {
  id: string;
  project_id?: string;
  project_name?: string;
  suite_id?: string;
  suite_name?: string;
  task_type: string;
  spec_type: string;
  content: string;
  sort_order: number;
  status: number;
  create_time?: string;
  update_time?: string;
}

export interface SpecForm {
  id?: string;
  project_id?: string;
  suite_id?: string;
  task_type: string;
  spec_type: string;
  content: string;
  sort_order: number;
  status: number;
}

// ── 审核请求 ──

export interface ReviewFieldItem {
  field_name: string;
  action: string; // accept / ignore / edit_accept
  edited_value?: string;
}

export interface ReviewItemReq {
  task_id: string;
  item_id: string;
  confirm_status: number;
  fields: ReviewFieldItem[];
  final_content?: string;
}

// ── 明细+用例 ──

export interface TaskItemWithCase {
  item: TaskItemVO;
  case: CaseVO | null;
}

// ── 审核工作台 ──

export interface PendingSuiteNode {
  id: string | number;
  label: string;
  name: string;
  project_id?: string | number;
  parent_id?: string | number;
  sort_order: number;
  case_count: number;
  pending_count: number;
  children: PendingSuiteNode[];
  cases: PendingCaseVO[];
}

export interface PendingCaseVO {
  id: string | number;
  external_id?: string;
  name: string;
  importance: number;
}

export interface FieldSuggestionVO {
  field_name: string;
  original: any;
  suggested: any;
  has_suggestion: boolean;
  conclusion: string;      // pass / fail
  rule_violated: string;   // 违反的规范说明
}

export interface CaseReviewDetailVO {
  case: CaseVO | null;
  task_item_id?: string;
  task_id?: string;
  score?: number;
  issues: string[];
  suggestions: FieldSuggestionVO[];
  overall_assessment: string;
}

export interface CaseFieldReviewItem {
  field_name: string;
  action: string; // accept / ignore / edit_accept
  edited_value?: any;
}

export interface CaseReviewReq {
  case_id: string;
  task_item_id: string;
  fields: CaseFieldReviewItem[];
}
