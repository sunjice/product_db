import request from "@/utils/request";
import type { SpecForm, SpecItem, SpecQueryParams } from "./types";
import type { OptionItem, PageResult } from "@/api/common";

const SPEC_BASE_URL = "/api/v1/aitc/specs";

const SpecAPI = {
  getPage(params: SpecQueryParams) {
    return request<unknown, PageResult<SpecItem>>({
      url: `${SPEC_BASE_URL}`,
      method: "get",
      params,
    });
  },

  getOptions(projectId?: string, taskType?: string, specType?: string) {
    return request<unknown, OptionItem[]>({
      url: `${SPEC_BASE_URL}/options`,
      method: "get",
      params: { projectId, taskType, specType },
    });
  },

  getById(id: string) {
    return request<unknown, SpecItem>({
      url: `${SPEC_BASE_URL}/${id}`,
      method: "get",
    });
  },

  create(data: SpecForm) {
    return request({
      url: `${SPEC_BASE_URL}`,
      method: "post",
      data,
    });
  },

  update(id: string, data: SpecForm) {
    return request({
      url: `${SPEC_BASE_URL}/${id}`,
      method: "put",
      data,
    });
  },

  delete(ids: string) {
    return request({
      url: `${SPEC_BASE_URL}/${ids}`,
      method: "delete",
    });
  },
};

export default SpecAPI;

export * from "./types";
