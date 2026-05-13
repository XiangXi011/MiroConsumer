# Deployment Guide

This guide is the root deployment entry point for MiroConsumer. It is intentionally self-contained for operators doing release review, rollback, or incident response.

## Quick Start

```bash
cp .env.example .env
# edit .env with production secrets and service URLs
docker compose -f docker-compose.prod.yml up -d
curl http://localhost:5000/health
curl http://localhost:5000/ready
curl http://localhost:5000/metrics
```

## Required Environment Variables

| Variable | Purpose | Example |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@db:5432/miroconsumer` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `LLM_API_KEY` | Provider key for LLM calls | `sk-...` |
| `SECRET_KEY` | Flask/JWT signing secret | 64+ random characters |
| `CORS_ALLOW_ORIGINS` | Explicit browser origin allowlist | `https://app.example.com` |
| `MINIO_ROOT_USER` | MinIO administrator user | `miroadmin` |
| `MINIO_ROOT_PASSWORD` | MinIO administrator password | strong random value |

## Optional Environment Variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `LOG_LEVEL` | Application log verbosity | `INFO` |
| `RATE_LIMIT_ENABLED` | Enable API rate limiting | `true` |
| `SENTRY_DSN` | Error reporting DSN | unset |
| `WORKER_CONCURRENCY` | Worker process concurrency | `4` |
| `CONSUMER_REPORT_LLM_ENABLED` | Use LLM-enhanced consumer report sections with template fallback | `false` |

## Health Checks

| Endpoint | Purpose | Expected Result |
| --- | --- | --- |
| `GET /health` | Liveness check | HTTP 200 when the app process is alive. |
| `GET /ready` | Readiness check | HTTP 200 when dependencies are usable, 503 otherwise. |
| `GET /metrics` | Prometheus scrape endpoint | Prometheus text format including request counters. |

## Deployment Steps

1. Build images from the release commit.
2. Run backend tests and frontend build/test gates.
3. Run `bandit`, `pip-audit`, and Trivy container scan.
4. Apply Alembic migrations with `cd backend && python -m alembic upgrade head`.
5. Start services with `docker compose -f docker-compose.prod.yml up -d`.
6. Confirm `/health`, `/ready`, and `/metrics`.
7. Confirm the MinIO console is not publicly reachable on port 9001.
8. Review application logs for startup errors and migration warnings.

## Backup

Database backups should run before every release and on a daily schedule.

```bash
pg_dump "$DATABASE_URL" > backups/miroconsumer-$(date +%Y%m%d%H%M%S).sql
find backups -name 'miroconsumer-*.sql' -mtime +30 -delete
```

For object storage, replicate MinIO buckets or snapshot the backing volume according to the hosting platform's storage guarantees.

## Rollback

1. Stop write-heavy workers or pause queue consumers.
2. Re-deploy the previous image tag.
3. If the release included a reversible migration, run the documented Alembic downgrade for that migration only.
4. Restore the latest pre-release database backup if data corruption is confirmed.
5. Re-run `/ready` and a representative smoke flow.
6. Record the incident and the release tag that was rolled back.

## Troubleshooting

| Symptom | First Checks |
| --- | --- |
| `/ready` returns 503 | Check `DATABASE_URL`, Redis connectivity, and Alembic head revision. |
| `/metrics` is empty | Confirm the Flask app registered the metrics blueprint and Prometheus scrapes the right port. |
| LLM reports fail | Check `LLM_API_KEY`, provider base URL, budget governor state, and PromptGuard blocks. |
| Worker does not start | Confirm `Dockerfile.backend` image was built before `Dockerfile.worker`. |
| MinIO console reachable externally | Confirm `127.0.0.1:9001:9001` binding or private network firewall rules. |

## Scaling

- Scale web containers horizontally behind a load balancer once Redis-backed rate limiting is enabled.
- Scale workers based on queue depth, task latency, and LLM provider budget.
- Keep database connection pool limits below the managed PostgreSQL maximum.
- Use Prometheus alerts for high error rate, queue backlog, and readiness failures.

## Related Documents

- `docs/deployment.md` for extended operational notes.
- `docker-compose.prod.yml` for the production compose topology.
- `.github/workflows/docker-image.yml` for release image build and scan order.