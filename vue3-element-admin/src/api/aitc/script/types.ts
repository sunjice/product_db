/**
 * 脚本库类型定义
 */

import type { BaseQueryParams } from "@/api/common";

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
