"""Data models for Phase 6I consumer interviews and focus groups."""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..society.consumer_roles import ConsumerRole


class LiveInterviewUnavailable(Exception):
    """Raised when a live interview is requested but the environment is not running."""


VALID_INTERVIEW_MODES = {"snapshot", "live", "auto"}


@dataclass
class RepresentativeConsumerCard:
    agent_id: str
    display_name: str
    role: str
    segment: str
    channel_id: str
    attitude_start: str
    attitude_latest: str
    purchase_intent_start: float
    purchase_intent_latest: float
    key_quote: str
    influence_score: float
    evidence_ids: List[str] = field(default_factory=list)
    event_ids: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.role = ConsumerRole(self.role).value


@dataclass
class ConsumerInterviewRequest:
    simulation_id: str
    topic: str
    questions: List[str] = field(default_factory=list)
    agent_ids: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    mode: str = "snapshot"
    max_agents: int = 1
    target_context: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.mode = str(self.mode or "snapshot")
        if self.mode not in VALID_INTERVIEW_MODES:
            raise ValueError(f"Unsupported interview mode: {self.mode}")
        self.questions = list(self.questions or [])
        self.agent_ids = list(self.agent_ids or [])
        self.roles = list(self.roles or [])
        self.target_context = dict(self.target_context or {})
        self.max_agents = max(1, int(self.max_agents or 1))
        self.roles = [ConsumerRole(role).value for role in self.roles]


@dataclass
class ConsumerInterviewResult:
    interview_id: str
    simulation_id: str
    topic: str
    mode: str
    answers: List[Dict[str, Any]] = field(default_factory=list)
    evidence_map: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    followup_questions: List[str] = field(default_factory=list)


@dataclass
class FocusGroupSession:
    focus_group_id: str
    simulation_id: str
    topic: str
    moderator_goal: str = ""
    participant_cards: List[Dict[str, Any]] = field(default_factory=list)
    turns: List[Dict[str, Any]] = field(default_factory=list)
    consensus: List[str] = field(default_factory=list)
    disagreements: List[str] = field(default_factory=list)
    next_what_if_experiments: List[str] = field(default_factory=list)
    evidence_map: Dict[str, Any] = field(default_factory=dict)
