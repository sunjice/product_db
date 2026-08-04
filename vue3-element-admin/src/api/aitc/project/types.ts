/**
 * 项目类型定义
 */

import type { BaseQueryParams } from "@/api/common";

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
