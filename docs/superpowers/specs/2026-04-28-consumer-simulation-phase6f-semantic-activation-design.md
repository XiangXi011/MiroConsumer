# Consumer Simulation Phase 6F Semantic Activation Execution Spec

## 1. Metadata

| Field | Value |
|---|---|
| Date | 2026-04-28 |
| Target branch | `codex/phase5-closure` |
| Target worktree | `D:\project\MiroFish\.worktrees\phase5a-identity` |
| Product name | MiroConsumer |
| Phase | Phase 6F |
| Status | Draft for product/architecture review |

## 2. Product Goal Reset

Phase 6F repositions MiroConsumer from an AI consumer research tool into a consumer propagation rehearsal system built on the MiroFish large-scale social sandbox.

The product promise is:

> MiroConsumer is not "8 AI personas scoring a concept." It is a pre-launch consumer society rehearsal where concepts, copy, price, and packaging spread through simulated consumer contexts, producing amplification, misreading, skepticism, trust decay, trust recovery, and conversion signals.

MiroFish native capabilities remain the substrate:

```text
Real-world materials
  -> GraphRAG
  -> Agent society
  -> dynamic evolution
  -> god-view intervention
  -> deep interaction
```

MiroConsumer productizes that substrate as:

```text
Consumer brief
  -> consumer research graph
  -> consumer propagation simulation
  -> trust / misread / objection / conversion dynamics
  -> research director report
  -> evidence, interviews, branch comparison, asset retention
```

Phase 6F is the semantic activation phase. It does not build the large society runtime yet. It makes existing MiroFish capabilities behave, read, and surface as consumer research capabilities.

## 3. Scope

### 3.1 In Scope

Phase 6F includes five workstreams:

1. **Research Director Agent**
   - Convert consumer-mode ReportAgent prompts from "future prediction report" to "consumer research director report."
   - Preserve default / legacy report prompts for `project_type=default`.
   - Make consumer reports explain why consumers react, which claims propagate, which risks spread, which evidence repairs trust, and which intervention should be tried next.

2. **Consumer research tool semantics**
   - Keep `ZepToolsService` and its existing tools.
   - Productize tool semantics in consumer context:
     - `InsightForge` -> consumer insight deep dive.
     - `PanoramaSearch` -> propagation path explainer.
     - `QuickSearch` -> evidence verifier.
     - `interview_agents` -> virtual consumer interview.
     - `get_all_nodes` / `get_all_edges` -> consumer cognition graph overview.
     - temporal facts -> consumer cognition evolution timeline.

3. **Consumer-facing interaction APIs**
   - Add canonical `/api/consumer/*` wrappers for research actions and interviews.
   - Keep existing `/api/simulation/interview*` routes as compatibility routes.
   - Add representative-consumer selection for advocate, skeptic, misreader, price-sensitive, and amplifier roles.

4. **Consumer event ontology**
   - Add a consumer event type layer over the existing coarse event buckets.
   - Preserve existing `PropagationEvent.event_type` buckets for compatibility.
   - Add event labels suitable for timeline, report audit, propagation path, and future society metrics.

5. **Frontend product entry points**
   - Add visible actions near consumer report findings:
     - Deep dive this conclusion.
     - View propagation path.
     - View evidence.
     - Ask related consumers.
     - Compare branch delta.
   - Add lightweight panels for representative consumer interviews and virtual focus groups.
   - Use existing report log and consumer report header surfaces; do not create a new standalone product surface in this phase.

### 3.2 Out of Scope

Phase 6F does not include:

- Large-scale `Consumer Society Runtime`.
- Population factory for 200-1000+ agents.
- Multi-channel runtime for Xiaohongshu / Douyin / WeChat / ecommerce review / livestream / offline word of mouth.
- OASIS-to-consumer runtime bridge beyond semantic mapping of current events.
- Database-backed repositories.
- Durable queue executor.
- Multi-instance locks.
- Production Docker split.
- Auth, teams, permissions, or billing.
- Full graph ontology migration.

Those belong to Phase 6G, Phase 6H, Phase 6I, and Phase 7.

## 4. Current Code Evidence

This spec is grounded in the current Phase 6E codebase.

| Area | Current State | Evidence |
|---|---|---|
| Zep tools | `ZepToolsService` still exposes InsightForge, PanoramaSearch, QuickSearch, interview, graph node/edge retrieval, temporal edge facts, local fallback. | `backend/app/services/zep_tools.py` |
| ReportAgent ReACT | Report generation still plans outline, generates sections, calls tools, logs ReACT steps, supports chat. | `backend/app/services/report_agent.py` |
| Consumer context | ReportAgent imports `ConsumerReportContextBuilder`; report context already includes consumer fields. | `backend/app/services/report_agent.py`, `backend/app/services/consumer/report_context.py` |
| Current prompt problem | Consumer mode still inherits "future prediction report" semantics in prompt constants. | `PLAN_SYSTEM_PROMPT`, `SECTION_SYSTEM_PROMPT_TEMPLATE`, `CHAT_SYSTEM_PROMPT_TEMPLATE` in `report_agent.py` |
| Interview APIs | Legacy routes exist for single, batch, all-agent, and history interviews. | `backend/app/api/simulation.py` |
| Consumer API | Canonical consumer route blueprint exists and is mounted at `/api/consumer`. | `backend/app/api/consumer.py`, `backend/app/__init__.py` |
| Frontend report | Step 4 already shows consumer report header, evidence summaries, event counts, causal chains, tool logs, and special display for `interview_agents`. | `frontend/src/components/Step4Report.vue` |
| Existing event model | `PropagationEvent.event_type` has coarse buckets: `positive_relay`, `skeptical_challenge`, `misread_amplification`, `risk_discovery`, `clarification_recovery`. | `backend/app/services/consumer/models.py` |

## 5. Design Principles

1. **Adapt, do not rewrite.**
   Phase 6F wraps existing capabilities in consumer semantics instead of renaming or replacing the core tools.

2. **Consumer mode only.**
   Prompt changes, action buttons, and consumer research APIs activate only for `consumer_test`.

3. **Backward compatibility.**
   Existing `/api/simulation/*`, `/api/report/*`, ReACT logs, and tool names remain valid.

4. **Evidence-first reporting.**
   Consumer reports must distinguish evidence-backed conclusions, simulation-derived inferences, weak support, and gatekept conclusions.

5. **No hidden Phase 7 work.**
   This phase may define future productionization needs, but implementation must not introduce DB, queue, locks, or deployment split work.

6. **No fake large society.**
   Phase 6F may use language that prepares the product for a society sandbox, but it must not imply 1000-agent execution until Phase 6G implements it.

## 6. User Experience

### 6.1 Report Conclusion Actions

Consumer reports should expose actions beside high-value findings rather than burying MiroFish tools in agent logs.

Primary action set:

| Button | Consumer meaning | Backend behavior |
|---|---|---|
| Deep dive | Explain why this conclusion emerged. | Calls insight deep dive with finding / claim / quote context. |
| Propagation path | Show how the reaction spread or was blocked. | Calls panorama path explanation and uses causal chains / events. |
| Evidence | Show source support and validation strength. | Calls evidence verifier over finding IDs, sources, and report context. |
| Ask consumers | Interview representative consumers related to the conclusion. | Calls representative sampler plus interview service. |
| Compare branch | Explain base vs intervention differences. | Calls existing branch comparison when a selected branch exists. |

These actions should appear for:

- Top risk findings.
- Top clarification opportunities.
- Causal chains.
- Generated report sections when a section has a stable section index.
- Branch comparison snapshots when available.

### 6.2 Virtual Consumer Interview

User-facing interview entry points:

- Interview advocates.
- Interview skeptics.
- Interview misreaders.
- Interview price-sensitive consumers.
- Interview high-propagation consumers.
- Build a virtual focus group.

The user should not need to understand agent IDs, Reddit, Twitter, or OASIS internals.

### 6.3 Research Director Report

The report should read as if written by a consumer research director:

- "Consumers resisted the price because..."
- "This claim propagated among..."
- "The strongest misread was..."
- "Trust recovered when..."
- "The next What-if experiment should..."

It should avoid:

- "The future will..."
- "In the predicted world..."
- "This is a future forecast..."
- Generic MiroFish "god view" phrasing in user-facing text.

## 7. Backend Design

### 7.1 Consumer Research Tool Semantics

Add a thin semantic layer that maps current tool names to consumer product concepts without breaking ReACT tool execution.

Proposed file:

```text
backend/app/services/consumer/research_tool_semantics.py
```

Responsibilities:

- Define consumer-facing tool labels.
- Define recommended prompt hints per tool.
- Define action type to tool mapping.
- Avoid importing Flask or frontend concepts.

Proposed constants:

```python
CONSUMER_TOOL_SEMANTICS = {
    "insight_forge": {
        "label": "Consumer Insight Deep Dive",
        "consumer_label_zh": "消费者洞察深挖",
        "purpose": "Explain why a finding emerged from consumer reactions, graph facts, and quotes.",
    },
    "panorama_search": {
        "label": "Propagation Path Explainer",
        "consumer_label_zh": "传播路径解释器",
        "purpose": "Explain how a claim, objection, misread, or trust repair moved through the simulation.",
    },
    "quick_search": {
        "label": "Evidence Verifier",
        "consumer_label_zh": "报告结论证据校验",
        "purpose": "Verify source support for a claim or report conclusion.",
    },
    "interview_agents": {
        "label": "Virtual Consumer Interview",
        "consumer_label_zh": "虚拟消费者深访",
        "purpose": "Ask representative consumers why they reacted, amplified, resisted, or changed intent.",
    },
}
```

This file is also the source of truth for frontend labels if exposed by API later.

### 7.2 Consumer Research Action Service

Add an application service for user-triggered report actions.

Proposed file:

```text
backend/app/services/application/consumer_research_action_service.py
```

Responsibilities:

- Validate that the simulation is `consumer_test`.
- Load simulation state, consumer summary, report context, branch context, and selected finding/section metadata.
- Call the appropriate existing capability:
  - `ZepToolsService.insight_forge`
  - `ZepToolsService.panorama_search`
  - `ZepToolsService.quick_search`
  - `ZepToolsService.interview_agents`
  - `BranchAppService.get_branch_comparison`
  - `ConsumerAppService.get_consumer_summary`
- Normalize response shape for the frontend.

Canonical action types:

```python
class ConsumerResearchActionType(str, Enum):
    DeepDiveConclusion = "deep_dive_conclusion"
    ExplainPropagationPath = "explain_propagation_path"
    VerifyEvidence = "verify_evidence"
    InterviewConsumers = "interview_consumers"
    CompareBranchDelta = "compare_branch_delta"
```

Canonical response shape:

```json
{
  "action_type": "deep_dive_conclusion",
  "simulation_id": "sim_xxx",
  "target": {
    "kind": "finding",
    "id": "finding_123",
    "label": "Low sugar claim triggers taste skepticism"
  },
  "title": "Why this conclusion emerged",
  "summary": "Short executive answer",
  "details_markdown": "Evidence-aware explanation...",
  "evidence": {
    "support_level": "strong",
    "source_count": 3,
    "simulation_quote_count": 5,
    "gatekeeping_status": "supported"
  },
  "tool_trace": {
    "tool_name": "insight_forge",
    "consumer_tool_label": "Consumer Insight Deep Dive",
    "query": "..."
  }
}
```

### 7.3 Consumer Research Action API

Add a single canonical endpoint first to avoid route sprawl.

Proposed route:

```http
POST /api/consumer/simulations/<simulation_id>/research-actions
```

Request:

```json
{
  "action_type": "deep_dive_conclusion",
  "target": {
    "kind": "finding",
    "id": "finding_123",
    "text": "Consumers doubt the low-sugar claim will taste good."
  },
  "context": {
    "report_id": "report_123",
    "section_index": 2,
    "branch_id": "branch_abc",
    "claim": "low sugar, full flavor"
  }
}
```

Response:

```json
{
  "success": true,
  "data": {
    "action_type": "deep_dive_conclusion",
    "title": "Why consumers doubted the low-sugar claim",
    "summary": "...",
    "details_markdown": "...",
    "evidence": {},
    "tool_trace": {}
  }
}
```

Error rules:

- `404`: simulation not found.
- `400`: unsupported `action_type`, missing target, or non-consumer simulation.
- `409`: branch comparison requested but selected branch is still running.
- `500`: tool execution failure.

### 7.4 Representative Consumer Service

Add a lightweight sampler for representative consumers. This is not the large society runtime.

Proposed file:

```text
backend/app/services/consumer/representative_sampler.py
```

Responsibilities:

- Load consumer round snapshots through `ConsumerStateRepository`.
- Load profiles through `SimulationRepository`.
- Identify representative consumers using existing fields:
  - attitude label
  - propagation events
  - supporting quotes
  - agent state if available
  - influence weight / role metadata if available
- Return stable role buckets.

Representative roles:

```text
advocate
skeptic
misreader
price_sensitive
high_propagation
trust_recovered
blocked_propagation
```

Response shape:

```json
{
  "agents": [
    {
      "agent_id": "agent_7",
      "display_name": "Pragmatic parent",
      "role": "skeptic",
      "segment": "family shopper",
      "attitude_start": "neutral",
      "attitude_latest": "skeptical",
      "key_quote": "I like the idea, but I need proof...",
      "round_index": 3,
      "evidence": {
        "event_ids": ["event_1"],
        "finding_ids": ["finding_2"]
      }
    }
  ]
}
```

### 7.5 Consumer Interview Service

Add a canonical consumer interview service that hides legacy platform details.

Proposed file:

```text
backend/app/services/application/consumer_interview_service.py
```

Responsibilities:

- Validate consumer simulation.
- Select representative agents if the request uses role filters.
- Build consumer research prompts.
- Prefer snapshot-based interview for completed consumer simulations.
- Optionally use live legacy interview APIs if the simulation environment is running.

Interview modes:

| Mode | Behavior |
|---|---|
| `snapshot` | Uses stored profile, quotes, round history, and LLMClient to answer as a representative consumer. Works after simulation completes. |
| `live` | Uses existing `SimulationRunner.interview_agents_batch` when the OASIS environment is alive. |
| `auto` | Use live when available, otherwise snapshot. Default. |

Canonical routes:

```http
GET  /api/consumer/simulations/<simulation_id>/representative-agents
POST /api/consumer/simulations/<simulation_id>/interviews
POST /api/consumer/simulations/<simulation_id>/focus-groups
```

Interview request:

```json
{
  "mode": "auto",
  "roles": ["skeptic", "misreader"],
  "agent_ids": [],
  "topic": "Why did the low-sugar claim trigger skepticism?",
  "questions": [
    "What would make you believe this claim?",
    "What did you think the brand was implying?"
  ],
  "max_agents": 4
}
```

Focus group request:

```json
{
  "topic": "Should we reveal ingredient proof before or after the price message?",
  "roles": ["advocate", "skeptic", "price_sensitive"],
  "max_agents": 6,
  "moderator_goal": "Find where consensus and disagreement form."
}
```

### 7.6 ReportAgent Consumer Prompt Split

Do not globally rewrite ReportAgent prompts. Add consumer-specific prompt templates and choose them only when the report context is consumer mode.

Proposed changes in:

```text
backend/app/services/report_agent.py
```

Add consumer prompt constants:

```python
CONSUMER_PLAN_SYSTEM_PROMPT
CONSUMER_PLAN_USER_PROMPT_TEMPLATE
CONSUMER_SECTION_SYSTEM_PROMPT_TEMPLATE
CONSUMER_SECTION_USER_PROMPT_TEMPLATE
CONSUMER_CHAT_SYSTEM_PROMPT_TEMPLATE
```

Prompt requirements:

- The agent identity is "Consumer Research Director Agent."
- The report must answer:
  - What first impression formed?
  - Which claims propagated?
  - Which objections or misreads spread?
  - Where did trust decay or recover?
  - What evidence changed interpretation?
  - Which What-if intervention should be tested next?
- The agent must call tools as consumer research tools:
  - Consumer Insight Deep Dive.
  - Propagation Path Explainer.
  - Evidence Verifier.
  - Virtual Consumer Interview.
- The agent must not frame consumer reports as generic future prediction reports.
- The agent must label unsupported findings as weak or simulation-only.

Selection rule:

```python
if self.project_type == "consumer_test" or report_context contains consumer fields:
    use consumer prompt templates
else:
    use existing default templates
```

Backward compatibility:

- Existing prompt constants may stay for default mode.
- Existing tool names stay unchanged in `<tool_call>` payloads.
- Existing ReACT parsing stays unchanged.

### 7.7 Consumer Event Ontology

Add a consumer event ontology layer while preserving existing coarse buckets.

Proposed file:

```text
backend/app/services/consumer/event_ontology.py
```

Canonical event types:

```text
VIEW_CLAIM
FIRST_IMPRESSION
ASK_PROOF
AMPLIFY_CLAIM
MISREAD_CLAIM
COMPARE_COMPETITOR
PRICE_RESISTANCE
TRUST_DECAY
TRUST_RECOVERY
SHARE_TO_CHANNEL
BLOCK_PROPAGATION
PURCHASE_INTENT_UP
PURCHASE_INTENT_DOWN
NEGATIVE_CASCADE
```

Compatibility strategy:

- Keep existing `PropagationEvent.event_type` values.
- Add `consumer_event_type` to generated event dictionaries where possible.
- For existing records, derive `consumer_event_type` through mapping:

| Existing bucket | Derived consumer event type |
|---|---|
| `positive_relay` | `AMPLIFY_CLAIM` |
| `skeptical_challenge` | `ASK_PROOF` |
| `misread_amplification` | `MISREAD_CLAIM` |
| `risk_discovery` | `TRUST_DECAY` |
| `clarification_recovery` | `TRUST_RECOVERY` |

This gives frontend timelines and report actions better labels without invalidating stored JSONL.

### 7.8 Evidence Verification Behavior

Evidence action should use existing evidence and confidence structures before calling generic graph search.

Order of evidence lookup:

1. `report_context.evidence_validation_summary`
2. `report_context.finding_confidences`
3. `report_context.enriched_findings`
4. `report_context.source_catalog`
5. `ZepToolsService.quick_search`

Evidence response must say:

- support level: `strong`, `medium`, `weak`, `insufficient`, `simulation_only`
- source count
- simulation quote count
- whether real materials support the conclusion
- whether gatekeeping downgraded it
- whether contradiction was detected, if available

## 8. Frontend Design

### 8.1 API Factory

Modify:

```text
frontend/src/api/consumerFactory.js
frontend/src/api/consumer.js
```

Add functions:

```javascript
runConsumerResearchAction(simulationId, data)
getRepresentativeAgents(simulationId, params)
interviewConsumers(simulationId, data)
runFocusGroup(simulationId, data)
```

All functions call `/api/consumer/*`, not legacy `/api/simulation/interview*`.

### 8.2 Consumer Research Action Bar

Proposed file:

```text
frontend/src/components/consumer/ConsumerResearchActionBar.vue
```

Responsibilities:

- Render icon/text buttons for consumer mode only.
- Emit action payloads for:
  - deep dive
  - propagation path
  - evidence
  - ask consumers
  - compare branch
- Disable branch comparison when no selected branch exists.
- Show loading state per action.

Initial mount points:

- Risk finding rows.
- Clarification opportunity rows.
- Causal chain rows.
- Section header rows in `Step4Report.vue` when completed.

### 8.3 Consumer Insight Drawer

Proposed file:

```text
frontend/src/components/consumer/ConsumerInsightDrawer.vue
```

Responsibilities:

- Display action response.
- Show title, summary, markdown details, evidence status, and tool trace.
- Distinguish:
  - insight deep dive
  - propagation path
  - evidence verification
  - branch delta
  - interview result
- Keep layout compact and analytical, not a marketing-style modal.

### 8.4 Representative Consumer Interview

Proposed file:

```text
frontend/src/components/consumer/RepresentativeConsumerInterview.vue
```

Responsibilities:

- Show representative consumer cards by role.
- Allow selecting one or more consumers.
- Provide question input and suggested prompts.
- Submit interview request.
- Render answers with agent role, segment, quote history, and support links.

Suggested prompt buttons:

- "Why did you hesitate?"
- "What proof would change your mind?"
- "What did you tell others?"
- "Where did the message become confusing?"
- "Would a price change alter your intent?"

### 8.5 Virtual Focus Group Panel

Proposed file:

```text
frontend/src/components/consumer/VirtualFocusGroupPanel.vue
```

Responsibilities:

- Select role mix.
- Set moderator goal.
- Run focus group.
- Show consensus, disagreement, surprising objections, and next What-if recommendation.

This panel can be embedded in Step 5 Interaction first, then optionally linked from Step 4 report actions.

### 8.6 Report Audit Enhancement

Step 4 already shows agent logs and special display for tool calls. Phase 6F should relabel consumer-mode tool calls:

| Raw tool | Consumer display |
|---|---|
| `insight_forge` | Consumer Insight Deep Dive |
| `panorama_search` | Propagation Path Explainer |
| `quick_search` | Evidence Verifier |
| `interview_agents` | Virtual Consumer Interview |

Modify:

```text
frontend/src/components/Step4Report.vue
frontend/src/utils/consumerMode.js
locales/en.json
locales/zh.json
```

Do not remove existing parsers for InsightForge / Panorama / Interview logs.

## 9. Data Flow

### 9.1 Report Action Flow

```text
User clicks report action
  -> ConsumerResearchActionBar emits action
  -> Step4Report calls runConsumerResearchAction()
  -> /api/consumer/simulations/{id}/research-actions
  -> ConsumerResearchActionService validates consumer simulation
  -> loads report / summary / target context
  -> calls ZepToolsService or branch comparison service
  -> returns normalized action response
  -> ConsumerInsightDrawer renders result
```

### 9.2 Interview Flow

```text
User opens interview panel
  -> frontend loads representative agents
  -> user chooses role or consumers
  -> POST /api/consumer/simulations/{id}/interviews
  -> ConsumerInterviewService builds consumer prompt
  -> auto mode chooses live or snapshot interview
  -> returns interview answers and summary
```

### 9.3 Event Ontology Flow

```text
Consumer simulation creates or loads event bucket
  -> event_ontology derives consumer_event_type
  -> ConsumerAppService includes consumer event labels in summary context
  -> frontend timeline / action surfaces use consumer labels
```

## 10. Error Handling

### 10.1 Backend

- Research actions must not fail the whole report page.
- Tool failure returns a structured error response with `tool_name`, `action_type`, and user-facing message.
- Non-consumer simulation returns `400` with "consumer research actions require consumer_test simulation."
- Missing graph ID returns a recoverable action error if summary/evidence can still be shown.
- Interview live mode returns `409` if the simulation environment is unavailable and `mode=live`.
- Interview auto mode falls back to snapshot mode when possible.

### 10.2 Frontend

- Each action button has its own loading and error state.
- Failed action opens the drawer with an error explanation instead of silently failing.
- Evidence verifier can show partial evidence if graph search fails.
- Interview panel shows "not enough representative consumers" when sampler returns empty.

## 11. Testing Strategy

### 11.1 Backend Unit Tests

Add tests:

```text
backend/tests/consumer/test_event_ontology.py
backend/tests/consumer/test_representative_sampler.py
backend/tests/services/application/test_consumer_research_action_service.py
backend/tests/services/application/test_consumer_interview_service.py
backend/tests/api/test_consumer_research_actions.py
backend/tests/api/test_consumer_interviews.py
```

Required assertions:

- Existing event buckets map to canonical consumer event types.
- Representative sampler returns expected roles from deterministic snapshots.
- Research action service validates consumer simulation.
- Research action service calls the correct Zep tool for each action type.
- Evidence action prefers report context evidence before graph search.
- Interview service falls back from live to snapshot in auto mode.
- API returns canonical success/error response shapes.

### 11.2 ReportAgent Prompt Tests

Add or update tests:

```text
backend/tests/consumer/test_report_agent_consumer_prompts.py
```

Required assertions:

- Consumer prompt contains "Consumer Research Director" or Chinese equivalent.
- Consumer prompt contains claim propagation, misread, objection, trust repair, evidence, and intervention language.
- Consumer prompt does not contain forbidden future-prediction framing:
  - "未来预测报告"
  - "未来会发生什么"
  - "future prediction report"
  - "what will happen in the future"
- Default prompt still preserves existing future prediction semantics for `project_type=default`.

### 11.3 Frontend Tests

Add tests:

```text
frontend/tests/consumerApi.behavior.test.js
frontend/tests/consumerResearchActions.test.js
frontend/tests/representativeConsumerInterview.test.js
```

Required assertions:

- Consumer API factory calls the canonical `/api/consumer` routes.
- Action bar emits the correct action payload.
- Insight drawer renders evidence support level and tool trace.
- Interview panel sends roles, topic, questions, and max agent count.
- Consumer-mode tool labels replace raw MiroFish tool names.

### 11.4 Regression Commands

Backend:

```bash
cd backend
python -m pytest tests/consumer/test_event_ontology.py tests/consumer/test_representative_sampler.py -q
python -m pytest tests/services/application/test_consumer_research_action_service.py tests/services/application/test_consumer_interview_service.py -q
python -m pytest tests/api/test_consumer_research_actions.py tests/api/test_consumer_interviews.py -q
python -m pytest tests/ --tb=short -q
```

Frontend:

```bash
cd frontend
node --test tests/*.test.js tests/composables/*.test.js
npm run build
```

Whitespace:

```bash
git diff --check
```

## 12. Acceptance Criteria

Phase 6F is complete when:

1. Consumer-mode ReportAgent output is framed as consumer research, not future prediction.
2. Default legacy report mode remains behaviorally compatible.
3. Consumer report findings have visible action buttons for deep dive, propagation path, evidence, interview, and branch comparison.
4. Research actions return normalized evidence-aware responses through `/api/consumer`.
5. Representative consumer selection works from existing snapshots.
6. Consumer interview and focus group endpoints exist and hide legacy platform details.
7. Consumer event ontology is available in summary context without breaking existing stored event buckets.
8. Report audit logs show consumer-facing tool labels in consumer mode.
9. Backend and frontend targeted tests pass.
10. Full existing backend/frontend regression commands are still expected to pass.

## 13. Recommended Implementation Sequence

### Batch 1: Backend semantics and prompt split

- Add `research_tool_semantics.py`.
- Add consumer prompt constants in `report_agent.py`.
- Add prompt selection logic.
- Add prompt tests.

### Batch 2: Consumer event ontology

- Add `event_ontology.py`.
- Update event generation or report context construction to include derived `consumer_event_type`.
- Add event ontology tests.

### Batch 3: Research action service and API

- Add `consumer_research_action_service.py`.
- Add `/api/consumer/simulations/<simulation_id>/research-actions`.
- Add API/service tests with mocked ZepToolsService.

### Batch 4: Representative sampler and interview service

- Add `representative_sampler.py`.
- Add `consumer_interview_service.py`.
- Add representative, interview, and focus group routes.
- Add sampler/service/API tests.

### Batch 5: Frontend API and report action surfaces

- Extend `consumerFactory.js`.
- Add `ConsumerResearchActionBar.vue`.
- Add `ConsumerInsightDrawer.vue`.
- Wire into `Step4Report.vue`.
- Add frontend tests.

### Batch 6: Interview and focus group panels

- Add `RepresentativeConsumerInterview.vue`.
- Add `VirtualFocusGroupPanel.vue`.
- Wire into `Step5Interaction.vue` and report action drawer.
- Add frontend tests.

### Batch 7: Regression and documentation

- Update `README.md` / `README-ZH.md` only if product copy needs to mention Phase 6F behavior.
- Run targeted tests.
- Run full regression if feasible.
- Run `git diff --check`.

## 14. Future Hooks

Phase 6F should leave clean extension points for later phases:

| Future phase | Hook created in Phase 6F |
|---|---|
| Phase 6G large society | Event ontology, representative sampler contract, research action service |
| Phase 6H multi-channel | Consumer event type and future `channel_id` field in event/action responses |
| Phase 6I focus group | Consumer interview service and focus group API |
| Phase 7 productionization | Canonical `/api/consumer` boundaries and service-layer isolation |

## 15. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Prompt rewrite changes default reports | Select prompts only for consumer mode; add tests proving default mode still uses legacy framing. |
| Tool labels diverge from actual tool names | Keep raw tool names in backend execution; use semantic labels only at prompt/UI layer. |
| Interview requires live simulation process | Support snapshot interview fallback in `auto` mode. |
| Frontend `Step4Report.vue` grows larger | Add focused child components for action bar and drawer; avoid embedding large new logic inline. |
| Event ontology breaks existing JSONL | Add derived `consumer_event_type`; do not replace existing `event_type`. |
| Evidence action overpromises certainty | Response must include support level and simulation-only/weak-support labels. |

## 16. Open Decisions for Review

This spec makes two decisions that should be explicitly reviewed:

1. **Snapshot interview is allowed.**
   Completed consumer simulations can support virtual consumer interviews using stored persona/profile/round history even when the live simulation process is no longer running.

2. **Single research action endpoint first.**
   Phase 6F starts with one `/research-actions` endpoint for report actions, plus separate interview/focus-group endpoints. If product usage grows, actions can later be split into dedicated routes.

If these decisions are accepted, the next step is to write a task-by-task implementation plan for Phase 6F.
