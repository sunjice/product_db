import request from "@/utils/request";
import type {
  ProjectForm, ProjectItem, ProjectQueryParams,
  SuiteNode,
  CaseCoreMark, CaseForm, CaseQueryParams, CaseVO,
  CaseSampleMark,
  ImportResult,
  SampleForm, SampleItem, SampleQueryParams,
  AiConfigForm, AiConfigItem, AiConfigQueryParams,
  ScriptForm, ScriptItem, ScriptQueryParams,
  TaskCreateForm, TaskQueryParams, TaskVO, TaskItemVO, TaskConfirmReq, TaskDetail,
  ReviewRecordVO, ReviewItemReq, TaskItemWithCase,
  PendingSuiteNode, PendingCaseVO, CaseReviewDetailVO,   CaseReviewReq,
  SpecForm, SpecItem, SpecQueryParams,
} from "./types";
import type { OptionItem, PageResult } from "@/api/common";

// ── 项目 ──

export const ProjectAPI = {
  getPage(params: ProjectQueryParams) {
    return request<unknown, PageResult<ProjectItem>>({
      url: "/api/v1/aitc/projects", method: "get", params,
    });
  },
  getOptions() {
    return request<unknown, OptionItem[]>({
      url: "/api/v1/aitc/projects/options", method: "get",
    });
  },
  getById(id: string) {
    return request<unknown, ProjectItem>({
      url: `/api/v1/aitc/projects/${id}`, method: "get",
    });
  },
  create(data: ProjectForm) {
    return request({ url: "/api/v1/aitc/projects", method: "post", data });
  },
  update(id: string, data: ProjectForm) {
    return request({ url: `/api/v1/aitc/projects/${id}`, method: "put", data });
  },
  delete(ids: string) {
    return request({ url: `/api/v1/aitc/projects/${ids}`, method: "delete" });
  },
};

// ── 套件树 ──

export const SuiteAPI = {
  getTree(projectId: string) {
    return request<unknown, SuiteNode[]>({
      url: "/api/v1/aitc/suites/tree", method: "get", params: { projectId },
    });
  },
  /** 懒加载套件子节点（子套件 + 用例），suiteId=0 获取根级套件 */
  getChildren(suiteId: string | number, projectId?: string) {
    return request<unknown, SuiteNode[]>({
      url: `/api/v1/aitc/suites/${suiteId}/children`,
      method: "get",
      params: projectId !== undefined ? { projectId } : {},
    });
  },
};

// ── 用例 ──

export const CaseAPI = {
  getPage(params: CaseQueryParams) {
    return request<unknown, PageResult<CaseVO>>({
      url: "/api/v1/aitc/cases", method: "get", params,
    });
  },
  getById(id: string) {
    return request<unknown, CaseVO>({
      url: `/api/v1/aitc/cases/${id}`, method: "get",
    });
  },
  update(id: string, data: CaseForm) {
    return request({ url: `/api/v1/aitc/cases/${id}`, method: "put", data });
  },
  markCore(data: CaseCoreMark) {
    return request({ url: "/api/v1/aitc/cases/core", method: "patch", data });
  },
  markSample(data: CaseSampleMark) {
    return request({ url: "/api/v1/aitc/cases/sample", method: "patch", data });
  },
  delete(ids: string) {
    return request({ url: `/api/v1/aitc/cases/${ids}`, method: "delete" });
  },
  downloadTemplate() {
    return request({
      url: "/api/v1/aitc/cases/import/template",
      method: "get",
      responseType: "blob",
    });
  },
  importExcel(projectId: string, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return request<unknown, ImportResult>({
      url: "/api/v1/aitc/cases/import",
      method: "post",
      data: formData,
      params: { projectId },
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

// ── 样本库 ──

export const SampleAPI = {
  getPage(params: SampleQueryParams) {
    return request<unknown, PageResult<SampleItem>>({
      url: "/api/v1/aitc/samples", method: "get", params,
    });
  },
  create(data: SampleForm) {
    return request({ url: "/api/v1/aitc/samples", method: "post", data });
  },
  update(id: string, data: SampleForm) {
    return request({ url: `/api/v1/aitc/samples/${id}`, method: "put", data });
  },
  delete(ids: string) {
    return request({ url: `/api/v1/aitc/samples/${ids}`, method: "delete" });
  },
};

// ── AI 配置 ──

export const AiConfigAPI = {
  getPage(params: AiConfigQueryParams) {
    return request<unknown, PageResult<AiConfigItem>>({
      url: "/api/v1/aitc/aiconfigs", method: "get", params,
    });
  },
  getOptions(scene?: string) {
    return request<unknown, OptionItem[]>({
      url: "/api/v1/aitc/aiconfigs/options", method: "get", params: { scene },
    });
  },
  create(data: AiConfigForm) {
    return request({ url: "/api/v1/aitc/aiconfigs", method: "post", data });
  },
  update(id: string, data: AiConfigForm) {
    return request({ url: `/api/v1/aitc/aiconfigs/${id}`, method: "put", data });
  },
  delete(ids: string) {
    return request({ url: `/api/v1/aitc/aiconfigs/${ids}`, method: "delete" });
  },
};

// ── 脚本库 ──

export const ScriptAPI = {
  getPage(params: ScriptQueryParams) {
    return request<unknown, PageResult<ScriptItem>>({
      url: "/api/v1/aitc/scripts", method: "get", params,
    });
  },
  update(id: string, data: ScriptForm) {
    return request({ url: `/api/v1/aitc/scripts/${id}`, method: "put", data });
  },
  publish(id: string) {
    return request({ url: `/api/v1/aitc/scripts/${id}/publish`, method: "post" });
  },
  delete(ids: string) {
    return request({ url: `/api/v1/aitc/scripts/${ids}`, method: "delete" });
  },
};

// ── AI 任务 ──

export const TaskAPI = {
  create(data: TaskCreateForm) {
    return request<unknown, TaskVO>({
      url: "/api/v1/aitc/tasks", method: "post", data,
    });
  },
  getPage(params: TaskQueryParams) {
    return request<unknown, PageResult<TaskVO>>({
      url: "/api/v1/aitc/tasks", method: "get", params,
    });
  },
  getDetail(taskId: string) {
    return request<unknown, TaskDetail>({
      url: `/api/v1/aitc/tasks/${taskId}`, method: "get",
    });
  },
  getItems(taskId: string) {
    return request<unknown, TaskItemVO[]>({
      url: `/api/v1/aitc/tasks/${taskId}/items`, method: "get",
    });
  },
  getItemWithCase(taskId: string, itemId: string) {
    return request<unknown, TaskItemWithCase>({
      url: `/api/v1/aitc/tasks/${taskId}/items/${itemId}`, method: "get",
    });
  },
  reviewItem(taskId: string, itemId: string, data: ReviewItemReq) {
    return request({
      url: `/api/v1/aitc/tasks/${taskId}/items/${itemId}/review`, method: "post", data,
    });
  },
  getReviewRecords(taskId: string) {
    return request<unknown, ReviewRecordVO[]>({
      url: `/api/v1/aitc/tasks/${taskId}/review-records`, method: "get",
    });
  },
  rerun(taskId: string) {
    return request({
      url: `/api/v1/aitc/tasks/${taskId}/rerun`, method: "post",
    });
  },
  confirm(taskId: string, data: TaskConfirmReq) {
    return request({
      url: `/api/v1/aitc/tasks/${taskId}/confirm`, method: "post", data,
    });
  },
};

// ── 审核工作台 ──

export const ReviewAPI = {
  getPendingTree(projectId: string) {
    return request<unknown, PendingSuiteNode[]>({
      url: "/api/v1/aitc/cases/pending-tree", method: "get", params: { projectId },
    });
  },
  getPendingList(suiteId: string) {
    return request<unknown, PendingCaseVO[]>({
      url: "/api/v1/aitc/cases/pending-list", method: "get", params: { suiteId },
    });
  },
  getReviewDetail(caseId: string) {
    return request<unknown, CaseReviewDetailVO>({
      url: `/api/v1/aitc/cases/${caseId}/review-detail`, method: "get",
    });
  },
  submitReview(caseId: string, data: CaseReviewReq) {
    return request({
      url: `/api/v1/aitc/cases/${caseId}/review`, method: "post", data,
    });
  },
};

// ── 规范管理 ──

export const SpecAPI = {
  getPage(params: SpecQueryParams) {
    return request<unknown, PageResult<SpecItem>>({
      url: "/api/v1/aitc/specs", method: "get", params,
    });
  },
  getOptions(projectId?: string, taskType?: string, specType?: string) {
    return request<unknown, OptionItem[]>({
      url: "/api/v1/aitc/specs/options", method: "get",
      params: { projectId, taskType, specType },
    });
  },
  getById(id: string) {
    return request<unknown, SpecItem>({
      url: `/api/v1/aitc/specs/${id}`, method: "get",
    });
  },
  create(data: SpecForm) {
    return request({ url: "/api/v1/aitc/specs", method: "post", data });
  },
  update(id: string, data: SpecForm) {
    return request({ url: `/api/v1/aitc/specs/${id}`, method: "put", data });
  },
  delete(ids: string) {
    return request({ url: `/api/v1/aitc/specs/${ids}`, method: "delete" });
  },
};
