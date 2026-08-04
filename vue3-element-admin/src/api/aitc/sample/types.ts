/**
 * 样本库类型定义
 */

import type { BaseQueryParams } from "@/api/common";

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
