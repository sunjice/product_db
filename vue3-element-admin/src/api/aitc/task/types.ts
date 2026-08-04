/**
 * AI 任务 & 审核 类型定义
 */

import type { BaseQueryParams } from "@/api/common";
import type { CaseVO } from "../case/types";

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

// ── 明细+用例 ──

export interface TaskItemWithCase {
  item: TaskItemVO;
  case: CaseVO | null;
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
