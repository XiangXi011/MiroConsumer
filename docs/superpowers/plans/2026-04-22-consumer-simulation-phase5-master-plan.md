# Consumer Simulation Phase 5 Master Plan

## 1. Objective

Execute the next upgrade wave for MiroConsumer after Phase 4, with emphasis on:

- stronger result trust and validation
- richer multimodal packaging and creative testing
- better runtime scalability and cost control
- deeper research memory and reusable operating assets

## 2. Execution Model

- Codex owns planning, task decomposition, review, and acceptance
- Claude Code owns implementation work
- Work is delivered subproject by subproject, with batch-level checkpoints
- Each subproject must preserve backward compatibility with existing `consumer_test` flows

## 3. Delivery Order

1. `Phase 5A` Trust and Validation Layer
2. `Phase 5B` Multimodal Packaging and Creative Stimulus
3. `Phase 5C` Scaled Runtime and Model Orchestration
4. `Phase 5D` Research Memory and Operating System

## 4. Phase 5A Plan

### Batch 1: Validation Model and Data Contracts

- define replay and backtest entities for historical validation
- standardize validation scores, replay confidence, and evidence coverage fields
- extend report and comparison contracts to include validation metadata

Acceptance:

- new validation fields are persisted and available through existing APIs
- default flows do not break when validation data is absent

### Batch 2: Historical Backtesting and Calibration

- support replay against stored benchmark or historical case artifacts
- compute alignment, drift, and confidence-adjustment signals
- surface calibration summaries in consumer summary and report context

Acceptance:

- at least one benchmark replay path produces structured calibration output
- report and comparison views can read calibration results

### Batch 3: Source Governance Upgrade

- strengthen provider-level scoring, freshness, and reliability tracking
- add source conflict and low-quality evidence flags
- improve traceability from confidence score back to source quality inputs

Acceptance:

- low-quality sources visibly affect confidence summaries
- evidence and source governance remain traceable in artifacts

## 5. Phase 5B Plan

### Batch 1: Visual Asset Ingest

- accept packaging images or simple creative visual assets
- persist assets in project research workspace with explicit lineage
- register multimodal source metadata

Acceptance:

- packaging assets are storable and retrievable in a project context
- non-visual projects remain unaffected

### Batch 2: Visual Descriptor Extraction

- derive structured descriptors from packaging and creative assets
- connect extracted descriptors into existing graph-building logic
- support visibility, provenance, and evidence references for visual findings

Acceptance:

- `packaging_test` can consume image-derived descriptors
- graph and report layers can reference visual-derived findings

### Batch 3: Multimodal Reporting and Comparison

- show how visual cues influenced perception, trust, and propagation
- support comparison between text-only and multimodal packaging variants
- expose representative visual evidence in report and interaction

Acceptance:

- packaging reports contain visual-specific interpretation sections
- A/B packaging comparison can include visual-driven differences

## 6. Phase 5C Plan

### Batch 1: Prepare-Time Performance

- improve profile generation concurrency
- add caching for repeated profile or artifact generation
- reduce redundant recomputation during repeated runs

Acceptance:

- prepare path shows measurable runtime improvement in repeated or larger runs
- failed retries do not corrupt existing artifacts

### Batch 2: Runtime Routing and Reuse

- add explicit routing between faster and deeper model paths
- optimize branch reruns with partial reuse
- reduce rerun cost when only limited inputs change

Acceptance:

- branch reruns complete with less redundant work
- model-routing decisions remain explicit and testable

### Batch 3: Stability and Recovery

- improve retry, timeout, and recovery behavior
- add clearer queue and execution-state visibility
- strengthen long-running task resilience

Acceptance:

- common runtime failures become resumable or more diagnosable
- status artifacts remain consistent after retries or partial failures

## 7. Phase 5D Plan

### Batch 1: Category Memory Foundation

- create category-level benchmark and recurring insight containers
- define explicit lineage from project findings into reusable category assets
- support opt-in project contribution to category memory

Acceptance:

- category memory artifacts can be generated without breaking existing project exports
- lineage from project to category asset is explicit

### Batch 2: Reusable Templates and Baselines

- support scenario presets, reusable prompt packs, and category baselines
- allow teams to start from prior category patterns instead of blank setup

Acceptance:

- at least one reusable category or scenario preset is supported end to end
- presets are distinguishable from project-specific findings

### Batch 3: Operating System Layer

- improve recurring comparison views and insight rollups
- support more operational research workflows across launches or campaigns
- make research assets easier to query, compare, and reuse over time

Acceptance:

- recurring project comparison becomes more structured than one-off comparison snapshots
- teams can reuse prior research assets in a controlled, lineage-aware way

## 8. Cross-Cutting Verification

Every Phase 5 subproject must include:

- targeted backend tests
- targeted frontend tests when UI changes are introduced
- full backend non-integration regression
- frontend build verification
- route-level smoke checks for any new user-visible workflow

## 9. Known Risks

- multimodal support may increase storage and provider variability
- stronger validation requires careful handling of incomplete historical data
- runtime optimization may introduce subtle cache or reuse bugs
- category memory can create hidden leakage if lineage and project boundaries are not explicit

## 10. Exit Criteria

Phase 5 is complete when:

- trust and validation are visibly stronger and evidence-backed
- packaging and creative testing accept richer multimodal inputs
- runtime performance and rerun efficiency are measurably improved
- research assets can accumulate into reusable category and team memory
- the existing Phase 1-4 feature set remains stable and backward compatible
