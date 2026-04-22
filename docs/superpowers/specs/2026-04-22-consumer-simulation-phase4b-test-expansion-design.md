# Consumer Simulation Phase 4B Test Expansion Design

**Date:** 2026-04-22  
**Branch:** `codex/consumer-simulation-phase1`

---

## 1. Goal

Phase 4B expands MiroConsumer from “concept + copy propagation testing” into a broader consumer testing workbench without replacing the existing architecture.

The phase adds three new task types:

- `packaging_test`
- `ab_test`
- `price_test`

The same MiroFish backbone remains:

`graph -> simulation -> report -> interaction`

---

## 2. Scope

### 2.1 In Scope

- extend `ConsumerTaskType`
- extend `ConsumerBusinessBrief`
- add graph support for packaging / variants / price points
- make report outputs task-aware
- add frontend input fields for the new task types
- keep concept/copy flows backward compatible

### 2.2 Out Of Scope

- computer-vision packaging understanding
- real checkout or market-sales prediction
- external pricing datasets
- a new product shell or separate workflow

---

## 3. Product Contract

### 3.1 New Task Types

#### `packaging_test`

Purpose:

- test whether packaging descriptors trigger trust, appeal, confusion, or risk

New brief fields:

- `packaging_assets`: list of packaging descriptions, claims, or asset labels

#### `ab_test`

Purpose:

- compare two or more message/product variants inside the same consumer-testing workflow

New brief fields:

- `test_variants`: ordered list of variants
- each variant can include:
  - `variant_id`
  - `label`
  - `concept_assets`
  - `copy_material`
  - `claims`
  - optional `packaging_assets`
  - optional `price_points`

#### `price_test`

Purpose:

- test price acceptance, objection triggers, and perceived value thresholds

New brief fields:

- `price_points`: ordered list of price options or ranges
- `price_context`: optional framing text such as “subscription”, “promo”, or “single pack”

### 3.2 Compatibility Rule

- old `concept_test` and `copy_feedback` payloads must continue to work unchanged
- the new fields are only required for their corresponding task types

---

## 4. Design

### 4.1 Brief Layer

`ConsumerBusinessBrief` becomes task-aware:

- all existing base fields stay
- task-specific optional fields are added
- validation rules depend on `task_type`

Examples:

- `packaging_test` requires `packaging_assets`
- `ab_test` requires at least 2 variants
- `price_test` requires at least 1 price point

### 4.2 Graph Layer

`ConsumerGraphBuilder` adds new node/edge families:

- `PackagingCue`
- `Variant`
- `PricePoint`

Example relationships:

- `HAS_PACKAGING_CUE`
- `HAS_VARIANT`
- `HAS_PRICE_POINT`
- `COMPARES_VARIANT`
- `EVALUATES_PRICE`

Visibility rules remain the same:

- direct stimuli are `Initial`
- discussion topics are `Propagation_Only`
- deeper risks remain `Restricted`

### 4.3 Simulation Layer

The consumer orchestrator remains shared, but prompt assembly becomes task-aware:

- `packaging_test` surfaces packaging cues in Round 0
- `ab_test` explicitly pins the active variant context
- `price_test` surfaces price anchors and framing context

No separate simulation engine is introduced.

### 4.4 Report Layer

Phase 4B adds task-aware summaries on top of the existing report format.

#### Packaging

- top packaging hooks
- trust/credibility objections
- confusion or misread triggers tied to pack language

#### A/B

- variant-level acceptance comparison
- resonance/risk delta by variant
- persona divergence by variant

#### Price

- acceptable vs resisted price points
- price objection triggers
- value-for-money framing opportunities

The common confidence / evidence / benchmark layers from Phase 4A remain active.

### 4.5 Frontend

The Home form remains one entry point with task-aware fields:

- keep `consumer_test`
- add task-type switch inside the consumer brief
- reveal only the fields needed for the active task

Step 4 and Step 5 should surface the new task-aware outputs without changing route structure.

---

## 5. Files

### Backend

- `backend/app/services/consumer/models.py`
- `backend/app/services/consumer/brief_adapter.py`
- `backend/app/services/consumer/graph_builder.py`
- `backend/app/services/consumer/research_ingest.py`
- `backend/app/services/consumer/orchestrator.py`
- `backend/app/services/consumer/scoring.py`
- `backend/app/services/consumer/report_context.py`
- `backend/app/services/simulation_manager.py`

### Frontend

- `frontend/src/views/Home.vue`
- `frontend/src/components/Step4Report.vue`
- `frontend/src/components/Step5Interaction.vue`
- `frontend/src/utils/consumerMode.js`
- `locales/en.json`
- `locales/zh.json`

---

## 6. Acceptance

- all three new task types validate correctly
- existing concept/copy briefs remain backward compatible
- graph metadata and summary outputs reflect the active task type
- Step 4 shows task-aware findings
- Step 5 suggests task-aware follow-up questions
- backend and frontend regression suites stay green

---

## 7. Implementation Outcome (2026-04-22)

Phase 4B is now implemented on `codex/consumer-simulation-phase1`.

Delivered changes:

- backend brief/schema now supports:
  - `packaging_assets`
  - `test_variants`
  - `price_points`
  - `price_context`
- old-style backend `variants: ["A", "B"]` payloads normalize into `test_variants`
- graph builder now emits:
  - `PackagingCue`
  - `Variant`
  - `PricePoint`
- simulation runner and orchestrator now carry task-aware prompt focus for:
  - `packaging_test`
  - `ab_test`
  - `price_test`
- consumer summary / report context now expose:
  - `task_type`
  - packaging-specific fields
  - A/B-specific fields
  - price-specific fields
- Home form now supports task-type-aware fields under the existing `consumer_test` entry
- Step 4 and Step 5 now surface task-aware findings and follow-up prompts

Verified results:

- backend targeted regression: `115 passed`
- backend full non-integration regression: `411 passed`
- frontend targeted tests: `89 passed`
- frontend build: success

---

## 8. Risks

- overcomplicating the brief schema; keep the first version compact
- trying to infer packaging visuals beyond text evidence; Phase 4B should stay descriptor-based
- building a separate comparison engine for A/B; reuse the existing comparison/report structures instead
