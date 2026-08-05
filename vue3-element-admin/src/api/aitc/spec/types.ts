/**
 * 规范管理类型定义
 */

import type { BaseQueryParams } from "@/api/common";

export interface SpecQueryParams extends BaseQueryParams {
  projectId?: string;
  suiteId?: string;
  taskType?: string;
  specType?: string;
  keywords?: string;
}

export interface SpecItem {
  id: number;
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
