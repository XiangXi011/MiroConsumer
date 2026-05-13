# API Versioning Policy

This policy defines how MiroConsumer publishes and retires HTTP API routes.

## Current Version

- `/api/v1/*` is the canonical and recommended public API prefix for client integrations, generated API clients, and OpenAPI documentation.
- `/api/openapi.json` documents canonical v1 routes and marks legacy aliases as deprecated while the migration window remains open.
- New public endpoints must be added under `/api/v1/` first. Legacy aliases may exist only for compatibility.

## Legacy Compatibility

Legacy `/api/*` routes are deprecated. They remain available during the migration window so existing local tools and older frontend builds do not break during rollout.

- Compatibility window: at least two minor releases after a v1 equivalent is documented.
- During the window, legacy routes should keep behavior-compatible request and response shapes.
- New client code should not introduce fresh dependencies on legacy routes.
- Legacy-only routes must be either promoted to `/api/v1/` or explicitly marked internal before the window closes.
- Legacy responses include `Deprecation`, `Sunset`, and `Link: rel="successor-version"` headers.
- Removal schedule: deprecate on 2026-11-01 and sunset on 2026-12-01 unless a release note extends the window.

## Deprecation Process

1. Add or confirm the canonical `/api/v1/` route.
2. Add the route to `/api/openapi.json` with request and response schemas when it is part of the public contract.
3. Keep the legacy `/api/*` route as an alias for at least two minor releases.
4. Announce deprecation in release notes and migration notes.
5. Add response deprecation headers for legacy routes before removal when practical:
   - `Deprecation: true`
   - `Sunset: <RFC 7231 HTTP-date>`
   - `Link: </api/openapi.json>; rel="successor-version"`
6. Remove the legacy route only after the compatibility window and after verifying no supported frontend or integration still calls it.

## OpenAPI Guardrails

- Documented v1 paths must map to registered Flask routes.
- OpenAPI should prefer canonical route names exactly as implemented by Flask.
- Route inventory tests should fail when a documented path drifts away from the actual registered route.
