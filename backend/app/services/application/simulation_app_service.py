"""
Simulation application service

Encapsulates route-level orchestration for simulation lifecycle operations.
"""

import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

from ...config import Config
from ...models.task import TaskManager, TaskStatus
from ...repositories import ProjectRepository, SimulationRepository
from ...repositories.filesystem import (
    FilesystemProjectRepository,
    FilesystemSimulationRepository,
)
from ...services.consumer.api_guard import ConsumerApiGuard
from ...services.consumer.persona_pack import load_default_persona_pack
from ...services.prepare_manifest import read_manifest
from ...services.simulation_manager import SimulationStatus
from ...services.simulation_runner import SimulationRunner
from ...services.zep_entity_reader import ZepEntityReader
from ...utils.locale import t, get_locale, set_locale
from ...utils.logger import get_logger
from .task_executor import TaskExecutor, ThreadTaskExecutor

logger = get_logger("miroconsumer.app_service.simulation")


def _check_simulation_prepared(simulation_id: str) -> Tuple[bool, dict]:
    """
    Check whether a simulation has finished preparation.

    Returns (is_prepared, info_dict).
    """
    simulation_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)

    if not os.path.exists(simulation_dir):
        return False, {"reason": "模拟目录不存在"}

    required_files = [
        "state.json",
        "simulation_config.json",
        "reddit_profiles.json",
        "twitter_profiles.csv",
    ]

    existing_files = []
    missing_files = []
    for f in required_files:
        file_path = os.path.join(simulation_dir, f)
        if os.path.exists(file_path):
            existing_files.append(f)
        else:
            missing_files.append(f)

    if missing_files:
        return False, {
            "reason": "缺少必要文件",
            "missing_files": missing_files,
            "existing_files": existing_files,
        }

    state_file = os.path.join(simulation_dir, "state.json")
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state_data = json.load(f)

        status = state_data.get("status", "")
        config_generated = state_data.get("config_generated", False)

        prepared_statuses = ["ready", "preparing", "running", "completed", "stopped", "failed"]
        if status in prepared_statuses and config_generated:
            profiles_file = os.path.join(simulation_dir, "reddit_profiles.json")
            profiles_count = 0
            if os.path.exists(profiles_file):
                with open(profiles_file, "r", encoding="utf-8") as f:
                    profiles_data = json.load(f)
                    profiles_count = len(profiles_data) if isinstance(profiles_data, list) else 0

            if status == "preparing":
                try:
                    from datetime import datetime
                    state_data["status"] = "ready"
                    state_data["updated_at"] = datetime.now().isoformat()
                    with open(state_file, "w", encoding="utf-8") as f:
                        json.dump(state_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"Auto-updated simulation status: {simulation_id} preparing -> ready")
                    status = "ready"
                except Exception as e:
                    logger.warning(f"Auto-update status failed: {e}")

            manifest = read_manifest(simulation_dir)
            prepare_info = {
                "status": status,
                "entities_count": state_data.get("entities_count", 0),
                "profiles_count": profiles_count,
                "entity_types": state_data.get("entity_types", []),
                "config_generated": config_generated,
                "project_type": state_data.get("project_type", "default"),
                "consumer_mode": state_data.get("consumer_mode", False),
                "persona_pack_id": state_data.get("persona_pack_id", ""),
                "pinned_brief_summary": state_data.get("pinned_brief_summary", ""),
                "enable_lane_b": state_data.get("enable_lane_b", False),
                "created_at": state_data.get("created_at"),
                "updated_at": state_data.get("updated_at"),
                "existing_files": existing_files,
            }
            if manifest:
                prepare_info["prepare_manifest"] = manifest.to_dict()
            return True, prepare_info
        else:
            return False, {
                "reason": f"状态不在已准备列表中或config_generated为false: status={status}, config_generated={config_generated}",
                "status": status,
                "config_generated": config_generated,
            }
    except Exception as e:
        return False, {"reason": f"读取状态文件失败: {str(e)}"}


class SimulationAppService:
    """Application service for simulation lifecycle orchestration."""

    _project_repo: ProjectRepository = FilesystemProjectRepository()
    _simulation_repo: SimulationRepository = FilesystemSimulationRepository()
    _executor: TaskExecutor = ThreadTaskExecutor()

    @classmethod
    def create_simulation(cls, data: dict) -> dict:
        """
        Validate inputs and create a new simulation.

        Returns the simulation state dict on success.
        Raises ValueError with a message on validation failure.
        """
        project_id = data.get("project_id")
        if not project_id:
            raise ValueError(t("api.requireProjectId"))

        project = cls._project_repo.get_project(project_id)
        if not project:
            raise ValueError(t("api.projectNotFound", id=project_id))

        graph_id = data.get("graph_id") or project.graph_id
        if not graph_id:
            raise ValueError(t("api.graphNotBuilt"))

        state = cls._simulation_repo.create_simulation(
            project_id=project_id,
            graph_id=graph_id,
            project_type=project.project_type or "default",
            enable_twitter=data.get("enable_twitter", True),
            enable_reddit=data.get("enable_reddit", True),
        )
        return state.to_dict()

    @classmethod
    def check_prepared(cls, simulation_id: str) -> Tuple[bool, dict]:
        """Public wrapper around internal prepared check."""
        return _check_simulation_prepared(simulation_id)

    @classmethod
    def prepare_simulation(
        cls,
        simulation_id: str,
        data: dict,
    ) -> dict:
        """
        Orchestrate simulation preparation.

        Returns a dict with the immediate response payload.
        If already prepared and not force_regenerate, returns ready metadata.
        Otherwise creates a background task and returns task metadata.
        """
        state = cls._simulation_repo.get_simulation(simulation_id)

        if not state:
            raise ValueError(t("api.simulationNotFound", id=simulation_id))

        force_regenerate = data.get("force_regenerate", False)

        if not force_regenerate:
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
            if is_prepared:
                manifest_dict = cls._simulation_repo.record_manifest_reuse(simulation_id)
                response_data = {
                    "simulation_id": simulation_id,
                    "status": "ready",
                    "message": t("api.alreadyPrepared"),
                    "already_prepared": True,
                    "prepare_info": prepare_info,
                }
                if manifest_dict:
                    response_data["prepare_manifest"] = manifest_dict
                return response_data

        project = cls._project_repo.get_project(state.project_id)
        if not project:
            raise ValueError(t("api.projectNotFound", id=state.project_id))

        consumer_mode = ConsumerApiGuard.is_consumer_context(state=state, project=project)
        simulation_requirement = project.simulation_requirement or ""
        if not consumer_mode and not simulation_requirement:
            raise ValueError(t("api.projectMissingRequirement"))

        document_text = cls._project_repo.get_extracted_text(state.project_id) or ""

        entity_types_list = data.get("entity_types")
        use_llm_for_profiles = data.get("use_llm_for_profiles", True)
        parallel_profile_count = data.get("parallel_profile_count", 5)

        # Sync entity count preview
        try:
            if consumer_mode:
                persona_pack = load_default_persona_pack()
                state.entities_count = len(persona_pack)
                state.entity_types = ["AudienceSegment"]
                logger.info(f"consumer_test preview Persona count: {state.entities_count}")
            else:
                logger.info(f"Sync entity count preview: graph_id={state.graph_id}")
                reader = ZepEntityReader()
                filtered_preview = reader.filter_defined_entities(
                    graph_id=state.graph_id,
                    defined_entity_types=entity_types_list,
                    enrich_with_edges=False,
                )
                state.entities_count = filtered_preview.filtered_count
                state.entity_types = list(filtered_preview.entity_types)
                logger.info(
                    f"Expected entity count: {filtered_preview.filtered_count}, types: {filtered_preview.entity_types}"
                )
        except Exception as e:
            logger.warning(f"Sync entity count preview failed (will retry in background): {e}")

        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="simulation_prepare",
            metadata={
                "simulation_id": simulation_id,
                "project_id": state.project_id,
            },
        )

        state.status = SimulationStatus.PREPARING
        cls._simulation_repo.save_simulation(state)

        current_locale = get_locale()

        def run_prepare():
            from ...services.simulation_manager import SimulationManager
            set_locale(current_locale)
            try:
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.PROCESSING,
                    progress=0,
                    message=t("progress.startPreparingEnv"),
                )

                stage_details = {}

                def progress_callback(stage, progress, message, **kwargs):
                    stage_weights = {
                        "reading": (0, 20),
                        "generating_profiles": (20, 70),
                        "generating_config": (70, 90),
                        "copying_scripts": (90, 100),
                    }
                    start, end = stage_weights.get(stage, (0, 100))
                    current_progress = int(start + (end - start) * progress / 100)

                    stage_names = {
                        "reading": t("progress.readingGraphEntities"),
                        "generating_profiles": t("progress.generatingProfiles"),
                        "generating_config": t("progress.generatingSimConfig"),
                        "copying_scripts": t("progress.preparingScripts"),
                    }

                    stage_index = list(stage_weights.keys()).index(stage) + 1 if stage in stage_weights else 1
                    total_stages = len(stage_weights)

                    stage_details[stage] = {
                        "stage_name": stage_names.get(stage, stage),
                        "stage_progress": progress,
                        "current": kwargs.get("current", 0),
                        "total": kwargs.get("total", 0),
                        "item_name": kwargs.get("item_name", ""),
                    }

                    detail = stage_details[stage]
                    progress_detail_data = {
                        "current_stage": stage,
                        "current_stage_name": stage_names.get(stage, stage),
                        "stage_index": stage_index,
                        "total_stages": total_stages,
                        "stage_progress": progress,
                        "current_item": detail["current"],
                        "total_items": detail["total"],
                        "item_description": message,
                    }

                    if detail["total"] > 0:
                        detailed_message = (
                            f"[{stage_index}/{total_stages}] {stage_names.get(stage, stage)}: "
                            f"{detail['current']}/{detail['total']} - {message}"
                        )
                    else:
                        detailed_message = f"[{stage_index}/{total_stages}] {stage_names.get(stage, stage)}: {message}"

                    task_manager.update_task(
                        task_id,
                        progress=current_progress,
                        message=detailed_message,
                        progress_detail=progress_detail_data,
                    )

                # prepare_simulation is domain logic; delegate to SimulationManager
                domain_manager = SimulationManager()
                result_state = domain_manager.prepare_simulation(
                    simulation_id=simulation_id,
                    simulation_requirement=simulation_requirement,
                    document_text=document_text,
                    defined_entity_types=entity_types_list,
                    use_llm_for_profiles=use_llm_for_profiles,
                    progress_callback=progress_callback,
                    parallel_profile_count=parallel_profile_count,
                )

                task_manager.complete_task(
                    task_id,
                    result=result_state.to_simple_dict(),
                )

            except Exception as e:
                logger.error(f"Prepare simulation failed: {str(e)}")
                task_manager.fail_task(task_id, str(e))

                state = cls._simulation_repo.get_simulation(simulation_id)
                if state:
                    state.status = SimulationStatus.FAILED
                    state.error = str(e)
                    cls._simulation_repo.save_simulation(state)

        cls._executor.submit(run_prepare)

        return {
            "simulation_id": simulation_id,
            "task_id": task_id,
            "status": "preparing",
            "message": t("api.prepareStarted"),
            "already_prepared": False,
            "expected_entities_count": state.entities_count,
            "entity_types": state.entity_types,
        }

    @classmethod
    def start_simulation(
        cls,
        simulation_id: str,
        data: dict,
    ) -> dict:
        """
        Validate and start a simulation run.

        Returns the run_state dict augmented with service metadata.
        Raises ValueError on validation failure.
        """
        platform = data.get("platform", "parallel")
        max_rounds = data.get("max_rounds")
        enable_graph_memory_update = data.get("enable_graph_memory_update", False)
        force = data.get("force", False)

        if max_rounds is not None:
            max_rounds = int(max_rounds)
            if max_rounds <= 0:
                raise ValueError(t("api.maxRoundsPositive"))

        if platform not in ["twitter", "reddit", "parallel"]:
            raise ValueError(t("api.invalidPlatform", platform=platform))

        state = cls._simulation_repo.get_simulation(simulation_id)

        if not state:
            raise ValueError(t("api.simulationNotFound", id=simulation_id))

        force_restarted = False

        if state.status != SimulationStatus.READY:
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)

            if is_prepared:
                if state.status == SimulationStatus.RUNNING:
                    run_state = SimulationRunner.get_run_state(simulation_id)
                    if run_state and run_state.runner_status.value == "running":
                        if force:
                            logger.info(f"Force mode: stopping running simulation {simulation_id}")
                            try:
                                SimulationRunner.stop_simulation(simulation_id)
                            except Exception as e:
                                logger.warning(f"Warning while stopping simulation: {str(e)}")
                        else:
                            raise ValueError(t("api.simRunningForceHint"))

                if force:
                    logger.info(f"Force mode: cleaning simulation logs {simulation_id}")
                    cleanup_result = SimulationRunner.cleanup_simulation_logs(simulation_id)
                    if not cleanup_result.get("success"):
                        logger.warning(f"Warning while cleaning logs: {cleanup_result.get('errors')}")
                    force_restarted = True

                logger.info(
                    f"Simulation {simulation_id} preparation complete, resetting to ready (was {state.status.value})"
                )
                state.status = SimulationStatus.READY
                cls._simulation_repo.save_simulation(state)
            else:
                raise ValueError(t("api.simNotReady", status=state.status.value))

        graph_id = None
        if enable_graph_memory_update:
            graph_id = state.graph_id
            if not graph_id:
                project = cls._project_repo.get_project(state.project_id)
                if project:
                    graph_id = project.graph_id

            if not graph_id:
                raise ValueError(t("api.graphIdRequiredForMemory"))

            logger.info(f"Graph memory update enabled: simulation_id={simulation_id}, graph_id={graph_id}")

        run_state = SimulationRunner.start_simulation(
            simulation_id=simulation_id,
            platform=platform,
            max_rounds=max_rounds,
            enable_graph_memory_update=enable_graph_memory_update,
            graph_id=graph_id,
        )

        state.status = SimulationStatus.RUNNING
        cls._simulation_repo.save_simulation(state)

        response_data = run_state.to_dict()
        if max_rounds:
            response_data["max_rounds_applied"] = max_rounds
        response_data["graph_memory_update_enabled"] = enable_graph_memory_update
        response_data["force_restarted"] = force_restarted
        if enable_graph_memory_update:
            response_data["graph_id"] = graph_id

        return response_data

    @classmethod
    def get_prepare_status(
        cls,
        task_id: Optional[str],
        simulation_id: Optional[str],
    ) -> dict:
        """Query prepare task progress or prepared state.

        Returns a dict with the status payload. Raises ValueError when
        neither task_id nor simulation_id is usable.
        """
        if simulation_id:
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
            if is_prepared:
                status_data = {
                    "simulation_id": simulation_id,
                    "status": "ready",
                    "progress": 100,
                    "message": t("api.alreadyPrepared"),
                    "already_prepared": True,
                    "prepare_info": prepare_info,
                }
                if prepare_info.get("prepare_manifest"):
                    status_data["prepare_manifest"] = prepare_info["prepare_manifest"]
                return status_data

        if not task_id:
            if simulation_id:
                return {
                    "simulation_id": simulation_id,
                    "status": "not_started",
                    "progress": 0,
                    "message": t("api.notStartedPrepare"),
                    "already_prepared": False,
                }
            raise ValueError(t("api.requireTaskOrSimId"))

        task_manager = TaskManager()
        task = task_manager.get_task(task_id)

        if not task:
            if simulation_id:
                is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
                if is_prepared:
                    status_data = {
                        "simulation_id": simulation_id,
                        "task_id": task_id,
                        "status": "ready",
                        "progress": 100,
                        "message": t("api.taskCompletedPrepared"),
                        "already_prepared": True,
                        "prepare_info": prepare_info,
                    }
                    if prepare_info.get("prepare_manifest"):
                        status_data["prepare_manifest"] = prepare_info["prepare_manifest"]
                    return status_data
            raise ValueError(t("api.taskNotFound", id=task_id))

        task_dict = task.to_dict()
        task_dict["already_prepared"] = False
        return task_dict
