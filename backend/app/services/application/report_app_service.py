"""
Report application service

Encapsulates route-level orchestration for report generation, lookups,
status checks, agent chat, and downloads.
"""

import os
import tempfile
import traceback
import uuid
from typing import Any, Callable, Dict, Optional

from ...config import Config
from ...models.project import ProjectManager
from ...models.task import TaskManager, TaskStatus
from ...contracts.errors import NotFoundError, ValidationError
from ...repositories import ProjectRepository, ReportRepository, SimulationRepository
from ...repositories.factory import create_repository_bundle
from ...services.consumer.api_guard import ConsumerApiGuard
from ...services.report_agent import ReportAgent, ReportManager, ReportStatus
from ...services.simulation_manager import SimulationManager
from ...utils.locale import t, get_locale, set_locale
from ...utils.logger import get_logger
from .concurrency import create_lock_manager, report_generation_lock
from .task_executor import TaskExecutor, create_task_executor

logger = get_logger("miroconsumer.app_service.report")


class ReportAppService:
    """Application service for report generation orchestration."""

    _repository_bundle = create_repository_bundle()
    _project_repo: ProjectRepository = _repository_bundle.project_repo
    _simulation_repo: SimulationRepository = _repository_bundle.simulation_repo
    _report_repo: ReportRepository = _repository_bundle.report_repo
    _executor: TaskExecutor = create_task_executor()
    _lock_manager = create_lock_manager()

    @classmethod
    def get_existing_report_for_simulation(cls, simulation_id: str) -> Optional[dict]:
        """Return an existing completed report dict, or None."""
        existing = cls._report_repo.get_report_by_simulation(simulation_id)
        if existing and existing.status == ReportStatus.COMPLETED:
            return {
                "simulation_id": simulation_id,
                "report_id": existing.report_id,
                "status": "completed",
                "message": t("api.reportAlreadyExists"),
                "already_generated": True,
            }
        return None

    @classmethod
    def generate_report(cls, simulation_id: str, force_regenerate: bool = False) -> dict:
        return cls._generate_report_unlocked(
            simulation_id=simulation_id,
            force_regenerate=force_regenerate,
        )

    @classmethod
    def _generate_report_unlocked(cls, simulation_id: str, force_regenerate: bool = False) -> dict:
        """
        Orchestrate report generation.

        Returns immediate response payload with task_id / report_id.
        Raises ValueError on validation failure.
        """
        state = cls._simulation_repo.get_simulation(simulation_id)

        if not state:
            raise NotFoundError(t("api.simulationNotFound", id=simulation_id))

        project = cls._project_repo.get_project(state.project_id)
        if not project:
            raise NotFoundError(t("api.projectNotFound", id=state.project_id))

        graph_id = state.graph_id or project.graph_id
        if not graph_id:
            raise ValidationError(t("api.missingGraphIdEnsure"))

        consumer_mode = ConsumerApiGuard.is_consumer_context(state=state, project=project)

        # Phase 6J hard gate: only block consumer report generation when calibration artifact is missing/blocked
        if consumer_mode:
            simulation_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
            from ...services.consumer.phase6j_calibration import check_phase6j_gate
            gate = check_phase6j_gate(simulation_dir)
            if gate["blocked"]:
                raise ValidationError(
                    gate["reason"],
                    details=gate["details"],
                )

        if not force_regenerate:
            existing = cls.get_existing_report_for_simulation(simulation_id)
            if existing:
                return existing

        simulation_requirement = project.simulation_requirement or ""
        if not consumer_mode and not simulation_requirement:
            raise ValidationError(t("api.missingSimRequirement"))
        if consumer_mode and not simulation_requirement:
            simulation_requirement = "Consumer propagation test"

        report_id = f"report_{uuid.uuid4().hex[:12]}"

        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="report_generate",
            metadata={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "report_id": report_id,
            },
        )

        current_locale = get_locale()

        def run_generate():
            set_locale(current_locale)
            try:
                with cls._lock_manager.acquire(
                    report_generation_lock,
                    simulation_id,
                    timeout_seconds=0,
                ):
                    task_manager.update_task(
                        task_id,
                        status=TaskStatus.PROCESSING,
                        progress=0,
                        message=t("api.initReportAgent"),
                    )

                    agent = ReportAgent(
                        graph_id=graph_id,
                        simulation_id=simulation_id,
                        simulation_requirement=simulation_requirement,
                        project_type=project.project_type or state.project_type or "default",
                        project_id=project.project_id,
                    )

                    def progress_callback(stage, progress, message):
                        task_manager.update_task(
                            task_id,
                            progress=progress,
                            message=f"[{stage}] {message}",
                        )

                    report = agent.generate_report(
                        progress_callback=progress_callback,
                        report_id=report_id,
                    )

                    cls._report_repo.save_report(report)

                    if report.status == ReportStatus.COMPLETED:
                        task_manager.complete_task(
                            task_id,
                            result={
                                "report_id": report.report_id,
                                "simulation_id": simulation_id,
                                "status": "completed",
                            },
                        )
                    else:
                        task_manager.fail_task(task_id, report.error or t("api.reportGenerateFailed"))

            except Exception as e:
                logger.error(f"Report generation failed: {str(e)}")
                task_manager.fail_task(task_id, str(e))

        trace_id = cls._executor.submit(
            run_generate,
            task_type="generate_report",
            idempotency_key=f"{simulation_id}:report",
            simulation_id=simulation_id,
            run_id="report",
            trace_id=report_id,
        )
        logger.info(
            "Report generation queued",
            extra={"trace_id": trace_id, "simulation_id": simulation_id, "task_id": task_id},
        )

        return {
            "simulation_id": simulation_id,
            "report_id": report_id,
            "task_id": task_id,
            "status": "generating",
            "message": t("api.reportGenerateStarted"),
            "already_generated": False,
        }

    @classmethod
    def get_generate_status(cls, simulation_id: Optional[str], task_id: Optional[str]) -> dict:
        """
        Return generate-status payload.

        Raises ValueError if neither simulation_id nor task_id is provided,
        or if the task is not found.
        """
        if simulation_id:
            existing_report = ReportManager.get_report_by_simulation(simulation_id)
            if existing_report and existing_report.status == ReportStatus.COMPLETED:
                return {
                    "simulation_id": simulation_id,
                    "report_id": existing_report.report_id,
                    "status": "completed",
                    "progress": 100,
                    "message": t("api.reportGenerated"),
                    "already_completed": True,
                }

        if not task_id:
            raise ValidationError(t("api.requireTaskOrSimId"))

        task_manager = TaskManager()
        task = task_manager.get_task(task_id)

        if not task:
            raise NotFoundError(t("api.taskNotFound", id=task_id))

        return task.to_dict()

    @classmethod
    def chat_with_report_agent(
        cls,
        simulation_id: str,
        message: str,
        chat_history: Optional[list] = None,
    ) -> dict:
        """
        Orchestrate a chat session with the Report Agent.

        Raises ValueError on validation failure.
        """
        if not simulation_id:
            raise ValidationError(t("api.requireSimulationId"))
        if not message:
            raise ValidationError(t("api.requireMessage"))

        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if not state:
            raise NotFoundError(t("api.simulationNotFound", id=simulation_id))

        project = ProjectManager.get_project(state.project_id)
        if not project:
            raise NotFoundError(t("api.projectNotFound", id=state.project_id))

        graph_id = state.graph_id or project.graph_id
        if not graph_id:
            raise ValidationError(t("api.missingGraphId"))

        simulation_requirement = project.simulation_requirement or ""

        agent = ReportAgent(
            graph_id=graph_id,
            simulation_id=simulation_id,
            simulation_requirement=simulation_requirement,
        )

        return agent.chat(message=message, chat_history=chat_history or [])

    @classmethod
    def get_report_sections(cls, report_id: str) -> dict:
        """
        Return generated sections and completion status for a report.

        Raises ValueError if report not found.
        """
        sections = ReportManager.get_generated_sections(report_id)
        report = ReportManager.get_report(report_id)
        is_complete = report is not None and report.status == ReportStatus.COMPLETED

        return {
            "report_id": report_id,
            "sections": sections,
            "total_sections": len(sections),
            "is_complete": is_complete,
        }

    @classmethod
    def check_report_status(cls, simulation_id: str) -> dict:
        """
        Return report-existence and interview-unlock status for a simulation.
        """
        report = ReportManager.get_report_by_simulation(simulation_id)

        has_report = report is not None
        report_status = report.status.value if report else None
        report_id = report.report_id if report else None
        interview_unlocked = has_report and report.status == ReportStatus.COMPLETED

        return {
            "simulation_id": simulation_id,
            "has_report": has_report,
            "report_status": report_status,
            "report_id": report_id,
            "interview_unlocked": interview_unlocked,
        }

    @classmethod
    def get_report_download_info(cls, report_id: str) -> dict:
        """
        Return download file path/info for a report.

        Returns a dict with:
            path: str — file path to send
            is_temp: bool — whether caller must clean up a temp file
            download_name: str — suggested download filename
            content: Optional[str] — temp-file content when is_temp is True

        Raises ValueError if report or markdown content is not found.
        """
        report = ReportManager.get_report(report_id)
        if not report:
            raise NotFoundError(t("api.reportNotFound", id=report_id))

        md_path = ReportManager._get_report_markdown_path(report_id)

        if os.path.exists(md_path):
            return {
                "path": md_path,
                "is_temp": False,
                "download_name": f"{report_id}.md",
                "content": None,
            }

        return {
            "path": None,
            "is_temp": True,
            "download_name": f"{report_id}.md",
            "content": report.markdown_content,
        }
