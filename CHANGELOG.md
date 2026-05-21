# Changelog

## [0.8.0] - 2026-05-21

### Comprehensive Review Fixes — Target Score 9.0+

Based on the 2026-05-21 comprehensive review (score 6.75 → target 9.0+), the following critical and high-priority issues were addressed:

#### Security (P0)
- **P0-4**: `.env.example` — Added explicit SECRET_KEY placeholder with security warning comments
- **P0-3**: `prompt_guard.py` — Added base64/Unicode normalization preprocessing layer to defeat encoding obfuscation attacks. Detects base64-encoded injections, Unicode confusables, and zero-width character bypasses
- **JWT revocation**: Added stub for token blacklist mechanism

#### Evidence & Confidence (P0/P1)
- **P0-2**: `evidence_validator.py` — Removed trace_aligned false strong atom injection that created circular validation loop
- **P1-7**: Semantic alignment weights changed from 70/30 (recall/precision) to 50/50 to reduce recall bias
- **9.5**: Blocking violations matching changed from prefix match to exact match

#### Convergence Detection (P0)
- **P0-6**: `convergence_detector.py` — Added dynamic threshold scaling for small samples (< 50 agents). Thresholds auto-adjust based on total_agent_count

#### ReasoningTrace — Filled (P0)
- **P0-1**: `orchestrator.py` — `build_round_snapshot()` now populates structured reasoning traces from perception/decision signals
- `reasoning_trace.py` — Added `is_complete()` audit method, `prompt_version` and `theoretical_framework` fields

#### Social Topology & Personas (P1)
- **P1-5**: `social_topology.py` — Added `reevaluate_roles_after_round()` for dynamic role reassessment based on engagement patterns
- **P1-6**: Role assignment now considers `category_involvement` dimension
- **6.1/6.2**: `persona_pack.py` — Added `category_involvement`, `brand_relationship`, `education_level` dimensions; `can_access_deep_graph()` upgraded from binary threshold to weighted scoring model (0.4×search + 0.4×cognition + 0.2×education, threshold ≥ 0.6)
- `default_personas.json` — All 16 personas updated with new dimension values

#### Event Engine (7.1/7.2)
- `event_engine.py` — Added theoretical grounding documentation (rumor psychology, social judgment theory, ELM, innovation diffusion)
- Continuous attitude value support (-1.0 to +1.0) with `_normalize_attitude()` helper

#### Report Quality (10.1/10.2)
- `report_context.py` — Added `_build_counterfactual_analysis()` with turning point identification and robustness scoring
- `scoring.py` — Keyword matching upgraded to `_semantic_match_stub()` with token overlap heuristic (backward compatible)

#### Frontend UX (P2-1/3.2)
- `Step2EnvSetup.vue` — Added error panel with retry and "degrade to manual" CTA buttons for prepare failures
- `Step3Simulation.vue` — Added summary/detailed view toggle to reduce information density

#### Test Coverage (P0-5)
- `.coveragerc` — Removed exemptions for 5 core business modules (simulation_runner, report_agent, graph_builder, simulation_ipc, simulation_config_generator)
- Added 113 new unit tests across 5 test files for previously exempted modules

#### Observability
- Enhanced `/metrics` endpoint with Prometheus-compatible format

#### Documentation
- `PRD.md` — Clarified Phase 4 (statistical significance) vs Phase 5 (causal inference + productization) boundaries

---

## [0.7.1] - 2026-05-11

### Added
- Password-backed auth registration/login with bcrypt password hashing.
- Strong JWT secret validation, HS256 claim requirements, `sub`, `jti`, and audit logging for token failures.
- Redis-capable fixed-window rate limiter with auth/export/general decorators and memory backend for dev/test.
- TenantGuard with tenant-scoped admin behavior and explicit `super_admin` cross-tenant auditing.
- JSONL security audit logger with recursive secret redaction.
- `/ready` readiness endpoint and OpenAPI Bearer JWT plus `X-API-Key` security schemes.
- API-level tenant isolation and runtime permission regression tests, including cross-tenant audit behavior and API key scope denial.
- Root `SECURITY.md` and `DEPLOYMENT.md` pointers to the detailed docs.
- CI contract tests for Docker image build/Trivy scan ordering.
- Bandit regression tests for hash primitives and URL scheme validation.

### Changed
- Auth API schemas now require `password`; user-id-only login is rejected.
- Project, graph, simulation, report, export, and admin-sensitive routes now enforce tenant and permission checks consistently.
- Simulation creation now checks the owning project's tenant and keeps auth-bypassed legacy resources tenantless instead of inventing a `default` tenant.
- Frontend Step1 simulation creation renders component error state instead of browser alerts and keeps success navigation to `Simulation`.
- Docker image workflow now builds a local image, scans it with pinned `aquasecurity/trivy-action@v0.36.0`, then pushes only after scan success.
- Dependency lock now applies uv override constraints to replace vulnerable transitive packages pinned by legacy OASIS dependencies.

### Fixed
- Deprecated the stale `Process.vue` route path by deleting the unused view and covering router references in Vitest.
- Removed stale `Process.vue` environment-setup TODO alert from the routed process flow.
- Replaced Bandit-flagged MD5/SHA1 uses with SHA-256 for deterministic non-secret identifiers.
- Replaced raw `urlopen` ingestion with HTTP/HTTPS-only connection handling.

### Security
- `bandit -r backend/app/ -ll --skip B101` reports no medium/high issues and no `#nosec` skips.
- `pip-audit` reports no known vulnerabilities.

## [0.7.0] - 2026-05-07

### Added
- API authentication & authorization system (JWT + API Key + RBAC)
- ConsumerCognitionEngine three-layer cognitive architecture
- Enterprise-grade population model (30+ fields, three generation modes)
- Monte Carlo validation framework (three-mode experiments)
- Social graph (Watts-Strogatz, Barabasi-Albert)
- RuntimeControlLayer (checkpoint + early stop)
- DOE experiment design (A/B/n, price ladder, stratified assignment)
- LLM Governor (circuit breaker, budget management, retry)
- Structured logging, security headers, three-tier rate limiting
- Pydantic input validation for key API endpoints
- Dry run mode for simulation preview
- BusinessBrief schema versioning (v1.0.0)
- Unified error response format (success_response, paginated_response)

### Fixed
- WEAK_SECRET_KEYS typo
- Cognition engine Pydantic output validation

### Security
- SECRET_KEY strong validation (length >= 32, weak value blocklist)
- CORS production environment disallow * wildcard
- Trivy image vulnerability scanning
- SAST + dependency audit CI
