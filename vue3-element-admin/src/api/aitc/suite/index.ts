import request from "@/utils/request";
import type { SuiteNode } from "./types";

const SUITE_BASE_URL = "/api/v1/aitc/suites";

const SuiteAPI = {
  getTree(projectId: string) {
    return request<unknown, SuiteNode[]>({
      url: `${SUITE_BASE_URL}/tree`,
      method: "get",
      params: { projectId },
    });
  },

  /** 懒加载套件子节点（子套件 + 用例），suiteId=0 获取根级套件 */
  getChildren(suiteId: string | number, projectId?: string) {
    return request<unknown, SuiteNode[]>({
      url: `${SUITE_BASE_URL}/${suiteId}/children`,
      method: "get",
      params: projectId !== undefined ? { projectId } : {},
    });
  },
};

export default SuiteAPI;

export * from "./types";
