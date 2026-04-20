# Consumer Simulation Testing Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate a `consumer_test` mode into MiroFish so Phase 1 supports concept/copy consumer testing with propagation-aware simulation, consumer-specific reporting, and backward-compatible APIs.

**Architecture:** Extend MiroFish's existing `/api/graph -> /api/simulation -> /api/report` pipeline with a branch keyed by `project_type=consumer_test`. Keep graph/simulation/report orchestration in MiroFish, but add a focused `backend/app/services/consumer/` package that owns BusinessBrief normalization, persona mapping, visibility-aware graph generation, propagation evidence/VOC extraction, and report context assembly.

**Tech Stack:** Flask, Pydantic, existing MiroFish OASIS/Zep services, Vue 3 + Vite, Axios, pytest via `uv`

---

## Constraints And Working Rules

- Follow `@test-driven-development` for backend behavior changes.
- Run `@verification-before-completion` before claiming the feature is ready.
- Use `@systematic-debugging` if the consumer branch diverges from existing simulation behavior.
- Do not import the external consumer project at runtime. Port the minimum Phase 1 contracts/data into repo-owned files under `backend/app/services/consumer/`.
- Preserve backward compatibility: if `project_type` is omitted, the system must behave exactly like current MiroFish.
- Keep scope to `concept_test` and `copy_feedback`. Do not add packaging, pricing, DingTalk, or web-crawl features in this implementation pass.

## File Structure

### Backend Files

- Create: `backend/tests/conftest.py`
  Responsibility: shared Flask app fixture, temp upload folder overrides, test helpers for stubbing LLM/Zep-heavy dependencies.
- Create: `backend/tests/models/test_project_model.py`
  Responsibility: protect `Project` serialization defaults and `consumer_test` round-trip behavior.
- Create: `backend/tests/consumer/test_brief_adapter.py`
  Responsibility: validate BusinessBrief parsing, required fields, and task-type normalization.
- Create: `backend/tests/consumer/test_persona_pack.py`
  Responsibility: protect persona loading and consumer-agent attribute mapping.
- Create: `backend/tests/consumer/test_graph_builder.py`
  Responsibility: protect graph node generation and visibility rules (`Initial`, `Propagation_Only`, `Restricted`).
- Create: `backend/tests/consumer/test_orchestrator.py`
  Responsibility: protect pinned brief prompt assembly and round-based access gating.
- Create: `backend/tests/consumer/test_scoring.py`
  Responsibility: protect summary metrics, VOC extraction, and quote prioritization.
- Create: `backend/tests/api/test_consumer_routes.py`
  Responsibility: ensure `/api/graph`, `/api/simulation`, `/api/report` branch correctly for `consumer_test` without breaking default mode.
- Create: `backend/app/services/consumer/__init__.py`
  Responsibility: package exports for consumer services.
- Create: `backend/app/services/consumer/models.py`
  Responsibility: typed `ConsumerBusinessBrief`, persona traits, graph visibility enums, evidence bundle, and report summary models.
- Create: `backend/app/services/consumer/brief_adapter.py`
  Responsibility: normalize raw request payload into `ConsumerBusinessBrief`.
- Create: `backend/app/services/consumer/data/default_personas.json`
  Responsibility: repo-owned Phase 1 persona pack imported from the consumer project and trimmed to propagation-relevant fields.
- Create: `backend/app/services/consumer/persona_pack.py`
  Responsibility: load persona pack and map to MiroFish/OASIS-friendly agent traits.
- Create: `backend/app/services/consumer/graph_builder.py`
  Responsibility: turn `ConsumerBusinessBrief` + optional background text + persona pack into consumer-specific graph payloads with visibility metadata.
- Create: `backend/app/services/consumer/orchestrator.py`
  Responsibility: assemble round prompts, pin BusinessBrief summaries, enforce graph visibility gating, and record consumer round snapshots.
- Create: `backend/app/services/consumer/scoring.py`
  Responsibility: compute initial/final attitude summaries, resonance/risk/misread metrics, and VOC bundles from simulation events.
- Create: `backend/app/services/consumer/report_context.py`
  Responsibility: turn simulation outputs into report-ready payloads for the existing report agent.
- Modify: `backend/app/models/project.py`
  Responsibility: persist `project_type`, `consumer_brief`, and lightweight consumer metadata while defaulting to original behavior.
- Modify: `backend/app/api/graph.py`
  Responsibility: accept consumer brief payloads on project creation and branch graph building for `consumer_test`.
- Modify: `backend/app/api/simulation.py`
  Responsibility: branch create/prepare/start behavior for `consumer_test`.
- Modify: `backend/app/api/report.py`
  Responsibility: choose consumer report generation path and keep default path untouched.
- Modify: `backend/app/services/simulation_manager.py`
  Responsibility: carry `project_type`, consumer persona pack results, and consumer config artifacts through simulation preparation.
- Modify: `backend/app/services/simulation_runner.py`
  Responsibility: invoke consumer orchestration hooks, persist round snapshots, and preserve existing default runner behavior.
- Modify: `backend/app/services/report_agent.py`
  Responsibility: switch outline/prompt/report rendering to consumer-specific mode when the project is a `consumer_test`.

### Frontend Files

- Modify: `frontend/src/store/pendingUpload.js`
  Responsibility: persist `projectType` and `consumerBrief` between Home and Process views.
- Modify: `frontend/src/views/Home.vue`
  Responsibility: collect consumer-testing inputs for concept/copy workflows without creating a separate product flow.
- Modify: `frontend/src/api/graph.js`
  Responsibility: send `project_type` and serialized `consumer_brief` on ontology generation / graph build requests.
- Modify: `frontend/src/api/simulation.js`
  Responsibility: pass through `project_type` and consumer-specific simulation settings.
- Modify: `frontend/src/api/report.js`
  Responsibility: pass through report mode if needed by backend branching.
- Modify: `frontend/src/views/MainView.vue`
  Responsibility: keep one 5-step flow while showing consumer-specific labels and state when `project_type=consumer_test`.
- Modify: `frontend/src/components/Step2EnvSetup.vue`
  Responsibility: present consumer persona generation and propagation-ready config instead of generic entity-only descriptions.
- Modify: `frontend/src/components/Step3Simulation.vue`
  Responsibility: display Round 0 / Round 1-N semantics, consumer events, and propagation-aware metrics.
- Modify: `frontend/src/components/Step4Report.vue`
  Responsibility: surface consumer-report sections, VOC quotes, and propagation findings.
- Modify: `frontend/src/components/Step5Interaction.vue`
  Responsibility: bias follow-up interactions toward report agent + representative consumer agents/groups.
- Modify: `locales/zh.json`
  Responsibility: add consumer-testing copy for new fields and step text.
- Modify: `locales/en.json`
  Responsibility: keep i18n parity for consumer-testing labels.

## Testing Strategy

- Backend: add focused pytest coverage for the new consumer package and API branching.
- Frontend: use `npm run build` as the minimum automated safety check in this repo, then perform one manual smoke run through the 5-step UI.
- Integration: verify both branches.
  - `project_type` omitted -> current MiroFish behavior
  - `project_type=consumer_test` -> consumer-specific graph, simulation, report flow

## Task 1: Persist Consumer Project Metadata Safely

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/models/test_project_model.py`
- Modify: `backend/app/models/project.py`

- [ ] **Step 1: Write the failing model round-trip test**

```python
def test_project_round_trips_consumer_fields():
    project = Project(
        project_id="proj_test",
        name="Consumer Test",
        status=ProjectStatus.CREATED,
        created_at="2026-04-20T00:00:00",
        updated_at="2026-04-20T00:00:00",
        project_type="consumer_test",
        consumer_brief={"task_type": "concept_test"},
        consumer_context={"persona_pack_id": "default"},
    )

    restored = Project.from_dict(project.to_dict())

    assert restored.project_type == "consumer_test"
    assert restored.consumer_brief["task_type"] == "concept_test"
    assert restored.consumer_context["persona_pack_id"] == "default"
```

- [ ] **Step 2: Run the test to verify current code fails**

Run: `cd backend && uv run pytest tests/models/test_project_model.py -q`
Expected: FAIL because `Project` does not yet accept or serialize consumer fields.

- [ ] **Step 3: Add backward-compatible project fields**

Implement in `backend/app/models/project.py`:

```python
project_type: str = "default"
consumer_brief: Optional[Dict[str, Any]] = None
consumer_context: Optional[Dict[str, Any]] = None
```

Update `to_dict()` / `from_dict()` so omitted fields still deserialize as current default behavior.

- [ ] **Step 4: Re-run the model test**

Run: `cd backend && uv run pytest tests/models/test_project_model.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/project.py backend/tests/conftest.py backend/tests/models/test_project_model.py
git commit -m "feat: persist consumer project metadata"
```

## Task 2: Create The Consumer Brief Contract

**Files:**
- Create: `backend/app/services/consumer/__init__.py`
- Create: `backend/app/services/consumer/models.py`
- Create: `backend/app/services/consumer/brief_adapter.py`
- Create: `backend/tests/consumer/test_brief_adapter.py`

- [ ] **Step 1: Write failing brief-adapter tests**

```python
def test_brief_adapter_builds_concept_test():
    payload = {
        "task_type": "concept_test",
        "product_concept_assets": ["High-protein yogurt for working moms"],
        "copy_material": ["14g protein, low sugar"],
        "research_goal": "Will this trigger sharing and trial interest?",
        "target_audience": ["working moms"],
        "usage_scene": ["weekday breakfast"],
    }

    brief = ConsumerBriefAdapter.from_payload(payload)

    assert brief.task_type == "concept_test"
    assert brief.claims == ["14g protein, low sugar"]
    assert brief.research_goal.startswith("Will this")
```

```python
def test_brief_adapter_rejects_missing_core_fields():
    with pytest.raises(ValueError):
        ConsumerBriefAdapter.from_payload({"task_type": "copy_feedback"})
```

- [ ] **Step 2: Run the tests to confirm they fail**

Run: `cd backend && uv run pytest tests/consumer/test_brief_adapter.py -q`
Expected: FAIL because the consumer models/adapter do not exist yet.

- [ ] **Step 3: Implement typed consumer models and adapter**

Minimum contract in `backend/app/services/consumer/models.py`:

```python
class GraphVisibility(str, Enum):
    INITIAL = "Initial"
    PROPAGATION_ONLY = "Propagation_Only"
    RESTRICTED = "Restricted"
```

```python
class ConsumerBusinessBrief(BaseModel):
    task_type: Literal["concept_test", "copy_feedback"]
    product_concept_assets: List[str]
    copy_material: List[str] = Field(default_factory=list)
    claims: List[str] = Field(default_factory=list)
    target_audience: List[str] = Field(default_factory=list)
    usage_scene: List[str] = Field(default_factory=list)
    research_goal: str
    optional_background_materials: List[str] = Field(default_factory=list)
```

Adapter rules in `brief_adapter.py`:
- normalize strings/lists
- derive `claims` from `copy_material` when claims are omitted
- reject unsupported task types
- emit a `to_summary()` method for later prompt pinning

- [ ] **Step 4: Re-run the adapter tests**

Run: `cd backend && uv run pytest tests/consumer/test_brief_adapter.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consumer backend/tests/consumer/test_brief_adapter.py
git commit -m "feat: add consumer brief contract"
```

## Task 3: Port The Phase 1 Persona Pack

**Files:**
- Create: `backend/app/services/consumer/data/default_personas.json`
- Create: `backend/app/services/consumer/persona_pack.py`
- Create: `backend/tests/consumer/test_persona_pack.py`

- [ ] **Step 1: Write failing persona-pack tests**

```python
def test_default_persona_pack_maps_consumer_traits():
    pack = load_default_persona_pack()
    agent = pack[0]

    assert "search_propensity" in agent
    assert "cognition_level" in agent
    assert "influence_weight" in agent
```

```python
def test_persona_pack_flags_deep_research_agents():
    pack = load_default_persona_pack()
    assert any(
        item["search_propensity"] == "high" and item["cognition_level"] == "high"
        for item in pack
    )
```

- [ ] **Step 2: Run the tests to confirm failure**

Run: `cd backend && uv run pytest tests/consumer/test_persona_pack.py -q`
Expected: FAIL because the data loader does not exist yet.

- [ ] **Step 3: Port the trimmed persona pack into repo-owned data**

Rules for `default_personas.json`:
- include only Phase 1 propagation-relevant attributes
- no runtime dependency on `C:\Users\05537\Desktop\agent\市场部agent teams`
- keep fields stable:

```json
{
  "persona_id": "M01",
  "label": "Care-driven urban mom",
  "attention_drivers": ["nutrition", "trust"],
  "risk_sensitivities": ["sugar", "overclaim"],
  "expression_style": "practical",
  "search_propensity": "high",
  "cognition_level": "high",
  "herd_tendency": "medium",
  "influence_weight": 0.8
}
```

Implement `persona_pack.py` so it can:
- load JSON
- map traits into the shape expected by `simulation_manager.py`
- expose `can_access_deep_graph(agent_traits)` helper

- [ ] **Step 4: Re-run persona-pack tests**

Run: `cd backend && uv run pytest tests/consumer/test_persona_pack.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consumer/data/default_personas.json backend/app/services/consumer/persona_pack.py backend/tests/consumer/test_persona_pack.py
git commit -m "feat: add consumer persona pack"
```

## Task 4: Build Visibility-Aware Consumer Graphs

**Files:**
- Create: `backend/app/services/consumer/graph_builder.py`
- Create: `backend/tests/consumer/test_graph_builder.py`
- Modify: `backend/app/api/graph.py`

- [ ] **Step 1: Write failing graph-builder tests**

```python
def test_graph_builder_marks_round_zero_content_as_initial():
    brief = ConsumerBusinessBrief(
        task_type="concept_test",
        product_concept_assets=["Portable probiotic yogurt pouch"],
        copy_material=["Light sugar", "Breakfast rescue"],
        claims=["Light sugar"],
        target_audience=["working moms"],
        usage_scene=["commute breakfast"],
        research_goal="Find shareable hooks",
    )

    graph = ConsumerGraphBuilder().build(brief, background_text="")

    concept_nodes = [n for n in graph["nodes"] if n["type"] == "ProductConcept"]
    assert concept_nodes[0]["visibility"] == "Initial"
```

```python
def test_graph_builder_keeps_risk_points_out_of_round_zero():
    graph = ConsumerGraphBuilder().build(
        brief,
        background_text="Competitor complaint and additive controversy",
    )

    risk_nodes = [n for n in graph["nodes"] if n["type"] == "RiskPoint"]
    assert all(node["visibility"] != "Initial" for node in risk_nodes)
```

- [ ] **Step 2: Run the tests to verify failure**

Run: `cd backend && uv run pytest tests/consumer/test_graph_builder.py -q`
Expected: FAIL because the builder does not exist yet.

- [ ] **Step 3: Implement graph builder and wire `/api/graph/build`**

Implementation rules:
- `Initial`: concept/copy/claim/basic scene facts from `ConsumerBusinessBrief`
- `Propagation_Only`: likely talking points and lower-cost secondary concerns
- `Restricted`: deep controversies, technical ingredient debates, competitor negative history
- keep legacy graph build untouched when `project_type != "consumer_test"`
- in `backend/app/api/graph.py`, parse `project_type`, persist `consumer_brief`, and choose the consumer graph path only when explicitly requested

- [ ] **Step 4: Re-run graph tests and one route-level compatibility test**

Run: `cd backend && uv run pytest tests/consumer/test_graph_builder.py tests/api/test_consumer_routes.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consumer/graph_builder.py backend/app/api/graph.py backend/tests/consumer/test_graph_builder.py backend/tests/api/test_consumer_routes.py
git commit -m "feat: add consumer graph build path"
```

## Task 5: Branch Simulation Creation And Preparation

**Files:**
- Modify: `backend/app/api/simulation.py`
- Modify: `backend/app/services/simulation_manager.py`
- Modify: `backend/app/models/project.py`
- Create: `backend/tests/api/test_consumer_routes.py`

- [ ] **Step 1: Write failing create/prepare simulation tests**

```python
def test_create_simulation_defaults_to_legacy_mode(client):
    response = client.post("/api/simulation/create", json={"project_id": "proj_legacy", "graph_id": "graph_x"})
    assert response.status_code == 200
    assert response.json["data"]["project_type"] == "default"
```

```python
def test_prepare_consumer_simulation_uses_persona_pack(client, seeded_consumer_project):
    response = client.post(
        "/api/simulation/prepare",
        json={"simulation_id": seeded_consumer_project["simulation_id"]}
    )

    assert response.status_code == 200
    assert response.json["data"]["profiles_count"] > 0
    assert response.json["data"]["consumer_mode"] is True
```

- [ ] **Step 2: Run the route tests to confirm failure**

Run: `cd backend && uv run pytest tests/api/test_consumer_routes.py -q`
Expected: FAIL because the simulation branch does not yet return consumer-aware state.

- [ ] **Step 3: Extend simulation state and preparation**

Required changes:
- `SimulationState` gains `project_type: str = "default"` and `consumer_mode: bool = False`
- `create_simulation()` copies `project_type` from the project
- `prepare_simulation()` branches:
  - legacy path unchanged
  - consumer path loads `consumer_brief`, loads persona pack, writes `consumer_config.json`, and returns summary fields needed by Step 2 UI

Persist at least:

```json
{
  "project_type": "consumer_test",
  "consumer_mode": true,
  "persona_pack_id": "default_phase1",
  "pinned_brief_summary": "concept + claim + goal summary"
}
```

- [ ] **Step 4: Re-run simulation route tests**

Run: `cd backend && uv run pytest tests/api/test_consumer_routes.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/simulation.py backend/app/services/simulation_manager.py backend/app/models/project.py backend/tests/api/test_consumer_routes.py
git commit -m "feat: branch simulation prep for consumer tests"
```

## Task 6: Add Consumer Orchestration And Prompt Pinning

**Files:**
- Create: `backend/app/services/consumer/orchestrator.py`
- Create: `backend/tests/consumer/test_orchestrator.py`
- Modify: `backend/app/services/simulation_runner.py`

- [ ] **Step 1: Write failing orchestration tests**

```python
def test_round_zero_prompt_pins_brief_and_hides_deep_risk():
    prompt = ConsumerSimulationOrchestrator().build_round_prompt(
        round_num=0,
        agent_traits={"search_propensity": "low", "cognition_level": "medium"},
        brief_summary="Pinned BusinessBrief Summary: yogurt pouch for breakfast",
        visible_graph_nodes=[
            {"type": "ProductConcept", "visibility": "Initial", "text": "yogurt pouch"},
            {"type": "RiskPoint", "visibility": "Restricted", "text": "ingredient controversy"},
        ],
    )

    assert "Pinned BusinessBrief Summary" in prompt
    assert "ingredient controversy" not in prompt
```

```python
def test_propagation_round_allows_high_search_agents_to_see_deep_nodes():
    prompt = ConsumerSimulationOrchestrator().build_round_prompt(
        round_num=2,
        agent_traits={"search_propensity": "high", "cognition_level": "high"},
        brief_summary="Pinned BusinessBrief Summary: yogurt pouch for breakfast",
        visible_graph_nodes=[{"type": "RiskPoint", "visibility": "Propagation_Only", "text": "sweetener debate"}],
    )

    assert "sweetener debate" in prompt
```

- [ ] **Step 2: Run the orchestration tests to confirm failure**

Run: `cd backend && uv run pytest tests/consumer/test_orchestrator.py -q`
Expected: FAIL because no orchestration helper exists yet.

- [ ] **Step 3: Implement orchestration and runner integration**

Implementation requirements:
- `build_round_prompt()` always prefixes the pinned brief summary
- `round_num == 0` only exposes `Initial` nodes
- `round_num >= 1` may expose `Propagation_Only`
- only high-search/high-cognition profiles may access `Restricted`
- persist consumer round snapshots to a file such as `uploads/simulations/<id>/consumer_rounds.jsonl`
- keep existing `SimulationRunner` behavior unchanged for default projects

- [ ] **Step 4: Re-run orchestration tests**

Run: `cd backend && uv run pytest tests/consumer/test_orchestrator.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consumer/orchestrator.py backend/app/services/simulation_runner.py backend/tests/consumer/test_orchestrator.py
git commit -m "feat: add consumer simulation orchestration"
```

## Task 7: Score Consumer Outcomes And Preserve VOC

**Files:**
- Create: `backend/app/services/consumer/scoring.py`
- Create: `backend/app/services/consumer/report_context.py`
- Create: `backend/tests/consumer/test_scoring.py`
- Modify: `backend/app/api/report.py`
- Modify: `backend/app/services/report_agent.py`
- Modify: `backend/app/api/simulation.py`

- [ ] **Step 1: Write failing scoring/VOC tests**

```python
def test_scoring_extracts_representative_quotes():
    events = [
        {"quote": "This actually sounds like a real breakfast fix", "engagement": 9, "bucket": "resonance"},
        {"quote": "Low sugar? I don't trust that claim", "engagement": 7, "bucket": "risk"},
    ]

    bundle = ConsumerScoringService().build_evidence_bundle(events)

    assert bundle.top_resonance_quotes[0]["quote"].startswith("This actually")
    assert bundle.top_risk_quotes[0]["quote"].startswith("Low sugar")
```

```python
def test_summary_tracks_attitude_shift():
    summary = ConsumerScoringService().summarize(
        initial_labels=["positive", "neutral", "negative"],
        final_labels=["positive", "positive", "negative"],
    )

    assert summary.attitude_shift_rate > 0
```

- [ ] **Step 2: Run the tests to confirm failure**

Run: `cd backend && uv run pytest tests/consumer/test_scoring.py -q`
Expected: FAIL because the scoring service does not exist yet.

- [ ] **Step 3: Implement evidence bundle and report branch**

Required outputs:

```python
ConsumerEvidenceBundle(
    top_resonance_quotes=[...],
    top_risk_quotes=[...],
    top_misread_quotes=[...],
    quote_metadata=[...],
)
```

`report_context.py` should build a report payload that includes:
- initial acceptance
- post-propagation acceptance
- attitude shift rate
- top resonance points
- top risk points
- top misreads
- representative VOC quotes

In `backend/app/services/report_agent.py`, switch outline/title/section prompts when `project_type == "consumer_test"`.

- [ ] **Step 4: Re-run scoring and report route tests**

Run: `cd backend && uv run pytest tests/consumer/test_scoring.py tests/api/test_consumer_routes.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consumer/scoring.py backend/app/services/consumer/report_context.py backend/app/services/report_agent.py backend/app/api/report.py backend/app/api/simulation.py backend/tests/consumer/test_scoring.py backend/tests/api/test_consumer_routes.py
git commit -m "feat: add consumer scoring and report context"
```

## Task 8: Add Consumer Intake To The Existing Home Flow

**Files:**
- Modify: `frontend/src/store/pendingUpload.js`
- Modify: `frontend/src/views/Home.vue`
- Modify: `frontend/src/api/graph.js`
- Modify: `locales/zh.json`
- Modify: `locales/en.json`

- [ ] **Step 1: Define the payload shape in code comments/tests-by-example**

Use this data shape end-to-end:

```js
{
  projectType: 'consumer_test',
  simulationRequirement: 'Run consumer propagation test',
  consumerBrief: {
    task_type: 'concept_test',
    product_concept_assets: ['High-protein yogurt for busy mornings'],
    copy_material: ['14g protein', 'Low sugar'],
    claims: ['14g protein', 'Low sugar'],
    target_audience: ['working moms'],
    usage_scene: ['weekday breakfast'],
    research_goal: 'Find resonance and misread risks'
  }
}
```

- [ ] **Step 2: Update pending upload state**

Modify `frontend/src/store/pendingUpload.js` so it stores:
- `projectType`
- `consumerBrief`
- existing `files`
- existing `simulationRequirement`

Keep defaults backward-compatible for current upload-only flow.

- [ ] **Step 3: Update `Home.vue` UI and submit logic**

Implementation rules:
- add a project-type selector or hidden Phase 1 mode switch that keeps one product flow
- show concept/copy/research-goal/target-audience fields only in consumer mode
- serialize `consumerBrief` into the same navigation path used today
- do not remove existing upload behavior

- [ ] **Step 4: Update graph API helpers and build the frontend**

Run: `cd frontend && npm run build`
Expected: PASS with no Vite compile errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store/pendingUpload.js frontend/src/views/Home.vue frontend/src/api/graph.js locales/zh.json locales/en.json
git commit -m "feat: add consumer test intake flow"
```

## Task 9: Adapt The 5-Step Workbench UI For Consumer Tests

**Files:**
- Modify: `frontend/src/views/MainView.vue`
- Modify: `frontend/src/components/Step2EnvSetup.vue`
- Modify: `frontend/src/components/Step3Simulation.vue`
- Modify: `frontend/src/components/Step4Report.vue`
- Modify: `frontend/src/components/Step5Interaction.vue`
- Modify: `frontend/src/api/simulation.js`
- Modify: `frontend/src/api/report.js`
- Modify: `locales/zh.json`
- Modify: `locales/en.json`

- [ ] **Step 1: Make the main flow mode-aware**

In `MainView.vue`, load `project_type` from the project payload and pass it into steps so each step can branch copy without forking the route structure.

- [ ] **Step 2: Update Step 2 and Step 3 semantics**

Required UI changes:
- Step 2: show consumer persona generation counts and propagation-related attributes
- Step 3: label Round 0 as first impression and Round 1-N as propagation rounds
- surface consumer metrics such as acceptance shift or risk quote count when available

- [ ] **Step 3: Update report and interaction panels**

Required UI changes:
- Step 4: display consumer report framing and representative quotes
- Step 5: bias prompts/actions toward report agent, representative consumers, and consumer groups

- [ ] **Step 4: Build the frontend again**

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/MainView.vue frontend/src/components/Step2EnvSetup.vue frontend/src/components/Step3Simulation.vue frontend/src/components/Step4Report.vue frontend/src/components/Step5Interaction.vue frontend/src/api/simulation.js frontend/src/api/report.js locales/zh.json locales/en.json
git commit -m "feat: adapt workbench ui for consumer tests"
```

## Task 10: Run Dual-Branch Verification

**Files:**
- Modify: `docs/superpowers/specs/2026-04-20-consumer-simulation-testing-design.md` (only if behavior changed during implementation)
- Modify: this plan file to check off completed steps during execution

- [ ] **Step 1: Run the backend test suite for touched areas**

Run: `cd backend && uv run pytest tests/models/test_project_model.py tests/consumer/test_brief_adapter.py tests/consumer/test_persona_pack.py tests/consumer/test_graph_builder.py tests/consumer/test_orchestrator.py tests/consumer/test_scoring.py tests/api/test_consumer_routes.py -q`
Expected: PASS

- [ ] **Step 2: Build the frontend**

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 3: Manual smoke test default mode**

Run:

```bash
npm run backend
npm run frontend
```

Expected:
- existing non-consumer project creation still works
- graph build / simulation / report flow still opens without consumer-only field requirements

- [ ] **Step 4: Manual smoke test `consumer_test` mode**

Expected:
- Home flow accepts concept/copy inputs
- Step 1 persists `consumer_brief`
- Step 2 shows consumer personas
- Step 3 keeps Round 0 and propagation rounds distinct
- Step 4 shows consumer report sections and VOC quotes
- Step 5 can chat with report agent or representative consumers

- [ ] **Step 5: Final commit (only if verification required follow-up fixes)**

```bash
git add <verified files>
git commit -m "fix: finish consumer simulation phase1 integration"
```

## Handoff Notes

- Start execution with backend tasks first. The frontend should only be wired after the consumer branch contract is stable.
- Keep PR/review scope tight by committing after each task.
- If implementation reveals the need for packaging/A-B/price support, stop and create a new spec instead of quietly expanding this plan.
