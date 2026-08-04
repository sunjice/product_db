import request from "@/utils/request";
import type { ProjectForm, ProjectItem, ProjectQueryParams } from "./types";
import type { OptionItem, PageResult } from "@/api/common";

const PROJECT_BASE_URL = "/api/v1/aitc/projects";

const ProjectAPI = {
  getPage(params: ProjectQueryParams) {
    return request<unknown, PageResult<ProjectItem>>({
      url: `${PROJECT_BASE_URL}`,
      method: "get",
      params,
    });
  },

  getOptions() {
    return request<unknown, OptionItem[]>({
      url: `${PROJECT_BASE_URL}/options`,
      method: "get",
    });
  },

  getById(id: string) {
    return request<unknown, ProjectItem>({
      url: `${PROJECT_BASE_URL}/${id}`,
      method: "get",
    });
  },

  create(data: ProjectForm) {
    return request({
      url: `${PROJECT_BASE_URL}`,
      method: "post",
      data,
    });
  },

  update(id: string, data: ProjectForm) {
    return request({
      url: `${PROJECT_BASE_URL}/${id}`,
      method: "put",
      data,
    });
  },

  delete(ids: string) {
    return request({
      url: `${PROJECT_BASE_URL}/${ids}`,
      method: "delete",
    });
  },
};

export default ProjectAPI;

export * from "./types";
