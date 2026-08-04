/**
 * 套件类型定义
 */

export interface SuiteNode {
  id: string | number;
  label: string;
  name: string;
  project_id: string | number;
  project_prefix?: string;
  parent_id: string | number;
  sort_order: number;
  case_count: number;
  node_type: string;   // "suite" | "case"
  external_id?: string; // 用例编号（仅 node_type="case" 时有值）
  children: SuiteNode[];
}
