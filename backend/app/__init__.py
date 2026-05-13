"""MiroConsumer Flask application factory."""

import json
import os
import re
import uuid
import warnings

# Suppress noisy multiprocessing resource tracker warnings from optional ML dependencies.
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, g, request
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger

SENSITIVE_FIELDS = {'api_key', 'token', 'secret', 'password', 'concept', 'price',
                    'claims', 'consumer_data', 'uploaded_text', 'LLM_API_KEY'}

LEGACY_API_DEPRECATION = 'date="Sun, 01 Nov 2026 00:00:00 GMT"'
LEGACY_API_SUNSET = "Sun, 01 Dec 2026 00:00:00 GMT"


def _schema_ref(name: str) -> dict:
    return {"$ref": f"#/components/schemas/{name}"}


def _json_request(schema_name: str, required: bool = True) -> dict:
    return {
        "required": required,
        "content": {
            "application/json": {
                "schema": _schema_ref(schema_name)
            }
        },
    }


def _json_response(description: str, schema_name: str | None = None) -> dict:
    content = {}
    if schema_name:
        content = {
            "application/json": {
                "schema": _schema_ref(schema_name)
            }
        }
    return {"description": description, **({"content": content} if content else {})}


def _path_param(name: str) -> dict:
    return {"name": name, "in": "path", "required": True, "schema": {"type": "string"}}


_FLASK_PATH_PARAM_RE = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")


def _flask_rule_to_openapi_path(rule: str) -> str:
    return _FLASK_PATH_PARAM_RE.sub(lambda match: "{" + match.group(1) + "}", rule)


def _route_tag_from_path(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
        return parts[2]
    return parts[0] if parts else "api"


def _route_summary_from_endpoint(endpoint: str) -> str:
    leaf = endpoint.split(".")[-1]
    return leaf.replace("_", " ").strip().title() or endpoint


def _auto_openapi_operation(rule, method: str) -> dict:
    openapi_path = _flask_rule_to_openapi_path(rule.rule)
    parameters = [_path_param(name) for name in sorted(rule.arguments or [])]
    response_content = {
        "application/json": {
            "schema": _schema_ref("SuccessResponse")
        }
    }
    return {
        "summary": _route_summary_from_endpoint(rule.endpoint),
        "operationId": rule.endpoint.replace(".", "_"),
        "tags": [_route_tag_from_path(openapi_path)],
        **({"parameters": parameters} if parameters else {}),
        "responses": {
            "200": {
                "description": f"{method.title()} response",
                "content": response_content,
            }
        },
    }


def _is_legacy_api_path(path: str) -> bool:
    return path.startswith("/api/") and not path.startswith("/api/v1/")


def _mark_legacy_operation_deprecated(operation: dict) -> dict:
    operation["deprecated"] = True
    operation["x-deprecation"] = LEGACY_API_DEPRECATION
    operation["x-sunset"] = LEGACY_API_SUNSET
    operation["x-successor-version"] = "/api/v1/"
    return operation


def _add_legacy_deprecation_headers(response):
    if _is_legacy_api_path(request.path):
        response.headers["Deprecation"] = LEGACY_API_DEPRECATION
        response.headers["Sunset"] = LEGACY_API_SUNSET
        response.headers["Link"] = '</api/openapi.json>; rel="successor-version"'
    return response


def _normalize_json_error_response(response):
    if not response.is_json:
        return response
    payload = response.get_json(silent=True)
    if not isinstance(payload, dict):
        return response
    from .utils.error_codes import normalize_error_payload
    normalized = normalize_error_payload(payload, response.status_code)
    if normalized != payload:
        response.set_data(json.dumps(normalized, ensure_ascii=False))
        response.mimetype = "application/json"
    return response

def _configured_cors_origins(config_class) -> list[str]:
    raw_new = getattr(config_class, "CORS_ALLOW_ORIGINS", None)
    raw_old = getattr(config_class, "CORS_ALLOWED_ORIGINS", None)
    raw_origins = raw_new if raw_new is not None else raw_old
    if raw_old and raw_new and raw_old != raw_new:
        raw_origins = raw_old
    if isinstance(raw_origins, str):
        origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    else:
        origins = [str(origin).strip() for origin in raw_origins if str(origin).strip()]
    if not origins:
        raise RuntimeError("CORS_ALLOW_ORIGINS must be explicitly set")
    return origins


def _openapi_components() -> dict:
    success_response = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "data": {"type": "object", "additionalProperties": True},
        },
        "required": ["success"],
    }
    return {
        "schemas": {
            "SuccessResponse": success_response,
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": False},
                    "error": {"type": "string"},
                    "message": {"type": "string"},
                    "error_code": {"type": "string"},
                    "error_message": {"type": "string"},
                    "field": {"type": "string"},
                    "request_id": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
                "required": ["success", "error", "error_code", "error_message", "field", "request_id", "suggestion"],
            },
            "RegisterUserRequest": {
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "role": {
                        "type": "string",
                        "enum": ["owner", "admin", "super_admin", "researcher", "viewer", "auditor", "service", "analyst"],
                        "default": "researcher",
                    },
                    "tenant_id": {"type": "string", "default": "default"},
                    "password": {"type": "string", "format": "password", "minLength": 10},
                },
                "required": ["username", "email", "password"],
            },
            "LoginRequest": {
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "user_id": {"type": "string"},
                    "password": {"type": "string", "format": "password"},
                },
                "required": ["password"],
            },
            "CreateApiKeyRequest": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "scopes": {"type": "array", "items": {"type": "string"}},
                },
            },
            "GenerateReportRequest": {
                "type": "object",
                "properties": {
                    "simulation_id": {"type": "string"},
                    "force_regenerate": {"type": "boolean", "default": False},
                },
                "required": ["simulation_id"],
            },
            "GenerateReportStatusRequest": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "simulation_id": {"type": "string"},
                },
            },
            "StartSimulationRequest": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "simulation_id": {"type": "string"},
                    "society_mode": {"type": "string"},
                    "society_seed": {"type": "integer"},
                    "society_max_agents": {"type": "integer"},
                    "society_audit_sample_size": {"type": "integer"},
                    "advanced_society_mode": {"type": "boolean"},
                    "enabled_channels": {"type": "array", "items": {"type": "string"}},
                    "channel_seed": {"type": "integer"},
                    "llm_budget_limit": {"type": "number"},
                },
            },
            "DeadLetter": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "task_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "error": {"type": "string"},
                    "created_at": {"type": "string"},
                },
            },
            "DeadLetterListResponse": {
                "type": "object",
                "properties": {
                    "backend": {"type": "string"},
                    "dead_letters": {
                        "type": "array",
                        "items": _schema_ref("DeadLetter"),
                    },
                },
                "required": ["backend", "dead_letters"],
            },
            "EvidenceGraphNode": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "type": {"type": "string", "enum": ["finding", "evidence", "source"]},
                    "label": {"type": "string"},
                    "resource_id": {"type": "string"},
                    "low_confidence": {"type": "boolean"},
                    "traceable_fields": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "type", "label"],
            },
            "EvidenceGraphEdge": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "type": {"type": "string", "enum": ["supported_by", "sourced_from"]},
                    "traceable_fields": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["source", "target", "type"],
            },
            "EvidenceGraphResponse": {
                "type": "object",
                "properties": {
                    "report_id": {"type": "string"},
                    "complete": {"type": "boolean"},
                    "nodes": {"type": "array", "items": _schema_ref("EvidenceGraphNode")},
                    "edges": {"type": "array", "items": _schema_ref("EvidenceGraphEdge")},
                    "node_count": {"type": "integer"},
                    "edge_count": {"type": "integer"},
                    "warnings": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["report_id", "nodes", "edges"],
            },
        }
    }


def _openapi_paths(app=None) -> dict:
    paths = {
        "/health": {"get": {"summary": "Health check", "responses": {"200": _json_response("OK", "SuccessResponse")}}},
        "/api/v1/auth/register": {
            "post": {
                "summary": "Register user",
                "requestBody": _json_request("RegisterUserRequest"),
                "responses": {"201": _json_response("Created", "SuccessResponse"), "400": _json_response("Validation error", "ErrorResponse")},
            }
        },
        "/api/v1/auth/login": {
            "post": {
                "summary": "Login",
                "requestBody": _json_request("LoginRequest"),
                "responses": {"200": _json_response("Token returned", "SuccessResponse"), "401": _json_response("Authentication failed", "ErrorResponse")},
            }
        },
        "/api/v1/auth/me": {
            "get": {
                "summary": "Current user info",
                "responses": {"200": _json_response("User info", "SuccessResponse"), "401": _json_response("Authentication required", "ErrorResponse")},
            }
        },
        "/api/v1/auth/api-keys": {
            "post": {
                "summary": "Create API key",
                "requestBody": _json_request("CreateApiKeyRequest", required=False),
                "responses": {"201": _json_response("API key created", "SuccessResponse"), "403": _json_response("Forbidden", "ErrorResponse")},
            }
        },
        "/api/v1/consumer/simulation/{simulation_id}/consumer-summary": {
            "get": {
                "summary": "Consumer propagation summary",
                "parameters": [_path_param("simulation_id")],
                "responses": {"200": _json_response("Summary data", "SuccessResponse")},
            }
        },
        "/api/v1/consumer/simulations/{simulation_id}/channel-summary": {
            "get": {
                "summary": "Channel metrics summary",
                "parameters": [_path_param("simulation_id")],
                "responses": {"200": _json_response("Channel data", "SuccessResponse")},
            }
        },
        "/api/v1/consumer/simulations/{simulation_id}/branches": {
            "get": {
                "summary": "List branches",
                "parameters": [_path_param("simulation_id")],
                "responses": {"200": _json_response("Branch list", "SuccessResponse")},
            },
            "post": {
                "summary": "Create branch",
                "parameters": [_path_param("simulation_id")],
                "responses": {"201": _json_response("Branch created", "SuccessResponse")},
            },
        },
        "/api/v1/consumer/simulations/{simulation_id}/interventions": {
            "get": {
                "summary": "List interventions",
                "parameters": [_path_param("simulation_id")],
                "responses": {"200": _json_response("Intervention list", "SuccessResponse")},
            }
        },
        "/api/v1/consumer/comparisons": {
            "get": {"summary": "List comparisons", "responses": {"200": _json_response("Comparison list", "SuccessResponse")}},
            "post": {"summary": "Create comparison", "responses": {"201": _json_response("Comparison created", "SuccessResponse")}},
        },
        "/api/v1/consumer/research-assets": {
            "get": {"summary": "List research assets", "responses": {"200": _json_response("Asset list", "SuccessResponse")}}
        },
        "/api/v1/consumer/simulations/{simulation_id}/interviews": {
            "post": {
                "summary": "Run consumer interview",
                "parameters": [_path_param("simulation_id")],
                "responses": {"200": _json_response("Interview result", "SuccessResponse")},
            }
        },
        "/api/v1/consumer/simulations/{simulation_id}/focus-groups": {
            "post": {
                "summary": "Run focus group",
                "parameters": [_path_param("simulation_id")],
                "responses": {"200": _json_response("Focus group result", "SuccessResponse")},
            }
        },
        "/api/v1/consumer/task-queue/dead-letters": {
            "get": {
                "summary": "List queue dead letters",
                "responses": {"200": _json_response("Dead letters", "DeadLetterListResponse")},
            }
        },
        "/api/v1/consumer/reports/{report_id}/evidence-graph": {
            "get": {
                "summary": "Report evidence graph",
                "parameters": [_path_param("report_id")],
                "responses": {"200": _json_response("Finding-evidence-source graph", "EvidenceGraphResponse")},
            }
        },
        "/api/v1/report/generate": {
            "post": {
                "summary": "Generate report",
                "requestBody": _json_request("GenerateReportRequest"),
                "responses": {"200": _json_response("Task ID returned", "SuccessResponse")},
            }
        },
        "/api/v1/report/generate/status": {
            "post": {
                "summary": "Get report generation status",
                "requestBody": _json_request("GenerateReportStatusRequest", required=False),
                "responses": {"200": _json_response("Task status", "SuccessResponse")},
            }
        },
        "/api/v1/simulation/start": {
            "post": {
                "summary": "Start simulation",
                "requestBody": _json_request("StartSimulationRequest"),
                "responses": {"200": _json_response("Simulation started", "SuccessResponse")},
            }
        },
        "/api/v1/simulation/entities/{graph_id}": {
            "get": {
                "summary": "Get graph entities",
                "parameters": [_path_param("graph_id")],
                "responses": {"200": _json_response("Entity list", "SuccessResponse")},
            }
        },
        "/api/v1/graph/project/list": {
            "get": {"summary": "List projects", "responses": {"200": _json_response("Project list", "SuccessResponse")}}
        },
    }
    if app is not None:
        for rule in app.url_map.iter_rules():
            if not rule.rule.startswith("/api/"):
                continue
            path = _flask_rule_to_openapi_path(rule.rule)
            path_item = paths.setdefault(path, {})
            is_legacy = _is_legacy_api_path(rule.rule)
            for method in sorted(rule.methods or []):
                if method in {"HEAD", "OPTIONS"}:
                    continue
                openapi_method = method.lower()
                if openapi_method in path_item:
                    continue
                operation = _auto_openapi_operation(rule, method)
                if is_legacy:
                    operation = _mark_legacy_operation_deprecated(operation)
                path_item[openapi_method] = operation
    return paths


def _sanitize_log_data(data, max_length=200):
    """Sanitize request payloads before logging."""
    if not isinstance(data, dict):
        return str(data)[:max_length]
    sanitized = {}
    for k, v in data.items():
        if any(s in k.lower() for s in SENSITIVE_FIELDS):
            sanitized[k] = '***REDACTED***'
        elif isinstance(v, str) and len(v) > 100:
            sanitized[k] = v[:50] + '...[truncated]'
        else:
            sanitized[k] = v
    return sanitized


def _validate_config(config_class, logger):
    config_errors = config_class.validate()
    if config_errors:
        for err in config_errors:
            logger.error(f"Configuration error: {err}")
        raise RuntimeError(f"Configuration errors: {'; '.join(config_errors)}")


def _should_log_startup(app) -> bool:
    is_reloader_process = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    return not app.config.get("DEBUG", False) or is_reloader_process


def create_flask_app(config_class=Config):
    """Create the bare Flask app and validate static configuration."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    if hasattr(app, "json") and hasattr(app.json, "ensure_ascii"):
        app.json.ensure_ascii = False
    logger = setup_logger("miroconsumer")
    _validate_config(config_class, logger)
    should_log_startup = _should_log_startup(app)
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("MiroConsumer Backend starting...")
        logger.info("=" * 50)
    return app, logger, should_log_startup


def _load_sentry_integrations():
    integrations = []
    try:
        from sentry_sdk.integrations.flask import FlaskIntegration
        integrations.append(FlaskIntegration())
    except ImportError:
        return []
    for module_name, class_name in (
        ("sentry_sdk.integrations.celery", "CeleryIntegration"),
        ("sentry_sdk.integrations.sqlalchemy", "SqlalchemyIntegration"),
    ):
        try:
            module = __import__(module_name, fromlist=[class_name])
            integrations.append(getattr(module, class_name)())
        except (ImportError, AttributeError):
            continue
    return integrations


def _build_sentry_traces_sampler(base_rate: float):
    def traces_sampler(sampling_context):
        transaction = sampling_context.get("transaction_context", {}) or {}
        environ = sampling_context.get("wsgi_environ", {}) or {}
        name = str(transaction.get("name", "") or "")
        path = str(environ.get("PATH_INFO", "") or "")
        target = f"{name} {path}".lower()
        if "/api/simulation" in target or "/api/report" in target:
            return 1.0
        return base_rate

    return traces_sampler


def init_observability(app, config_class, logger):
    """Initialize structured logging and optional error tracking."""
    from .utils.structured_logger import setup_structured_logger
    if config_class.LOG_FORMAT == "json":
        setup_structured_logger(app)

    sentry_dsn = app.config.get("SENTRY_DSN") or os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            integrations = _load_sentry_integrations()
            if not integrations:
                logger.warning("sentry integrations unavailable, skipping Sentry integration")
                return
            sample_rate = float(app.config.get("SENTRY_TRACES_SAMPLE_RATE", 0.05))
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=integrations,
                traces_sampler=_build_sentry_traces_sampler(sample_rate),
                environment=app.config.get("SENTRY_ENVIRONMENT", os.environ.get("FLASK_ENV", "production")),
            )
            logger.info("Sentry enabled")
        except ImportError:
            logger.warning("sentry-sdk not installed, skipping Sentry integration")


def register_trace_context(app):
    """Inject request trace and span IDs before auth and other middleware."""
    @app.before_request
    def inject_trace_context():
        trace_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        g.trace_id = trace_id
        g.request_id = trace_id
        g.span_id = uuid.uuid4().hex[:16]

def init_extensions(app, config_class, logger, should_log_startup):
    """Initialize CORS, auth, rate limiting, and process cleanup hooks."""
    origins = _configured_cors_origins(config_class)
    if "*" in origins and not app.debug:
        raise RuntimeError("CORS wildcard '*' is not allowed in production. Set CORS_ALLOWED_ORIGINS in .env")
    CORS(app, resources={r"/api/*": {"origins": origins}})

    from .auth.middleware import init_auth
    from .auth.repository import create_auth_repository_from_config
    auth_repository, auth_engine = create_auth_repository_from_config(config_class)
    app.extensions["auth_engine"] = auth_engine
    init_auth(app, auth_repository=auth_repository)

    from .middleware.rate_limiter import configure_rate_limiter
    configure_rate_limiter(app)
    if not app.config.get("RATE_LIMIT_ENABLED", False):
        logger.warning("Rate limiting is disabled; production deployments must enable RATE_LIMIT_ENABLED")

    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("Simulation process cleanup registered")


def register_request_hooks(app, config_class):
    """Register request ID, logging, security headers, and metrics hooks."""
    @app.before_request
    def log_request():
        import time
        if not getattr(g, "trace_id", None):
            trace_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
            g.trace_id = trace_id
            g.request_id = trace_id
        if not getattr(g, "span_id", None):
            g.span_id = uuid.uuid4().hex[:16]
        g.request_start_time = time.perf_counter()
        request_logger = get_logger('miroconsumer.request')
        request_logger.debug(f"request: {request.method} {request.path}")
        if request.content_type and "json" in request.content_type:
            request_logger.debug(f"request_body: {_sanitize_log_data(request.get_json(silent=True))}")

    @app.after_request
    def log_response(response):
        request_logger = get_logger('miroconsumer.request')
        request_logger.debug(f"response: {response.status_code}")
        from .utils.security_headers import apply_security_headers
        import time
        from .utils.metrics import record_request
        apply_security_headers(response, config_class)
        response.headers["X-Request-ID"] = getattr(g, "trace_id", getattr(g, "request_id", "unknown"))
        response.headers["X-Span-ID"] = getattr(g, "span_id", "unknown")
        _add_legacy_deprecation_headers(response)
        _normalize_json_error_response(response)
        started_at = getattr(g, "request_start_time", None)
        duration_ms = (time.perf_counter() - started_at) * 1000 if started_at else None
        record_request(response.status_code, duration_ms=duration_ms)
        return response


def register_blueprints(app):
    """Register public API, versioned API, auth, and metrics blueprints."""
    from .api import graph_bp, simulation_bp, report_bp, consumer_bp
    from .auth.routes import auth_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(graph_bp, url_prefix="/api/graph")
    app.register_blueprint(simulation_bp, url_prefix="/api/simulation")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.register_blueprint(consumer_bp, url_prefix="/api/consumer")
    app.register_blueprint(graph_bp, url_prefix="/api/v1/graph", name="graph_v1")
    app.register_blueprint(simulation_bp, url_prefix="/api/v1/simulation", name="simulation_v1")
    app.register_blueprint(report_bp, url_prefix="/api/v1/report", name="report_v1")
    app.register_blueprint(consumer_bp, url_prefix="/api/v1/consumer", name="consumer_v1")
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth", name="auth_v1")
    from .utils.metrics import metrics_bp
    app.register_blueprint(metrics_bp)


def register_health_routes(app):
    """Register health and readiness endpoints."""
    @app.route("/health")
    def health():
        status = "enabled" if app.config.get("RATE_LIMIT_ENABLED", False) else "disabled"
        from .utils.metrics import performance_snapshot
        return {"status": "ok", "rate_limiter": status, "performance": performance_snapshot()}

    @app.route("/ready")
    def ready():
        checks = {}
        errors = {}
        warnings = {}
        from .redis.health import check_redis
        redis_status, redis_message = check_redis(
            app.config.get("REDIS_URL", ""),
            persistence_required=bool(app.config.get("REDIS_PERSISTENCE_ENABLED", False)),
        )
        checks["redis"] = redis_status
        if redis_message:
            if redis_status == "error":
                errors["redis"] = redis_message
            else:
                warnings["redis"] = redis_message
        status_code = 200 if all(value in {"ok", "skipped", "warning"} for value in checks.values()) else 503
        payload = {"status": "ready" if status_code == 200 else "not_ready", "checks": checks}
        if errors:
            payload["errors"] = errors
        if warnings:
            payload["warnings"] = warnings
        return payload, status_code


def register_version_routes(app):
    from .utils.version import get_version_info

    @app.route("/api/version")
    def version():
        return get_version_info()


def register_openapi_routes(app):
    from .utils.version import get_version_info

    @app.route("/api/openapi.json")
    def openapi_spec():
        return {
            "openapi": "3.0.3",
            "info": {"title": "MiroConsumer API", "version": get_version_info()["version"]},
            "servers": [{"url": "/", "description": "Current host"}],
            "paths": _openapi_paths(app),
            "components": {**_openapi_components(), "securitySchemes": {"BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}, "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}}},
            "security": [{"BearerAuth": []}, {"ApiKeyAuth": []}],
        }

    @app.route("/api/docs")
    def api_docs():
        return '<html><head><title>MiroConsumer API Docs</title></head><body><h1>MiroConsumer API Docs</h1><p>OpenAPI spec: <a href="/api/openapi.json">/api/openapi.json</a></p></body></html>'


def create_app(config_class=Config):
    """Flask application factory orchestration."""
    app, logger, should_log_startup = create_flask_app(config_class)
    init_observability(app, config_class, logger)
    register_trace_context(app)
    init_extensions(app, config_class, logger, should_log_startup)
    register_request_hooks(app, config_class)
    register_blueprints(app)
    register_health_routes(app)
    register_version_routes(app)
    register_openapi_routes(app)
    if should_log_startup:
        logger.info("MiroConsumer Backend started")
    return app







