# Log Aggregation Runbook

MiroConsumer emits structured JSON logs for backend and worker services. Each log line carries `timestamp`, `level`, `logger`, `message`, `trace_id`, `span_id`, `service`, `tenant_id`, and `user_id` so Grafana Loki or Kibana can correlate a request across services.

## Runtime flow

1. Flask reads `X-Request-ID`; if absent it generates a UUID trace id.
2. Middleware stores `g.trace_id` and `g.span_id` for the request lifecycle.
3. The JSON formatter adds tenant and user context from authentication middleware when available.
4. Promtail reads Docker JSON logs and forwards parsed labels to Grafana Loki through `LOKI_URL`.

## Grafana Loki queries

Find a complete request chain by trace id:

```logql
{service=~"backend|worker|frontend", trace_id="trace-123"} | json
```

List errors by error code:

```logql
sum by (error_code) (count_over_time({service="backend", level=~"ERROR|CRITICAL"} | json [5m]))
```

Filter one tenant:

```logql
{tenant_id="tenant-a"} | json
```

## Kibana equivalents

- `trace_id:"trace-123"`
- `tenant_id:"tenant-a" AND level:(ERROR OR CRITICAL)`
- `service:"backend" AND error_code:*`

The production Compose file includes a Promtail sidecar and `ops/promtail-config.yml`. Set `LOKI_URL` to your Grafana Loki push endpoint, or adapt the same JSON fields in Fluent Bit for ELK.