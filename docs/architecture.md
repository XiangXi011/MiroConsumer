# Architecture Notes

Updated: 2026-05-11

## Real Code Layout

The backend codebase is organized under `backend/app`, not `backend/src`.

Key areas:

- `backend/app/auth`: users, password auth, JWT, API keys, permissions, tenant guard.
- `backend/app/api`: graph, simulation, report, and consumer API routes.
- `backend/app/middleware`: rate limiting and request middleware.
- `backend/app/repositories`: filesystem and SQLAlchemy repository adapters.
- `backend/app/security`: audit logging and redaction utilities.
- `backend/app/redis`: readiness helpers.

## Auth Flow

1. Register validates password strength and stores a bcrypt hash.
2. Login resolves username/email/user_id and verifies password.
3. Successful login signs HS256 JWT with `sub` and `jti`.
4. Protected endpoints load user context from Bearer JWT or `X-API-Key`.
5. Permission decorators and `TenantGuard` enforce route access.

## Tenant Model

`Project` now carries optional `tenant_id` metadata. New projects inherit the authenticated user's tenant. Legacy projects without `tenant_id` remain compatible where existing tests require it, but tenant checks prefer explicit ownership.

## Frontend Routing

`/process/:projectId` routes to `MainView.vue`. `Process.vue` is treated as stale legacy UI and no longer contains the environment setup alert. The active Step1 component creates a simulation and routes to `Simulation` on success; failures render component state.

## Known Residual Work

`backend/app/services/consumer/confidence_scoring.py` still contains `replay_score = 0.5`; this placeholder is documented as post-gate work because it is not part of the P0/P1 security repair surface.
