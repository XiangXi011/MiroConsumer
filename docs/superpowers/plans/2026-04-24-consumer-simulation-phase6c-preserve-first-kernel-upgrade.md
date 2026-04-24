# Consumer Simulation Phase 6C Preserve-First Kernel Upgrade Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the two core consumer simulation deficiencies - template-heavy output with near-zero quote diversity, and near-zero cross-round propagation dynamics - while preserving every existing consumer product contract, API surface, typed output, and test.

**Diagnosed Problems:**
1. **Template-heavy output:** `_generate_response()` selects from ~4 hardcoded f-strings (`"I keep thinking about {x}..."`, `"People would probably keep sharing {x}..."`, etc.), producing near-identical quotes across agents and rounds.
2. **Near-zero cross-round propagation:** No per-agent round state is maintained between rounds, so agents react only to the current round's visible nodes. Attitudes are nearly flat across rounds even when exposed to risk or social reinforcement.

**Architecture:** Keep `ConsumerSimulationOrchestrator` as the public facade; keep `SimulationRunner._run_consumer_simulation` and `run_branch_simulation` as the entry points; keep `report_agent._build_consumer_report_context` as the report consumer. Introduce a kernel adapter interface with three implementations: `LegacySimulationKernel` (preserves current deterministic fallback byte-for-byte), `HybridSimulationKernel` (uses previous-round state, visible findings, persona traits, and topology signals to produce varied quotes and meaningful attitude movement while keeping the output schema identical), and the adapter itself. All downstream typed outputs (`attitude_label`, `bucket`, `quote`, `visible_finding_ids`, `propagation_events`, consumer summary, report context, replay JSONL) remain identical in shape.

**Tech Stack:** Python 3.11+, Pydantic models, existing pytest suite

---

## What Stays, What Adapts, What Replaces, What Defers

### (1) Keep As-Is

| Layer | Files | Rationale |
|-------|-------|-----------|
| Data models | `consumer/models.py` | `PropagationEvent`, `ResearchFinding`, `ConsumerBusinessBrief`, `GraphVisibility`, `ConsumerTaskType` are the stable contract |
| Social topology | `consumer/social_topology.py` | `SocialTopology`, `build_social_topology()`, `select_topology_aware_targets()` are deterministic graph logic, not simulation core |
| Cascade metrics | `consumer/cascade_metrics.py` | `compute_cascade_metrics()` consumes event dicts post-hoc; no simulation dependency |
| Scoring & evidence | `consumer/scoring.py` | `ConsumerScoringService`, `build_consumer_summary()`, `ConsumerPhase2Summary`, `_extract_task_aware_fields()` are pure aggregation |
| Report context | `consumer/report_context.py` | `ConsumerReportContextBuilder`, `build_consumer_report_context()`, `enrich_report_context_with_snapshot()` consume snapshot/event dicts |
| Event taxonomy | `consumer/event_engine.py` | `classify_propagation_event()`, `build_propagation_event()`, `derive_trigger_from_findings()`, `derive_speech_act_from_bucket()` are stateless classifiers |
| Persona pack | `consumer/persona_pack.py` | `load_default_persona_pack()`, `map_persona_to_agent_traits()`, `can_access_deep_graph()` |
| Access policy | `consumer/access_policy.py` | `resolve_visible_findings()` |
| Evidence validation | `consumer/evidence_validator.py` | gatekeeping, validation, summary builders |
| Confidence scoring | `consumer/confidence_scoring.py` | `compute_report_confidence()`, `compute_finding_confidence()` |
| Source quality | `consumer/source_quality.py` | `evaluate_source()`, `evaluate_sources()` |
| Persistence | `consumer/project_research_persistence.py` | snapshot/chunk/finding persistence |
| Graph builder | `consumer/graph_builder.py` | `ConsumerGraphBuilder` |
| Intervention manager | `consumer/intervention_manager.py` | branch/fork/intervention CRUD |
| Brief adapter | `consumer/brief_adapter.py` | `ConsumerBriefAdapter.from_payload()` |
| API routes | route handlers | consumer routes remain unchanged |
| Frontend | all frontend files | Phase 6B just modularized; no frontend changes |
| Benchmark replay/report consumption | existing contract tests, replay scripts | schema shape unchanged |
| Scripts | `backend/scripts/run_parallel_simulation.py`, `backend/scripts/run_reddit_simulation.py` | OASIS platform scripts are untouched |

### (2) Keep But Adapt

| Layer | Files | What Changes |
|-------|-------|-------------|
| Orchestrator facade | `consumer/orchestrator.py` | `build_round_snapshot()` calls the kernel adapter instead of `_generate_response()`. Method signature gains an optional `kernel` parameter defaulted to `None`, which resolves to `LegacySimulationKernel` (preserve-first safety). `build_round_snapshot()` also accepts an optional `prior_state` dict for round-to-round propagation context. |
| Simulation runner consumer loops | `backend/app/services/simulation_runner.py` - `_run_consumer_simulation()`, `run_branch_simulation()` | The per-persona loop stays, but constructs a `HybridSimulationKernel` and maintains a `_consumer_agent_states` dict keyed by agent_id across rounds, passing prior state into each snapshot call. |
| Existing orchestrator tests | `backend/tests/consumer/test_orchestrator.py` | Must pass with the default kernel; snapshot contract unchanged. |
| Contract tests | `backend/tests/contracts/test_consumer_contracts.py` | Must continue to pass; output shape invariant. |
| Report agent consumer context | `backend/app/services/report_agent.py` - `_build_consumer_report_context()` | No changes needed if snapshot shape is preserved. Verified as safe by contract tests. |
| Replay compatibility checks | existing replay tests | Must pass because `consumer_rounds.jsonl` schema is unchanged. |

### (3) Replace

| Layer | Files | What Is Replaced |
|-------|-------|-----------------|
| Hardcoded `_generate_response` path | `consumer/orchestrator.py` lines 288-332 | The `if risk_nodes / if talking_nodes / if herd_tendency` rule block is replaced by a kernel adapter delegation. The method itself remains as thin pass-through. |
| Deterministic quote templating | `consumer/orchestrator.py` - the ~4 f-string templates inside `_generate_response()` | `HybridSimulationKernel` uses persona traits, finding text, topology signals, and prior-round state to produce varied quotes within the same schema. |
| Deterministic engagement formula | `consumer/orchestrator.py` line 178 | `engagement = max(1, min(10, int(round(3 + influence_weight * 7 + round_num))))` is delegated through the kernel; hybrid kernel adjusts engagement based on cumulative exposure. |
| Lack of persistent per-agent round state | `backend/app/services/simulation_runner.py` consumer paths | A `PropagationState` model tracks per-agent attitude history, engagement history, cumulative risk exposure, and social reinforcement count across rounds, fed into the hybrid kernel. |

### (4) Defer

| Item | Rationale |
|------|-----------|
| Full direct OASIS/native-kernel action streaming | The native kernel is built in a separate branch; this plan introduces the adapter interface so bridging is a later one-step swap |
| Replacing `backend/scripts/*.py` | Simulation scripts are OASIS-platform plumbing, not consumer logic |
| Frontend kernel-visibility UX | No frontend changes in this phase |
| Multi-tenant kernel configuration | The adapter interface supports it structurally but no config surface is added |

---

## File Map

### New Files

- Create: `backend/app/services/consumer/kernel_adapter.py` - adapter ABC, `SimulationKernelResult`
- Create: `backend/app/services/consumer/legacy_kernel.py` - `LegacySimulationKernel`: byte-for-byte preservation of current deterministic logic
- Create: `backend/app/services/consumer/hybrid_kernel.py` - `HybridSimulationKernel`: preserve-first kernel that uses prior-round state, persona traits, finding diversity, and topology signals
- Create: `backend/app/services/consumer/propagation_state.py` - `PropagationState` model: per-agent round-to-round state (attitude history, engagement history, cumulative risk exposure, social reinforcement count)
- Create: `backend/tests/consumer/test_kernel_adapter.py` - adapter contract tests
- Create: `backend/tests/consumer/test_hybrid_kernel.py` - hybrid kernel behavior tests (quote variety, attitude dynamics)
- Create: `backend/tests/consumer/test_consumer_dynamics.py` - end-to-end dynamics tests (multi-round propagation, attitude movement under risk exposure)

### Modified Files

- Modify: `backend/app/services/consumer/orchestrator.py` - wire adapter into `__init__`, `build_round_snapshot()`, and engagement formula; add optional `prior_state` parameter
- Modify: `backend/app/services/simulation_runner.py` - maintain `_consumer_agent_states` dict, construct `HybridSimulationKernel`, pass prior state into each snapshot call
- Modify: `backend/tests/consumer/test_orchestrator.py` - ensure existing tests pass with the default kernel
- Modify: `backend/app/services/consumer/__init__.py` - export new types

---

## Task 1: Lock Current Product Contract and Add Failing Behavior Guardrails

**Goal:** Freeze the output schema and add failing tests that prove the current code violates the desired dynamics (template-heavy output, near-zero attitude movement).

**Files:**
- Create: `backend/tests/consumer/test_consumer_dynamics.py`
- Create: `backend/tests/consumer/test_kernel_adapter.py` (partial - contract-only tests)

- [ ] **Step 1: Write schema contract tests (should already pass)**

Create `backend/tests/consumer/test_kernel_adapter.py` with contract tests that verify `SimulationKernelResult` fields, valid attitudes/buckets, and orchestrator snapshot key shape. These confirm the current schema without depending on any new kernel code.

```python
"""Contract tests for the simulation kernel adapter layer and output schema."""

from __future__ import annotations

import pytest

from app.services.consumer.kernel_adapter import (
    SimulationKernelAdapter,
    SimulationKernelResult,
)


class TestSimulationKernelResult:
    def test_fields(self):
        result = SimulationKernelResult(
            attitude_label="positive",
            bucket="resonance",
            quote="This sounds great.",
            engagement=7,
        )
        assert result.attitude_label == "positive"
        assert result.bucket == "resonance"
        assert result.quote == "This sounds great."
        assert result.engagement == 7

    def test_attitude_label_must_be_valid(self):
        with pytest.raises(ValueError, match="attitude_label"):
            SimulationKernelResult(
                attitude_label="excited",
                bucket="resonance",
                quote="test",
                engagement=5,
            )

    def test_bucket_must_be_valid(self):
        with pytest.raises(ValueError, match="bucket"):
            SimulationKernelResult(
                attitude_label="positive",
                bucket="confused",
                quote="test",
                engagement=5,
            )

    def test_engagement_must_be_in_bounds(self):
        for val in [1, 5, 10]:
            r = SimulationKernelResult(
                attitude_label="positive", bucket="resonance", quote="x", engagement=val
            )
            assert r.engagement == val
```

- [ ] **Step 2: Write behavior guardrail tests (should FAIL against current code)**

Create `backend/tests/consumer/test_consumer_dynamics.py` with tests that will fail against the existing deterministic logic but pass once the hybrid kernel is wired:

```python
"""Behavior guardrails: prove the current code is too template-heavy and flat."""

from __future__ import annotations

import pytest

from app.services.consumer.orchestrator import ConsumerSimulationOrchestrator


class TestQuoteVarietyGuardrails:
    """Across N agents seeing the same initial node, quotes must not be identical."""

    def test_initial_round_quotes_vary_across_agents(self):
        orch = ConsumerSimulationOrchestrator()
        quotes = set()
        for i in range(8):
            snap = orch.build_round_snapshot(
                round_num=0,
                agent_traits={"herd_tendency": "medium", "influence_weight": 0.5},
                brief_summary="New product launch",
                visible_graph_nodes=[
                    {"type": "Claim", "text": "affordable price", "visibility": "Initial"}
                ],
                agent_id=f"persona_{i:02d}",
                agent_name=f"Persona {i}",
            )
            quotes.add(snap["quote"].strip())
        # At least 3 distinct quotes across 8 agents with same inputs
        assert len(quotes) >= 3, f"Only {len(quotes)} distinct quotes: {quotes}"

    def test_propagation_round_quotes_differ_from_initial(self):
        orch = ConsumerSimulationOrchestrator()
        initial_quotes = set()
        prop_quotes = set()
        for i in range(4):
            snap0 = orch.build_round_snapshot(
                round_num=0,
                agent_traits={"herd_tendency": "medium", "influence_weight": 0.5},
                brief_summary="Test brief",
                visible_graph_nodes=[
                    {"type": "Claim", "text": "great value", "visibility": "Initial"}
                ],
                agent_id=f"persona_{i:02d}",
                agent_name=f"Persona {i}",
            )
            initial_quotes.add(snap0["quote"].strip())
            snap1 = orch.build_round_snapshot(
                round_num=1,
                agent_traits={"herd_tendency": "medium", "influence_weight": 0.5},
                brief_summary="Test brief",
                visible_graph_nodes=[
                    {"type": "Claim", "text": "great value", "visibility": "Initial"},
                    {"type": "Entity", "text": "word of mouth", "visibility": "Propagation_Only"},
                ],
                agent_id=f"persona_{i:02d}",
                agent_name=f"Persona {i}",
            )
            prop_quotes.add(snap1["quote"].strip())
        # Propagation quotes should not be a subset of initial quotes
        assert not prop_quotes.issubset(initial_quotes), (
            f"Propagation quotes are identical to initial: {prop_quotes}"
        )


class TestAttitudeDynamicsGuardrails:
    """Agents exposed to sustained risk should show attitude movement across rounds."""

    def test_sustained_risk_exposure_moves_attitude_negative(self):
        orch = ConsumerSimulationOrchestrator()
        attitudes = []
        for round_num in range(4):
            snap = orch.build_round_snapshot(
                round_num=round_num,
                agent_traits={"herd_tendency": "low", "influence_weight": 0.3},
                brief_summary="Risky product",
                visible_graph_nodes=[
                    {"type": "RiskPoint", "text": "safety concern", "visibility": "Initial"},
                    {"type": "RiskPoint", "text": "regulatory risk", "visibility": "Initial"},
                ],
                agent_id="persona_00",
                agent_name="Skeptic",
            )
            attitudes.append(snap["attitude_label"])
        # After 4 rounds of sustained risk, attitude should trend negative
        assert attitudes[-1] == "negative", f"Final attitude not negative: {attitudes}"
        # At least one attitude change across the 4 rounds (not flat)
        assert len(set(attitudes)) >= 2, f"Attitude completely flat: {attitudes}"
```

- [ ] **Step 3: Run the guardrail tests to confirm they fail**

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
python -m pytest backend/tests/consumer/test_kernel_adapter.py backend/tests/consumer/test_consumer_dynamics.py -v
```

Expected: contract tests pass, `test_initial_round_quotes_vary_across_agents` and `test_sustained_risk_exposure_moves_attitude_negative` FAIL (confirming the diagnosed problems).

- [ ] **Step 4: Commit the guardrails**

```bash
git add backend/tests/consumer/test_kernel_adapter.py backend/tests/consumer/test_consumer_dynamics.py
git commit -m "test: add schema contract tests and failing behavior guardrails for consumer dynamics"
```

---

## Task 2: Introduce Kernel Adapter and Legacy Kernel Fallback

**Goal:** Create the adapter ABC and `LegacySimulationKernel` that preserves the current deterministic logic byte-for-byte.

**Files:**
- Create: `backend/app/services/consumer/kernel_adapter.py`
- Create: `backend/app/services/consumer/legacy_kernel.py`

- [ ] **Step 1: Implement the kernel adapter ABC and `SimulationKernelResult`**

Create `backend/app/services/consumer/kernel_adapter.py`:

```python
"""Simulation kernel adapter interface.

Decouples the consumer orchestrator from simulation generation logic.
Implementations: LegacySimulationKernel (deterministic fallback),
HybridSimulationKernel (preserve-first with dynamics).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional


_VALID_ATTITUDES = {"positive", "neutral", "negative"}
_VALID_BUCKETS = {"resonance", "risk", "question", "misread"}


@dataclass(frozen=True)
class SimulationKernelResult:
    """Typed output from a single agent-round kernel invocation."""

    attitude_label: str
    bucket: str
    quote: str
    engagement: int

    def __post_init__(self) -> None:
        if self.attitude_label not in _VALID_ATTITUDES:
            raise ValueError(
                f"attitude_label must be one of {_VALID_ATTITUDES}, got {self.attitude_label!r}"
            )
        if self.bucket not in _VALID_BUCKETS:
            raise ValueError(
                f"bucket must be one of {_VALID_BUCKETS}, got {self.bucket!r}"
            )


class SimulationKernelAdapter(ABC):
    """Interface that any simulation kernel must implement."""

    @abstractmethod
    def generate_response(
        self,
        round_num: int,
        agent_traits: Mapping[str, Any],
        visible_nodes: List[Mapping[str, Any]],
        prior_state: Optional[Mapping[str, Any]] = None,
    ) -> SimulationKernelResult:
        """Generate attitude, bucket, quote for one agent in one round."""
        ...

    @abstractmethod
    def compute_engagement(
        self,
        influence_weight: float,
        round_num: int,
        prior_state: Optional[Mapping[str, Any]] = None,
    ) -> int:
        """Compute engagement score (1-10) for one agent in one round."""
        ...


__all__ = [
    "SimulationKernelAdapter",
    "SimulationKernelResult",
]
```

- [ ] **Step 2: Implement `LegacySimulationKernel`**

Create `backend/app/services/consumer/legacy_kernel.py`:

```python
"""Legacy deterministic simulation kernel - byte-for-byte preservation.

This kernel produces identical output to the pre-Phase6C
ConsumerSimulationOrchestrator._generate_response() and engagement formula.
Used as the safe fallback when no hybrid kernel is configured.
"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional

from .kernel_adapter import SimulationKernelAdapter, SimulationKernelResult


class LegacySimulationKernel(SimulationKernelAdapter):

    def generate_response(
        self,
        round_num: int,
        agent_traits: Mapping[str, Any],
        visible_nodes: List[Mapping[str, Any]],
        prior_state: Optional[Mapping[str, Any]] = None,
    ) -> SimulationKernelResult:
        risk_nodes = [node for node in visible_nodes if node.get("type") == "RiskPoint"]
        talking_nodes = [node for node in visible_nodes if node.get("type") != "RiskPoint"]

        if risk_nodes:
            risk_text = risk_nodes[0]["text"]
            return SimulationKernelResult(
                attitude_label="negative",
                bucket="risk",
                quote=f"I keep thinking about {risk_text}, so the claim starts to feel less trustworthy.",
                engagement=0,
            )

        if round_num >= 1 and talking_nodes:
            topic_text = talking_nodes[0]["text"]
            herd_tendency = str(agent_traits.get("herd_tendency", "medium")).strip().lower()
            if herd_tendency == "high":
                return SimulationKernelResult(
                    attitude_label="positive",
                    bucket="resonance",
                    quote=f"People would probably keep sharing {topic_text}, and that makes the idea feel credible.",
                    engagement=0,
                )
            return SimulationKernelResult(
                attitude_label="neutral",
                bucket="question",
                quote=f"I keep seeing {topic_text}, but I still want more proof before I fully buy in.",
                engagement=0,
            )

        if talking_nodes:
            topic_text = talking_nodes[0]["text"]
            return SimulationKernelResult(
                attitude_label="positive",
                bucket="resonance",
                quote=f"This actually sounds like a practical fix because of {topic_text}.",
                engagement=0,
            )

        return SimulationKernelResult(
            attitude_label="neutral",
            bucket="question",
            quote="I understand the pitch, but I need more concrete proof before reacting strongly.",
            engagement=0,
        )

    def compute_engagement(
        self,
        influence_weight: float,
        round_num: int,
        prior_state: Optional[Mapping[str, Any]] = None,
    ) -> int:
        return max(1, min(10, int(round(3 + influence_weight * 7 + round_num))))


__all__ = ["LegacySimulationKernel"]
```

- [ ] **Step 3: Update `__init__.py` exports**

In `backend/app/services/consumer/__init__.py`, add:

```python
from .kernel_adapter import SimulationKernelAdapter, SimulationKernelResult
from .legacy_kernel import LegacySimulationKernel
```

and add to `__all__`:

```python
"SimulationKernelAdapter",
"SimulationKernelResult",
"LegacySimulationKernel",
```

- [ ] **Step 4: Run adapter contract tests to confirm they pass**

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
python -m pytest backend/tests/consumer/test_kernel_adapter.py -v
```

Expected: all contract tests pass.

- [ ] **Step 5: Commit the adapter and legacy kernel**

```bash
git add backend/app/services/consumer/kernel_adapter.py backend/app/services/consumer/legacy_kernel.py backend/app/services/consumer/__init__.py
git commit -m "refactor: introduce kernel adapter ABC and legacy deterministic kernel fallback"
```

---

## Task 3: Implement Hybrid Kernel and Propagation State Model

**Goal:** Build `HybridSimulationKernel` and `PropagationState` that use previous-round state, visible findings, persona traits, and topology signals to produce varied quotes and meaningful attitude movement, while keeping the output schema unchanged.

**Files:**
- Create: `backend/app/services/consumer/propagation_state.py`
- Create: `backend/app/services/consumer/hybrid_kernel.py`
- Create: `backend/tests/consumer/test_hybrid_kernel.py`

- [ ] **Step 1: Implement `PropagationState` model**

Create `backend/app/services/consumer/propagation_state.py`:

```python
"""Per-agent round-to-round propagation state for the hybrid kernel.

Tracks attitude history, engagement history, cumulative risk exposure,
and social reinforcement count so the hybrid kernel can produce
cross-round dynamics without changing the output schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PropagationState:
    """Mutable per-agent state carried across simulation rounds."""

    agent_id: str
    attitude_history: List[str] = field(default_factory=list)
    engagement_history: List[int] = field(default_factory=list)
    cumulative_risk_exposure: int = 0
    social_reinforcement_count: int = 0
    last_bucket: Optional[str] = None
    rounds_seen_propagation_only: int = 0

    def update(
        self,
        attitude_label: str,
        engagement: int,
        bucket: str,
        visible_nodes: List[Dict[str, Any]],
    ) -> None:
        """Update state after a round completes."""
        self.attitude_history.append(attitude_label)
        self.engagement_history.append(engagement)
        self.last_bucket = bucket

        risk_count = sum(1 for n in visible_nodes if n.get("type") == "RiskPoint")
        self.cumulative_risk_exposure += risk_count

        prop_only = all(n.get("visibility") == "Propagation_Only" for n in visible_nodes)
        if prop_only and visible_nodes:
            self.rounds_seen_propagation_only += 1

        if bucket in ("resonance",):
            self.social_reinforcement_count += 1

    def to_prior_state_dict(self) -> Dict[str, Any]:
        """Serialize for passing into kernel.generate_response()."""
        return {
            "agent_id": self.agent_id,
            "attitude_history": list(self.attitude_history),
            "engagement_history": list(self.engagement_history),
            "cumulative_risk_exposure": self.cumulative_risk_exposure,
            "social_reinforcement_count": self.social_reinforcement_count,
            "last_bucket": self.last_bucket,
            "rounds_seen_propagation_only": self.rounds_seen_propagation_only,
        }


def create_initial_state(agent_id: str) -> PropagationState:
    """Factory for a fresh PropagationState."""
    return PropagationState(agent_id=agent_id)


__all__ = ["PropagationState", "create_initial_state"]
```

- [ ] **Step 2: Implement `HybridSimulationKernel`**

Create `backend/app/services/consumer/hybrid_kernel.py`:

```python
"""Hybrid simulation kernel - preserve-first with dynamics.

Uses prior-round state, persona traits, finding diversity, and topology
signals to produce varied quotes and meaningful attitude movement.
Output schema is identical to LegacySimulationKernel.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any, Dict, List, Mapping, Optional

from .kernel_adapter import SimulationKernelAdapter, SimulationKernelResult

# Quote pools keyed by (attitude, bucket). Each template has {subject} and {detail} slots.
_QUOTE_POOLS = {
    ("negative", "risk"): [
        "I keep thinking about {detail}, so the claim starts to feel less trustworthy.",
        "The fact that {detail} keeps coming up worries me - it undermines confidence.",
        "Every time I hear about {detail}, I trust this less.",
        "{detail} is a real problem. I can't ignore it after seeing it again.",
        "I'm increasingly concerned about {detail}. This doesn't add up.",
    ],
    ("positive", "resonance"): [
        "This actually sounds like a practical fix because of {detail}.",
        "People would probably keep sharing {detail}, and that makes the idea feel credible.",
        "After seeing {detail} come up repeatedly, I'm convinced there's something here.",
        "{detail} keeps reinforcing my positive impression. It really works.",
        "The more I think about {detail}, the more I believe in this approach.",
    ],
    ("neutral", "question"): [
        "I keep seeing {detail}, but I still want more proof before I fully buy in.",
        "{detail} is interesting, but I need to see more before deciding.",
        "I understand the pitch about {detail}, but I need more concrete proof before reacting strongly.",
        "The point about {detail} is valid, yet I'm not fully persuaded yet.",
        "{detail} is worth noting, though it alone doesn't convince me.",
    ],
    ("neutral", "misread"): [
        "I'm not sure I fully understood the point about {detail}.",
        "Something about {detail} feels like it's being oversimplified.",
    ],
}

_DEFAULT_QUOTE = "I understand the pitch, but I need more concrete proof before reacting strongly."

# Attitude shift thresholds
_RISK_CUMULATIVE_NEGATIVE_THRESHOLD = 2
_REINFORCEMENT_POSITIVE_THRESHOLD = 3
_PROPAGATION_ONLY_PATIENCE_LIMIT = 3


def _seeded_rng(round_num: int, agent_id: str, bucket: str) -> random.Random:
    """Deterministic RNG seeded from agent identity + round + bucket."""
    seed_str = f"{agent_id}:{round_num}:{bucket}"
    seed = int(hashlib.sha256(seed_str.encode()).hexdigest()[:8], 16)
    return random.Random(seed)


def _pick_quote(
    attitude: str,
    bucket: str,
    detail: str,
    round_num: int,
    agent_id: str,
) -> str:
    """Select a quote from the pool, deterministically varied by agent+round."""
    pools = _QUOTE_POOLS.get((attitude, bucket))
    if not pools:
        return _DEFAULT_QUOTE
    rng = _seeded_rng(round_num, agent_id, bucket)
    template = rng.choice(pools)
    return template.format(detail=detail)


def _resolve_subject(visible_nodes: List[Mapping[str, Any]]) -> str:
    """Extract the most relevant subject text from visible nodes."""
    risk_nodes = [n for n in visible_nodes if n.get("type") == "RiskPoint"]
    if risk_nodes:
        return risk_nodes[0].get("text", "this concern")
    non_risk = [n for n in visible_nodes if n.get("type") != "RiskPoint"]
    if non_risk:
        return non_risk[0].get("text", "this point")
    return "this topic"


class HybridSimulationKernel(SimulationKernelAdapter):
    """Preserve-first kernel with cross-round propagation dynamics.

    Produces varied quotes via pooled templates and meaningful attitude
    movement based on cumulative risk exposure, social reinforcement,
    and propagation-only patience. Output schema matches LegacySimulationKernel.
    """

    def generate_response(
        self,
        round_num: int,
        agent_traits: Mapping[str, Any],
        visible_nodes: List[Mapping[str, Any]],
        prior_state: Optional[Mapping[str, Any]] = None,
    ) -> SimulationKernelResult:
        herd_tendency = str(agent_traits.get("herd_tendency", "medium")).strip().lower()
        detail = _resolve_subject(visible_nodes)

        risk_nodes = [n for n in visible_nodes if n.get("type") == "RiskPoint"]
        talking_nodes = [n for n in visible_nodes if n.get("type") != "RiskPoint"]

        # Base determination (preserve-first: same primary logic as legacy)
        if risk_nodes:
            attitude = "negative"
            bucket = "risk"
        elif round_num >= 1 and talking_nodes:
            if herd_tendency == "high":
                attitude = "positive"
                bucket = "resonance"
            else:
                attitude = "neutral"
                bucket = "question"
        elif talking_nodes:
            attitude = "positive"
            bucket = "resonance"
        else:
            attitude = "neutral"
            bucket = "question"

        # Cross-round adjustments from prior state
        if prior_state:
            cum_risk = prior_state.get("cumulative_risk_exposure", 0)
            reinforcement = prior_state.get("social_reinforcement_count", 0)
            prop_only_rounds = prior_state.get("rounds_seen_propagation_only", 0)
            attitude_hist = prior_state.get("attitude_history", [])

            # Sustained cumulative risk pushes attitude negative
            if cum_risk >= _RISK_CUMULATIVE_NEGATIVE_THRESHOLD and attitude != "negative":
                attitude = "negative"
                bucket = "risk"

            # Repeated social reinforcement pulls toward positive
            elif reinforcement >= _REINFORCEMENT_POSITIVE_THRESHOLD and attitude == "neutral":
                attitude = "positive"
                bucket = "resonance"

            # Patience erosion: agent seeing only propagation-only info for too long
            elif prop_only_rounds >= _PROPAGATION_ONLY_PATIENCE_LIMIT and attitude == "neutral":
                bucket = "misread"

        quote = _pick_quote(attitude, bucket, detail, round_num, prior_state.get("agent_id", "") if prior_state else "")

        return SimulationKernelResult(
            attitude_label=attitude,
            bucket=bucket,
            quote=quote,
            engagement=0,  # caller uses compute_engagement()
        )

    def compute_engagement(
        self,
        influence_weight: float,
        round_num: int,
        prior_state: Optional[Mapping[str, Any]] = None,
    ) -> int:
        base = max(1, min(10, int(round(3 + influence_weight * 7 + round_num))))
        if prior_state:
            # Engagement dampens slightly with repeated negative exposure
            cum_risk = prior_state.get("cumulative_risk_exposure", 0)
            if cum_risk >= _RISK_CUMULATIVE_NEGATIVE_THRESHOLD:
                base = max(1, base - 1)
            # Engagement boosts with social reinforcement
            reinforcement = prior_state.get("social_reinforcement_count", 0)
            if reinforcement >= _REINFORCEMENT_POSITIVE_THRESHOLD:
                base = min(10, base + 1)
        return base


__all__ = ["HybridSimulationKernel"]
```

- [ ] **Step 3: Write hybrid kernel tests**

Create `backend/tests/consumer/test_hybrid_kernel.py`:

```python
"""Tests for the HybridSimulationKernel and PropagationState."""

from __future__ import annotations

import pytest

from app.services.consumer.hybrid_kernel import HybridSimulationKernel
from app.services.consumer.propagation_state import PropagationState, create_initial_state


class TestHybridKernelQuoteVariety:
    """Verify that the hybrid kernel produces varied quotes across agents."""

    def test_quotes_vary_across_agents_same_round(self):
        kernel = HybridSimulationKernel()
        quotes = set()
        for i in range(8):
            result = kernel.generate_response(
                round_num=0,
                agent_traits={"herd_tendency": "medium", "influence_weight": 0.5},
                visible_nodes=[
                    {"type": "Claim", "text": "affordable price", "visibility": "Initial"}
                ],
                prior_state={"agent_id": f"persona_{i:02d}"},
            )
            quotes.add(result.quote)
        assert len(quotes) >= 3, f"Only {len(quotes)} distinct quotes across 8 agents"

    def test_quotes_differ_across_rounds_same_agent(self):
        kernel = HybridSimulationKernel()
        quotes = set()
        for rn in range(4):
            result = kernel.generate_response(
                round_num=rn,
                agent_traits={"herd_tendency": "medium", "influence_weight": 0.5},
                visible_nodes=[
                    {"type": "Claim", "text": "good value", "visibility": "Initial"}
                ],
                prior_state={"agent_id": "persona_00"},
            )
            quotes.add(result.quote)
        assert len(quotes) >= 2, f"Quotes identical across 4 rounds: {quotes}"


class TestHybridKernelAttitudeDynamics:
    """Verify cross-round attitude movement."""

    def test_sustained_risk_moves_attitude_negative(self):
        kernel = HybridSimulationKernel()
        state = create_initial_state("persona_00")
        nodes = [
            {"type": "RiskPoint", "text": "safety concern", "visibility": "Initial"},
            {"type": "RiskPoint", "text": "regulatory risk", "visibility": "Initial"},
        ]
        attitudes = []
        for rn in range(4):
            result = kernel.generate_response(
                round_num=rn,
                agent_traits={"herd_tendency": "low", "influence_weight": 0.3},
                visible_nodes=nodes,
                prior_state=state.to_prior_state_dict(),
            )
            attitudes.append(result.attitude_label)
            state.update(result.attitude_label, result.engagement, result.bucket, nodes)
        assert attitudes[-1] == "negative", f"Final attitude not negative: {attitudes}"

    def test_repeated_reinforcement_moves_toward_positive(self):
        kernel = HybridSimulationKernel()
        state = create_initial_state("persona_01")
        attitudes = []
        for rn in range(5):
            result = kernel.generate_response(
                round_num=rn,
                agent_traits={"herd_tendency": "high", "influence_weight": 0.8},
                visible_nodes=[
                    {"type": "Claim", "text": "great taste", "visibility": "Initial"}
                ],
                prior_state=state.to_prior_state_dict(),
            )
            attitudes.append(result.attitude_label)
            state.update(result.attitude_label, result.engagement, result.bucket, [
                {"type": "Claim", "text": "great taste", "visibility": "Initial"}
            ])
        assert "positive" in attitudes

    def test_schema_matches_legacy(self):
        """Output must have same keys and value types as legacy."""
        kernel = HybridSimulationKernel()
        result = kernel.generate_response(
            round_num=0,
            agent_traits={"herd_tendency": "medium", "influence_weight": 0.5},
            visible_nodes=[{"type": "Entity", "text": "x", "visibility": "Initial"}],
            prior_state={"agent_id": "p1"},
        )
        assert result.attitude_label in {"positive", "neutral", "negative"}
        assert result.bucket in {"resonance", "risk", "question", "misread"}
        assert isinstance(result.quote, str) and len(result.quote) > 0
        assert isinstance(result.engagement, int)


class TestPropagationState:
    def test_update_tracks_history(self):
        state = create_initial_state("p1")
        state.update("positive", 5, "resonance", [{"type": "Claim", "text": "x", "visibility": "Initial"}])
        state.update("negative", 3, "risk", [{"type": "RiskPoint", "text": "y", "visibility": "Initial"}])
        d = state.to_prior_state_dict()
        assert d["attitude_history"] == ["positive", "negative"]
        assert d["cumulative_risk_exposure"] == 1
        assert d["social_reinforcement_count"] == 1

    def test_propagation_only_tracking(self):
        state = create_initial_state("p1")
        nodes = [{"type": "Entity", "text": "word of mouth", "visibility": "Propagation_Only"}]
        state.update("neutral", 4, "question", nodes)
        state.update("neutral", 4, "question", nodes)
        d = state.to_prior_state_dict()
        assert d["rounds_seen_propagation_only"] == 2
```

- [ ] **Step 4: Run hybrid kernel tests**

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
python -m pytest backend/tests/consumer/test_hybrid_kernel.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit hybrid kernel and propagation state**

```bash
git add backend/app/services/consumer/hybrid_kernel.py backend/app/services/consumer/propagation_state.py backend/tests/consumer/test_hybrid_kernel.py backend/app/services/consumer/__init__.py
git commit -m "feat: add HybridSimulationKernel with cross-round propagation dynamics and PropagationState model"
```

---

## Task 4: Wire Simulation Runner Consumer and Branch Paths to Maintain and Feed Round-to-Round State

**Goal:** Update `simulation_runner.py` to maintain a `_consumer_agent_states` dict across rounds and pass prior state into each snapshot call, while keeping `consumer_rounds.jsonl` schema unchanged. Update orchestrator to accept kernel + prior_state.

**Files:**
- Modify: `backend/app/services/consumer/orchestrator.py`
- Modify: `backend/app/services/simulation_runner.py`

- [ ] **Step 1: Wire kernel adapter into `ConsumerSimulationOrchestrator`**

In `backend/app/services/consumer/orchestrator.py`:

1. Add import:
```python
from .kernel_adapter import SimulationKernelAdapter, SimulationKernelResult
from .legacy_kernel import LegacySimulationKernel
```

2. Update `__init__`:
```python
class ConsumerSimulationOrchestrator:
    def __init__(
        self,
        output_path: Optional[Path | str] = None,
        topology: Optional[SocialTopology] = None,
        kernel: Optional[SimulationKernelAdapter] = None,
    ):
        self.output_path = Path(output_path) if output_path is not None else None
        self._topology = topology or build_social_topology()
        self._kernel = kernel or LegacySimulationKernel()
```

3. Replace `_generate_response()` body (lines 288-332) with:
```python
def _generate_response(
    self,
    round_num: int,
    agent_traits: Mapping[str, Any],
    visible_nodes: List[Mapping[str, Any]],
    prior_state: Optional[Mapping[str, Any]] = None,
) -> tuple[str, str, str]:
    result = self._kernel.generate_response(
        round_num=round_num,
        agent_traits=agent_traits,
        visible_nodes=visible_nodes,
        prior_state=prior_state,
    )
    return result.attitude_label, result.bucket, result.quote
```

4. Update `build_round_snapshot()` engagement formula (around line 178) from:
```python
engagement = max(1, min(10, int(round(3 + influence_weight * 7 + round_num))))
```
to:
```python
engagement = self._kernel.compute_engagement(influence_weight, round_num, prior_state=prior_state)
```

5. Add `prior_state` parameter to `build_round_snapshot()` signature, preserving existing optional parameters:
```python
def build_round_snapshot(
    self,
    round_num: int,
    agent_traits: Mapping[str, Any],
    brief_summary: str,
    visible_graph_nodes: List[Mapping[str, Any]],
    agent_id: str,
    agent_name: str,
    research_findings: Optional[Iterable[ResearchFinding]] = None,
    task_type: Optional[str] = None,
    prior_state: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
```

6. Pass `prior_state` through to `_generate_response()` call inside `build_round_snapshot()`.

- [ ] **Step 2: Maintain agent state dict in `simulation_runner.py`**

In `backend/app/services/simulation_runner.py`:

1. Add import:
```python
from .consumer.hybrid_kernel import HybridSimulationKernel
from .consumer.propagation_state import PropagationState, create_initial_state
```

2. In `_run_consumer_simulation()` (around line 544):
```python
kernel = HybridSimulationKernel()
orchestrator = ConsumerSimulationOrchestrator(output_path=output_path, kernel=kernel)
agent_states: Dict[str, PropagationState] = {}
```

3. Inside the per-persona loop, before `build_round_snapshot()`:
```python
if agent_id not in agent_states:
    agent_states[agent_id] = create_initial_state(agent_id)
prior_state = agent_states[agent_id].to_prior_state_dict()
```

4. Pass `prior_state=prior_state` to `orchestrator.build_round_snapshot(...)`.

5. After snapshot is built, update state using snapshot fields already available in scope:
```python
agent_states[agent_id].update(
    attitude_label=snapshot["attitude_label"],
    engagement=snapshot["engagement"],
    bucket=snapshot["bucket"],
    visible_nodes=snapshot.get("visible_nodes", snapshot.get("visible_graph_nodes", [])),
)
```

6. Repeat the same pattern in `run_branch_simulation()` (around line 708).

- [ ] **Step 3: Run existing orchestrator tests**

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
python -m pytest backend/tests/consumer/test_orchestrator.py -v
```

Expected: all existing tests pass (they don't pass `prior_state`, so the hybrid kernel falls back to base behavior).

- [ ] **Step 4: Run behavior guardrail tests**

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
python -m pytest backend/tests/consumer/test_consumer_dynamics.py -v
```

Expected: previously-failing guardrail tests now PASS (quote variety and attitude dynamics).

- [ ] **Step 5: Run full consumer test suite**

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
python -m pytest backend/tests/consumer/ backend/tests/api/test_consumer_routes.py backend/tests/api/test_consumer_canonical_routes.py backend/tests/contracts/test_consumer_contracts.py backend/tests/api/test_consumer_interventions.py -v
```

Expected: all tests pass. JSONL schema unchanged.

- [ ] **Step 6: Commit the wiring**

```bash
git add backend/app/services/consumer/orchestrator.py backend/app/services/simulation_runner.py
git commit -m "feat: wire HybridSimulationKernel into orchestrator and simulation runner with round-to-round state"
```

---

## Task 5: Verify Summary/Report/Replay Compatibility and Full Consumer Regression

**Goal:** Confirm that the hybrid kernel produces compatible inputs for summary, report, and replay consumers.

**Files:**
- Verify only (no code changes unless a fix is needed)

- [ ] **Step 1: Run the full consumer regression suite**

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
python -m pytest backend/tests/consumer/ backend/tests/api/test_consumer_routes.py backend/tests/api/test_consumer_canonical_routes.py backend/tests/contracts/test_consumer_contracts.py backend/tests/api/test_consumer_interventions.py -v
```

Expected: all tests pass. JSONL entries contain the same keys: `round_num`, `agent_id`, `agent_name`, `prompt`, `visible_nodes`, `visible_finding_ids`, `attitude_label`, `bucket`, `quote`, `engagement`, `propagation_events`.

- [ ] **Step 2: Confirm report agent consumer report still builds**

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
python -m pytest backend/tests/ -k "report" -v
```

Expected: report-related tests pass.

- [ ] **Step 3: Run all backend tests to catch transitive regressions**

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
python -m pytest backend/tests/ -v --tb=short
```

Expected: all tests pass.

- [ ] **Step 4: Confirm measurable acceptance criteria**

Checklist:

- [ ] `ConsumerSimulationOrchestrator` accepts an optional `kernel` parameter; defaults to `LegacySimulationKernel` for preserve-first safety
- [ ] `simulation_runner` consumer and branch paths explicitly construct `HybridSimulationKernel` and pass it to the orchestrator
- [ ] `build_round_snapshot()` accepts an optional `prior_state` parameter for cross-round propagation
- [ ] `_generate_response()` body is replaced by a one-line delegation through `self._kernel.generate_response()`
- [ ] Engagement formula in `build_round_snapshot()` delegates through `self._kernel.compute_engagement()`
- [ ] `consumer_rounds.jsonl` entries contain the same keys and value types as before the change
- [ ] Across 8 agents with identical inputs, at least 3 distinct quotes are produced (was 1)
- [ ] Under sustained risk exposure, agent attitude trends negative across rounds (was flat)
- [ ] `PropagationState` correctly tracks attitude history, risk exposure, and reinforcement across rounds
- [ ] `build_consumer_summary()` and `build_consumer_report_context()` receive compatible inputs
- [ ] `PropagationEvent` objects produced by `build_propagation_events_for_transition()` are unchanged in shape
- [ ] All existing backend tests pass without modification
- [ ] `LegacySimulationKernel` produces byte-identical output to the pre-change orchestrator logic
- [ ] `HybridSimulationKernel` output schema matches `LegacySimulationKernel` (same fields, same valid values)
- [ ] `SimulationRunner._run_consumer_simulation()` and `run_branch_simulation()` maintain agent state across rounds

- [ ] **Step 5: Commit any fixes (if needed)**

If any verification surfaced a regression, fix and commit. Otherwise no commit needed.

---

## Final Verification

- [ ] Run the complete consumer test suite

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
python -m pytest backend/tests/consumer/ backend/tests/api/test_consumer_routes.py backend/tests/api/test_consumer_canonical_routes.py backend/tests/contracts/test_consumer_contracts.py backend/tests/api/test_consumer_interventions.py -v
```

- [ ] Run all backend tests to catch transitive regressions

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
python -m pytest backend/tests/ -v --tb=short
```

- [ ] Confirm behavior guardrails pass

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
python -m pytest backend/tests/consumer/test_consumer_dynamics.py backend/tests/consumer/test_hybrid_kernel.py -v
```

---

## Notes for Execution

- Execute against `D:\project\MiroFish\.worktrees\phase5a-identity`, not the root `main` worktree
- The Phase 6B plan is at `docs/superpowers/plans/2026-04-23-consumer-simulation-phase6b-workspace-modularization.md`
- Do not modify frontend code, API routes, or persistence behavior
- `LegacySimulationKernel` is a direct port of the existing `_generate_response()` logic - any behavioral difference is a bug
- `HybridSimulationKernel` is not the orchestrator default: it is explicitly constructed by `simulation_runner` consumer and branch paths, preserving a safe legacy default at the facade while adding cross-round state, quote variety, and attitude dynamics only on the runner path
- The adapter interface accepts `prior_state: Optional[Mapping[str, Any]]` so legacy callers that don't pass it get unchanged behavior
- Phase6C improves consumer dynamics inside the current contract; a later phase can bridge to the full MiroFish native kernel through the adapter if the behavior proves stable
- When the MiroFish kernel is ready, create `MiroFishKernel(SimulationKernelAdapter)` and pass it to the orchestrator; no other files need to change
