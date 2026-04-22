# Consumer Simulation Phase 5 Roadmap Design

## 1. Background

By the end of Phase 4, MiroConsumer has already formed a usable consumer testing and propagation decision platform:

- `concept_test`, `copy_feedback`, `packaging_test`, `ab_test`, and `price_test` are all available in one unified workflow
- project-level research workspace, dual-lane research ingest, propagation simulation, branch rerun, comparison, and research asset export are in place
- credibility, evidence validation, benchmark replay, efficiency upgrades, and broader test coverage have already been added

At this point, the bottleneck is no longer "can the workflow run", but rather:

- how trustworthy the results feel in real business decisions
- how much real creative material the system can understand
- how far the runtime can scale in sample size, concurrency, and cost control
- how effectively research outputs can become reusable organizational memory

Phase 5 focuses on strengthening those four dimensions.

## 2. Phase 5 Goal

Phase 5 upgrades MiroConsumer from a strong internal research workbench into a more credible, more multimodal, more scalable, and more reusable consumer decision platform.

In practical terms, Phase 5 should make the system better at answering:

- "How much should we trust this result?"
- "Can it test the actual packaging or visual creative, not just text descriptions?"
- "Can it run larger and faster without becoming too expensive?"
- "Can our research accumulate into reusable category and brand memory?"

## 3. Non-Goals

Phase 5 is not intended to:

- introduce DingTalk or external live focus-group workflows
- turn `price_test` into a sales forecasting engine
- replace all human qualitative research
- rebuild the MiroFish core architecture

## 4. Roadmap Principles

- Keep the existing `brief -> graph -> simulation -> report -> interaction` backbone intact
- Prefer extensions that improve trust, realism, and operational reuse over adding flashy but weakly grounded features
- Make every new confidence or benchmark claim traceable to evidence
- Preserve backward compatibility for existing `consumer_test` projects
- Keep subprojects independently deliverable so Claude Code can execute them in batches without blocking the whole roadmap

## 5. Phase 5 Subprojects

### 5.1 Phase 5A: Trust and Validation Layer

This subproject strengthens the answer to "How reliable is this result?"

Scope:

- expand benchmark replay into a fuller validation layer
- support historical case backtesting and result calibration
- refine source governance, freshness scoring, and provider-level reliability signals
- introduce confidence calibration based on replay quality, evidence sufficiency, and source quality
- surface validation status in report, comparison, and interaction flows

Expected impact:

- results become easier to defend in business reviews
- the system becomes more transparent about where confidence comes from
- "simulation says so" turns into "simulation says so, and here is how well that pattern has held historically"

### 5.2 Phase 5B: Multimodal Packaging and Creative Stimulus

This subproject upgrades testing from mostly text-based packaging and creative descriptors into richer multimodal stimuli.

Scope:

- ingest packaging images, KV assets, and simple creative boards
- extract visual descriptors and map them into the existing consumer graph
- support multimodal packaging interpretation in `packaging_test`
- support comparison between text-only and image-backed stimulus interpretations
- expose visual evidence references in report and interaction

Expected impact:

- packaging and creative testing become far more realistic
- teams can test real materials rather than only textual descriptions
- visual cues become first-class inputs in propagation and trust formation

### 5.3 Phase 5C: Scaled Runtime and Model Orchestration

This subproject improves throughput, latency, and cost control.

Scope:

- optimize profile generation and prepare-time concurrency
- add more explicit caching, batching, and retry policies
- improve branch rerun efficiency and partial reuse of intermediate artifacts
- introduce model-routing policies for fast vs deep tasks
- improve failure recovery, queue behavior, and longer-run stability

Expected impact:

- larger simulations become practical
- repeated experiments become cheaper
- runtime becomes more predictable for daily team usage

### 5.4 Phase 5D: Research Memory and Operating System

This subproject turns repeated tests into a stronger organizational asset layer.

Scope:

- build category-level benchmark and memory views
- improve project-to-project comparison and recurring insight extraction
- strengthen reusable templates, scenario presets, and category baselines
- support more structured lineage for assets, conclusions, and downstream reuse
- build toward a research operating system rather than a set of isolated runs

Expected impact:

- research value compounds over time
- teams avoid re-learning the same category patterns from scratch
- the platform becomes more embedded in recurring planning and launch workflows

## 6. Recommended Execution Order

Recommended order:

1. `Phase 5A: Trust and Validation Layer`
2. `Phase 5B: Multimodal Packaging and Creative Stimulus`
3. `Phase 5C: Scaled Runtime and Model Orchestration`
4. `Phase 5D: Research Memory and Operating System`

Rationale:

- trust comes first because stronger validation increases the value of every later capability
- multimodal stimulus is the most visible realism upgrade for customer-facing use cases
- scaling work is most efficient once the intended workload shape is clearer
- memory and operating-system features benefit from the stronger validation and richer stimuli produced upstream

## 7. Architecture Direction

Phase 5 should continue to extend existing modules rather than replacing them:

- `consumer/research_*` continues to host source quality, replay, benchmark, and provider governance work
- `consumer/graph_builder`, `consumer/scoring`, and `consumer/report_context` continue to absorb richer stimulus and validation signals
- simulation runtime changes should stay centered in `simulation_manager`, `simulation_runner`, and consumer orchestration modules
- project-level assets should remain explicit, persisted, and lineage-aware

## 8. Acceptance Standard for Phase 5 Completion

Phase 5 should be considered complete only when:

- validation status is visible and testable across report and comparison flows
- `packaging_test` can consume real visual assets in a repeatable way
- prepare/runtime throughput measurably improves under larger workloads
- recurring research assets are reusable across projects with explicit lineage
- default modes and previously completed Phase 1-4 workflows remain backward compatible

## 9. Delivery Strategy

Phase 5 should be executed as four sequential but independently shippable subprojects.

For each subproject, the delivery pattern should remain:

1. spec refinement
2. implementation plan
3. Claude Code execution in batches
4. Codex-led acceptance and regression verification
5. docs and handoff sync

This keeps the roadmap realistic and compatible with the existing "Codex plans and accepts, Claude Code implements" workflow.
