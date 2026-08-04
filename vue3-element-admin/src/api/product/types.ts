/**
 * 产品数据库 - TypeScript 类型定义
 */

import type { BaseQueryParams } from "@/api/common";

// ── 分类 ──

export interface CategoryQueryParams extends BaseQueryParams {
  keywords?: string;
}

export interface CategoryItem {
  id: string;
  name: string;
  slug: string;
  sort_order: number;
  create_time?: string;
  update_time?: string;
}

export interface CategoryForm {
  id?: string;
  name: string;
  slug: string;
  sort_order: number;
}

// ── 品牌 ──

export interface BrandQueryParams extends BaseQueryParams {
  keywords?: string;
}

export interface BrandItem {
  id: string;
  name: string;
  logo_url?: string;
  sort_order: number;
  create_time?: string;
  update_time?: string;
}

export interface BrandForm {
  id?: string;
  name: string;
  logo_url?: string;
  sort_order: number;
}

// ── 规格分组 ──

export interface SpecGroupQueryParams extends BaseQueryParams {
  category_id?: string;
  keywords?: string;
}

export interface SpecGroupItem {
  id: string;
  category_id: string;
  category_name?: string;
  name: string;
  sort_order: number;
  create_time?: string;
  update_time?: string;
}

export interface SpecGroupForm {
  id?: string;
  category_id: string;
  name: string;
  sort_order: number;
}

// ── 规格项 ──

export interface SpecItem {
  id?: string;
  group_id: string | number;
  group_name?: string;
  spec_name: string;
  spec_value?: string;
  spec_unit?: string;
  sort_order: number;
}

// ── 产品 ──

export interface ProductQueryParams extends BaseQueryParams {
  categoryId?: string;
  brandId?: string;
  keywords?: string;
  status?: number;
}

export interface SpecGroupVO {
  group_id: string | number;
  group_name: string;
  sort_order: number;
  items: SpecItem[];
}

export interface ProductVO {
  id: string;
  category_id: string;
  category_name?: string;
  brand_id: string;
  brand_name?: string;
  name: string;
  model?: string;
  description?: string;
  image_urls: string[];
  status: number;
  sort_order: number;
  groups: SpecGroupVO[];
  create_time?: string;
  update_time?: string;
}

export interface ProductForm {
  id?: string;
  category_id: string;
  brand_id: string;
  name: string;
  model?: string;
  description?: string;
  image_urls: string[];
  status: number;
  sort_order: number;
  specifications: SpecItem[];
}

export interface ProductCompareVO {
  products: ProductVO[];
  common_groups: string[];
}
