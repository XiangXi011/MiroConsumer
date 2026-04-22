# Consumer Simulation Phase 4B Test Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend MiroConsumer to support packaging, A/B, and price testing while preserving the current graph/simulation/report backbone.

**Architecture:** Expand the consumer brief schema, make graph/report layers task-aware, and surface the new task types through the existing consumer UI instead of creating a new workflow.

**Tech Stack:** Flask, Python dataclasses/Pydantic, Vue 3, Vite

---

### Task 1: Extend Consumer Brief Schema

**Files:**
- Modify: `backend/app/services/consumer/models.py`
- Modify: `backend/app/services/consumer/brief_adapter.py`
- Test: `backend/tests/consumer/test_consumer_brief.py`

- [ ] Add failing tests for `packaging_test`, `ab_test`, and `price_test`
- [ ] Add task-specific validation rules with backward compatibility for old task types
- [ ] Re-run the targeted tests
- [ ] Commit with: `feat: extend consumer brief task types`

### Task 2: Add Graph Support For Packaging / Variant / Price

**Files:**
- Modify: `backend/app/services/consumer/graph_builder.py`
- Modify: `backend/app/services/consumer/research_ingest.py`
- Test: `backend/tests/consumer/test_graph_builder.py`

- [ ] Add failing graph-builder tests for:
  - packaging nodes
  - variant nodes
  - price-point nodes
- [ ] Implement the new node/edge families with existing visibility semantics
- [ ] Re-run targeted graph/research tests
- [ ] Commit with: `feat: add graph support for expanded test types`

### Task 3: Make Simulation & Summary Task-Aware

**Files:**
- Modify: `backend/app/services/consumer/orchestrator.py`
- Modify: `backend/app/services/consumer/scoring.py`
- Modify: `backend/app/services/consumer/report_context.py`
- Modify: `backend/app/services/simulation_manager.py`
- Test: `backend/tests/consumer/test_orchestrator.py`
- Test: `backend/tests/consumer/test_report_context.py`

- [ ] Add failing tests for task-aware prompt context and report summaries
- [ ] Implement packaging/variant/price-aware prompt shaping
- [ ] Add task-aware summary/report sections
- [ ] Re-run targeted tests, then the full backend non-integration suite
- [ ] Commit with: `feat: add task-aware simulation summaries`

### Task 4: Add Frontend Task Inputs

**Files:**
- Modify: `frontend/src/views/Home.vue`
- Modify: `frontend/src/store/pendingUpload.js`
- Modify: `frontend/src/utils/consumerMode.js`
- Modify: `locales/en.json`
- Modify: `locales/zh.json`
- Test: `frontend/tests/consumerBrief.test.js`

- [ ] Add task-type selector and conditional inputs for packaging / A/B / price
- [ ] Keep old concept/copy inputs working
- [ ] Re-run targeted frontend tests
- [ ] Commit with: `feat: add phase4b consumer input fields`

### Task 5: Surface Task-Aware Reports & Follow-Ups

**Files:**
- Modify: `frontend/src/components/Step4Report.vue`
- Modify: `frontend/src/components/Step5Interaction.vue`
- Modify: `frontend/tests/consumerMode.test.js`

- [ ] Add task-aware report cards and labels
- [ ] Add follow-up prompts specific to packaging / A/B / price
- [ ] Re-run targeted frontend tests and `npm run build`
- [ ] Commit with: `feat: surface phase4b report outputs`

### Task 6: Verification & Docs

**Files:**
- Modify: `PRD.md`
- Add or Modify: `docs/superpowers/handoffs/2026-04-22-consumer-simulation-phase4b-handoff.md`

- [ ] Run backend full non-integration tests
- [ ] Run frontend targeted tests
- [ ] Run frontend build
- [ ] Update docs/handoff with 4B outcomes, limits, and examples
- [ ] Commit with: `docs: record phase4b completion`

