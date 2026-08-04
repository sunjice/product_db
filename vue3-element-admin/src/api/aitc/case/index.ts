import request from "@/utils/request";
import type {
  CaseCoreMark,
  CaseForm,
  CaseQueryParams,
  CaseVO,
  CaseSampleMark,
  ImportResult,
} from "./types";
import type { PageResult } from "@/api/common";

const CASE_BASE_URL = "/api/v1/aitc/cases";

const CaseAPI = {
  getPage(params: CaseQueryParams) {
    return request<unknown, PageResult<CaseVO>>({
      url: `${CASE_BASE_URL}`,
      method: "get",
      params,
    });
  },

  getById(id: string) {
    return request<unknown, CaseVO>({
      url: `${CASE_BASE_URL}/${id}`,
      method: "get",
    });
  },

  update(id: string, data: CaseForm) {
    return request({
      url: `${CASE_BASE_URL}/${id}`,
      method: "put",
      data,
    });
  },

  markCore(data: CaseCoreMark) {
    return request({
      url: `${CASE_BASE_URL}/core`,
      method: "patch",
      data,
    });
  },

  markSample(data: CaseSampleMark) {
    return request({
      url: `${CASE_BASE_URL}/sample`,
      method: "patch",
      data,
    });
  },

  delete(ids: string) {
    return request({
      url: `${CASE_BASE_URL}/${ids}`,
      method: "delete",
    });
  },

  downloadTemplate() {
    return request({
      url: `${CASE_BASE_URL}/import/template`,
      method: "get",
      responseType: "blob",
    });
  },

  importExcel(projectId: string, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return request<unknown, ImportResult>({
      url: `${CASE_BASE_URL}/import`,
      method: "post",
      data: formData,
      params: { projectId },
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

export default CaseAPI;

export * from "./types";
