# MiroConsumer Service Split Assessment

## Candidate Boundaries

### Simulation Engine Service

- Owns society runtime, channel propagation, replay checkpoints, and graph snapshots.
- Data contract: accepts a `BusinessBrief`, persona pack id, channel configuration, and deterministic seed; returns round events, reasoning traces, and checkpoint manifests.
- Communication path: HTTP for job submission, Redis/RQ or Celery for async execution, and object storage for large replay artifacts. A later gRPC interface can expose low-latency round streaming.

### Report Generation Service

- Owns report assembly, methodology page generation, evidence gatekeeping summaries, and LLM fallback diagnostics.
- Data contract: consumes simulation outputs, evidence atoms, confidence summaries, and quote authenticity flags; returns versioned report JSON and export artifacts.
- Communication path: HTTP request/response for interactive report reads, async queue for heavy exports, and signed object URLs for downloads.

### Authentication Service

- Owns user identity, API keys, tenant membership, role mapping, and audit-friendly authorization decisions.
- Data contract: exposes token introspection, permission checks, tenant binding, and API key metadata.
- Communication path: internal HTTP initially; gRPC can be introduced once auth decisions need lower-latency service-to-service calls.

## Migration Roadmap

1. Keep the Flask app as the composition root while `create_app()` delegates to single-purpose factory functions.
2. Move new service objects behind explicit constructors instead of pulling them from a Service Locator.
3. Introduce interface protocols for simulation, reporting, and auth operations.
4. Move persistence behind repository factories with dependency injection at the application-service boundary.
5. Extract each candidate service only after contract tests cover its request schema, response schema, retry behavior, and tenant isolation.

## Container Migration

The current container pattern remains as a compatibility layer. New code should prefer Constructor Injection: API routes receive an application service, the application service receives repositories and adapters, and tests instantiate the same graph with fake adapters. Existing `Container` lookups should be wrapped at the composition root and gradually replaced when touching the owning module.

## Tenant Isolation Decorator

The target API pattern is `@require_tenant_access(resource_type)`. The decorator should resolve the authenticated user and current tenant once, load the resource tenant through a typed repository, and return a standardized `TENANT_ISOLATION_VIOLATION` error when access is denied. This keeps tenant checks out of route bodies and prepares the auth boundary for extraction.
