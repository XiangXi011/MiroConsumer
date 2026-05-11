# Security Notes

Updated: 2026-05-11

## Authentication

- Registration requires `username`, `email`, `password`, and tenant metadata.
- Login accepts `username`, `email`, or `user_id`, but always requires `password`.
- User-id-only login is intentionally rejected with the same auth failure contract as bad credentials.
- Passwords are stored only as bcrypt hashes and are not returned in API responses.

## Tokens

- JWT signing uses `JWT_SECRET_KEY` or a strong `SECRET_KEY` fallback.
- Weak defaults such as `dev-secret`, empty strings, and short secrets are rejected during app setup.
- JWTs include `sub`, `user_id`, `jti`, `iat`, and `exp`.
- Decoding accepts only HS256 and requires standard claims; expired, forged, malformed, and `alg=none` tokens are rejected.

## Authorization And Tenancy

- `TenantGuard` enforces tenant ownership for project, graph, simulation, and report resources.
- `admin` is tenant-scoped.
- `super_admin` may cross tenant boundaries, and cross-tenant access is audit logged.
- Sensitive prepare/status/get/list/history/export/start/stop/report/admin routes require explicit permissions.

## Audit And Rate Limits

- Security audit logs are JSONL and redact password/token/API key/secret values recursively.
- Rate limiting supports Redis fixed-window counters with atomic `INCR` and `EXPIRE`.
- Memory rate limiting is intended for dev/test only; production memory backend validation fails.

## Static And Dependency Scans

- Bandit passes with no high/medium findings and no `#nosec` suppressions.
- pip-audit passes for the backend project environment after uv dependency overrides replace vulnerable transitive packages pinned by legacy OASIS dependencies.
