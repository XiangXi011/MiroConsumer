# Deployment Notes

Updated: 2026-05-11

## Container Release Gate

The Docker image workflow must build the current source before any push:

1. Checkout source and compute GHCR metadata.
2. Build a local Docker image tagged `miroconsumer:${{ github.sha }}` with `push: false` and `load: true`.
3. Scan that local image with `aquasecurity/trivy-action@v0.36.0`.
4. Push GHCR tags only after Trivy exits successfully.

The workflow must not use `continue-on-error` for Trivy and must not scan a remote image reference that was not produced by the same job.

## Runtime Secrets

- `JWT_SECRET_KEY` is preferred for auth tokens.
- `SECRET_KEY` may be used as fallback only when it is non-empty, not a known weak value, and at least 32 characters.
- Production deployments must set `RATE_LIMIT_BACKEND=redis` with `REDIS_URL`.
- Production deployments must set an audit log location via `AUDIT_LOG_PATH` or mount the default path durably.

## Local Verification Caveat

Local Docker build/scan requires Docker Desktop service access. On the 2026-05-11 verification host, Docker Desktop processes existed but the daemon pipe was unavailable and `com.docker.service` could not be started without elevated permissions.
