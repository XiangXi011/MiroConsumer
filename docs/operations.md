# Operations Notes

Updated: 2026-05-11

## Readiness

- `/health` remains the lightweight service health endpoint.
- `/ready` validates dependencies required for traffic readiness, including configured Redis readiness when Redis-backed rate limiting or queues are enabled.

## Required Production Environment

- `JWT_SECRET_KEY`: strong JWT signing key, at least 32 characters.
- `SECRET_KEY`: strong Flask fallback key, at least 32 characters.
- `RATE_LIMIT_BACKEND=redis`.
- `REDIS_URL`: required when Redis rate limiting, RQ queues, or Redis locks are enabled.
- `AUDIT_LOG_PATH`: writable durable JSONL audit log location.
- `DB_URL`: optional; empty means filesystem repositories, supported SQLAlchemy schemes include SQLite/PostgreSQL variants used by repository tests.

## Verification Runbook

Run before release:

```bash
cd backend && uv sync --dev
cd backend && uv run --python 3.12 pytest --cov=app --cov-report=term-missing
cd frontend && npm ci && npm run build && npm test
bandit -r backend/app/ -ll --skip B101
pip-audit
cd backend && uv run --python 3.12 --with pip-audit pip-audit
docker build -t miroconsumer:test .
trivy image --severity HIGH,CRITICAL --exit-code 1 miroconsumer:test
```

If Docker Desktop is unavailable locally, rerun the Docker commands on a host with a reachable Docker daemon. Do not mark the image gate complete from the workflow contract test alone.

## Incident Review Hooks

Security-relevant events are emitted to audit JSONL with sensitive fields redacted. Review these event classes during incident response:

- auth register/login/API-key events
- token rejection
- permission denial
- tenant denial
- super_admin cross-tenant access
- rate limit rejection
