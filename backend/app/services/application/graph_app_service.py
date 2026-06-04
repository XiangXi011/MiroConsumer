"""
Graph application service

Encapsulates route-level orchestration for graph build operations.
"""

import json
import threading
import traceback
from pathlib import Path

from ...config import Config
from ...models.project import ProjectStatus
from ...models.task import TaskManager, TaskStatus
from ...repositories import ProjectRepository
from ...repositories.factory import create_repository_bundle
from ...services.graph_builder import GraphBuilderService
from ...services.text_processor import TextProcessor
from ...services.consumer import ConsumerBriefAdapter, ConsumerGraphBuilder
from ...services.consumer.document_ingest import DocumentIngestService
from ...services.consumer.lane_b_provider import build_lane_b_provider
from ...services.consumer.models import ResearchSourceLane, ResearchSourceType
from ...services.consumer.persona_pack_registry import get_registry
from ...services.consumer.project_research_persistence import persist_findings, persist_snapshot
from ...services.consumer.research_ingest import (
    build_research_summary,
    resolve_research_findings,
    default_auto_research_provider,
    llm_auto_research_provider,
    build_research_snapshot,
)
from ...services.consumer.source_quality import build_source_quality_summary
from ...services.consumer.source_registry import SourceRegistry
from ...services.consumer.url_ingest import ingest_background_url_sources
from ...utils.locale import t, get_locale, set_locale
from ...utils.logger import get_logger

logger = get_logger("miroconsumer.app_service.graph")


def _normalize_consumer_brief_payload(raw_payload):
    """Parse a consumer brief from form/json payloads into a persisted summary."""
    if raw_payload is None:
        return None

    payload = raw_payload
    if isinstance(raw_payload, str):
        raw_payload = raw_payload.strip()
        if not raw_payload:
            return None
        payload = json.loads(raw_payload)

    brief = ConsumerBriefAdapter.from_payload(payload)
    return brief.to_summary()


def _consumer_graph_id(project_id: str) -> str:
    return f"consumer_{project_id}"


def _ingest_project_files_into_research_workspace(project_id: str, file_texts: list) -> None:
    """Register uploaded files as Lane A sources and ingest their text into the research workspace."""
    if not file_texts:
        return
    registry = SourceRegistry(project_id, upload_root=Config.UPLOAD_FOLDER)
    ingest = DocumentIngestService(project_id, upload_root=Config.UPLOAD_FOLDER)
    for file_info in file_texts:
        original_filename = file_info.get("original_filename", "unknown")
        text = file_info.get("text", "")
        if not text:
            continue
        source = registry.register_source(
            lane=ResearchSourceLane.LaneA,
            source_type=ResearchSourceType.Upload,
            label=f"User upload: {original_filename}",
            uri=file_info.get("path", ""),
        )
        ingest.ingest_text(
            source_id=source.source_id,
            text=text,
            title=original_filename,
        )


def _project_persona_dir(project_id: str) -> Path:
    return Path(Config.UPLOAD_FOLDER) / "projects" / project_id / "persona_packs"


def _build_consumer_graph(project, text: str, project_repo: ProjectRepository):
    """Synchronous consumer graph build (domain logic)."""
    if not project.consumer_brief:
        raise ValueError("consumer_brief is required for consumer_test graph builds")

    brief = ConsumerBriefAdapter.from_payload(project.consumer_brief)
    source_evidence_spans = getattr(brief, "source_evidence_spans", []) or []
    has_openclaw_evidence = bool(source_evidence_spans)

    # Ingest any URL entries from optional_background_materials into Lane A
    ingest_background_url_sources(
        project.project_id,
        brief=brief,
        upload_root=Config.UPLOAD_FOLDER,
    )

    use_live_lane_b = bool(brief.enable_lane_b and not has_openclaw_evidence)
    lane_b_provider = (
        build_lane_b_provider(project.project_id, upload_root=Config.UPLOAD_FOLDER)
        if use_live_lane_b
        else None
    )
    if has_openclaw_evidence:
        auto_research_provider = None
    elif brief.research_mode == "auto_enrich":
        auto_research_provider = llm_auto_research_provider
    else:
        auto_research_provider = default_auto_research_provider
    research_findings = resolve_research_findings(
        brief,
        provider=auto_research_provider,
        project_id=project.project_id,
        upload_root=Config.UPLOAD_FOLDER,
        enable_lane_b=use_live_lane_b,
        lane_b_provider=lane_b_provider,
    )

    # Resolve persona pack through registry (supports built-in and custom project packs)
    registry = get_registry(project_persona_dir=_project_persona_dir(project.project_id))
    personas = registry.resolve_selection(brief.persona_pack_selection)

    graph_payload = ConsumerGraphBuilder().build(
        brief=brief,
        background_text=text,
        persona_pack=personas,
        graph_id=_consumer_graph_id(project.project_id),
        research_findings=research_findings,
    )

    project_repo.save_consumer_graph_payload(project.project_id, graph_payload)
    project.graph_id = graph_payload["graph_id"]
    project.status = ProjectStatus.GRAPH_COMPLETED

    # Build research snapshot for Phase 3A provenance
    snapshot = build_research_snapshot(
        project.project_id,
        brief=brief,
        upload_root=Config.UPLOAD_FOLDER,
        provider=auto_research_provider,
        enable_lane_b=use_live_lane_b,
        lane_b_provider=lane_b_provider,
        precomputed_findings=research_findings,
    )

    # Persist formal project-level research artifacts
    persist_findings(project.project_id, research_findings, upload_root=Config.UPLOAD_FOLDER)
    persist_snapshot(project.project_id, snapshot, upload_root=Config.UPLOAD_FOLDER)

    # Persist research context for downstream simulation/reporting
    source_quality_summary = build_source_quality_summary(snapshot.sources)

    # Resolve pack metadata for context
    pack_meta = registry.get_pack(brief.persona_pack_selection.pack_id)
    pack_summary = pack_meta.to_summary() if pack_meta else {"pack_id": brief.persona_pack_selection.pack_id}

    project.consumer_context = {
        "research_mode": brief.research_mode,
        "enable_lane_b": brief.enable_lane_b,
        "live_lane_b_used": use_live_lane_b,
        "source_evidence_span_count": len(source_evidence_spans),
        "research_summary": build_research_summary(research_findings),
        "research_findings_count": len(research_findings),
        "auto_enrich_count": sum(
            1 for f in research_findings if f.source_label == "auto_enrich"
        ),
        "manual_background_count": sum(
            1 for f in research_findings if f.source_label == "brief_background"
        ),
        "source_evidence_count": sum(
            1 for f in research_findings if f.source_label == "source_evidence"
        ),
        "ingested_document_count": sum(
            1 for f in research_findings if f.source_label == "ingested_document"
        ),
        "public_web_count": sum(
            1 for f in research_findings if f.source_label == "public_web"
        ),
        "research_snapshot": {
            "snapshot_id": snapshot.snapshot_id,
            "source_count": len(snapshot.sources),
            "document_count": len(snapshot.documents),
            "chunk_count": len(snapshot.chunks),
            "finding_count": len(snapshot.findings),
            "retrieval_trace_count": len(snapshot.retrieval_traces),
        },
        "source_quality_summary": source_quality_summary,
        "persona_pack": pack_summary,
    }
    project_repo.save_project(project)

    return graph_payload


class GraphAppService:
    """Application service for graph build orchestration."""

    _repository_bundle = create_repository_bundle()
    _project_repo: ProjectRepository = _repository_bundle.project_repo

    @staticmethod
    def allowed_file(filename: str) -> bool:
        """Check if file extension is allowed."""
        if not filename or "." not in filename:
            return False
        ext = filename.split(".")[-1].lower()
        return ext in Config.ALLOWED_EXTENSIONS

    @classmethod
    def build_consumer_graph_sync(
        cls,
        project,
        text: str,
        task_manager: TaskManager,
        task_id: str,
    ) -> dict:
        """
        Build a consumer_test graph synchronously and update task progress.

        Returns the graph payload on success. Raises on failure.
        """
        try:
            task_manager.update_task(
                task_id,
                status=TaskStatus.PROCESSING,
                message=t("progress.initGraphService"),
                progress=10,
            )
            graph_data = _build_consumer_graph(project, text, cls._project_repo)
            node_count = graph_data.get("node_count", 0)
            edge_count = graph_data.get("edge_count", 0)
            task_manager.update_task(
                task_id,
                status=TaskStatus.COMPLETED,
                message=t("progress.graphBuildComplete"),
                progress=100,
                result={
                    "project_id": project.project_id,
                    "graph_id": graph_data["graph_id"],
                    "node_count": node_count,
                    "edge_count": edge_count,
                    "chunk_count": 1,
                },
            )
            return graph_data
        except Exception:
            logger.error(f"Consumer graph build failed: {traceback.format_exc()}")
            project.status = ProjectStatus.FAILED
            project.error = traceback.format_exc()
            cls._project_repo.save_project(project)
            task_manager.update_task(
                task_id,
                status=TaskStatus.FAILED,
                message=t("progress.buildFailed", error="see traceback"),
                error=traceback.format_exc(),
            )
            raise

    @classmethod
    def spawn_legacy_graph_build(
        cls,
        project,
        task_id: str,
        graph_name: str,
        text: str,
        ontology: dict,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        """Spawn a background thread for legacy Zep graph builds."""
        current_locale = get_locale()
        task_manager = TaskManager()

        def build_task():
            set_locale(current_locale)
            build_logger = get_logger("miroconsumer.build")
            try:
                build_logger.info(f"[{task_id}] Starting legacy graph build...")
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.PROCESSING,
                    message=t("progress.initGraphService"),
                )

                builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)

                task_manager.update_task(
                    task_id,
                    message=t("progress.textChunking"),
                    progress=5,
                )
                chunks = TextProcessor.split_text(
                    text,
                    chunk_size=chunk_size,
                    overlap=chunk_overlap,
                )
                total_chunks = len(chunks)

                task_manager.update_task(
                    task_id,
                    message=t("progress.creatingZepGraph"),
                    progress=10,
                )
                graph_id = builder.create_graph(name=graph_name)

                project.graph_id = graph_id
                cls._project_repo.save_project(project)

                task_manager.update_task(
                    task_id,
                    message=t("progress.settingOntology"),
                    progress=15,
                )
                builder.set_ontology(graph_id, ontology)

                def add_progress_callback(msg, progress_ratio):
                    progress = 15 + int(progress_ratio * 40)
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress,
                    )

                task_manager.update_task(
                    task_id,
                    message=t("progress.addingChunks", count=total_chunks),
                    progress=15,
                )

                episode_uuids = builder.add_text_batches(
                    graph_id,
                    chunks,
                    batch_size=3,
                    progress_callback=add_progress_callback,
                )

                task_manager.update_task(
                    task_id,
                    message=t("progress.waitingZepProcess"),
                    progress=55,
                )

                def wait_progress_callback(msg, progress_ratio):
                    progress = 55 + int(progress_ratio * 35)
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress,
                    )

                builder._wait_for_episodes(episode_uuids, wait_progress_callback)

                task_manager.update_task(
                    task_id,
                    message=t("progress.fetchingGraphData"),
                    progress=95,
                )
                graph_data = builder.get_graph_data(graph_id)

                project.status = ProjectStatus.GRAPH_COMPLETED
                cls._project_repo.save_project(project)

                node_count = graph_data.get("node_count", 0)
                edge_count = graph_data.get("edge_count", 0)
                build_logger.info(
                    f"[{task_id}] Graph build complete: graph_id={graph_id}, nodes={node_count}, edges={edge_count}"
                )

                task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    message=t("progress.graphBuildComplete"),
                    progress=100,
                    result={
                        "project_id": project.project_id,
                        "graph_id": graph_id,
                        "node_count": node_count,
                        "edge_count": edge_count,
                        "chunk_count": total_chunks,
                    },
                )

            except Exception as e:
                build_logger.error(f"[{task_id}] Graph build failed: {str(e)}")
                build_logger.debug(traceback.format_exc())

                project.status = ProjectStatus.FAILED
                project.error = str(e)
                cls._project_repo.save_project(project)

                task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message=t("progress.buildFailed", error=str(e)),
                    error=traceback.format_exc(),
                )

        thread = threading.Thread(target=build_task, daemon=True)
        thread.start()
