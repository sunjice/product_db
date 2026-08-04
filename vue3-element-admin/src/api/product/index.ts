import request from "@/utils/request";
import type {
  BrandForm, BrandItem, BrandQueryParams,
  CategoryForm, CategoryItem, CategoryQueryParams,
  ProductCompareVO, ProductForm, ProductQueryParams, ProductVO,
  SpecGroupForm, SpecGroupItem, SpecGroupQueryParams,
} from "./types";
import type { OptionItem, PageResult } from "@/api/common";

// ── 分类 ──

export const CategoryAPI = {
  getPage(params: CategoryQueryParams) {
    return request<unknown, PageResult<CategoryItem>>({
      url: "/api/v1/categories", method: "get", params,
    });
  },
  getOptions() {
    return request<unknown, OptionItem[]>({
      url: "/api/v1/categories/options", method: "get",
    });
  },
  getById(id: string) {
    return request<unknown, CategoryItem>({
      url: `/api/v1/categories/${id}`, method: "get",
    });
  },
  create(data: CategoryForm) {
    return request({ url: "/api/v1/categories", method: "post", data });
  },
  update(id: string, data: CategoryForm) {
    return request({ url: `/api/v1/categories/${id}`, method: "put", data });
  },
  delete(ids: string) {
    return request({ url: `/api/v1/categories/${ids}`, method: "delete" });
  },
};

// ── 品牌 ──

export const BrandAPI = {
  getPage(params: BrandQueryParams) {
    return request<unknown, PageResult<BrandItem>>({
      url: "/api/v1/brands", method: "get", params,
    });
  },
  getOptions() {
    return request<unknown, OptionItem[]>({
      url: "/api/v1/brands/options", method: "get",
    });
  },
  getById(id: string) {
    return request<unknown, BrandItem>({
      url: `/api/v1/brands/${id}`, method: "get",
    });
  },
  create(data: BrandForm) {
    return request({ url: "/api/v1/brands", method: "post", data });
  },
  update(id: string, data: BrandForm) {
    return request({ url: `/api/v1/brands/${id}`, method: "put", data });
  },
  delete(ids: string) {
    return request({ url: `/api/v1/brands/${ids}`, method: "delete" });
  },
};

// ── 规格分组 ──

export const SpecGroupAPI = {
  getPage(params: SpecGroupQueryParams) {
    return request<unknown, PageResult<SpecGroupItem>>({
      url: "/api/v1/specgroups", method: "get", params,
    });
  },
  getOptions(categoryId?: string) {
    return request<unknown, OptionItem[]>({
      url: "/api/v1/specgroups/options", method: "get", params: { category_id: categoryId },
    });
  },
  create(data: SpecGroupForm) {
    return request({ url: "/api/v1/specgroups", method: "post", data });
  },
  update(id: string, data: SpecGroupForm) {
    return request({ url: `/api/v1/specgroups/${id}`, method: "put", data });
  },
  delete(ids: string) {
    return request({ url: `/api/v1/specgroups/${ids}`, method: "delete" });
  },
};

// ── 产品 ──

export const ProductAPI = {
  getPage(params: ProductQueryParams) {
    return request<unknown, PageResult<ProductVO>>({
      url: "/api/v1/products", method: "get", params,
    });
  },
  getById(id: string) {
    return request<unknown, ProductVO>({
      url: `/api/v1/products/${id}`, method: "get",
    });
  },
  create(data: ProductForm) {
    return request({ url: "/api/v1/products", method: "post", data });
  },
  update(id: string, data: ProductForm) {
    return request({ url: `/api/v1/products/${id}`, method: "put", data });
  },
  delete(ids: string) {
    return request({ url: `/api/v1/products/${ids}`, method: "delete" });
  },
  compare(ids: string) {
    return request<unknown, ProductCompareVO>({
      url: "/api/v1/products/compare", method: "get", params: { ids },
    });
  },
};
