# Consumer Simulation Phase 5 Roadmap Design

## 1. Background

By the end of Phase 4, MiroConsumer already has a strong consumer testing workflow:

- unified `consumer_test` flow across concept, copy, packaging, A/B, and price testing
- project-level research workspace, branch rerun, comparison, and research asset export
- credibility, evidence validation, benchmark replay, efficiency upgrades, and broader test coverage

However, the next bottleneck is no longer feature coverage. It is product clarity and backend structure.

The main remaining issues are:

- the product identity is still partially mixed with legacy `MiroFish` naming
- Flask route modules are becoming too thick and hold too much application logic
- filesystem persistence is still coupled directly to services instead of going through repository interfaces
- persona packs are still too hard-coded for a platform that claims research realism
- evidence validation is still mostly advisory scoring instead of acting as a hard gate
- the `consumer_test` line is only partially isolated and still lives too close to legacy flow internals

Phase 5 exists to close that gap.

## 2. Phase 5 Goal

Phase 5 turns MiroConsumer from a successful feature-evolved fork into a cleaner, more independent, and more maintainable product platform.

The priority is to finish the product and architecture closure before opening the next capability wave.

In practical terms, Phase 5 should make the system better at answering:

- "Is this clearly MiroConsumer rather than a renamed MiroFish branch?"
- "Can we keep adding consumer features without Flask routes turning into a monolith?"
- "Can we replace file persistence later without rewriting the whole application?"
- "Can persona realism and evidence governance be controlled like product assets rather than hidden code defaults?"
- "Is `consumer_test` now a real bounded context rather than a feature branch living inside a general backend?"

## 3. Non-Goals

Phase 5 is not intended to:

- introduce DingTalk or external live focus-group workflows
- migrate the whole system to a database immediately
- turn `price_test` into a sales forecasting engine
- replace all existing MiroFish core runtime modules in one step
- start multimodal packaging, larger-scale runtime tuning, or research operating-system work before the platform foundation is cleaned up

## 4. Roadmap Principles

- Product identity comes before new surface area
- Routes should orchestrate, not own business logic
- Persistence should be abstracted before storage is upgraded
- Domain assets should be configurable rather than hard-coded
- Evidence governance should block unsupported conclusions, not merely annotate them
- `consumer_test` should continue moving toward an explicit bounded context with its own contracts

## 5. Priority Stack

### 5.1 Priority 1: Product Identity Cleanup

This is the fastest and highest-perception change.

Scope:

- replace remaining global `MiroFish` identity with `MiroConsumer` where the consumer product is the primary surface
- align root package naming, log labels, homepage brand, GitHub links, README references, screenshot captions, and docker/service naming
- make the repository feel like an independent product rather than a fork narrative

Expected impact:

- immediate improvement in product perception
- clearer repo identity for developers, reviewers, and stakeholders
- less confusion between legacy backbone and consumer-facing product layer

### 5.2 Priority 2: Thin API Route Layer

Flask route modules should be reduced to:

1. parse
2. validate
3. call application service
4. return response

The recommended application services are:

- `graph_app_service`
- `simulation_app_service`
- `report_app_service`
- `branch_app_service`
- `benchmark_app_service`

Expected impact:

- route modules stop accumulating feature logic
- new consumer features can be added without turning API files into monoliths
- orchestration and business rules become easier to test independently

### 5.3 Priority 3: Repository Abstraction for File Persistence

The system does not need to jump to SQLite or Postgres immediately, but it should stop letting file persistence leak everywhere.

Required repository interfaces:

- `ProjectRepository`
- `SimulationRepository`
- `BranchRepository`
- `ReportRepository`
- `BenchmarkRepository`

Initial implementation should stay filesystem-backed.

Expected impact:

- future storage upgrades become feasible
- state management becomes easier to reason about
- services depend on abstractions rather than file layout details

### 5.4 Priority 4: Configurable Persona Packs

Persona realism should become a configurable asset system rather than a hard-coded default set.

Required pack classes:

- generic pack
- industry pack
- category pack
- geography pack
- custom uploaded pack

Expected impact:

- stronger research realism and controllability
- clearer separation between core engine and scenario assets
- better fit for different business domains and markets

### 5.5 Priority 5: Evidence Validation as Gatekeeping

Evidence governance should move from scoring-only behavior to explicit release gates.

Required gates include:

- minimum evidence-count threshold for findings
- minimum source-tier requirement for certain claims
- unsupported conclusions blocked from executive summary
- weak evidence down-weighted or failed in comparison and benchmark replay

Expected impact:

- fewer report conclusions that look polished but are weakly supported
- more trustworthy summary and benchmark outputs
- stronger consistency between evidence policy and business confidence

### 5.6 Priority 6: `consumer_test` as Bounded Context

The consumer domain is already partially isolated, but Phase 5 should make that separation explicit.

Target direction:

- `app/services/consumer/...`
- `app/api/consumer/...`
- consumer-owned state, storage contracts, and report contracts

Expected impact:

- future packaging, A/B, pricing, and propagation work becomes easier to extend
- legacy and consumer flows stop interfering conceptually
- the codebase becomes clearer for both planning and implementation

## 6. Recommended Execution Order

Recommended order:

1. `Phase 5A: Product Identity Cleanup`
2. `Phase 5B: Application Services and Repository Backbone`
3. `Phase 5C: Persona Packs and Evidence Gates`
4. `Phase 5D: Consumer Bounded Context Extraction`

Rationale:

- identity cleanup is fast, visible, and strategically clarifying
- route/service/repository cleanup is the core maintainability move
- configurable assets and evidence gates become much cleaner once the service boundaries are improved
- bounded context extraction is easier and safer after route and persistence seams exist

## 7. Architecture Direction

Phase 5 should push the codebase toward these boundaries:

- Flask routes become thin orchestration shells
- application services hold request-to-domain orchestration
- repositories encapsulate filesystem persistence
- consumer domain assets are externalized and selectable
- executive reporting is governed by evidence gates
- consumer-specific API, storage, and report contracts progressively move under consumer-owned modules

## 8. Phase 5 Completion Standard

Phase 5 should be considered complete only when:

- the user-facing product identity is consistently `MiroConsumer`
- route modules are measurably thinner and delegate to application services
- repository interfaces exist and filesystem persistence is behind them
- persona pack selection is configurable across multiple pack types
- unsupported findings are blocked from summary-level outputs
- `consumer_test` has a clearer dedicated API and contract boundary without breaking backward compatibility

## 9. Follow-On After Phase 5

Once this closure work is complete, the next capability wave can safely continue with:

- multimodal packaging and creative stimulus
- larger-scale runtime and model-orchestration improvements
- category memory and research operating-system layers

Those remain important, but they should come after the product and architecture foundation is cleaned up.

## 10. Delivery Strategy

Phase 5 should still be executed in the existing workflow:

1. spec refinement
2. implementation plan
3. Claude Code batch execution
4. Codex-led acceptance and regression review
5. docs and handoff sync

This keeps the roadmap compatible with the current "Codex plans and accepts, Claude Code implements" execution model.

## 11. Completion Update (2026-04-23)

Phase 5 is now complete.

Delivered closure outcomes:

- product-facing identity now reads as `MiroConsumer` across the main repo and core workflow views
- route/application-service split is in place, with thinner route orchestration and clearer service ownership
- repository abstraction now includes `ProjectRepository`, `ConsumerStateRepository`, `SimulationRepository`, `BranchRepository`, `ReportRepository`, and `BenchmarkRepository`, all with filesystem-backed implementations
- persona packs are now configurable assets with built-in and custom-uploaded selection paths
- evidence governance now acts as a hard gate for high-level outputs rather than annotation-only scoring
- consumer-specific API/state ownership is clearer via `app/api/consumer`, `ConsumerAppService`, `ConsumerApiGuard`, and `ConsumerSimulationStateAccessor`

Verification evidence:

- targeted backend acceptance: `166 passed`
- full backend non-integration regression: `534 passed, 1 deselected`
- targeted frontend tests: `92 passed`
- frontend build: passed
- Flask app smoke: `/api/consumer/simulation/<simulation_id>/consumer-summary` successfully registered

With Phase 5 closed, the codebase is ready to move into the next capability wave rather than continue architecture catch-up.
