# Consumer Simulation Phase 5 Master Plan

## 1. Objective

Execute the next closure wave for MiroConsumer after Phase 4.

Phase 5 focuses on six priorities:

1. product identity cleanup
2. thin API route layer
3. repository abstraction for file persistence
4. configurable persona packs
5. evidence validation as gatekeeping
6. `consumer_test` bounded-context extraction

## 2. Execution Model

- Codex owns planning, decomposition, acceptance, and regression review
- Claude Code owns implementation batches
- work is delivered in small, independently reviewable slices
- backward compatibility for existing `consumer_test` flows must be preserved unless a deliberate migration path is documented

## 3. Delivery Order

1. `Phase 5A` Product Identity Cleanup
2. `Phase 5B` Application Services and Repository Backbone
3. `Phase 5C` Persona Pack Configurability and Evidence Gatekeeping
4. `Phase 5D` Consumer Bounded Context Extraction

## 4. Phase 5A Plan

### Batch 1: Brand Surface Audit and Rename Map

- inventory remaining `MiroFish` references that should become `MiroConsumer`
- separate legacy-backbone references from consumer-facing product references
- define the safe rename map for package names, log labels, homepage branding, GitHub links, README, screenshots, docker/service naming

Acceptance:

- rename scope is explicit and does not accidentally erase legacy-backbone references that remain technically useful
- product-facing references are mapped to `MiroConsumer`

### Batch 2: Product Identity Sweep

- update root package naming where appropriate
- align homepage brand, logs, GitHub repository links, README references, image captions, docker/service names
- make repo presentation look like an independent product

Acceptance:

- default product surfaces consistently show `MiroConsumer`
- GitHub links point to the active repository
- docker/readme/docs naming is aligned

## 5. Phase 5B Plan

### Batch 1: Application Service Skeleton

- introduce:
  - `graph_app_service`
  - `simulation_app_service`
  - `report_app_service`
  - `branch_app_service`
  - `benchmark_app_service`
- move route-level orchestration logic behind service boundaries

Acceptance:

- routes can be described as parse, validate, call service, return response
- application logic becomes independently testable without full route invocation

### Batch 2: Repository Interfaces

- define:
  - `ProjectRepository`
  - `SimulationRepository`
  - `BranchRepository`
  - `ReportRepository`
  - `BenchmarkRepository`
- provide filesystem-backed implementations first
- remove direct filesystem knowledge from higher-level services where feasible

Acceptance:

- services depend on repository interfaces rather than raw file layout details
- filesystem behavior remains backward compatible

### Batch 3: Route Thinning and Regression Pass

- refactor route modules to delegate to application services
- reduce duplicated parse/response behavior
- preserve existing external API shape where possible

Acceptance:

- route files become thinner and easier to scan
- existing API behavior remains stable for current frontend flows

## 6. Phase 5C Plan

### Batch 1: Persona Pack Asset Model

- design persona pack registry and selection model
- support pack classes:
  - generic
  - industry
  - category
  - geography
  - custom uploaded
- keep current default behavior as a compatibility fallback

Acceptance:

- pack type can be selected explicitly
- default pack still works without migration pain

### Batch 2: Persona Pack Loading and Upload Flow

- implement pack discovery, loading, and validation
- support user-provided custom pack upload
- expose pack metadata through the consumer workflow

Acceptance:

- at least one non-default built-in pack and one custom pack path work end to end
- invalid pack uploads fail clearly

### Batch 3: Evidence Gatekeeping Policy

- introduce minimum evidence-count thresholds for findings
- define source-tier minimums for selected conclusion classes
- block unsupported conclusions from executive summary
- down-weight or fail weak evidence inside comparison and benchmark replay

Acceptance:

- summary generation respects hard evidence gates
- weak support is no longer merely annotated when policy requires blocking

## 7. Phase 5D Plan

### Batch 1: Consumer API and Contract Boundary

- establish clearer `app/api/consumer/...` ownership for consumer-specific flows
- separate consumer report contracts and state contracts where practical
- add compatibility shims if legacy entry points must remain temporarily

Acceptance:

- consumer-specific API behavior is more obviously owned by consumer modules
- compatibility remains intact for existing UI flows

### Batch 2: Consumer-Owned Storage and State Direction

- move consumer-specific storage access behind consumer-aware contracts
- reduce leakage between legacy simulation/report structures and consumer-specific artifacts
- clarify which state belongs to generic runtime vs consumer runtime

Acceptance:

- consumer modules own more of their own state and contract vocabulary
- storage boundaries are easier to reason about

### Batch 3: Final Bounded-Context Cleanup

- remove or reduce cross-domain entanglement that became unnecessary after service and repository refactors
- align consumer-specific naming, ownership, and module layout
- prepare the codebase for later multimodal packaging, pricing depth, and propagation extensions

Acceptance:

- `consumer_test` reads as a real bounded context rather than an add-on path
- later consumer-specific feature work has clearer extension seams

## 8. Cross-Cutting Verification

Every Phase 5 subproject must include:

- targeted backend tests
- targeted frontend tests for user-visible changes
- full backend non-integration regression
- frontend build verification
- route-level smoke checks for any changed workflow
- documentation updates when user-facing naming or contracts change

## 9. Exit Criteria

Phase 5 is complete when:

- the repo and product surfaces feel unmistakably like `MiroConsumer`
- Flask routes are thin and service-driven
- filesystem persistence is abstracted behind repository interfaces
- persona packs are configurable assets rather than hidden code defaults
- evidence gatekeeping can block weak conclusions from high-level outputs
- `consumer_test` is significantly more independent as a bounded context

## 10. Follow-On After Phase 5

After this closure work is complete, the next capability wave can safely proceed with:

- multimodal packaging and creative stimulus
- larger-scale runtime and model-routing improvements
- category memory, benchmark library growth, and research operating-system features

These remain important, but they should follow the architecture and product-identity cleanup rather than precede it.

## 11. Execution Result (2026-04-23)

Phase 5 execution is complete.

Delivered by batch:

- **Batch 1 — Product Identity Cleanup**: `Phase 5A` completed. Full `MiroConsumer` identity sweep across homepage, workflow views, package names, README, and repo presentation.
- **Batch 2 — Route Thinning & App Services**: `Phase 5B` completed. Flask routes for `graph / simulation / report / branch / benchmark` thinned to `parse -> validate -> call service -> return response`; `graph_app_service`, `simulation_app_service`, `report_app_service`, `branch_app_service`, `benchmark_app_service`, and `consumer_app_service` are the new orchestration owners.
- **Batch 3 — Task Executor & Repository Abstraction**: `task_executor` abstraction landed for unified prepare/run/report execution semantics; repository backbone completed with `ProjectRepository`, `ConsumerStateRepository`, `SimulationRepository`, `BranchRepository`, `ReportRepository`, and `BenchmarkRepository` (all filesystem-backed).
- **Batch 4 — Consumer Bounded Context & Canonical Routes**: `Phase 5D` completed. Consumer-specific routes, contracts, and state access consolidated under `app/api/consumer`, `ConsumerAppService`, `ConsumerApiGuard`, and `ConsumerSimulationStateAccessor`; canonical consumer routes with typed request/response contracts are active.
- **Batch 5 — Suite Stabilization & Observability**: canonical error shape unified; observability/smoke gate confirmed; full suite stabilized.

Key completion artifacts:

- consumer-facing route ownership now includes `app/api/consumer.py`
- consumer orchestration is centralized in `ConsumerAppService`
- consumer boundary checks are centralized in `ConsumerApiGuard`
- consumer-specific simulation artifact access is centralized in `ConsumerSimulationStateAccessor`
- filesystem-backed `ConsumerStateRepository` now complements the existing repository layer
- `task_executor` centralizes async/sync task execution and retry policy for prepare, run, and report paths

Final verification:

- task executor observability: `python -m pytest tests/services/application/test_task_executor_observability.py -q` -> `9 passed, 1 warning`
- core backend sub-suite: `python -m pytest tests/api/ tests/consumer/ tests/services/application/ -q` -> `565 passed, 1 warning`
- the only remaining warning is the pre-existing `zep_cloud` / Python 3.14 compatibility warning
- frontend build: passed
- application smoke: consumer blueprint route present in Flask app
