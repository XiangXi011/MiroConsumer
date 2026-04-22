"""
Report application service

Encapsulates route-level orchestration for report generation and lookups.
"""

import threading
import traceback
import uuid
from typing import Any, Callable, Dict, Optional

from ...config import Config
from ...models.task import TaskManager, TaskStatus
from ...repositories import ProjectRepository, ReportRepository, SimulationRepository
from ...repositories.filesystem import (
    FilesystemProjectRepository,
    FilesystemReportRepository,
    FilesystemSimulationRepository,
)
from ...services.report_agent import ReportAgent, ReportStatus
from ...utils.locale import t, get_locale, set_locale
from ...utils.logger import get_logger

logger = get_logger("miroconsumer.app_service.report")


class ReportAppService:
    """Application service for report generation orchestration."""

    _project_repo: ProjectRepository = FilesystemProjectRepository()
    _simulation_repo: SimulationRepository = FilesystemSimulationRepository()
    _report_repo: ReportRepository = FilesystemReportRepository()

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
        """
        Orchestrate report generation.

        Returns immediate response payload with task_id / report_id.
        Raises ValueError on validation failure.
        """
        state = cls._simulation_repo.get_simulation(simulation_id)

        if not state:
            raise ValueError(t("api.simulationNotFound", id=simulation_id))

        if not force_regenerate:
            existing = cls.get_existing_report_for_simulation(simulation_id)
            if existing:
                return existing

        project = cls._project_repo.get_project(state.project_id)
        if not project:
            raise ValueError(t("api.projectNotFound", id=state.project_id))

        graph_id = state.graph_id or project.graph_id
        if not graph_id:
            raise ValueError(t("api.missingGraphIdEnsure"))

        consumer_mode = (project.project_type == "consumer_test") or state.project_type == "consumer_test"

        simulation_requirement = project.simulation_requirement or ""
        if not consumer_mode and not simulation_requirement:
            raise ValueError(t("api.missingSimRequirement"))
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

        thread = threading.Thread(target=run_generate, daemon=True)
        thread.start()

        return {
            "simulation_id": simulation_id,
            "report_id": report_id,
            "task_id": task_id,
            "status": "generating",
            "message": t("api.reportGenerateStarted"),
            "already_generated": False,
        }
