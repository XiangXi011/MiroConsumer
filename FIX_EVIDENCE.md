# MiroConsumer Phase7 Gatekeeper Fix Evidence

Date: 2026-05-11
Branch: phase7/gatekeeper-comprehensive-fixes

## Verified Real Issues

- Auth routes live under `backend/app/auth/routes.py`, not `backend/src/...`.
- `/api/auth/login` accepted `user_id` without a password and signed a JWT.
- `backend/app/auth/middleware.py` used a weak `dev-secret` fallback path through `SECRET_KEY` handling.
- `backend/app/middleware/rate_limiter.py` used process-local list state only.
- Several graph/simulation/report routes lacked explicit permission decorators and had inconsistent tenant filtering.
- `frontend/src/router/index.js` maps `/process/:projectId` to `MainView.vue`; stale `Process.vue` still contained a TODO alert.
- `.github/workflows/docker-image.yml` scanned an image reference before building the current image.
- `backend/app/services/consumer/confidence_scoring.py` still has `replay_score = 0.5  # placeholder`; documented as residual non-P0/P1 work.
- Phase7 dependency audit also found vulnerable transitive packages pinned by `camel-oasis==0.2.5`.

## Report Misjudgments / Corrections

- Repository code is under `backend/app/repositories/*` and is a filesystem/SQLAlchemy adapter layer, not empty `backend/src/...` stubs.
- Simulation export already supports `json`, `csv`, and `manifest`; missing business-facing PDF/Word/PPT export remains outside this P0/P1 repair set.
- Trivy was not literally "push then scan"; the real CI flaw was scanning a non-local image before building the current job artifact.
- Phase6J replay has benchmark code, while `confidence_scoring.py` keeps a separate placeholder score.

## Repair Evidence

- Auth: `User` now stores bcrypt password hashes; register/login require password; username/email/user_id login requires a valid password; user-id-only login is rejected.
- JWT: secrets now require `JWT_SECRET_KEY` or strong `SECRET_KEY`, weak/short secrets fail, tokens include `sub` and `jti`, and decode requires HS256 plus required claims.
- Rate limiting: added `RateLimiter` abstraction with Redis fixed-window `INCR`/`EXPIRE` backend and memory backend for dev/test; auth/export/general decorators are covered.
- Tenant/permission: added `TenantGuard`, tenant ownership on `Project`, tenant-aware graph/simulation/report guards, and permission decorators/tests for sensitive routes.
- Audit/readiness/OpenAPI/errors: added JSONL audit logging with redaction, `/ready`, auth schema password requirements, Bearer JWT and `X-API-Key` docs, and structured error tests.
- Frontend: removed stale `Process.vue` alert path and replaced Step1 simulation creation alerts with rendered `createError` state while preserving success navigation to `Simulation`.
- CI: Docker workflow now builds a local image first, scans `miroconsumer:${{ github.sha }}` with pinned `aquasecurity/trivy-action@v0.36.0`, and pushes only after scan success.
- Security scan hardening: replaced MD5/SHA1 Bandit findings with SHA-256 and replaced raw `urlopen` with explicit HTTP/HTTPS-only connections.
- Dependency audit: added uv override constraints to lift vulnerable transitive packages while retaining `camel-oasis` and full backend test compatibility.

## Residual Blockers

- Local Docker verification is blocked by host Docker Desktop daemon unavailability: Docker CLI is installed, but both `desktop-linux` and `default` contexts cannot connect to their named pipes, and `com.docker.service` cannot be started without elevated permissions.
