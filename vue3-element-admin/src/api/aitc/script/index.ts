import request from "@/utils/request";
import type { ScriptForm, ScriptItem, ScriptQueryParams } from "./types";
import type { PageResult } from "@/api/common";

const SCRIPT_BASE_URL = "/api/v1/aitc/scripts";

const ScriptAPI = {
  getPage(params: ScriptQueryParams) {
    return request<unknown, PageResult<ScriptItem>>({
      url: `${SCRIPT_BASE_URL}`,
      method: "get",
      params,
    });
  },

  update(id: string, data: ScriptForm) {
    return request({
      url: `${SCRIPT_BASE_URL}/${id}`,
      method: "put",
      data,
    });
  },

  publish(id: string) {
    return request({
      url: `${SCRIPT_BASE_URL}/${id}/publish`,
      method: "post",
    });
  },

  delete(ids: string) {
    return request({
      url: `${SCRIPT_BASE_URL}/${ids}`,
      method: "delete",
    });
  },
};

export default ScriptAPI;

export * from "./types";
