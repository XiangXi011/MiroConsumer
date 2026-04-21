"""
Simulation management for legacy and consumer_test preparation flows.
"""

import csv
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..config import Config
from ..models.project import ProjectManager
from ..utils.locale import t
from ..utils.logger import get_logger
from .consumer.brief_adapter import ConsumerBriefAdapter
from .consumer.models import ConsumerBusinessBrief
from .consumer.persona_pack import load_default_persona_pack, map_persona_to_agent_traits
from .consumer.lane_b_provider import build_lane_b_provider
from .consumer.research_ingest import (
    build_research_snapshot,
    build_research_summary,
    default_auto_research_provider,
    resolve_research_findings,
)
from .consumer.url_ingest import ingest_background_url_sources
from .oasis_profile_generator import OasisProfileGenerator
from .simulation_config_generator import (
    AgentActivityConfig,
    EventConfig,
    PlatformConfig,
    SimulationConfigGenerator,
    SimulationParameters,
    TimeSimulationConfig,
)
from .zep_entity_reader import ZepEntityReader

logger = get_logger("mirofish.simulation")


class SimulationStatus(str, Enum):
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class PlatformType(str, Enum):
    TWITTER = "twitter"
    REDDIT = "reddit"


@dataclass
class SimulationState:
    simulation_id: str
    project_id: str
    graph_id: str
    project_type: str = "default"
    consumer_mode: bool = False

    enable_twitter: bool = True
    enable_reddit: bool = True

    status: SimulationStatus = SimulationStatus.CREATED

    entities_count: int = 0
    profiles_count: int = 0
    entity_types: List[str] = field(default_factory=list)

    config_generated: bool = False
    config_reasoning: str = ""
    persona_pack_id: str = ""
    pinned_brief_summary: str = ""
    enable_lane_b: bool = False

    current_round: int = 0
    twitter_status: str = "not_started"
    reddit_status: str = "not_started"

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "project_type": self.project_type,
            "consumer_mode": self.consumer_mode,
            "enable_twitter": self.enable_twitter,
            "enable_reddit": self.enable_reddit,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "config_reasoning": self.config_reasoning,
            "persona_pack_id": self.persona_pack_id,
            "pinned_brief_summary": self.pinned_brief_summary,
            "enable_lane_b": self.enable_lane_b,
            "current_round": self.current_round,
            "twitter_status": self.twitter_status,
            "reddit_status": self.reddit_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }

    def to_simple_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "project_type": self.project_type,
            "consumer_mode": self.consumer_mode,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "persona_pack_id": self.persona_pack_id,
            "pinned_brief_summary": self.pinned_brief_summary,
            "enable_lane_b": self.enable_lane_b,
            "error": self.error,
        }


class SimulationManager:
    SIMULATION_DATA_DIR = os.path.join(
        os.path.dirname(__file__),
        "../../uploads/simulations",
    )

    def __init__(self):
        os.makedirs(self.SIMULATION_DATA_DIR, exist_ok=True)
        self._simulations: Dict[str, SimulationState] = {}

    def _get_simulation_dir(self, simulation_id: str) -> str:
        sim_dir = os.path.join(self.SIMULATION_DATA_DIR, simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        return sim_dir

    def _save_simulation_state(self, state: SimulationState):
        sim_dir = self._get_simulation_dir(state.simulation_id)
        state_file = os.path.join(sim_dir, "state.json")

        state.updated_at = datetime.now().isoformat()

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)

        self._simulations[state.simulation_id] = state

    def _load_simulation_state(self, simulation_id: str) -> Optional[SimulationState]:
        if simulation_id in self._simulations:
            return self._simulations[simulation_id]

        sim_dir = self._get_simulation_dir(simulation_id)
        state_file = os.path.join(sim_dir, "state.json")

        if not os.path.exists(state_file):
            return None

        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        state = SimulationState(
            simulation_id=simulation_id,
            project_id=data.get("project_id", ""),
            graph_id=data.get("graph_id", ""),
            project_type=data.get("project_type", "default"),
            consumer_mode=data.get("consumer_mode", False),
            enable_twitter=data.get("enable_twitter", True),
            enable_reddit=data.get("enable_reddit", True),
            status=SimulationStatus(data.get("status", "created")),
            entities_count=data.get("entities_count", 0),
            profiles_count=data.get("profiles_count", 0),
            entity_types=data.get("entity_types", []),
            config_generated=data.get("config_generated", False),
            config_reasoning=data.get("config_reasoning", ""),
            persona_pack_id=data.get("persona_pack_id", ""),
            pinned_brief_summary=data.get("pinned_brief_summary", ""),
            enable_lane_b=data.get("enable_lane_b", False),
            current_round=data.get("current_round", 0),
            twitter_status=data.get("twitter_status", "not_started"),
            reddit_status=data.get("reddit_status", "not_started"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            error=data.get("error"),
        )

        self._simulations[state.simulation_id] = state
        return state

    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        project_type: str = "default",
        enable_twitter: bool = True,
        enable_reddit: bool = True,
    ) -> SimulationState:
        import uuid

        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        normalized_project_type = project_type or "default"

        state = SimulationState(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            project_type=normalized_project_type,
            consumer_mode=(normalized_project_type == "consumer_test"),
            enable_twitter=enable_twitter,
            enable_reddit=enable_reddit,
            status=SimulationStatus.CREATED,
        )

        self._save_simulation_state(state)
        logger.info(f"创建模拟: {simulation_id}, project={project_id}, graph={graph_id}")

        return state

    def prepare_simulation(
        self,
        simulation_id: str,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]] = None,
        use_llm_for_profiles: bool = True,
        progress_callback: Optional[Callable[..., None]] = None,
        parallel_profile_count: int = 3,
    ) -> SimulationState:
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"模拟不存在: {simulation_id}")

        try:
            state.status = SimulationStatus.PREPARING
            self._save_simulation_state(state)

            if state.consumer_mode:
                return self._prepare_consumer_simulation(
                    state=state,
                    simulation_requirement=simulation_requirement,
                    document_text=document_text,
                    progress_callback=progress_callback,
                )

            return self._prepare_legacy_simulation(
                state=state,
                simulation_requirement=simulation_requirement,
                document_text=document_text,
                defined_entity_types=defined_entity_types,
                use_llm_for_profiles=use_llm_for_profiles,
                progress_callback=progress_callback,
                parallel_profile_count=parallel_profile_count,
            )
        except Exception as e:
            logger.error(f"模拟准备失败: {simulation_id}, error={str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            state.status = SimulationStatus.FAILED
            state.error = str(e)
            self._save_simulation_state(state)
            raise

    def _prepare_legacy_simulation(
        self,
        state: SimulationState,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]] = None,
        use_llm_for_profiles: bool = True,
        progress_callback: Optional[Callable[..., None]] = None,
        parallel_profile_count: int = 3,
    ) -> SimulationState:
        sim_dir = self._get_simulation_dir(state.simulation_id)

        if progress_callback:
            progress_callback("reading", 0, t("progress.connectingZepGraph"))

        reader = ZepEntityReader()

        if progress_callback:
            progress_callback("reading", 30, t("progress.readingNodeData"))

        filtered = reader.filter_defined_entities(
            graph_id=state.graph_id,
            defined_entity_types=defined_entity_types,
            enrich_with_edges=True,
        )

        state.entities_count = filtered.filtered_count
        state.entity_types = list(filtered.entity_types)

        if progress_callback:
            progress_callback(
                "reading",
                100,
                t("progress.readingComplete", count=filtered.filtered_count),
                current=filtered.filtered_count,
                total=filtered.filtered_count,
            )

        if filtered.filtered_count == 0:
            state.status = SimulationStatus.FAILED
            state.error = "没有找到符合条件的实体，请检查图谱是否正确构建"
            self._save_simulation_state(state)
            return state

        total_entities = len(filtered.entities)

        if progress_callback:
            progress_callback(
                "generating_profiles",
                0,
                t("progress.startGenerating"),
                current=0,
                total=total_entities,
            )

        generator = OasisProfileGenerator(graph_id=state.graph_id)

        def profile_progress(current, total, msg):
            if progress_callback:
                progress_callback(
                    "generating_profiles",
                    int(current / total * 100),
                    msg,
                    current=current,
                    total=total,
                    item_name=msg,
                )

        realtime_output_path = None
        realtime_platform = "reddit"
        if state.enable_reddit:
            realtime_output_path = os.path.join(sim_dir, "reddit_profiles.json")
            realtime_platform = "reddit"
        elif state.enable_twitter:
            realtime_output_path = os.path.join(sim_dir, "twitter_profiles.csv")
            realtime_platform = "twitter"

        profiles = generator.generate_profiles_from_entities(
            entities=filtered.entities,
            use_llm=use_llm_for_profiles,
            progress_callback=profile_progress,
            graph_id=state.graph_id,
            parallel_count=parallel_profile_count,
            realtime_output_path=realtime_output_path,
            output_platform=realtime_platform,
        )

        state.profiles_count = len(profiles)

        if progress_callback:
            progress_callback(
                "generating_profiles",
                95,
                t("progress.savingProfiles"),
                current=total_entities,
                total=total_entities,
            )

        if state.enable_reddit:
            generator.save_profiles(
                profiles=profiles,
                file_path=os.path.join(sim_dir, "reddit_profiles.json"),
                platform="reddit",
            )

        if state.enable_twitter:
            generator.save_profiles(
                profiles=profiles,
                file_path=os.path.join(sim_dir, "twitter_profiles.csv"),
                platform="twitter",
            )

        if progress_callback:
            progress_callback(
                "generating_profiles",
                100,
                t("progress.profilesComplete", count=len(profiles)),
                current=len(profiles),
                total=len(profiles),
            )

        if progress_callback:
            progress_callback(
                "generating_config",
                0,
                t("progress.analyzingRequirements"),
                current=0,
                total=3,
            )

        config_generator = SimulationConfigGenerator()

        if progress_callback:
            progress_callback(
                "generating_config",
                30,
                t("progress.callingLLMConfig"),
                current=1,
                total=3,
            )

        sim_params = config_generator.generate_config(
            simulation_id=state.simulation_id,
            project_id=state.project_id,
            graph_id=state.graph_id,
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            entities=filtered.entities,
            enable_twitter=state.enable_twitter,
            enable_reddit=state.enable_reddit,
        )

        if progress_callback:
            progress_callback(
                "generating_config",
                70,
                t("progress.savingConfigFiles"),
                current=2,
                total=3,
            )

        config_path = os.path.join(sim_dir, "simulation_config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(sim_params.to_json())

        state.config_generated = True
        state.config_reasoning = sim_params.generation_reasoning

        if progress_callback:
            progress_callback(
                "generating_config",
                100,
                t("progress.configComplete"),
                current=3,
                total=3,
            )

        state.status = SimulationStatus.READY
        self._save_simulation_state(state)

        logger.info(
            f"模拟准备完成: {state.simulation_id}, "
            f"entities={state.entities_count}, profiles={state.profiles_count}"
        )
        return state

    def _prepare_consumer_simulation(
        self,
        state: SimulationState,
        simulation_requirement: str,
        document_text: str,
        progress_callback: Optional[Callable[..., None]] = None,
    ) -> SimulationState:
        project = ProjectManager.get_project(state.project_id)
        if not project:
            raise ValueError(f"项目不存在: {state.project_id}")
        if not project.consumer_brief:
            raise ValueError("consumer_test project missing consumer_brief")

        brief = ConsumerBriefAdapter.from_payload(project.consumer_brief)
        persona_pack = load_default_persona_pack()
        sim_dir = self._get_simulation_dir(state.simulation_id)

        state.project_type = project.project_type or "default"
        state.consumer_mode = True
        state.entity_types = ["AudienceSegment"]
        state.entities_count = len(persona_pack)
        state.persona_pack_id = "default_persona_pack"
        state.pinned_brief_summary = self._build_consumer_brief_summary(brief)
        state.enable_lane_b = brief.enable_lane_b

        if progress_callback:
            progress_callback(
                "reading",
                100,
                state.pinned_brief_summary,
                current=state.entities_count,
                total=state.entities_count,
            )

        reddit_profiles: List[Dict[str, Any]] = []
        twitter_profiles: List[Dict[str, Any]] = []
        agent_configs: List[AgentActivityConfig] = []

        # Ingest any URL entries from optional_background_materials into Lane A
        ingest_background_url_sources(
            state.project_id,
            brief=brief,
            upload_root=Config.UPLOAD_FOLDER,
        )

        lane_b_provider = build_lane_b_provider(state.project_id, upload_root=Config.UPLOAD_FOLDER)

        total_personas = len(persona_pack)
        if progress_callback:
            progress_callback(
                "generating_profiles",
                0,
                t("progress.startGenerating"),
                current=0,
                total=total_personas,
            )

        for index, persona in enumerate(persona_pack):
            agent_traits = map_persona_to_agent_traits(persona)
            reddit_profiles.append(
                self._build_consumer_reddit_profile(
                    brief=brief,
                    agent_traits=agent_traits,
                    user_id=index,
                )
            )
            twitter_profiles.append(
                self._build_consumer_twitter_profile(
                    brief=brief,
                    agent_traits=agent_traits,
                    user_id=index,
                )
            )
            agent_configs.append(
                self._build_consumer_agent_config(
                    agent_traits=agent_traits,
                    user_id=index,
                )
            )

            if progress_callback:
                progress_callback(
                    "generating_profiles",
                    int(((index + 1) / total_personas) * 100),
                    agent_traits["label"],
                    current=index + 1,
                    total=total_personas,
                    item_name=agent_traits["label"],
                )

        state.profiles_count = len(reddit_profiles)

        if state.enable_reddit:
            self._write_json(
                os.path.join(sim_dir, "reddit_profiles.json"),
                reddit_profiles,
            )

        if state.enable_twitter:
            self._write_twitter_profiles_csv(
                os.path.join(sim_dir, "twitter_profiles.csv"),
                twitter_profiles,
            )

        config_payload = self._build_consumer_config_payload(
            state=state,
            brief=brief,
            simulation_requirement=simulation_requirement or brief.research_goal,
            document_text=document_text,
            agent_configs=agent_configs,
        )
        self._write_json(os.path.join(sim_dir, "simulation_config.json"), config_payload)
        research_findings = resolve_research_findings(
            brief,
            provider=default_auto_research_provider,
            project_id=state.project_id,
            upload_root=Config.UPLOAD_FOLDER,
            enable_lane_b=brief.enable_lane_b,
            lane_b_provider=lane_b_provider,
        )
        snapshot = build_research_snapshot(
            state.project_id,
            brief=brief,
            upload_root=Config.UPLOAD_FOLDER,
            provider=default_auto_research_provider,
            enable_lane_b=brief.enable_lane_b,
            lane_b_provider=lane_b_provider,
        )
        self._write_json(
            os.path.join(sim_dir, "consumer_config.json"),
            {
                "project_type": state.project_type,
                "consumer_mode": state.consumer_mode,
                "persona_pack_id": state.persona_pack_id,
                "pinned_brief_summary": state.pinned_brief_summary,
                "profiles_count": state.profiles_count,
                "consumer_brief": brief.to_summary(),
                "research_mode": brief.research_mode,
                "enable_lane_b": brief.enable_lane_b,
                "research_summary": build_research_summary(research_findings),
                "research_findings": [f.model_dump() for f in research_findings],
                "research_findings_count": len(research_findings),
                "auto_enrich_count": sum(
                    1 for f in research_findings if f.source_label == "auto_enrich"
                ),
                "manual_background_count": sum(
                    1 for f in research_findings if f.source_label == "brief_background"
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
                "retrieval_traces": [
                    t.model_dump() for t in snapshot.retrieval_traces
                ],
            },
        )

        state.config_generated = True
        state.config_reasoning = "Generated from consumer brief and default persona pack."
        state.status = SimulationStatus.READY
        self._save_simulation_state(state)

        if progress_callback:
            progress_callback(
                "generating_config",
                100,
                t("progress.configComplete"),
                current=1,
                total=1,
            )

        logger.info(
            f"Consumer simulation prepared: {state.simulation_id}, "
            f"profiles={state.profiles_count}"
        )
        return state

    def _build_consumer_config_payload(
        self,
        state: SimulationState,
        brief: ConsumerBusinessBrief,
        simulation_requirement: str,
        document_text: str,
        agent_configs: List[AgentActivityConfig],
    ) -> Dict[str, Any]:
        sim_params = SimulationParameters(
            simulation_id=state.simulation_id,
            project_id=state.project_id,
            graph_id=state.graph_id,
            simulation_requirement=simulation_requirement,
            time_config=TimeSimulationConfig(),
            agent_configs=agent_configs,
            event_config=EventConfig(
                hot_topics=list(brief.claims or brief.copy_material),
                narrative_direction=brief.research_goal,
            ),
            twitter_config=PlatformConfig(platform="twitter") if state.enable_twitter else None,
            reddit_config=PlatformConfig(platform="reddit") if state.enable_reddit else None,
            generation_reasoning="Generated from consumer brief and default persona pack.",
        )
        payload = sim_params.to_dict()
        payload.update(
            {
                "project_type": state.project_type,
                "consumer_mode": state.consumer_mode,
                "persona_pack_id": state.persona_pack_id,
                "pinned_brief_summary": state.pinned_brief_summary,
                "consumer_brief": brief.to_summary(),
                "document_summary": document_text[:500],
            }
        )
        return payload

    def _build_consumer_brief_summary(self, brief: ConsumerBusinessBrief) -> str:
        concepts = ", ".join(brief.product_concept_assets[:2])
        audience = ", ".join(brief.target_audience[:2]) or "general audience"
        return (
            f"{brief.task_type.value}: {brief.research_goal} | "
            f"Concepts: {concepts} | Audience: {audience}"
        )

    def _build_consumer_reddit_profile(
        self,
        brief: ConsumerBusinessBrief,
        agent_traits: Dict[str, Any],
        user_id: int,
    ) -> Dict[str, Any]:
        label = agent_traits["label"]
        username = self._build_consumer_username(label, user_id)
        attention = ", ".join(agent_traits["attention_drivers"])
        risks = ", ".join(agent_traits["risk_sensitivities"])
        return {
            "user_id": user_id,
            "username": username,
            "name": label,
            "bio": f"{label} reacting to {brief.research_goal}. Focuses on {attention}.",
            "persona": f"Sensitive to {risks}. Style: {agent_traits['expression_style']}.",
            "karma": int(1000 + float(agent_traits["influence_weight"]) * 1000),
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "profession": "Consumer cohort",
            "interested_topics": list(agent_traits["attention_drivers"]),
        }

    def _build_consumer_twitter_profile(
        self,
        brief: ConsumerBusinessBrief,
        agent_traits: Dict[str, Any],
        user_id: int,
    ) -> Dict[str, Any]:
        label = agent_traits["label"]
        username = self._build_consumer_username(label, user_id)
        description = f"{label} discussing {brief.research_goal}"
        user_char = (
            f"{description}. Attention drivers: "
            f"{', '.join(agent_traits['attention_drivers'])}. "
            f"Risk sensitivities: {', '.join(agent_traits['risk_sensitivities'])}. "
            f"Style: {agent_traits['expression_style']}."
        )
        return {
            "user_id": user_id,
            "name": label,
            "username": username,
            "user_char": user_char,
            "description": description,
        }

    def _build_consumer_agent_config(
        self,
        agent_traits: Dict[str, Any],
        user_id: int,
    ) -> AgentActivityConfig:
        influence_weight = float(agent_traits["influence_weight"])
        return AgentActivityConfig(
            agent_id=user_id,
            entity_uuid=agent_traits["persona_id"],
            entity_name=agent_traits["label"],
            entity_type="AudienceSegment",
            activity_level=max(0.2, min(1.0, influence_weight)),
            posts_per_hour=round(0.5 + influence_weight, 2),
            comments_per_hour=round(1.0 + influence_weight * 2, 2),
            active_hours=list(range(8, 23)),
            response_delay_min=5,
            response_delay_max=45,
            influence_weight=influence_weight,
        )

    def _build_consumer_username(self, label: str, user_id: int) -> str:
        cleaned = "".join(ch.lower() for ch in label if ch.isalnum())
        return f"{cleaned[:12]}_{user_id}"

    def _write_json(self, file_path: str, payload: Any) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _write_twitter_profiles_csv(self, file_path: str, rows: List[Dict[str, Any]]) -> None:
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["user_id", "name", "username", "user_char", "description"],
            )
            writer.writeheader()
            writer.writerows(rows)

    def get_simulation(self, simulation_id: str) -> Optional[SimulationState]:
        return self._load_simulation_state(simulation_id)

    def list_simulations(self, project_id: Optional[str] = None) -> List[SimulationState]:
        simulations = []

        if os.path.exists(self.SIMULATION_DATA_DIR):
            for sim_id in os.listdir(self.SIMULATION_DATA_DIR):
                sim_path = os.path.join(self.SIMULATION_DATA_DIR, sim_id)
                if sim_id.startswith(".") or not os.path.isdir(sim_path):
                    continue

                state = self._load_simulation_state(sim_id)
                if state and (project_id is None or state.project_id == project_id):
                    simulations.append(state)

        return simulations

    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"模拟不存在: {simulation_id}")

        sim_dir = self._get_simulation_dir(simulation_id)
        profile_path = os.path.join(sim_dir, f"{platform}_profiles.json")

        if not os.path.exists(profile_path):
            return []

        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")

        if not os.path.exists(config_path):
            return None

        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_run_instructions(self, simulation_id: str) -> Dict[str, str]:
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../scripts"))

        return {
            "simulation_dir": sim_dir,
            "scripts_dir": scripts_dir,
            "config_file": config_path,
            "commands": {
                "twitter": f"python {scripts_dir}/run_twitter_simulation.py --config {config_path}",
                "reddit": f"python {scripts_dir}/run_reddit_simulation.py --config {config_path}",
                "parallel": f"python {scripts_dir}/run_parallel_simulation.py --config {config_path}",
            },
            "instructions": (
                f"1. 激活 conda 环境: conda activate MiroFish\n"
                f"2. 运行模拟 (脚本位于 {scripts_dir}):\n"
                f"   - 单独运行Twitter: python {scripts_dir}/run_twitter_simulation.py --config {config_path}\n"
                f"   - 单独运行Reddit: python {scripts_dir}/run_reddit_simulation.py --config {config_path}\n"
                f"   - 并行运行双平台: python {scripts_dir}/run_parallel_simulation.py --config {config_path}"
            ),
        }
