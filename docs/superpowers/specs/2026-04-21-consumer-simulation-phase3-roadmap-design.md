# Consumer Simulation Testing Phase 3 Roadmap Design

## 1. Goal

Phase 3 upgrades `consumer_test` from a validated simulation workflow into a research-grade consumer insight platform, while keeping MiroFish's existing `/api/graph -> /api/simulation -> /api/report` backbone intact.

The design target is not "more test types" yet. Phase 3 focuses on four realism and usability upgrades:

- dual-source Tiered RAG research grounding
- researcher-in-the-loop interventions and branch reruns
- fuller OASIS-style social sandbox behavior
- reusable research assets and comparative analysis

## 2. Scope And Explicit Exclusions

### 2.1 In Scope

- project-scoped research workspaces
- user-uploaded material ingestion and structured retrieval
- public-web supplemental search with source governance
- branchable simulation runs with intervention logs
- richer community / cascade / role-aware propagation
- reusable research packs and cross-run comparison

### 2.2 Out Of Scope

- DingTalk or external focus-group connectors
- packaging / A-B / pricing test expansion
- auth, database, Celery, or SaaS multi-tenant replatforming
- real-time live search during every propagation round

## 3. Why Phase 3 Must Be Decomposed

Phase 3 is not one feature. It is a program made of four dependent subprojects:

1. `Phase 3A`: Dual-Source Tiered RAG Research Foundation
2. `Phase 3B`: Researcher-In-The-Loop Intervention And Branching
3. `Phase 3C`: OASIS Social Sandbox Upgrade
4. `Phase 3D`: Research Assetization And Comparative Workspace

Trying to implement all four as one Claude task would create the same failure mode we already avoided in earlier phases: mixed responsibilities, blurry acceptance criteria, and hard-to-review diffs.

## 4. Cross-Cutting Principles

- MiroFish remains the primary product skeleton.
- `consumer_test` stays an explicit branch, not a replacement for default mode.
- project-local snapshots come before cross-project reuse.
- user-provided materials always outrank public-web supplements.
- every finding must preserve provenance:
  - source
  - snippet
  - retrieval trace
  - visibility layer
- reports may summarize, but they cannot erase the evidence chain.
- every Phase 3 subproject must preserve:
  - `project_type=default` behavior
  - reproducible reruns from stored state
  - repo-local file persistence patterns already used by MiroFish

## 5. Shared Data Model Direction

Phase 3 introduces a richer project-scoped research workspace beside the current consumer graph and simulation state.

### 5.1 Research Workspace

Recommended storage root:

`backend/uploads/projects/<project_id>/research/`

Planned artifacts:

- `sources.json`
- `documents.json`
- `chunks.jsonl`
- `retrieval_traces.jsonl`
- `findings.json`
- `research_snapshot.json`

### 5.2 Simulation Branch Workspace

Recommended storage root:

`backend/uploads/simulations/<simulation_id>/branches/<branch_id>/`

Planned artifacts:

- `branch_state.json`
- `interventions.jsonl`
- `branch_metrics.json`
- `branch_report_context.json`

### 5.3 Research Asset Workspace

Recommended storage root:

`backend/uploads/research_assets/`

Planned artifacts:

- curated source packs
- reusable findings packs
- benchmark summaries
- comparison snapshots

## 6. Phase 3A: Dual-Source Tiered RAG Research Foundation

### 6.1 Objective

Replace the current repo-owned deterministic `auto_enrich` synthesis with a real, project-scoped research substrate that combines:

- `Lane A`: user uploads and user-provided URLs
- `Lane B`: public-web supplemental search

This layer should feed graph build, simulation preparation, reports, and Step 5 follow-up with source-backed findings.

### 6.2 Core Modules

- `Research Source Registry`
- `Extraction And Chunking`
- `Dual-Lane Retrieval`
- `Finding Distiller`
- `Graph And Simulation Adapter`
- `Report And Interaction Adapter`

### 6.3 Key Rules

- user materials have higher trust and ranking priority
- public-web results can fill gaps but not override user-provided context
- findings must be typed, cited, and visibility-tagged
- the first version uses a frozen pre-simulation research snapshot

### 6.4 Acceptance

- one project can ingest uploaded files plus URLs into a retrievable corpus
- enabling public search adds lane-B findings with explicit source labels
- reports can cite source snippets and retrieval traces
- the orchestrator receives research findings from the research snapshot, not only synthetic brief-derived hints

## 7. Phase 3B: Researcher-In-The-Loop Intervention And Branching

### 7.1 Objective

Allow researchers to intervene in a running or prepared simulation without destroying reproducibility.

Examples:

- inject a clarification message
- add a new claim or revised copy
- reveal a new source-backed fact
- fork a branch from round N and compare outcomes

### 7.2 Core Modules

- `Intervention Contract`
- `Branch Manager`
- `Run Control API`
- `Branch Comparison Context`
- `Step 3 Intervention UI`
- `Step 4 Branch Diff UI`

### 7.3 Key Rules

- original run remains immutable
- every intervention must be logged with actor, timestamp, target round, and payload
- branch outputs must be comparable to the base run
- interventions should reuse the same research snapshot unless explicitly refreshed

### 7.4 Acceptance

- a researcher can fork from an existing run
- the branch records its intervention log
- reports can explain what changed after the intervention
- base and branch outcomes can be compared on attitude, cascade, and risk signals

## 8. Phase 3C: OASIS Social Sandbox Upgrade

### 8.1 Objective

Move from a primarily round-based propagation simulation to a richer consumer social sandbox with community structure, role asymmetry, and cascade-aware metrics.

### 8.2 Core Modules

- `Community Topology Builder`
- `Narrative Seeding Strategy`
- `Role And Influence Expansion`
- `Cascade Metrics`
- `Sandbox Report Context`

### 8.3 Key Rules

- community topology must remain interpretable, not arbitrary noise
- role behavior must still stay grounded in persona traits and visible findings
- cascade metrics must be evidence-backed, not only LLM-described
- the sandbox should remain replayable from persisted state

### 8.4 Acceptance

- simulations can represent multiple communities or audience clusters
- seeded narratives produce measurable spread differences
- reports can identify cross-community amplification, blockage, and reversal
- UI can surface the main network and cascade signals without replacing the existing Step flow

## 9. Phase 3D: Research Assetization And Comparative Workspace

### 9.1 Objective

Turn one-off simulation work into reusable research assets, while still staying repo-local and project-safe in the first version.

### 9.2 Core Modules

- `Research Pack Export`
- `Findings Library`
- `Comparison Engine`
- `Benchmark Report Builder`

### 9.3 Key Rules

- assetization comes after evidence quality, not before
- reusable packs must keep source lineage
- comparison must be explicit about which projects / branches / source packs were used
- the first version should avoid hidden cross-project leakage

### 9.4 Acceptance

- a project can export a reusable research pack
- two or more runs can be compared on stable metrics and evidence bundles
- reports can highlight recurring resonance / risk patterns across runs

## 10. Dependency Order

Recommended execution order:

1. `Phase 3A`
2. `Phase 3B`
3. `Phase 3C`
4. `Phase 3D`

Rationale:

- `3A` is the hard dependency because it replaces the weakest current realism layer
- `3B` creates a practical researcher workflow on top of the current validated engine
- `3C` deepens the simulation once evidence grounding and intervention controls exist
- `3D` should only happen after the preceding outputs are stable enough to reuse and compare

## 11. Claude Code Execution Strategy

Phase 3 should not be sent to Claude Code as one monolithic ask.

Recommended working mode:

- one subproject at a time
- one implementation plan per subproject
- Codex handles:
  - planning
  - task slicing
  - acceptance review
- Claude Code handles:
  - implementation
  - test execution
  - incremental fixes after review

## 12. Phase Gates

Phase 3A gate:

- source-backed findings replace purely synthetic `auto_enrich`

Phase 3B gate:

- branchable intervention workflow is reproducible and reviewable

Phase 3C gate:

- richer sandbox behavior yields measurable, reportable social dynamics

Phase 3D gate:

- reusable packs and comparisons create repeatable research leverage without hidden leakage

## 13. Final Recommendation

Treat Phase 3 as a staged program, not a single sprint:

- build the research foundation first
- layer in intervention control second
- deepen sandbox realism third
- only then productize reuse and comparison

This keeps MiroConsumer aligned with its core promise: consumer testing that is not only simulated, but grounded, steerable, and explainable.

## 14. Implementation Status (2026-04-22)

Phase 3 is now implemented on `codex/consumer-simulation-phase1`.

### 14.1 Delivered Scope

- **Phase 3A:** project-scoped research workspace, lane-aware ingestion, URL ingestion, public-web supplement, persisted findings/snapshots, citation-ready findings and traces in Step 4/5
- **Phase 3B:** branch creation, intervention logging, runnable branch simulations, branch status, branch comparison, branch-aware prompts
- **Phase 3C:** social topology roles and communities, topology-aware propagation targets, cascade metrics, sandbox metrics in Step 3/4, sandbox-aware prompts in Step 5
- **Phase 3D:** reusable research pack export, persisted comparison snapshots, `run_vs_run` / `branch_vs_base` / `project_vs_project` comparisons, Step 4 comparison workspace, Step 5 comparison-aware follow-ups

### 14.2 Verification Snapshot

- Backend regression:
  - `backend/.venv/Scripts/python.exe -m pytest tests -q --ignore=tests/integration`
  - Result: `270 passed`
- Frontend targeted regression:
  - `node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js frontend/tests/pendingUpload.test.js`
  - Result: `61 passed`
- Frontend build:
  - `npm run build`
  - Result: success

### 14.3 Residual Non-Blocking Limits

- `Lane B` already supports a grounded provider path plus deterministic fallback, but stronger real-world provider quality is still a future upgrade path.
- `project_vs_project` comparison currently prioritizes research artifacts and signal divergence; if a project lacks run-level outputs, acceptance fields remain conservative.
- Existing non-blocking frontend warnings remain:
  - `pendingUpload.js` mixed dynamic/static import warning
  - chunk size warning
