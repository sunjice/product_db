import request from "@/utils/request";
import type { SampleForm, SampleItem, SampleQueryParams } from "./types";
import type { PageResult } from "@/api/common";

const SAMPLE_BASE_URL = "/api/v1/aitc/samples";

const SampleAPI = {
  getPage(params: SampleQueryParams) {
    return request<unknown, PageResult<SampleItem>>({
      url: `${SAMPLE_BASE_URL}`,
      method: "get",
      params,
    });
  },

  create(data: SampleForm) {
    return request({
      url: `${SAMPLE_BASE_URL}`,
      method: "post",
      data,
    });
  },

  update(id: string, data: SampleForm) {
    return request({
      url: `${SAMPLE_BASE_URL}/${id}`,
      method: "put",
      data,
    });
  },

  delete(ids: string) {
    return request({
      url: `${SAMPLE_BASE_URL}/${ids}`,
      method: "delete",
    });
  },
};

export default SampleAPI;

export * from "./types";
