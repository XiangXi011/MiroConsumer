# Consumer Simulation Phase 6A Product Surface Design

## 1. Objective

Phase 6A removes `project_type=default` from all product-facing MiroConsumer surfaces while preserving `default` as an internal compatibility mode for old callers and stored artifacts.

After Phase 6A:

- MiroConsumer is the only visible product.
- New users only see the consumer testing flow.
- Shared lifecycle, runtime, repository, and task execution capabilities remain as shared engine infrastructure.
- Consumer-specific orchestration enters through consumer-owned modules and routes.
- `default` remains supported only for compatibility callers and persisted legacy artifacts.
- No new product-owned create may persist `project_type=default`.

## 2. Scope

Phase 6A covers four things:

1. Product surfaces become consumer-only.
2. Product-facing documentation describes only the consumer workflow.
3. Consumer-owned routes and modules become the canonical entry points for consumer-specific behavior.
4. The `project_type` contract is made explicit so new product flows stop creating visible `default` projects while old callers and persisted artifacts keep working.

This phase is complete when product surfaces, docs, route ownership, and compatibility behavior all match the same contract.

## 3. Non-Goals

Phase 6A does not:

- delete `project_type=default` from the backend data model
- backfill or rewrite existing stored `default` projects, simulations, reports, or manifests
- remove legacy routes that old callers still use
- collapse shared engine infrastructure into consumer-only services
- require a full package or directory reorganization in one change
- change the runtime semantics of old compatibility callers unless required to keep them working

## 4. Design Constraints and Invariants

The following rules are normative for this phase:

1. `default` is not a product mode. It is an internal compatibility mode.
2. Product surfaces must not ask a user to choose between `default` and `consumer_test`.
3. New user-facing flows must assume consumer testing semantics by default.
4. Shared engine code remains shared if it owns lifecycle, repository, artifact, or task execution responsibilities.
5. New consumer-specific business logic must enter through consumer-owned modules and routes.
6. Compatibility behavior may delegate across layers, but it may not become the canonical implementation path for new work.
7. Existing stored artifacts keep their persisted `project_type` values unless a later phase introduces an explicit migration.
8. Any new product-owned project, simulation, or report artifact created through shared lifecycle routes must persist `project_type=consumer_test` before first write.

## 5. Product Docs vs Maintainer Docs

Phase 6A requires a hard distinction between product-facing materials and maintainer-facing materials.

### 5.1 Product-Facing Docs

These documents describe what users can do in MiroConsumer. They must present only the consumer testing product.

Included:

- homepage copy and UI labels
- onboarding and creation flow copy
- all of `README.md`
- all of `README-ZH.md`
- product overview, goals, user journey, UX, feature, and quickstart sections of `PRD.md`
- any future product overview or quickstart pages

Rules:

- `README.md` must not mention `default` or `project_type=default`
- `README-ZH.md` must not mention `default` or `project_type=default`
- product-facing sections of `PRD.md` must not mention `default` or `project_type=default`
- do not describe a generic simulation product beside MiroConsumer
- do describe the consumer flow as the canonical path

### 5.2 Maintainer and Handoff Docs

These documents explain architecture, migration, compatibility, and ownership boundaries to developers.

Included:

- `docs/superpowers/specs/*`
- `docs/superpowers/plans/*`
- explicitly labeled maintainer-only, implementation, migration, or compatibility sections of `PRD.md`
- migration notes and handoff notes
- code comments around compatibility seams

Rules:

- if `PRD.md` mentions `default`, the mention must live only in an explicitly labeled maintainer-only, implementation, migration, or compatibility section
- maintainer docs may describe `default` only as an internal compatibility mode
- must distinguish product surface, shared engine, consumer runtime, and compatibility layer
- must document route delegation and artifact preservation rules precisely

## 6. Execution Shape

Phase 6A lands in four batches. Each batch must leave the product deployable and keep old compatibility paths operational.

### 6.1 Batch 1: Consumer-Only Product Surface

Goal:

- remove visible `default` affordances from product surfaces

Work:

- remove product wording that implies two visible modes
- make the consumer testing flow the only visible creation flow
- remove UI copy that suggests generic prediction, generic simulation, or `default` mode selection

Exit criteria:

- no product surface renders a `default` mode selector
- a new user can only start the consumer testing flow
- product copy refers to MiroConsumer as a single product

### 6.2 Batch 2: Product Docs and Contract Alignment

Goal:

- align product docs and creation semantics with the consumer-only surface

Work:

- update product-facing docs to describe only the consumer workflow
- document the `project_type` migration contract in maintainer docs
- ensure new UI-owned creation paths no longer rely on omitted `project_type` meaning "legacy product mode"

Exit criteria:

- product-facing docs no longer present `default` as a user-visible mode
- maintainer docs define omitted, explicit `default`, and explicit `consumer_test` behavior
- new product creation paths are specified as consumer-first

### 6.3 Batch 3: Canonical Consumer Ownership

Goal:

- make consumer-owned routes and modules the canonical path for consumer-specific behavior

Work:

- designate consumer routes as canonical for summaries, branches, interventions, comparisons, and research assets
- keep shared lifecycle routes canonical where they own lifecycle state
- downgrade legacy consumer behavior under shared routes to compatibility shims

Exit criteria:

- route ownership is documented and implemented consistently
- new consumer feature work is expected to attach to consumer-owned modules first
- compatibility shims delegate instead of hosting new business logic

### 6.4 Batch 4: Compatibility Hardening

Goal:

- keep old callers and artifacts working while `default` is no longer product-visible

Work:

- preserve explicit `project_type=default` behavior for old callers
- preserve read and execution support for existing stored `default` artifacts
- add or retain compatibility tests for legacy routes and stored data

Exit criteria:

- explicit `default` still works for compatibility callers
- existing stored `default` artifacts still load without backfill
- compatibility behavior is tested
- non-route legacy artifact compatibility is implemented in shared engine services and repositories, not only in route shims

## 7. Target Ownership Model

Phase 6A formalizes four layers.

### 7.1 Product Surface

Owns:

- homepage and user-visible navigation
- creation flow wording and user choice architecture
- product-facing docs
- the visible "what product is this?" story

Must not own:

- compatibility branching
- backend lifecycle orchestration
- consumer business logic implementation

### 7.2 Shared Engine

Owns:

- project, graph, simulation, and report lifecycle mechanics
- repository-backed persistence
- artifact storage and retrieval
- legacy artifact loading, replay, and round-trip preservation for persisted `default` and `consumer_test` artifacts
- task executor and background job plumbing
- shared application-service coordination that is not consumer-specific

Must not own:

- consumer-specific brief semantics
- persona pack semantics
- consumer branch or intervention meaning
- product-facing mode selection

### 7.3 Consumer Runtime

Owns:

- consumer brief normalization
- consumer graph semantics
- persona pack selection and loading
- branch, intervention, comparison, replay, and research-asset behavior with consumer meaning
- consumer-specific report context and explanation logic

Must not own:

- generic repository plumbing
- generic lifecycle persistence
- generic task runner mechanics

### 7.4 Compatibility Layer

Owns:

- old route preservation
- request translation from legacy shapes into canonical service calls
- response-shape preservation where old callers depend on it

Must not own:

- new feature logic
- long-term canonical routing
- core business rules
- persisted artifact load, replay, or round-trip compatibility logic

### 7.5 Non-Route Compatibility Ownership

Legacy artifact loading, simulation replay, report generation, and round-trip preservation are shared engine responsibilities because they operate on persisted state and repositories rather than on public route shapes.

Route-level compatibility shims only translate legacy requests and responses into shared engine or consumer runtime service calls. Phase 6A is not complete if legacy artifacts work only when loaded through a shim route.

## 8. Responsibility Matrix

| Layer | Primary responsibilities | Forbidden responsibilities | Typical implementation targets |
| --- | --- | --- | --- |
| Product surface | UI entry points, visible workflow copy, product docs, default new-user path | compatibility behavior, legacy mode selection, business orchestration | homepage, onboarding, locale strings, README/product docs |
| Shared engine | graph/project/simulation/report lifecycle, repositories, artifact IO, task execution, shared app services, persisted artifact compatibility for load/replay/round-trip | consumer semantics, persona logic, branch meaning, product positioning | shared API lifecycle handlers, shared app services, repositories, task executor |
| Consumer runtime | consumer orchestration, summaries, branches, interventions, comparisons, research assets, consumer report context | generic persistence, generic task execution, user-visible compatibility messaging | consumer API, consumer app services, consumer domain modules |
| Compatibility layer | legacy route shims, old request/response translation, compatibility logging | new orchestration, canonical routing, new feature ownership, persisted artifact compatibility ownership | legacy endpoints under shared route families |

Dependency rules:

- consumer runtime may depend on shared engine services and repositories
- shared engine must not depend on consumer-specific modules for core lifecycle behavior
- compatibility shims may depend on both shared engine and consumer runtime, but only for delegation
- shared engine must preserve persisted artifact compatibility even when no legacy route shim is involved
- new consumer-specific behavior must enter through consumer-owned modules even if a compatibility shim also exposes it

## 9. `project_type` Migration Contract

Phase 6A changes product behavior without deleting compatibility behavior. The contract below is normative.

### 9.1 Contract Table

| Case | Required Phase 6A behavior |
| --- | --- |
| Omitted `project_type` in new product-facing flows | allowed only if the backend deterministically persists `consumer_test` before first write; the user never sees a mode decision |
| Explicit `project_type=default` from new product-facing flows | forbidden; product surface, docs, and product-owned callers must not generate or recommend this value |
| Explicit `project_type=consumer_test` from new product-facing flows | allowed; newly created project, simulation, and report artifacts from that flow must persist `consumer_test` |
| Omitted `project_type` from old callers | preserve current compatibility behavior unless and until those callers are explicitly migrated |
| Explicit `project_type=default` from old callers | preserve compatibility behavior |
| Explicit `project_type=consumer_test` from old callers | preserve current consumer behavior |
| Existing stored artifacts with `project_type=default` | keep stored value unchanged and continue to load and run them |
| Existing stored artifacts with `project_type=consumer_test` | keep stored value unchanged and continue to load and run them |

### 9.2 Required Interpretation Rules

1. Phase 6A does not rewrite persisted artifacts in place.
2. Product-facing omission and backend omission are not the same thing.
   Product-facing omission means "the product only offers consumer testing."
   Backend omission from old callers still follows the compatibility path until those callers are migrated.
3. Any new product-owned create that uses `/api/graph/ontology/generate`, `/api/graph/build`, `/api/simulation/create`, `/api/report/generate`, or another shared lifecycle create route must persist `project_type=consumer_test` on every newly created project, simulation state or manifest, and report artifact created by that flow.
4. For shared lifecycle routes, only two behaviors are acceptable for a new product-owned create:
   - the caller sends `project_type=consumer_test` before the first persisted write
   - the backend injects `project_type=consumer_test` from product-owned context before the first persisted write
5. For a new product-owned create, allowing omitted `project_type` to fall through to persisted `default` is a Phase 6A failure.
6. If `/api/simulation/create` derives a simulation from an existing project, the simulation must persist the source project's `project_type`. For a Phase 6A product-owned project, that source value must already be `consumer_test`.
7. Explicit `default` remains valid only for compatibility callers and stored artifacts.
8. Explicit `consumer_test` remains the canonical explicit project type for consumer behavior where a shared backend contract still requires a value.
9. New product work must not introduce fresh product-level branching on `default` versus `consumer_test`.
10. Existing artifacts must round-trip with their original `project_type` intact through load, run, report generation, export, and re-read.

### 9.3 Backend Persistence Consequence

Phase 6A does not require changing omission semantics for every old caller in one step. It does require the following persisted outcomes:

- a new product-owned create never writes `default` into a newly created project, simulation, or report artifact
- a legacy caller may continue writing `default` when it intentionally or implicitly enters the compatibility path
- reloading any persisted artifact returns the same `project_type` value that was originally written

## 10. Canonical Route Table

Phase 6A separates shared lifecycle routes, canonical consumer routes, and legacy compatibility shims.

### 10.1 Canonical Consumer Path

Phase 6A defines one canonical consumer path from product entry to consumer-specific interaction. Shared lifecycle routes remain canonical where they own shared state transitions; consumer routes remain canonical where they own consumer meaning.

| Stage | Canonical route(s) | Owning layer | Required Phase 6A behavior |
| --- | --- | --- | --- |
| Consumer brief intake and project creation | `/api/graph/ontology/generate`, `/api/graph/project/<project_id>` | product surface + shared engine | new product-owned project creation persists `project_type=consumer_test`; `consumer_brief` is stored as consumer data, not as a `default` product fallback |
| Consumer graph build | `/api/graph/build`, `/api/graph/task/<task_id>`, `/api/graph/project/<project_id>` | shared engine | graph build reads the persisted consumer project and must not create or rewrite the project as `default` |
| Simulation lifecycle | `/api/simulation/create`, `/api/simulation/prepare`, `/api/simulation/prepare/status`, `/api/simulation/start`, `/api/simulation/stop`, `/api/simulation/<simulation_id>` | shared engine | simulations created from new product-owned projects persist `project_type=consumer_test`; lifecycle routes remain canonical because they own shared run state |
| Report lifecycle | `/api/report/generate`, `/api/report/generate/status`, `/api/report/<report_id>`, `/api/report/by-simulation/<simulation_id>` | shared engine | reports generated from new product-owned simulations preserve `project_type=consumer_test`; report lifecycle remains canonical because it owns shared report state |
| Consumer-specific interaction and iteration | `/api/consumer/simulation/<simulation_id>/consumer-summary`, `/api/consumer/simulations/<simulation_id>/branches`, `/api/consumer/simulations/<simulation_id>/interventions`, `/api/consumer/simulations/<simulation_id>/branches/<branch_id>/interventions`, `/api/consumer/simulations/<simulation_id>/branches/<branch_id>/comparison`, `/api/consumer/simulations/<simulation_id>/branches/<branch_id>/resume`, `/api/consumer/simulations/<simulation_id>/branches/<branch_id>/status`, `/api/consumer/comparisons`, `/api/consumer/comparisons/<comparison_id>`, `/api/consumer/research-assets/export`, `/api/consumer/research-assets`, `/api/consumer/research-assets/<asset_id>` | consumer runtime | all consumer-specific post-run behavior uses `/api/consumer/*` as the canonical route family |
| Report interaction | `/api/report/chat` | shared engine | report chat remains canonical under report routes because it operates on report state rather than consumer branch semantics |

Rule:

- the canonical consumer path uses shared lifecycle routes for shared lifecycle state and `/api/consumer/*` routes for consumer-specific meaning; Phase 6A must document and implement both halves of that path together

### 10.2 Shared Lifecycle Routes That Remain Canonical

These stay canonical because they own lifecycle state rather than consumer-specific meaning.

| Route family | Canonical routes | Why they stay canonical |
| --- | --- | --- |
| Graph lifecycle | `/api/graph/build`, `/api/graph/task/<task_id>`, `/api/graph/project/<project_id>` | graph and project lifecycle remain shared engine responsibilities |
| Simulation lifecycle | `/api/simulation/create`, `/api/simulation/prepare`, `/api/simulation/prepare/status`, `/api/simulation/start`, `/api/simulation/stop`, `/api/simulation/<simulation_id>` | simulation state creation and execution remain shared engine responsibilities |
| Report lifecycle | `/api/report/generate`, `/api/report/generate/status`, `/api/report/<report_id>`, `/api/report/by-simulation/<simulation_id>` | report generation lifecycle remains shared engine responsibility |

Rule:

- these routes may continue to accept both compatibility and consumer-backed state, but they must not be described as separate products

### 10.3 Canonical Consumer Routes

These are the canonical paths for consumer-specific behavior and future product work.

| Capability | Canonical route |
| --- | --- |
| Consumer summary | `/api/consumer/simulation/<simulation_id>/consumer-summary` |
| Branch creation and listing | `/api/consumer/simulations/<simulation_id>/branches` |
| Intervention listing | `/api/consumer/simulations/<simulation_id>/interventions` |
| Branch interventions | `/api/consumer/simulations/<simulation_id>/branches/<branch_id>/interventions` |
| Branch comparison | `/api/consumer/simulations/<simulation_id>/branches/<branch_id>/comparison` |
| Branch resume | `/api/consumer/simulations/<simulation_id>/branches/<branch_id>/resume` |
| Branch run status | `/api/consumer/simulations/<simulation_id>/branches/<branch_id>/status` |
| Comparisons | `/api/consumer/comparisons`, `/api/consumer/comparisons/<comparison_id>` |
| Research asset export and retrieval | `/api/consumer/research-assets/export`, `/api/consumer/research-assets`, `/api/consumer/research-assets/<asset_id>` |

Rule:

- new consumer-specific features must be added under consumer-owned route families unless the feature only creates, starts, stops, or fetches shared lifecycle state and contains no consumer-specific branching

### 10.4 Legacy Compatibility Shims

These remain supported in Phase 6A but are not canonical for new work.

| Legacy route | Canonical target |
| --- | --- |
| `/api/simulation/<simulation_id>/consumer-summary` | consumer summary route/service |
| `/api/simulation/<simulation_id>/branches` | consumer branch route/service |
| `/api/simulation/<simulation_id>/interventions` | consumer intervention route/service |
| `/api/simulation/<simulation_id>/branches/<branch_id>/interventions` | consumer intervention route/service |
| `/api/simulation/<simulation_id>/branches/<branch_id>/comparison` | consumer comparison route/service |
| `/api/simulation/<simulation_id>/branches/<branch_id>/resume` | consumer branch resume route/service |
| `/api/simulation/<simulation_id>/branches/<branch_id>/status` | consumer branch status route/service |
| `/api/report/research-assets/export` | consumer research asset route/service |
| `/api/report/research-assets` | consumer research asset route/service |
| `/api/report/research-assets/<asset_id>` | consumer research asset route/service |
| `/api/report/compare` | consumer comparison route/service |
| `/api/report/comparisons` | consumer comparison route/service |
| `/api/report/comparisons/<comparison_id>` | consumer comparison route/service |

Rules:

- legacy routes must preserve compatibility behavior for old callers
- legacy routes must delegate instead of hosting new business logic
- compatibility logging is optional and does not affect Phase 6A acceptance

## 11. Migration Strategy

Phase 6A uses a hide, canonize, preserve strategy.

### 11.1 Hide

- remove `default` from product surfaces and product docs
- stop presenting mode choice as part of the MiroConsumer product story

### 11.2 Canonize

- route new product work through consumer-owned flows
- document shared lifecycle routes as engine infrastructure, not alternate products
- document consumer routes as the canonical home for consumer behavior

### 11.3 Preserve

- preserve explicit `default` handling for old callers
- preserve old route shapes where they are already in use
- preserve stored artifacts without backfill

## 12. Risks and Mitigations

### 12.1 Risk: Product Copy Changes Without Behavioral Change

If only the UI copy changes, the codebase will continue to drift around a hidden two-product model.

Mitigation:

- require route canon and ownership updates, not just copy edits
- require the `project_type` contract to be documented and tested

### 12.2 Risk: Shared Engine Responsibilities Get Mistaken for `default` Product Logic

Some current `default`-associated code is actually neutral engine infrastructure.

Mitigation:

- classify by responsibility, not by historical label
- keep lifecycle, repository, artifact, and executor capabilities shared unless the capability depends on consumer brief semantics, persona semantics, or branch/intervention/comparison behavior

### 12.3 Risk: Old Callers Break When Product Semantics Change

Legacy callers are allowed to omit `project_type` or explicitly send `default`.

Mitigation:

- preserve old caller behavior behind compatibility contracts
- keep legacy route shims in place during Phase 6A
- add regression coverage for omitted and explicit legacy inputs

### 12.4 Risk: Existing Stored Artifacts Become Unreadable

Persisted projects and simulations already contain both `default` and `consumer_test`.

Mitigation:

- do not rewrite stored artifacts in this phase
- keep load, replay, and report-generation paths compatible with both persisted values

## 13. Objective Verification and Acceptance Criteria

Phase 6A is accepted only if every item below is true.

### 13.1 Product Surface Acceptance

- homepage and creation flow show only the consumer testing path
- no visible product surface offers `default` as a selectable mode
- product-facing copy describes MiroConsumer as a single consumer-testing product

### 13.2 Documentation Acceptance

- `README.md` contains zero mentions of `default` or `project_type=default`
- `README-ZH.md` contains zero mentions of `default` or `project_type=default`
- any mention of `default` in `PRD.md` appears only in an explicitly labeled maintainer-only, implementation, migration, or compatibility section
- maintainer and handoff docs explicitly document the compatibility role of `default`
- product docs and maintainer docs do not contradict each other on route ownership or `project_type` behavior

### 13.3 Route Ownership Acceptance

- the spec defines the end-to-end canonical consumer path across brief intake, graph build, simulation lifecycle, report lifecycle, consumer-specific interaction, and report chat
- shared lifecycle routes remain canonical only for lifecycle concerns
- consumer-specific capabilities are documented and implemented under `/api/consumer/*`
- legacy shared-route consumer endpoints remain functional as shims and delegate to the same canonical services used by `/api/consumer/*`

### 13.4 `project_type` Contract Acceptance

- new product-facing flows do not expose or recommend `project_type=default`
- any new product-owned create using `/api/graph/ontology/generate`, `/api/graph/build`, `/api/simulation/create`, `/api/report/generate`, or another shared lifecycle create route persists `project_type=consumer_test` before the first artifact write
- no new product-owned project, simulation, or report artifact is persisted with `project_type=default`
- explicit `project_type=consumer_test` remains supported for canonical consumer behavior
- old callers that omit `project_type` still follow the compatibility path unless explicitly migrated
- old callers that send `project_type=default` still work
- existing stored artifacts with either value still load, run, generate reports, export, and round-trip without backfill

### 13.5 Test and Review Acceptance

- tests cover canonical consumer routes and legacy compatibility shims
- tests cover omitted `project_type`, explicit `default`, explicit `consumer_test`, and persisted legacy artifacts
- tests cover the shared-route persistence contract for new product-owned creates
- tests cover legacy artifact load and round-trip behavior without going through a legacy route shim
- code review confirms no new product-facing branching reintroduces `default` as a visible mode

## 14. Completion Standard

Phase 6A is complete when MiroConsumer is visibly consumer-only, consumer-owned routes and modules are canonical for consumer behavior, shared engine infrastructure remains shared, and `default` survives only as an internal compatibility contract for old callers and stored artifacts.
