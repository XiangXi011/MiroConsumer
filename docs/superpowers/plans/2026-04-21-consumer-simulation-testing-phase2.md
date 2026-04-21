# Consumer Simulation Testing Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `consumer_test` from a validated Phase 1 workflow into a more realistic market-simulation system by adding automatic pre-research, persona-aware information access, richer propagation events, and reportable causal evidence.

**Architecture:** Keep MiroFish's existing `/api/graph -> /api/simulation -> /api/report` backbone and extend the repo-owned `backend/app/services/consumer/` package with new Phase 2 units for research ingest, access policy, and propagation event modeling. The core change is that agents should no longer share the same knowledge surface: research findings get typed and layered into the graph, persona traits determine who can discover or trust each layer, and propagation events become first-class evidence that scoring and reporting can cite.

**Tech Stack:** Flask, existing MiroFish simulation/report stack, Pydantic models, pytest, Vue 3 + Vite, Axios, locale JSON

---

## Constraints And Working Rules

- Follow `@test-driven-development` for backend behavior changes.
- Run `@verification-before-completion` before claiming Phase 2 is ready.
- Use `@systematic-debugging` if the consumer branch diverges from Phase 1 behavior.
- Preserve Phase 1 backward compatibility:
  - omitting `project_type` must still run default MiroFish
  - `project_type=consumer_test` with no new research data must still behave sensibly
- Keep Phase 2 scoped to realism upgrades:
  - automatic pre-research
  - information asymmetry
  - richer propagation event design
  - better causal reporting
- Do not expand test types yet. Packaging, A/B, pricing, DingTalk, and subscription workflows stay out of scope.

## File Structure

### Backend Files

- Create: `backend/tests/consumer/test_research_ingest.py`
  Responsibility: validate automatic pre-research, manual background normalization, and summary assembly.
- Create: `backend/tests/consumer/test_access_policy.py`
  Responsibility: validate who can see which findings in Round 0 vs propagation rounds.
- Create: `backend/tests/consumer/test_event_engine.py`
  Responsibility: validate propagation event typing, event transitions, and evidence payload shape.
- Modify: `backend/tests/consumer/test_graph_builder.py`
  Responsibility: extend graph assertions to cover research nodes, provenance, and access tiers.
- Modify: `backend/tests/consumer/test_orchestrator.py`
  Responsibility: extend prompt-gating assertions to include persona-aware research access and event recording.
- Modify: `backend/tests/consumer/test_scoring.py`
  Responsibility: extend scoring assertions to cover causal event chains, research-triggered risks, and richer VOC bundles.
- Modify: `backend/tests/api/test_consumer_routes.py`
  Responsibility: protect API branching and new summary/report fields.
- Create: `backend/app/services/consumer/research_ingest.py`
  Responsibility: run automatic pre-research plus uploaded-context normalization into typed research artifacts.
- Create: `backend/app/services/consumer/access_policy.py`
  Responsibility: decide visibility per persona, round, and finding type.
- Create: `backend/app/services/consumer/event_engine.py`
  Responsibility: define propagation event taxonomy and helper functions for event creation and transition labeling.
- Modify: `backend/app/services/consumer/models.py`
  Responsibility: add typed models for research findings, knowledge views, propagation events, and Phase 2 report evidence.
- Modify: `backend/app/services/consumer/brief_adapter.py`
  Responsibility: carry optional research preferences and background materials forward in a stable contract.
- Modify: `backend/app/services/consumer/persona_pack.py`
  Responsibility: expose richer traits for search depth, source trust, skepticism, and rumor sensitivity.
- Modify: `backend/app/services/consumer/graph_builder.py`
  Responsibility: add research-backed nodes and edges with provenance plus layered visibility.
- Modify: `backend/app/services/consumer/orchestrator.py`
  Responsibility: inject round-aware knowledge views, call the event engine, and persist event-rich round state.
- Modify: `backend/app/services/consumer/scoring.py`
  Responsibility: compute causal metrics from propagation events and research-triggered attitude shifts.
- Modify: `backend/app/services/consumer/report_context.py`
  Responsibility: turn research findings + propagation events into report-ready causal stories and recommendations.
- Modify: `backend/app/api/graph.py`
  Responsibility: accept optional Phase 2 research settings and persist research context during graph build.
- Modify: `backend/app/api/simulation.py`
  Responsibility: expose richer consumer summary payloads including research coverage and propagation events.
- Modify: `backend/app/api/report.py`
  Responsibility: pass Phase 2 report context fields into the existing report generation path.
- Modify: `backend/app/services/simulation_manager.py`
  Responsibility: persist research artifacts and runtime knowledge metadata alongside existing simulation config.
- Modify: `backend/app/services/simulation_runner.py`
  Responsibility: store per-round event evidence and knowledge-access metadata without affecting default mode.
- Modify: `backend/app/services/report_agent.py`
  Responsibility: render Phase 2 consumer reports with causal references to findings and propagation events.

### Frontend Files

- Modify: `frontend/src/views/Home.vue`
  Responsibility: expose optional Phase 2 research toggles/settings without creating a second flow.
- Modify: `frontend/src/store/pendingUpload.js`
  Responsibility: persist optional research settings and uploaded background material selections.
- Modify: `frontend/src/api/graph.js`
  Responsibility: send Phase 2 research settings during project setup and graph build.
- Modify: `frontend/src/api/simulation.js`
  Responsibility: request Phase 2 consumer summary payloads with event and research metadata.
- Modify: `frontend/src/api/report.js`
  Responsibility: request the richer Phase 2 report context.
- Modify: `frontend/src/components/Step2EnvSetup.vue`
  Responsibility: show research findings, knowledge layers, and which persona groups can access what.
- Modify: `frontend/src/components/Step3Simulation.vue`
  Responsibility: surface event types, propagation chains, and research-triggered reactions.
- Modify: `frontend/src/components/Step4Report.vue`
  Responsibility: show causal report sections, triggering findings, propagation roles, and action recommendations.
- Modify: `frontend/src/components/Step5Interaction.vue`
  Responsibility: bias follow-up prompts toward “why did this spread?” and “which finding caused the shift?” questions.
- Modify: `locales/zh.json`
  Responsibility: add Phase 2 research/event labels and report copy.
- Modify: `locales/en.json`
  Responsibility: keep i18n parity for Phase 2 additions.

## Testing Strategy

- Backend unit tests:
  - typed research findings
  - `auto_enrich` provider behavior
  - persona-aware access policy
  - propagation event generation
  - graph enrichment and scoring
- Backend API tests:
  - `consumer_test` summary/report payloads include Phase 2 fields
  - default mode still stays untouched
- Frontend validation:
  - targeted tests for any new helpers
  - `npm run build`
- Integration:
  - run one consumer case with no extra research data
  - run one consumer case with `auto_enrich` enabled and no manual background
  - run one consumer case with manual background materials
  - confirm both produce sensible summaries and reports

## Task 1: Introduce Typed Research Findings

**Files:**
- Create: `backend/tests/consumer/test_research_ingest.py`
- Modify: `backend/app/services/consumer/models.py`
- Modify: `backend/app/services/consumer/brief_adapter.py`
- Create: `backend/app/services/consumer/research_ingest.py`

- [ ] **Step 1: Write the failing research-ingest tests**

```python
def test_research_ingest_builds_typed_findings():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["High-protein yogurt pouch"],
            "copy_material": ["14g protein", "low sugar"],
            "research_goal": "Find likely debate points",
            "optional_background_materials": ["Ingredient concern: sweetener debates"],
        }
    )

    findings = build_research_findings(brief)

    assert findings[0].finding_type in {"category_context", "risk_signal", "trend_signal"}
    assert findings[0].visibility in {"Propagation_Only", "Restricted"}
    assert findings[0].summary
```

```python
def test_auto_enrich_uses_provider_output_without_manual_background():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["High-protein yogurt pouch"],
            "copy_material": ["14g protein", "low sugar"],
            "research_goal": "Find likely debate points",
            "research_mode": "auto_enrich",
        }
    )

    findings = resolve_research_findings(
        brief,
        provider=lambda _: [
            ResearchFinding(
                finding_id="auto_1",
                finding_type="trend_signal",
                summary="High-protein breakfast is trending",
                visibility="Propagation_Only",
            )
        ],
    )

    assert [item.finding_id for item in findings] == ["auto_1"]
```

```python
def test_research_ingest_can_build_pinned_research_summary():
    findings = [ResearchFinding(finding_id="r1", finding_type="risk_signal", summary="Sweetener concern", visibility="Restricted")]
    summary = build_research_summary(findings)
    assert "Sweetener concern" in summary
```

- [ ] **Step 2: Run the new tests and confirm failure**

Run: `Set-Location backend; .\.venv\Scripts\python.exe -m pytest tests/consumer/test_research_ingest.py -q`
Expected: FAIL because Phase 2 research models/helpers do not exist yet.

- [ ] **Step 3: Implement typed research models and ingest helpers**

Add to `backend/app/services/consumer/models.py`:

```python
class ResearchFinding(BaseModel):
    finding_id: str
    finding_type: Literal["category_context", "competitor_signal", "risk_signal", "trend_signal"]
    summary: str
    evidence_snippets: List[str] = Field(default_factory=list)
    source_label: str = "brief_background"
    visibility: GraphVisibility = GraphVisibility.PROPAGATION_ONLY
    confidence: float = 0.5
```

Add to `brief_adapter.py`:
- `research_mode: Literal["manual_only", "auto_enrich"] = "manual_only"`
- normalized `optional_background_materials`

Implement in `research_ingest.py`:
- `build_research_findings(brief)`
- `run_auto_research(brief, provider)`
- `resolve_research_findings(brief, provider=None)`
- `build_research_summary(findings)`
- deterministic finding IDs
- default mapping rules from background materials to `finding_type` + `visibility`
- when `research_mode="auto_enrich"`, call a provider hook even if manual background is empty
- merge provider results with manual findings under stable ordering rules

- [ ] **Step 4: Re-run the research-ingest tests**

Run: `Set-Location backend; .\.venv\Scripts\python.exe -m pytest tests/consumer/test_research_ingest.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consumer/models.py backend/app/services/consumer/brief_adapter.py backend/app/services/consumer/research_ingest.py backend/tests/consumer/test_research_ingest.py
git commit -m "feat: add consumer research ingest contract"
```

## Task 2: Enrich The Consumer Graph With Research Provenance

**Files:**
- Modify: `backend/tests/consumer/test_graph_builder.py`
- Modify: `backend/app/services/consumer/graph_builder.py`
- Modify: `backend/app/api/graph.py`
- Modify: `backend/app/services/simulation_manager.py`

- [ ] **Step 1: Extend graph-builder tests to cover research nodes**

```python
def test_graph_builder_adds_research_findings_with_visibility():
    graph = build_consumer_graph(brief, personas, findings=[
        ResearchFinding(
            finding_id="r1",
            finding_type="risk_signal",
            summary="Sweetener concern",
            visibility=GraphVisibility.RESTRICTED,
        )
    ])

    research_nodes = [node for node in graph["nodes"] if node["type"] == "research_finding"]
    assert research_nodes[0]["visibility"] == "Restricted"
    assert research_nodes[0]["provenance"]["source_label"] == "brief_background"
```

- [ ] **Step 2: Run graph-builder tests and confirm failure**

Run: `Set-Location backend; .\.venv\Scripts\python.exe -m pytest tests/consumer/test_graph_builder.py -q`
Expected: FAIL because research nodes/provenance are not emitted yet.

- [ ] **Step 3: Update graph-building and persistence path**

In `graph_builder.py`:
- accept `research_findings`
- create `research_finding` nodes
- connect them to claims/themes/persona anxieties
- store provenance metadata on nodes/edges

In `graph.py` and `simulation_manager.py`:
- persist normalized research findings into project/simulation context
- persist whether findings came from `manual_only` or `auto_enrich`
- keep empty/default behavior for Phase 1-style inputs

- [ ] **Step 4: Re-run graph and API tests**

Run: `Set-Location backend; .\.venv\Scripts\python.exe -m pytest tests/consumer/test_graph_builder.py tests/api/test_consumer_routes.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consumer/graph_builder.py backend/app/api/graph.py backend/app/services/simulation_manager.py backend/tests/consumer/test_graph_builder.py backend/tests/api/test_consumer_routes.py
git commit -m "feat: attach research findings to consumer graph"
```

## Task 3: Add Persona-Aware Knowledge Access Policy

**Files:**
- Create: `backend/tests/consumer/test_access_policy.py`
- Create: `backend/app/services/consumer/access_policy.py`
- Modify: `backend/app/services/consumer/persona_pack.py`
- Modify: `backend/app/services/consumer/orchestrator.py`
- Modify: `backend/tests/consumer/test_orchestrator.py`

- [ ] **Step 1: Write failing access-policy tests**

```python
def test_round_zero_only_exposes_initial_knowledge():
    visible = resolve_visible_findings(
        persona={"search_propensity": "high", "cognition_level": "high"},
        findings=[
            ResearchFinding(finding_id="r1", finding_type="risk_signal", summary="Deep risk", visibility=GraphVisibility.RESTRICTED)
        ],
        round_index=0,
    )
    assert visible == []
```

```python
def test_high_search_persona_can_unlock_restricted_findings_after_round_one():
    visible = resolve_visible_findings(
        persona={"search_propensity": "high", "cognition_level": "high"},
        findings=[
            ResearchFinding(finding_id="r1", finding_type="risk_signal", summary="Deep risk", visibility=GraphVisibility.RESTRICTED)
        ],
        round_index=2,
    )
    assert [item.finding_id for item in visible] == ["r1"]
```

- [ ] **Step 2: Run the policy tests and confirm failure**

Run: `Set-Location backend; .\.venv\Scripts\python.exe -m pytest tests/consumer/test_access_policy.py tests/consumer/test_orchestrator.py -q`
Expected: FAIL because no Phase 2 access-policy helper exists.

- [ ] **Step 3: Implement access policy and orchestrator integration**

In `access_policy.py`:
- `resolve_visible_findings(persona, findings, round_index)`
- `build_knowledge_view(persona, brief, graph_nodes, findings, round_index)`

Rules:
- Round 0: only `Initial`
- Round 1+: `Propagation_Only` visible to all consumer personas
- `Restricted` only visible to high-search/high-cognition personas

In `persona_pack.py`:
- expose source-trust and skepticism traits if missing

In `orchestrator.py`:
- pin `BusinessBrief` summary every round
- inject `knowledge_view` into prompt assembly
- persist which findings were visible to each agent per round

- [ ] **Step 4: Re-run access-policy and orchestrator tests**

Run: `Set-Location backend; .\.venv\Scripts\python.exe -m pytest tests/consumer/test_access_policy.py tests/consumer/test_orchestrator.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consumer/access_policy.py backend/app/services/consumer/persona_pack.py backend/app/services/consumer/orchestrator.py backend/tests/consumer/test_access_policy.py backend/tests/consumer/test_orchestrator.py
git commit -m "feat: add persona-aware research access policy"
```

## Task 4: Promote Propagation Events To First-Class Evidence

**Files:**
- Create: `backend/tests/consumer/test_event_engine.py`
- Create: `backend/app/services/consumer/event_engine.py`
- Modify: `backend/app/services/consumer/models.py`
- Modify: `backend/app/services/consumer/orchestrator.py`
- Modify: `backend/app/services/simulation_runner.py`

- [ ] **Step 1: Write failing event-engine tests**

```python
def test_event_engine_labels_misread_events():
    event = classify_propagation_event(
        before_attitude="positive",
        after_attitude="negative",
        trigger="risk_signal",
        speech_act="reinterpretation",
    )
    assert event.event_type == "misread_amplification"
```

```python
def test_event_engine_records_event_chain_metadata():
    event = build_propagation_event(
        actor_id="agent_1",
        target_ids=["agent_2"],
        event_type="skeptical_challenge",
        trigger_finding_ids=["r1"],
        supporting_quote="This sounds too good to be true",
        round_index=2,
    )
    assert event.trigger_finding_ids == ["r1"]
    assert event.round_index == 2
```

- [ ] **Step 2: Run the event-engine tests and confirm failure**

Run: `Set-Location backend; .\.venv\Scripts\python.exe -m pytest tests/consumer/test_event_engine.py -q`
Expected: FAIL because event types/helpers do not exist yet.

- [ ] **Step 3: Implement event taxonomy and persistence**

Add to `models.py`:

```python
class PropagationEvent(BaseModel):
    event_id: str
    event_type: Literal[
        "positive_relay",
        "skeptical_challenge",
        "misread_amplification",
        "risk_discovery",
        "clarification_recovery",
    ]
    actor_id: str
    target_ids: List[str]
    trigger_finding_ids: List[str] = Field(default_factory=list)
    supporting_quote: str = ""
    round_index: int
```

Implement in `event_engine.py`:
- `classify_propagation_event(...)`
- `build_propagation_event(...)`

Integrate in `orchestrator.py` and `simulation_runner.py`:
- emit events per round
- persist them in consumer round snapshots
- keep default mode runner untouched

- [ ] **Step 4: Re-run event and orchestrator tests**

Run: `Set-Location backend; .\.venv\Scripts\python.exe -m pytest tests/consumer/test_event_engine.py tests/consumer/test_orchestrator.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consumer/models.py backend/app/services/consumer/event_engine.py backend/app/services/consumer/orchestrator.py backend/app/services/simulation_runner.py backend/tests/consumer/test_event_engine.py backend/tests/consumer/test_orchestrator.py
git commit -m "feat: add propagation event engine"
```

## Task 5: Upgrade Scoring, Summary, And Report Context

**Files:**
- Modify: `backend/tests/consumer/test_scoring.py`
- Modify: `backend/tests/api/test_consumer_routes.py`
- Modify: `backend/app/services/consumer/scoring.py`
- Modify: `backend/app/services/consumer/report_context.py`
- Modify: `backend/app/api/simulation.py`
- Modify: `backend/app/api/report.py`
- Modify: `backend/app/services/report_agent.py`

- [ ] **Step 1: Extend scoring/report tests to cover Phase 2 evidence**

```python
def test_scoring_groups_events_into_causal_findings():
    summary = build_consumer_summary(
        events=[
            PropagationEvent(
                event_id="e1",
                event_type="risk_discovery",
                actor_id="agent_1",
                target_ids=["agent_2"],
                trigger_finding_ids=["r1"],
                supporting_quote="Wait, what sweetener is in this?",
                round_index=2,
            )
        ],
        findings=[
            ResearchFinding(finding_id="r1", finding_type="risk_signal", summary="Sweetener concern", visibility=GraphVisibility.RESTRICTED)
        ],
    )

    assert summary.top_risk_findings[0]["finding_id"] == "r1"
    assert summary.event_counts["risk_discovery"] == 1
```

```python
def test_report_context_keeps_trigger_finding_and_event_chain():
    context = build_consumer_report_context(
        summary=summary,
        findings=[
            ResearchFinding(finding_id="r1", finding_type="risk_signal", summary="Sweetener concern", visibility=GraphVisibility.RESTRICTED)
        ],
        events=[
            PropagationEvent(
                event_id="e1",
                event_type="risk_discovery",
                actor_id="agent_1",
                target_ids=["agent_2"],
                trigger_finding_ids=["r1"],
                supporting_quote="Wait, what sweetener is in this?",
                round_index=2,
            )
        ],
    )

    assert context["causal_chains"][0]["trigger_finding_ids"] == ["r1"]
    assert context["causal_chains"][0]["event_ids"] == ["e1"]
```

```python
def test_consumer_summary_route_exposes_phase2_fields(client):
    response = client.get("/api/simulation/sim_test/consumer-summary")
    payload = response.get_json()
    assert "event_counts" in payload
    assert "top_risk_findings" in payload
```

- [ ] **Step 2: Run the updated tests and confirm failure**

Run: `Set-Location backend; .\.venv\Scripts\python.exe -m pytest tests/consumer/test_scoring.py tests/api/test_consumer_routes.py -q`
Expected: FAIL because Phase 2 summary/report fields are not produced yet.

- [ ] **Step 3: Implement richer scoring and report context**

In `scoring.py`:
- add `event_counts`
- add `top_risk_findings`
- add `top_clarification_opportunities`
- map representative VOC quotes back to event chains

In `report_context.py`:
- add sections for:
  - triggering findings
  - event-led attitude reversal
  - which persona groups amplified or blocked each signal
- keep explicit `trigger_finding_ids` and `event_ids` in the report context payload so the report agent can cite them

In `simulation.py`, `report.py`, and `report_agent.py`:
- expose these fields in API/report payloads
- ensure generated consumer report sections can cite the triggering finding summary and linked event chain
- preserve current Phase 1 consumers if Phase 2 fields are absent

- [ ] **Step 4: Re-run scoring, API, and report tests**

Run: `Set-Location backend; .\.venv\Scripts\python.exe -m pytest tests/consumer/test_scoring.py tests/api/test_consumer_routes.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consumer/scoring.py backend/app/services/consumer/report_context.py backend/app/api/simulation.py backend/app/api/report.py backend/app/services/report_agent.py backend/tests/consumer/test_scoring.py backend/tests/api/test_consumer_routes.py
git commit -m "feat: add phase2 consumer causal reporting"
```

## Task 6: Surface Phase 2 Research And Events In The UI

**Files:**
- Modify: `frontend/src/views/Home.vue`
- Modify: `frontend/src/store/pendingUpload.js`
- Modify: `frontend/src/api/graph.js`
- Modify: `frontend/src/api/simulation.js`
- Modify: `frontend/src/api/report.js`
- Modify: `frontend/src/components/Step2EnvSetup.vue`
- Modify: `frontend/src/components/Step3Simulation.vue`
- Modify: `frontend/src/components/Step4Report.vue`
- Modify: `frontend/src/components/Step5Interaction.vue`
- Modify: `frontend/tests/consumerBrief.test.js`
- Modify: `frontend/tests/consumerMode.test.js`
- Modify: `locales/zh.json`
- Modify: `locales/en.json`

- [ ] **Step 1: Add failing frontend tests for Phase 2 helper behavior**

```javascript
test("consumer brief helper preserves research mode", () => {
  const brief = normalizeConsumerBrief({
    taskType: "concept_test",
    productConceptAssets: ["Protein yogurt"],
    researchMode: "auto_enrich",
  });

  expect(brief.research_mode).toBe("auto_enrich");
});
```

```javascript
test("consumer mode helpers expose phase2 event labels", () => {
  expect(getConsumerEventLabel("risk_discovery")).toContain("risk");
});
```

- [ ] **Step 2: Run frontend tests and confirm failure**

Run: `node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js`
Expected: FAIL because Phase 2 helpers/UI labels do not exist yet.

- [ ] **Step 3: Implement Phase 2 UI surfacing**

Update:
- `Home.vue` and `pendingUpload.js` to preserve optional `researchMode`
- `graph.js` / `simulation.js` / `report.js` to pass through Phase 2 payloads
- `Step2EnvSetup.vue` to display research findings and who can access them
- `Step3Simulation.vue` to display propagation event chips/tables
- `Step4Report.vue` to show triggering findings, event counts, and action recommendations
- `Step5Interaction.vue` to add follow-up prompts like “Which finding triggered the negative turn?”
- locales to keep full Chinese/English parity

- [ ] **Step 4: Re-run frontend tests and build**

Run: `node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js frontend/tests/pendingUpload.test.js`
Expected: PASS

Run: `Set-Location frontend; npm run build`
Expected: build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/Home.vue frontend/src/store/pendingUpload.js frontend/src/api/graph.js frontend/src/api/simulation.js frontend/src/api/report.js frontend/src/components/Step2EnvSetup.vue frontend/src/components/Step3Simulation.vue frontend/src/components/Step4Report.vue frontend/src/components/Step5Interaction.vue frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js locales/zh.json locales/en.json
git commit -m "feat: surface phase2 consumer research flow"
```

## Task 7: Verify The Full Phase 2 Flow And Sync Docs

**Files:**
- Modify: `PRD.md`
- Modify: `docs/superpowers/specs/2026-04-20-consumer-simulation-testing-design.md`
- Modify: `docs/superpowers/handoffs/2026-04-21-consumer-simulation-phase1-handoff.md`
- Create: `docs/superpowers/handoffs/2026-04-21-consumer-simulation-phase2-handoff.md`

- [ ] **Step 1: Record the Phase 2 verification checklist**

Add a checklist covering:
- consumer brief without research findings
- consumer brief with `auto_enrich`
- consumer brief with manual background materials
- Round 0 access restrictions
- propagation-event summary output
- report context cites `trigger_finding_ids` and `event_ids`
- default mode backward compatibility

- [ ] **Step 2: Run full verification commands**

Run:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest

Set-Location ..\
node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js frontend/tests/pendingUpload.test.js

Set-Location frontend
npm run build
```

Expected:
- backend suite passes
- frontend targeted tests pass
- build succeeds

- [ ] **Step 3: Perform one manual consumer smoke run**

Verify:
- research findings appear in Step 2
- `auto_enrich` produces findings even when no manual background text is uploaded
- Round 0 hides deep findings
- propagation events appear in Step 3
- report references findings and event chains with explicit causal linkage
- follow-up prompts in Step 5 feel causal, not generic

- [ ] **Step 4: Sync docs to the new Phase 2 baseline**

Update PRD/spec/handoff docs with:
- implemented scope
- accepted limitations
- recommended model/runtime settings
- follow-up priorities for the next phase

- [ ] **Step 5: Commit**

```bash
git add PRD.md docs/superpowers/specs/2026-04-20-consumer-simulation-testing-design.md docs/superpowers/handoffs/2026-04-21-consumer-simulation-phase1-handoff.md docs/superpowers/handoffs/2026-04-21-consumer-simulation-phase2-handoff.md
git commit -m "docs: capture phase2 implementation baseline"
```
