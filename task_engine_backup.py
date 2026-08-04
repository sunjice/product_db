"""任务引擎 — 创建任务、后台执行、进度追踪、结果入库。"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.exceptions import BusinessException
from app.pagination import PageResult
from app.response import ResultCode
from app.system.aitc.ai_client import AiClient
from app.system.aitc.service import AiTcService
from app.system.aitc.constants import (
    BatchSizeMap, ConfirmStatus, CoreSource, ItemStatus,
    ScriptSource, ScriptStatus, TaskStatus, TaskType,
)
from app.system.aitc.models import (
    AiTcAiConfig, AiTcCase, AiTcProject, AiTcSample, AiTcSpec,
    AiTcSuite, AiTcTask, AiTcTaskItem, AiTcScript, AiTcReviewRecord,
)

# 提示词模板文件目录
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
from app.system.aitc.schemas import (
    TaskCreate, TaskQuery, TaskVO, TaskItemVO, TaskConfirmReq, ScriptVO,
    ReviewItemReq, ReviewRecordVO, TaskItemWithCaseVO, CaseVO, CaseStep,
)


class TaskEngine:
    """AI 任务执行引擎。

    创建任务后通过 asyncio.create_task 在后台异步执行，
    前端可通过查询任务状态获取进度。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ═══════════════ 创建任务 ═══════════════

    async def create_task(self, form: TaskCreate, create_by: str = "") -> TaskVO:
        """创建 AI 任务，验证参数，写入 DB，启动后台执行。"""
        # 验证项目
        proj = await self.db.execute(
            text("SELECT 1 FROM ai_tc_projects WHERE id = :pid AND is_deleted = 0"),
            {"pid": form.project_id},
        )
        if proj.scalar() is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="项目不存在")

        # 确定用例范围
        if form.case_ids:
            case_ids = form.case_ids
        else:
            case_ids = await self._get_subtree_case_ids(form.suite_id)

        if not case_ids:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="套件下无用例")

        # 加载 AI 配置
        ai_config = await self._resolve_ai_config(form.ai_config_id, form.task_type)

        # 加载提示词（从 prompts/ 目录下的模板文件加载）
        prompt_content = self._load_prompt_from_file(form.task_type)

        # 加载样本
        samples_text = ""
        if form.sample_ids:
            samples_text = await self._load_samples(form.sample_ids)

        # 加载规范（显式指定优先，否则按场景自动解析）
        spec_ids, specs_text = await AiTcService(self.db).resolve_specs_text(
            form.task_type, form.project_id, form.suite_id
        )
        if form.spec_ids:
            spec_ids = form.spec_ids
            specs_text = await self._load_specs(form.spec_ids)

        # 创建任务记录
        task = AiTcTask(
            task_type=form.task_type,
            project_id=form.project_id,
            suite_id=form.suite_id,
            sample_ids=form.sample_ids if form.sample_ids else None,
            spec_ids=spec_ids if spec_ids else None,
            ai_config_id=ai_config.id if ai_config else None,
            model=ai_config.model if ai_config else None,
            status=TaskStatus.QUEUED,
            total_count=len(case_ids),
            done_count=0,
            create_by=create_by,
        )
        self.db.add(task)
        await self.db.flush()

        # 批量创建任务明细
        cases = await self._load_cases_brief(case_ids)
        for case in cases:
            item = AiTcTaskItem(
                task_id=task.id,
                case_id=case["id"],
                case_name=case["name"],
                item_status=ItemStatus.PENDING,
                confirm_status=ConfirmStatus.PENDING,
            )
            self.db.add(item)
        await self.db.flush()

        # 提交事务，确保后台任务能读取到刚创建的数据
        await self.db.commit()

        logger.info(
            f"Task created: id={task.id} type={form.task_type} "
            f"cases={len(cases)} ai_config={ai_config.model if ai_config else 'default'}"
        )

        # 启动后台执行（在 commit 之后，保证后台独立会话能看到任务数据）
        asyncio.create_task(self._execute_task(task.id, form.task_type, prompt_content, samples_text, specs_text, ai_config))

        return self._task_to_vo(task)

    # ═══════════════ 重新执行 ═══════════════

    async def rerun_task(self, task_id: int) -> None:
        """重置任务状态和明细结果，重新拉起后台执行。"""
        result = await self.db.execute(
            select(AiTcTask).where(AiTcTask.id == task_id, AiTcTask.is_deleted == 0)
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="任务不存在")

        if task.status == TaskStatus.RUNNING:
            raise BusinessException(code=ResultCode.PARAM_VALID_FAIL, msg="任务正在运行中，无法重跑")

        # 重置任务状态
        task.status = TaskStatus.QUEUED
        task.done_count = 0
        task.error_msg = None
        task.input_tokens = 0
        task.output_tokens = 0
        task.update_time = datetime.now()

        # 重置所有明细：清空结果，回到待处理
        await self.db.execute(
            text(
                "UPDATE ai_tc_task_items SET item_status = 0, confirm_status = 0, "
                "output = NULL, final_content = NULL, reviewed_by = NULL, review_time = NULL, "
                "update_time = NOW() "
                "WHERE task_id = :tid AND is_deleted = 0"
            ),
            {"tid": task_id},
        )
        await self.db.flush()

        # 重新加载执行所需的上下文（传 None 让引擎重新解析默认配置）
        ai_config = await self._resolve_ai_config(None, task.task_type)

        # 更新任务记录里的 ai_config_id 和 model（rerun 后可能换了配置）
        if ai_config:
            task.ai_config_id = ai_config.id
            task.model = ai_config.model
        else:
            task.ai_config_id = None
            task.model = None

        # 提示词直接从文件加载
        prompt_content = self._load_prompt_from_file(task.task_type)

        samples_text = ""
        if task.sample_ids:
            samples_text = await self._load_samples(task.sample_ids)

        # 加载规范（已记录则用已记录，否则按场景自动解析）
        specs_text = ""
        if task.spec_ids:
            specs_text = await self._load_specs(task.spec_ids)
        else:
            spec_ids, specs_text = await AiTcService(self.db).resolve_specs_text(
                task.task_type, task.project_id, task.suite_id
            )
            if spec_ids:
                task.spec_ids = spec_ids   # 回写留痕

        logger.info(f"Task {task_id} rerun triggered")

        # 重新拉起后台执行
        asyncio.create_task(
            self._execute_task(task_id, task.task_type, prompt_content, samples_text, specs_text, ai_config)
        )

    # ═══════════════ 后台执行 ═══════════════

    async def _execute_task(
        self,
        task_id: int,
        task_type: str,
        prompt_content: str,
        samples_text: str,
        specs_text: str,
        ai_config: Any,
    ):
        """后台协程：独立 DB session 执行 AI 调用。"""
        async with AsyncSessionLocal() as bg_db:
            try:
                # 标记运行中
                await bg_db.execute(
                    text("UPDATE ai_tc_tasks SET status = :s WHERE id = :id"),
                    {"s": TaskStatus.RUNNING, "id": task_id},
                )
                await bg_db.commit()

                # 加载 task_items
                items = (await bg_db.execute(
                    select(AiTcTaskItem).where(
                        AiTcTaskItem.task_id == task_id,
                        AiTcTaskItem.is_deleted == 0,
                    ).order_by(AiTcTaskItem.id)
                )).scalars().all()

                if not items:
                    await self._finish_task(bg_db, task_id, TaskStatus.FAILED, "任务明细为空")
                    return

                # 初始化 AI 客户端
                client = AiClient(ai_config)

                batch_size = {
                    TaskType.CORE_SELECT: BatchSizeMap.CORE_SELECT,
                    TaskType.CASE_REVIEW: BatchSizeMap.CASE_REVIEW,
                    TaskType.SCRIPT_GEN: BatchSizeMap.SCRIPT_GEN,
                }.get(task_type, 1)

                if task_type == TaskType.CORE_SELECT:
                    await self._exec_core_select(
                        bg_db, client, items, prompt_content, samples_text, specs_text, batch_size, task_id
                    )

                elif task_type == TaskType.CASE_REVIEW:
                    await self._exec_case_review(
                        bg_db, client, items, prompt_content, samples_text, specs_text, batch_size, task_id
                    )
                elif task_type == TaskType.SCRIPT_GEN:
                    await self._exec_script_gen(
                        bg_db, client, items, prompt_content, samples_text, specs_text, task_id
                    )

                total_tokens_in = client.input_tokens
                total_tokens_out = client.output_tokens

                # 更新 token 统计
                await bg_db.execute(
                    text(
                        "UPDATE ai_tc_tasks SET input_tokens = :i, output_tokens = :o WHERE id = :id"
                    ),
                    {"i": total_tokens_in, "o": total_tokens_out, "id": task_id},
                )
                await self._finish_task(bg_db, task_id, TaskStatus.COMPLETED)

            except Exception as e:
                logger.exception(f"Task {task_id} execution failed: {e}")
                try:
                    await self._finish_task(bg_db, task_id, TaskStatus.FAILED, str(e)[:500])
                except Exception:
                    pass

    # ── 核心用例挑选执行 ──

    async def _exec_core_select(
        self, db: AsyncSession, client: AiClient,
        items: list[AiTcTaskItem], prompt: str, samples: str, specs: str,
        batch_size: int, task_id: int,
    ) -> None:
        """批量挑选核心用例。"""
        done = 0

        for batch_start in range(0, len(items), batch_size):
            batch_items = items[batch_start: batch_start + batch_size]

            # 加载本批用例详情
            case_ids_batch = [it.case_id for it in batch_items]
            cases = (await db.execute(
                select(AiTcCase).where(AiTcCase.id.in_(case_ids_batch))
            )).scalars().all()
            case_map = {c.id: c for c in cases}

            cases_data = []
            for it in batch_items:
                c = case_map.get(it.case_id)
                if c:
                    cases_data.append({
                        "name": c.name or "",
                        "summary": c.summary or "",
                        "importance": c.importance or 2,
                    })
                else:
                    cases_data.append({"name": it.case_name, "summary": "", "importance": 2})

            try:
                results = await client.core_select(cases_data, prompt, samples, specs)
                for i, it in enumerate(batch_items):
                    r = results[i] if i < len(results) else {"selected": False, "reason": ""}
                    it.output = r
                    it.item_status = ItemStatus.SUCCESS
                    done += 1
            except Exception as e:
                logger.error(f"Core select batch failed at offset {batch_start}: {e}")
                for it in batch_items:
                    it.item_status = ItemStatus.FAILED
                    it.output = {"error": str(e)[:500]}

            # 刷新到 DB
            await db.execute(
                text("UPDATE ai_tc_tasks SET done_count = :d WHERE id = :id"),
                {"d": done, "id": task_id},
            )
            await db.commit()

    # ── 用例审核执行 ──

    async def _exec_case_review(
        self, db: AsyncSession, client: AiClient,
        items: list[AiTcTaskItem], prompt: str, samples: str, specs: str,
        batch_size: int, task_id: int,
    ) -> None:
        """逐条审核用例。"""
        done = 0

        # 加载全部用例详情
        case_ids = [it.case_id for it in items]
        cases = (await db.execute(
            select(AiTcCase).where(AiTcCase.id.in_(case_ids))
        )).scalars().all()
        case_map: dict[int, AiTcCase] = {c.id: c for c in cases}

        for it in items:
            c = case_map.get(it.case_id)
            if not c:
                it.item_status = ItemStatus.FAILED
                it.output = {"error": "用例不存在"}
                continue

            case_detail = {
                "name": c.name or "",
                "summary": c.summary or "",
                "preconditions": c.preconditions or "",
                "test_data": c.test_data or "",
                "steps": c.steps or [],
                "importance": c.importance or 2,
            }

            try:
                result = await client.case_review(case_detail, prompt, samples, specs)
                it.output = result
                it.item_status = ItemStatus.SUCCESS
            except Exception as e:
                logger.error(f"Case review failed for case {c.id}: {e}")
                it.output = {"error": str(e)[:500]}
                it.item_status = ItemStatus.FAILED

            done += 1
            await db.execute(
                text("UPDATE ai_tc_tasks SET done_count = :d WHERE id = :id"),
                {"d": done, "id": task_id},
            )
            await db.commit()

    # ── 脚本生成执行 ──

    async def _exec_script_gen(
        self, db: AsyncSession, client: AiClient,
        items: list[AiTcTaskItem], prompt: str, samples: str, specs: str,
        task_id: int,
    ) -> None:
        """逐条生成测试脚本。"""
        done = 0

        case_ids = [it.case_id for it in items]
        cases = (await db.execute(
            select(AiTcCase).where(AiTcCase.id.in_(case_ids))
        )).scalars().all()
        case_map: dict[int, AiTcCase] = {c.id: c for c in cases}

        for it in items:
            c = case_map.get(it.case_id)
            if not c:
                it.item_status = ItemStatus.FAILED
                it.output = {"error": "用例不存在"}
                continue

            case_detail = {
                "name": c.name or "",
                "summary": c.summary or "",
                "preconditions": c.preconditions or "",
                "test_data": c.test_data or "",
                "steps": c.steps or [],
                "importance": c.importance or 2,
            }

            try:
                result = await client.script_gen(case_detail, prompt, samples)
                it.output = result
                it.item_status = ItemStatus.SUCCESS
            except Exception as e:
                logger.error(f"Script gen failed for case {c.id}: {e}")
                it.output = {"error": str(e)[:500]}
                it.item_status = ItemStatus.FAILED

            done += 1
            await db.execute(
                text("UPDATE ai_tc_tasks SET done_count = :d WHERE id = :id"),
                {"d": done, "id": task_id},
            )
            await db.commit()

        await db.execute(
            text("UPDATE ai_tc_tasks SET done_count = :d WHERE id = :id"),
            {"d": done, "id": task_id},
        )
        await db.commit()

    async def _finish_task(self, db: AsyncSession, task_id: int, status: int, error_msg: str = ""):
        await db.execute(
            text(
                "UPDATE ai_tc_tasks SET status = :s, error_msg = :e, update_time = NOW() WHERE id = :id"
            ),
            {"s": status, "e": error_msg, "id": task_id},
        )
        await db.commit()
        logger.info(f"Task {task_id} finished with status={status}")

    # ═══════════════ 任务查询 ═══════════════

    async def get_task_page(self, query: TaskQuery) -> PageResult:
        conditions = [AiTcTask.is_deleted == 0]
        if query.projectId is not None:
            conditions.append(AiTcTask.project_id == query.projectId)
        if query.taskType:
            conditions.append(AiTcTask.task_type == query.taskType)
        if query.status is not None:
            conditions.append(AiTcTask.status == query.status)

        stmt = select(AiTcTask).where(*conditions).order_by(AiTcTask.id.desc())
        count_q = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        offset = (query.pageNum - 1) * query.pageSize
        rows = await self.db.execute(stmt.offset(offset).limit(query.pageSize))
        items = rows.scalars().all()

        # 批量取项目名
        pids = list({t.project_id for t in items})
        pname_map: dict[int, str] = {}
        if pids:
            prows = await self.db.execute(
                select(AiTcProject.id, AiTcProject.name).where(AiTcProject.id.in_(pids))
            )
            pname_map = {r.id: r.name for r in prows}

        # 批量取套件名（全路径）
        sids = list({t.suite_id for t in items})
        sname_map: dict[int, str] = {}
        if sids:
            for sid in sids:
                sname_map[sid] = await self._get_suite_full_path(sid)

        return PageResult(
            records=[
                self._task_to_vo(t, pname_map.get(t.project_id), sname_map.get(t.suite_id))
                for t in items
            ],
            total=total, pageNum=query.pageNum, pageSize=query.pageSize,
        )

    async def get_task_detail(self, task_id: int) -> dict:
        """获取任务详情 + 明细列表。"""
        result = await self.db.execute(
            select(AiTcTask).where(AiTcTask.id == task_id, AiTcTask.is_deleted == 0)
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="任务不存在")

        pname = ""
        sname = ""
        proj = await self.db.get(AiTcProject, task.project_id)
        if proj:
            pname = proj.name
        sname = await self._get_suite_full_path(task.suite_id)

        task_vo = self._task_to_vo(task, pname, sname)

        # 明细列表
        items = (await self.db.execute(
            select(AiTcTaskItem).where(
                AiTcTaskItem.task_id == task_id,
                AiTcTaskItem.is_deleted == 0,
            ).order_by(AiTcTaskItem.id)
        )).scalars().all()

        item_vos = [self._task_item_to_vo(it) for it in items]

        return {"task": task_vo, "items": item_vos}

    async def get_task_items(self, task_id: int) -> list[TaskItemVO]:
        items = (await self.db.execute(
            select(AiTcTaskItem).where(
                AiTcTaskItem.task_id == task_id,
                AiTcTaskItem.is_deleted == 0,
            ).order_by(AiTcTaskItem.id)
        )).scalars().all()
        return [self._task_item_to_vo(it) for it in items]

    # ═══════════════ 确认任务结果 ═══════════════

    async def confirm_task_items(
        self, task_id: int, form: TaskConfirmReq, reviewed_by: str = "", reviewer_ip: str = ""
    ) -> None:
        """确认 AI 任务结果：
        - 采纳(1) / 编辑采纳(3)：将结果写入用例
        - 忽略(2)：仅标记状态
        """
        task = await self.db.get(AiTcTask, task_id)
        if task is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="任务不存在")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        action_map = {
            ConfirmStatus.ACCEPTED: "accept",
            ConfirmStatus.IGNORED: "ignore",
            ConfirmStatus.EDITED_ACCEPTED: "edit_accept",
        }

        for ci in form.items:
            item = await self.db.get(AiTcTaskItem, ci.item_id)
            if item is None or item.task_id != task_id:
                continue

            # 获取修改前的用例内容（用于审计记录）
            before_snapshot = await self._get_case_snapshot(item.case_id)

            item.confirm_status = ci.confirm_status
            item.reviewed_by = reviewed_by
            item.review_time = now

            if ci.confirm_status == ConfirmStatus.EDITED_ACCEPTED and ci.final_content:
                item.final_content = ci.final_content

            # 根据任务类型写入目标
            if ci.confirm_status in (ConfirmStatus.ACCEPTED, ConfirmStatus.EDITED_ACCEPTED):
                await self._apply_result(task.task_type, item, ci)

            # 获取修改后的用例内容（用于审计记录）
            after_snapshot = await self._get_case_snapshot(item.case_id) if task.task_type in (TaskType.CASE_REVIEW, TaskType.CORE_SELECT) else None

            # 写入审核记录
            review_record = AiTcReviewRecord(
                task_id=task_id,
                task_item_id=ci.item_id,
                case_id=item.case_id,
                review_action=action_map.get(ci.confirm_status, "unknown"),
                before_value=json.dumps(before_snapshot, ensure_ascii=False) if before_snapshot else None,
                after_value=json.dumps(after_snapshot, ensure_ascii=False) if after_snapshot else None,
                reviewer=reviewed_by,
                reviewer_ip=reviewer_ip,
                review_time=now,
                memo="task_confirm" if task.task_type == TaskType.CORE_SELECT else None,
            )
            self.db.add(review_record)

        # 更新任务状态为已确认
        await self.db.execute(
            text("UPDATE ai_tc_tasks SET status = :s, update_time = NOW() WHERE id = :id"),
            {"s": TaskStatus.CONFIRMED, "id": task_id},
        )
        await self.db.flush()
        logger.info(f"Task {task_id} confirmed by {reviewed_by}")

    async def _apply_result(self, task_type: str, item: AiTcTaskItem, ci):
        """将 AI 结果写入实际数据表。"""
        if task_type == TaskType.CORE_SELECT:
            # 标记核心用例
            output = item.output or {}
            if output.get("selected"):
                await self.db.execute(
                    text(
                        "UPDATE ai_tc_cases SET is_core = 1, core_reason = :reason, "
                        "core_source = :src, update_time = NOW() WHERE id = :id"
                    ),
                    {
                        "reason": output.get("reason", "AI挑选")[:512],
                        "src": CoreSource.AI,
                        "id": item.case_id,
                    },
                )

        elif task_type == TaskType.CASE_REVIEW:
            # 更新审核状态 + 用例内容
            content = ci.final_content if ci.final_content else ""
            output = item.output or {}
            rewritten = output.get("rewritten")

            if rewritten and isinstance(rewritten, dict):
                update_fields: dict = {}
                if rewritten.get("name"):
                    update_fields["name"] = rewritten["name"]
                if rewritten.get("summary"):
                    update_fields["summary"] = rewritten["summary"]
                if rewritten.get("preconditions"):
                    update_fields["preconditions"] = rewritten["preconditions"]
                if rewritten.get("steps"):
                    update_fields["steps"] = json.dumps(rewritten["steps"])
                if update_fields:
                    set_clause = ", ".join(f"{k} = :{k}" for k in update_fields)
                    update_fields["id"] = item.case_id
                    await self.db.execute(
                        text(f"UPDATE ai_tc_cases SET {set_clause}, review_status = 1, update_time = NOW() WHERE id = :id"),
                        update_fields,
                    )

            # 无论如何更新审核状态
            await self.db.execute(
                text("UPDATE ai_tc_cases SET review_status = 1, update_time = NOW() WHERE id = :id AND review_status = 0"),
                {"id": item.case_id},
            )

        elif task_type == TaskType.SCRIPT_GEN:
            # 写入脚本库（草稿状态）
            output = item.output or {}
            script_content = output.get("script", "")
            if ci.confirm_status == ConfirmStatus.EDITED_ACCEPTED and ci.final_content:
                script_content = ci.final_content

            if script_content:
                language = output.get("language", "python")
                framework = output.get("framework", "pytest")
                script = AiTcScript(
                    case_id=item.case_id,
                    language=language,
                    framework=framework,
                    content=script_content,
                    source=ScriptSource.AI,
                    task_item_id=item.id,
                    version=1,
                    status=ScriptStatus.DRAFT,
                )
                self.db.add(script)

                # 更新用例脚本计数
                await self.db.execute(
                    text(
                        "UPDATE ai_tc_cases SET script_count = script_count + 1, "
                        "update_time = NOW() WHERE id = :id"
                    ),
                    {"id": item.case_id},
                )

    # ═══════════════ 审核记录 & 单条审核 ═══════════════

    async def get_item_with_case(self, task_id: int, item_id: int) -> dict:
        """获取单条任务明细 + 关联用例详情（供审核页面使用）。"""
        item = await self.db.get(AiTcTaskItem, item_id)
        if item is None or item.task_id != task_id:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="明细不存在")

        case = await self.db.get(AiTcCase, item.case_id)
        case_vo: CaseVO | None = None
        if case:
            case_vo = CaseVO(
                id=case.id, project_id=case.project_id, suite_id=case.suite_id,
                external_id=case.external_id, name=case.name, summary=case.summary,
                preconditions=case.preconditions, topo=case.topo,
                test_data=case.test_data,
                steps=[CaseStep(**s) for s in (case.steps or [])] if case.steps else [],
                importance=case.importance, is_core=case.is_core,
                core_reason=case.core_reason, core_source=case.core_source,
                review_status=case.review_status, script_count=case.script_count,
            )

        item_vo = self._task_item_to_vo(item)
        return {"item": item_vo, "case": case_vo}

    async def review_single_item(
        self, task_id: int, item_id: int, form: ReviewItemReq,
        reviewed_by: str = "", reviewer_ip: str = ""
    ) -> None:
        """逐字段审核单条任务明细，记录每个字段的审核操作到审计表。"""
        item = await self.db.get(AiTcTaskItem, item_id)
        if item is None or item.task_id != task_id:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="明细不存在")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output: dict = item.output or {}
        case = await self.db.get(AiTcCase, item.case_id)

        # 逐字段审核记录
        for f in form.fields:
            if f.action == "accept":
                # 将 AI 建议的字段值写入用例
                actual_value = self._get_field_from_output(output, f.field_name)
                before_val = self._get_case_field_value(case, f.field_name) if case else ""
                if actual_value is not None:
                    await self._update_case_field(item.case_id, f.field_name, actual_value)

                review_record = AiTcReviewRecord(
                    task_id=task_id, task_item_id=item_id, case_id=item.case_id,
                    review_action="field_accept", field_name=f.field_name,
                    before_value=json.dumps(before_val, ensure_ascii=False),
                    after_value=json.dumps(actual_value, ensure_ascii=False),
                    reviewer=reviewed_by, reviewer_ip=reviewer_ip, review_time=now,
                )
                self.db.add(review_record)

            elif f.action == "edit_accept" and f.edited_value:
                before_val = self._get_case_field_value(case, f.field_name) if case else ""
                await self._update_case_field(item.case_id, f.field_name, f.edited_value)

                review_record = AiTcReviewRecord(
                    task_id=task_id, task_item_id=item_id, case_id=item.case_id,
                    review_action="field_accept", field_name=f.field_name,
                    before_value=json.dumps(before_val, ensure_ascii=False),
                    after_value=json.dumps(f.edited_value, ensure_ascii=False),
                    reviewer=reviewed_by, reviewer_ip=reviewer_ip, review_time=now,
                    memo="manual_edit",
                )
                self.db.add(review_record)

            elif f.action == "ignore":
                review_record = AiTcReviewRecord(
                    task_id=task_id, task_item_id=item_id, case_id=item.case_id,
                    review_action="ignore", field_name=f.field_name,
                    before_value=json.dumps(self._get_case_field_value(case, f.field_name) if case else "", ensure_ascii=False),
                    after_value=None,
                    reviewer=reviewed_by, reviewer_ip=reviewer_ip, review_time=now,
                )
                self.db.add(review_record)

        # 更新整个 item 的确认状态
        if form.confirm_status == ConfirmStatus.ACCEPTED and not form.fields:
            # 无字段级别审核，整体采纳
            if output.get("script"):
                await self._apply_script_from_output(item, output)
            review_record = AiTcReviewRecord(
                task_id=task_id, task_item_id=item_id, case_id=item.case_id,
                review_action="accept",
                before_value=json.dumps(self._get_case_snapshot(item.case_id), ensure_ascii=False),
                after_value=None,
                reviewer=reviewed_by, reviewer_ip=reviewer_ip, review_time=now,
            )
            self.db.add(review_record)

        if form.confirm_status == ConfirmStatus.EDITED_ACCEPTED and form.final_content:
            item.final_content = form.final_content
            if output.get("script"):
                await self._apply_script_from_output(item, output, form.final_content)

        item.confirm_status = form.confirm_status or (
            ConfirmStatus.ACCEPTED if form.fields and all(f.action == "accept" or f.action == "edit_accept" for f in form.fields) else ConfirmStatus.IGNORED
        )
        item.reviewed_by = reviewed_by
        item.review_time = now

        await self.db.flush()
        logger.info(f"Item {item_id} reviewed by {reviewed_by}, fields: {len(form.fields)}")

    async def get_review_records(self, task_id: int) -> list[ReviewRecordVO]:
        """获取任务的审核记录列表。"""
        rows = await self.db.execute(
            select(AiTcReviewRecord).where(
                AiTcReviewRecord.task_id == task_id,
            ).order_by(AiTcReviewRecord.id.desc())
        )
        records = rows.scalars().all()
        return [
            ReviewRecordVO(
                id=r.id, task_id=r.task_id, task_item_id=r.task_item_id, case_id=r.case_id,
                review_action=r.review_action, field_name=r.field_name,
                before_value=r.before_value, after_value=r.after_value,
                reviewer=r.reviewer, reviewer_ip=r.reviewer_ip,
                review_time=r.review_time, memo=r.memo,
                create_time=str(r.create_time) if r.create_time else None,
            )
            for r in records
        ]

    # ── 审核辅助方法 ──

    async def _get_case_snapshot(self, case_id: int) -> dict | None:
        """获取用例内容快照。"""
        case = await self.db.get(AiTcCase, case_id)
        if case is None:
            return None
        return {
            "name": case.name or "",
            "summary": case.summary or "",
            "preconditions": case.preconditions or "",
            "test_data": case.test_data or "",
            "steps": case.steps or [],
            "is_core": case.is_core,
            "core_reason": case.core_reason or "",
        }

    def _get_case_field_value(self, case: AiTcCase | None, field_name: str):
        """获取用例字段的原始值。"""
        if case is None:
            return ""
        field_map = {
            "name": case.name, "summary": case.summary,
            "preconditions": case.preconditions, "test_data": case.test_data,
            "steps": case.steps, "is_core": case.is_core,
        }
        return field_map.get(field_name, "")

    def _get_field_from_output(self, output: dict, field_name: str):
        """从 AI 输出的 rewritten 中提取字段值。"""
        rewritten = output.get("rewritten") or output
        if isinstance(rewritten, dict):
            return rewritten.get(field_name)
        return None

    async def _update_case_field(self, case_id: int, field_name: str, value):
        """更新用例的单个字段。"""
        if field_name == "steps" and value is not None:
            value = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        set_clause = f"{field_name} = :val"
        if field_name == "steps":
            # steps needs to be cast to jsonb
            set_clause = f"{field_name} = :val::jsonb"
        await self.db.execute(
            text(f"UPDATE ai_tc_cases SET {set_clause}, update_time = NOW() WHERE id = :id"),
            {"val": value, "id": case_id},
        )

    async def _apply_script_from_output(self, item: AiTcTaskItem, output: dict, edited_content: str = ""):
        """将脚本写入脚本库。"""
        script_content = edited_content or output.get("script", "")
        if not script_content:
            return
        language = output.get("language", "python")
        framework = output.get("framework", "pytest")
        script = AiTcScript(
            case_id=item.case_id,
            language=language, framework=framework,
            content=script_content,
            source=ScriptSource.AI,
            task_item_id=item.id,
            version=1, status=ScriptStatus.DRAFT,
        )
        self.db.add(script)
        await self.db.execute(
            text("UPDATE ai_tc_cases SET script_count = script_count + 1, update_time = NOW() WHERE id = :id"),
            {"id": item.case_id},
        )

    # ═══════════════ 辅助方法 ═══════════════

    async def _get_suite_full_path(self, suite_id: int) -> str:
        """根据 tree_path 获取套件从根到当前节点的完整路径，如 根模块 / 子模块 / 当前。"""
        suite = await self.db.get(AiTcSuite, suite_id)
        if suite is None:
            return ""
        ancestor_ids: list[int] = []
        if suite.tree_path:
            for part in suite.tree_path.split(","):
                part = part.strip().lstrip("$")
                if part and part != "0":
                    ancestor_ids.append(int(part))
        ancestor_ids.append(suite_id)

        if not ancestor_ids:
            return suite.name

        rows = await self.db.execute(
            select(AiTcSuite.id, AiTcSuite.name).where(AiTcSuite.id.in_(ancestor_ids))
        )
        name_map: dict[int, str] = {r.id: r.name for r in rows}

        names = [name_map.get(aid, "") for aid in ancestor_ids]
        return " / ".join(filter(None, names))

    async def _get_subtree_case_ids(self, suite_id: int) -> list[int]:
        """获取指定套件及其子套件的所有用例 ID。"""
        suite = await self.db.get(AiTcSuite, suite_id)
        if suite is None:
            return []
        prefix = f"{suite.tree_path}{suite_id},"
        suite_rows = await self.db.execute(
            select(AiTcSuite.id).where(
                AiTcSuite.tree_path.like(f"{prefix}%"),
                AiTcSuite.is_deleted == 0,
            )
        )
        all_suite_ids = [suite_id] + [r[0] for r in suite_rows]

        case_rows = await self.db.execute(
            select(AiTcCase.id).where(
                AiTcCase.suite_id.in_(all_suite_ids),
                AiTcCase.is_deleted == 0,
            )
        )
        return [r[0] for r in case_rows]

    async def _resolve_ai_config(self, config_id: int | None, scene: str) -> Any:
        """解析 AI 配置：优先指定 config_id，其次全局默认(is_default=1)，最后按 scenes 匹配。"""
        if config_id:
            cfg = await self.db.get(AiTcAiConfig, config_id)
            if cfg and cfg.is_deleted == 0:
                return cfg

        # 全局默认优先（用户标记 is_default=1 的就是要用它）
        rows = await self.db.execute(
            select(AiTcAiConfig).where(
                AiTcAiConfig.is_deleted == 0,
                AiTcAiConfig.status == 1,
                AiTcAiConfig.is_default == 1,
            )
        )
        cfg = rows.scalars().first()
        if cfg:
            return cfg

        # 按 scenes 匹配兜底
        scene_pattern = f'"{scene}"'
        rows = await self.db.execute(
            select(AiTcAiConfig).where(
                AiTcAiConfig.is_deleted == 0,
                AiTcAiConfig.status == 1,
                text("scenes::text LIKE :pat").bindparams(pat=f"%{scene_pattern}%"),
            ).order_by(AiTcAiConfig.is_default.desc())
        )
        cfg = rows.scalars().first()
        if cfg:
            return cfg

        # 任意启用的配置
        rows = await self.db.execute(
            select(AiTcAiConfig).where(
                AiTcAiConfig.is_deleted == 0,
                AiTcAiConfig.status == 1,
            ).order_by(AiTcAiConfig.id)
        )
        return rows.scalars().first()

    @staticmethod
    def _load_prompt_from_file(task_type: str) -> str:
        """从 prompts/ 目录加载对应场景的提示词模板文件。"""
        filename = f"{task_type}.txt"
        filepath = PROMPTS_DIR / filename
        if filepath.exists():
            return filepath.read_text(encoding="utf-8")
        logger.warning(f"Prompt file not found: {filepath}, using empty prompt")
        return ""

    # ========== 样本 & 规范加载 ==========

    async def _load_samples(self, sample_ids: list[int]) -> str:
        """根据 ID 加载样本内容并拼接为文本。"""
        rows = await self.db.execute(
            select(AiTcSample).where(
                AiTcSample.id.in_(sample_ids),
                AiTcSample.is_deleted == 0,
            )
        )
        parts = []
        for s in rows.scalars().all():
            parts.append(f"【样本：{s.name}】\n{s.content}")
        return "\n\n".join(parts)

    async def _load_specs(self, spec_ids: list[int]) -> str:
        """根据 ID 加载规范内容并拼接为文本。"""
        if not spec_ids:
            return ""
        rows = await self.db.execute(
            select(AiTcSpec).where(
                AiTcSpec.id.in_(spec_ids),
                AiTcSpec.is_deleted == 0,
            )
        )
        spec_type_names = {"general": "通用规范", "module_specific": "模块专用规范", "common_issues": "常见问题规范"}
        parts = []
        for s in rows.scalars().all():
            stype = spec_type_names.get(s.spec_type, s.spec_type)
            parts.append(f"【{stype}】\n{s.content}")
        return "\n\n".join(parts)

    async def _load_cases_brief(self, case_ids: list[int]) -> list[dict]:
        """加载用例简要信息 [[id, name], ...]。"""
        rows = await self.db.execute(
            select(AiTcCase.id, AiTcCase.name).where(AiTcCase.id.in_(case_ids))
        )
        return [{"id": r.id, "name": r.name} for r in rows]

    # ═══════════════ VO 组装 ═══════════════

    def _task_to_vo(self, t: AiTcTask, project_name: str = "", suite_name: str = "") -> TaskVO:
        return TaskVO(
            id=t.id, task_type=t.task_type,
            project_id=t.project_id, project_name=project_name,
            suite_id=t.suite_id, suite_name=suite_name,
            prompt_id=None, sample_ids=t.sample_ids or [],
            spec_ids=t.spec_ids,
            ai_config_id=t.ai_config_id, model=t.model,
            status=t.status, total_count=t.total_count, done_count=t.done_count,
            input_tokens=t.input_tokens, output_tokens=t.output_tokens,
            error_msg=t.error_msg, create_by=t.create_by,
            create_time=str(t.create_time) if t.create_time else None,
        )

    def _task_item_to_vo(self, it: AiTcTaskItem) -> TaskItemVO:
        return TaskItemVO(
            id=it.id, task_id=it.task_id,
            case_id=it.case_id, case_name=it.case_name,
            output=it.output, item_status=it.item_status,
            confirm_status=it.confirm_status,
            final_content=it.final_content,
            reviewed_by=it.reviewed_by,
            review_time=it.review_time,
        )
