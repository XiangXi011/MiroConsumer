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

## Worker Scaling

The production Compose file defines the worker as a replicated service with
resource reservations. Docker Compose honors the healthcheck locally; Docker
Swarm or Kubernetes should own automatic scaling in production.

Worker healthcheck:

- confirms the worker container can start Python in the runtime image
- records the configured `RQ_QUEUE_NAME`
- acts as a fast liveness probe for orchestrators

Resource defaults:

- replicas: 2
- CPU limit: 2 cores
- memory limit: 4 GiB
- CPU reservation: 0.5 cores
- memory reservation: 1 GiB

Queue depth policy:

- scale out when simulation queue depth stays above 100 for five minutes
- scale in only after queue depth stays below 20 for ten minutes
- keep at least two workers for report/export backpressure isolation
- keep the maximum parallel experiment-group count aligned with LLM budget caps

Kubernetes HPA example:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: miroconsumer-worker
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: miroconsumer-worker
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: miroconsumer_queue_depth
        target:
          type: AverageValue
          averageValue: "100"
```

Prometheus adapter metric sketch:

```yaml
rules:
  - seriesQuery: 'miroconsumer_queue_depth{queue="simulation"}'
    resources:
      overrides:
        namespace: {resource: namespace}
        pod: {resource: pod}
    name:
      matches: "miroconsumer_queue_depth"
      as: "miroconsumer_queue_depth"
    metricsQuery: 'avg(<<.Series>>{<<.LabelMatchers>>}) by (<<.GroupBy>>)'
```

## Alerting

Prometheus rules live in `alerts/prometheus-rules.yml`. Validate them before
deployment:

```bash
promtool check rules alerts/prometheus-rules.yml
```

AlertManager Slack route example:

```yaml
route:
  receiver: slack-runtime
receivers:
  - name: slack-runtime
    slack_configs:
      - api_url: $SLACK_WEBHOOK_URL
        channel: "#miroconsumer-alerts"
```

Teams webhook routing can use an AlertManager webhook receiver that posts to the
Teams incoming webhook URL. PagerDuty integration should route `critical`
severity alerts to the production escalation policy and keep `warning` alerts in
Slack/Teams during business hours.

Simulated trigger checks:

- set `miroconsumer_queue_depth{queue="simulation"}` above 100 for five minutes
  to trigger `SimulationQueueHigh`
- stop worker scrape targets for one minute to trigger `WorkerDown`
- raise LLM errors above ten percent for two minutes to trigger
  `LLMErrorRateHigh`

## Backup And Restore

Database backup:

```bash
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U miroconsumer -d miroconsumer > backups/miroconsumer-$(date +%F).sql
```

Database restore:

```bash
cat backups/miroconsumer-YYYY-MM-DD.sql | docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U miroconsumer -d miroconsumer
```

Redis queue backup uses AOF persistence in production. Copy `redis_data` only
after stopping Redis or after creating a filesystem snapshot.

## Rollback

1. Pause worker scale-out.
2. Stop traffic to the new backend deployment.
3. Run `alembic downgrade -1` only when the release note marks the migration as
   reversible.
4. Redeploy the previous image tag and verify `/ready`.
5. Resume workers and inspect queue depth.

## Troubleshooting FAQ

Q: `/ready` fails Redis.
A: Check `REDIS_URL`, network policies, and whether Redis AOF replay completed.

Q: simulations stay queued.
A: Check worker health, queue depth, and `RQ_QUEUE_NAME` consistency between
backend and worker.

Q: report generation times out.
A: Check LLM error-rate alerts, retry budget, and provider rate limits.

Q: MinIO console is unreachable remotely.
A: The production compose file binds port 9001 to loopback only; use an SSH
tunnel or VPN.
