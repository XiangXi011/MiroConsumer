# Consumer Simulation Testing Phase 3 Master Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the full Phase 3 program for `consumer_test` by executing four ordered subprojects: dual-source Tiered RAG, researcher interventions, social sandbox upgrades, and research assetization.

**Architecture:** Keep MiroFish's existing `/api/graph -> /api/simulation -> /api/report` backbone and extend the `backend/app/services/consumer/` package with a project-scoped research workspace, branchable simulation state, richer network-aware sandbox logic, and reusable comparison artifacts. Each subproject should ship as a self-contained slice that preserves default mode and leaves a stable acceptance baseline for the next slice.

**Tech Stack:** Flask, existing MiroFish simulation/report stack, Pydantic models, repo-local file persistence, pytest, Vue 3 + Vite, Axios, locale JSON

---

## Constraints And Working Rules

- Phase 3 must stay inside the current repo-local persistence model.
- `consumer_test` remains the only Phase 3 entry point.
- `project_type=default` behavior must remain unchanged.
- DingTalk stays out of scope.
- Packaging, A/B, and pricing remain out of scope.
- Every subproject must end with:
  - backend tests
  - targeted frontend tests
  - `npm run build`
  - one realistic manual smoke path if the slice changes end-user workflow

## Execution Order

1. `Phase 3A`: Dual-Source Tiered RAG Research Foundation
2. `Phase 3B`: Researcher-In-The-Loop Intervention And Branching
3. `Phase 3C`: OASIS Social Sandbox Upgrade
4. `Phase 3D`: Research Assetization And Comparative Workspace

## Task Group 1: Phase 3A Research Foundation

**Files:**
- Create: `backend/app/services/consumer/source_registry.py`
- Create: `backend/app/services/consumer/document_ingest.py`
- Create: `backend/app/services/consumer/retrieval.py`
- Create: `backend/app/services/consumer/finding_distiller.py`
- Create: `backend/tests/consumer/test_source_registry.py`
- Create: `backend/tests/consumer/test_document_ingest.py`
- Create: `backend/tests/consumer/test_retrieval.py`
- Create: `backend/tests/consumer/test_finding_distiller.py`
- Modify: `backend/app/services/consumer/models.py`
- Modify: `backend/app/services/consumer/research_ingest.py`
- Modify: `backend/app/services/consumer/graph_builder.py`
- Modify: `backend/app/services/consumer/report_context.py`
- Modify: `backend/app/api/graph.py`
- Modify: `backend/app/api/simulation.py`
- Modify: `backend/app/services/simulation_manager.py`
- Modify: `frontend/src/views/Home.vue`
- Modify: `frontend/src/api/graph.js`
- Modify: `frontend/src/components/Step2EnvSetup.vue`
- Modify: `frontend/src/components/Step4Report.vue`
- Modify: `locales/zh.json`
- Modify: `locales/en.json`

- [ ] Write failing backend tests for source registration, chunk extraction, retrieval ranking, and finding distillation.
- [ ] Implement project-scoped research workspace storage under `backend/uploads/projects/<project_id>/research/`.
- [ ] Replace deterministic-only `auto_enrich` output with dual-lane findings resolution:
  - lane A = uploaded/user-provided materials
  - lane B = public-web supplemental search
- [ ] Preserve provenance on every distilled finding:
  - `source_id`
  - `snippet_id`
  - `retrieval_trace_id`
  - `visibility`
- [ ] Expose research mode and source summary in Step 2 and citation-ready findings in Step 4.
- [ ] Run verification:
  - `Set-Location backend; .\.venv\Scripts\python.exe -m pytest tests -q --ignore=tests/integration`
  - `node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js frontend/tests/pendingUpload.test.js`
  - `Set-Location frontend; npm run build`
- [ ] Commit with a Phase 3A-specific message.

## Task Group 2: Phase 3B Intervention And Branching

**Files:**
- Create: `backend/app/services/consumer/intervention_manager.py`
- Create: `backend/tests/consumer/test_intervention_manager.py`
- Create: `backend/tests/api/test_consumer_interventions.py`
- Modify: `backend/app/services/consumer/models.py`
- Modify: `backend/app/services/consumer/orchestrator.py`
- Modify: `backend/app/services/consumer/scoring.py`
- Modify: `backend/app/services/consumer/report_context.py`
- Modify: `backend/app/api/simulation.py`
- Modify: `backend/app/services/simulation_runner.py`
- Modify: `frontend/src/api/simulation.js`
- Modify: `frontend/src/components/Step3Simulation.vue`
- Modify: `frontend/src/components/Step4Report.vue`
- Modify: `frontend/src/components/Step5Interaction.vue`
- Modify: `locales/zh.json`
- Modify: `locales/en.json`

- [ ] Write failing tests for branch creation, intervention logging, and branch-vs-base comparison fields.
- [ ] Introduce intervention contracts:
  - clarification injection
  - revised claim injection
  - evidence reveal
  - branch fork from round N
- [ ] Persist branch state under `backend/uploads/simulations/<simulation_id>/branches/<branch_id>/`.
- [ ] Add API routes for:
  - creating a branch
  - listing interventions
  - resuming a branch
  - fetching branch comparison context
- [ ] Surface intervention controls in Step 3 and branch diffs in Step 4.
- [ ] Add Step 5 follow-up prompts that reference the selected branch.
- [ ] Run verification:
  - backend tests including new intervention routes
  - targeted frontend tests for branch/intervention helpers
  - `npm run build`
- [ ] Commit with a Phase 3B-specific message.

## Task Group 3: Phase 3C Social Sandbox Upgrade

**Files:**
- Create: `backend/app/services/consumer/social_topology.py`
- Create: `backend/app/services/consumer/cascade_metrics.py`
- Create: `backend/tests/consumer/test_social_topology.py`
- Create: `backend/tests/consumer/test_cascade_metrics.py`
- Modify: `backend/app/services/consumer/persona_pack.py`
- Modify: `backend/app/services/consumer/orchestrator.py`
- Modify: `backend/app/services/consumer/event_engine.py`
- Modify: `backend/app/services/consumer/scoring.py`
- Modify: `backend/app/services/consumer/report_context.py`
- Modify: `backend/app/api/simulation.py`
- Modify: `frontend/src/components/Step3Simulation.vue`
- Modify: `frontend/src/components/Step4Report.vue`
- Modify: `frontend/src/utils/consumerMode.js`
- Modify: `locales/zh.json`
- Modify: `locales/en.json`

- [ ] Write failing tests for multi-community topology, seeded narrative spread, and cascade metric computation.
- [ ] Expand persona pack and run-time cohort logic to support:
  - communities
  - amplifiers
  - skeptics
  - bridge nodes
  - low-visibility lurkers
- [ ] Add community-aware propagation paths and measurable cascade metrics.
- [ ] Update scoring and report context to explain:
  - cross-community spread
  - blockage
  - reversal
  - narrative takeover
- [ ] Extend Step 3 and Step 4 to surface sandbox metrics without breaking the current flow.
- [ ] Run verification:
  - backend tests for topology and cascade metrics
  - targeted frontend tests
  - `npm run build`
- [ ] Commit with a Phase 3C-specific message.

## Task Group 4: Phase 3D Research Assets And Comparison

**Files:**
- Create: `backend/app/services/consumer/asset_library.py`
- Create: `backend/app/services/consumer/comparison_engine.py`
- Create: `backend/tests/consumer/test_asset_library.py`
- Create: `backend/tests/consumer/test_comparison_engine.py`
- Modify: `backend/app/services/consumer/report_context.py`
- Modify: `backend/app/services/report_agent.py`
- Modify: `backend/app/api/report.py`
- Modify: `backend/app/api/simulation.py`
- Modify: `frontend/src/api/report.js`
- Modify: `frontend/src/components/Step4Report.vue`
- Modify: `frontend/src/components/Step5Interaction.vue`
- Modify: `locales/zh.json`
- Modify: `locales/en.json`

- [ ] Write failing tests for exporting reusable research packs and comparing two runs or branches.
- [ ] Implement repo-local asset storage under `backend/uploads/research_assets/`.
- [ ] Add comparison workflows that can compare:
  - run vs run
  - branch vs base
  - project vs project
- [ ] Render stable comparison outputs:
  - resonance overlap
  - recurring risk signals
  - evidence-backed divergences
- [ ] Add report-side access to saved packs and comparisons.
- [ ] Run verification:
  - backend comparison and asset tests
  - targeted frontend tests
  - `npm run build`
- [ ] Commit with a Phase 3D-specific message.

## Global Acceptance Gate

- [ ] Phase 3A through Phase 3D all land as separate reviewable diffs.
- [ ] Each subproject preserves default-mode compatibility.
- [ ] Each subproject updates its own docs and handoff notes before the next one starts.
- [ ] The final branch can demonstrate:
  - source-grounded findings
  - branchable interventions
  - richer social sandbox behavior
  - reusable comparison artifacts
