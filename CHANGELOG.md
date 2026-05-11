# Changelog

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
