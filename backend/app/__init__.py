"""
MiroConsumer Backend - Flask应用工厂
"""

import os
import re
import uuid
import warnings

# 抑制 multiprocessing resource_tracker 的警告（来自第三方库如 transformers）
# 需要在所有其他导入之前设置
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, g, request
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger

SENSITIVE_FIELDS = {'api_key', 'token', 'secret', 'password', 'concept', 'price',
                    'claims', 'consumer_data', 'uploaded_text', 'LLM_API_KEY'}


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
                },
                "required": ["success", "error"],
            },
            "RegisterUserRequest": {
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "role": {
                        "type": "string",
                        "enum": ["owner", "admin", "researcher", "viewer", "auditor", "service"],
                        "default": "researcher",
                    },
                    "tenant_id": {"type": "string", "default": "default"},
                },
                "required": ["username", "email"],
            },
            "LoginRequest": {
                "type": "object",
                "properties": {"user_id": {"type": "string"}},
                "required": ["user_id"],
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
            if not rule.rule.startswith("/api/v1/"):
                continue
            path = _flask_rule_to_openapi_path(rule.rule)
            path_item = paths.setdefault(path, {})
            for method in sorted(rule.methods or []):
                if method in {"HEAD", "OPTIONS"}:
                    continue
                openapi_method = method.lower()
                if openapi_method in path_item:
                    continue
                path_item[openapi_method] = _auto_openapi_operation(rule, method)
    return paths


def _sanitize_log_data(data, max_length=200):
    """脱敏日志数据"""
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


def create_app(config_class=Config):
    """Flask应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 运行配置校验（SECRET_KEY弱值/长度、DB_URL格式等）
    config_errors = config_class.validate()
    if config_errors:
        logger = setup_logger('miroconsumer')
        for err in config_errors:
            logger.error(f"配置错误: {err}")
        raise RuntimeError(f"Configuration errors: {'; '.join(config_errors)}")

    # 请求体大小限制
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
    
    # 设置JSON编码：确保中文直接显示（而不是 \uXXXX 格式）
    # Flask >= 2.3 使用 app.json.ensure_ascii，旧版本使用 JSON_AS_ASCII 配置
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False
    
    # 设置日志
    logger = setup_logger('miroconsumer')

    # 结构化日志（JSON格式时启用）
    from .utils.structured_logger import setup_structured_logger
    if config_class.LOG_FORMAT == 'json':
        setup_structured_logger(app)

    # 只在 reloader 子进程中打印启动信息（避免 debug 模式下打印两次）
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process

    if should_log_startup:
        logger.info("=" * 50)
        logger.info("MiroConsumer Backend 启动中...")
        logger.info("=" * 50)
    
    # 启用CORS
    origins = [o.strip() for o in config_class.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
    CORS(app, resources={r"/api/*": {"origins": origins}})

    # CORS 通配符校验（生产环境禁止 *）
    if '*' in origins and not app.debug:
        raise RuntimeError("CORS wildcard '*' is not allowed in production. Set CORS_ALLOWED_ORIGINS in .env")

    # 初始化认证授权系统
    from .auth.middleware import init_auth
    from .auth.repository import create_auth_repository_from_config
    auth_repository, auth_engine = create_auth_repository_from_config(config_class)
    app.extensions['auth_engine'] = auth_engine
    init_auth(app, auth_repository=auth_repository)

    # 注册模拟进程清理函数（确保服务器关闭时终止所有模拟进程）
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("已注册模拟进程清理函数")
    
    # 请求日志中间件
    @app.before_request
    def log_request():
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4())[:8])
        logger = get_logger('miroconsumer.request')
        logger.debug(f"请求: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"请求体: {_sanitize_log_data(request.get_json(silent=True))}")

    @app.after_request
    def log_response(response):
        logger = get_logger('miroconsumer.request')
        logger.debug(f"响应: {response.status_code}")
        # Security response headers
        from .utils.security_headers import apply_security_headers
        apply_security_headers(response, config_class)
        # Inject request_id into response
        response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
        # Record metrics
        from .utils.metrics import record_request
        record_request(response.status_code)
        return response
    
    # 注册蓝图
    from .api import graph_bp, simulation_bp, report_bp, consumer_bp
    from .auth.routes import auth_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    app.register_blueprint(consumer_bp, url_prefix='/api/consumer')

    # P2-2: API v1 version prefix — same blueprints, dual paths
    app.register_blueprint(graph_bp, url_prefix='/api/v1/graph', name='graph_v1')
    app.register_blueprint(simulation_bp, url_prefix='/api/v1/simulation', name='simulation_v1')
    app.register_blueprint(report_bp, url_prefix='/api/v1/report', name='report_v1')
    app.register_blueprint(consumer_bp, url_prefix='/api/v1/consumer', name='consumer_v1')
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth', name='auth_v1')
    
    # Sentry error tracking (configurable)
    sentry_dsn = os.environ.get('SENTRY_DSN')
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[FlaskIntegration()],
                traces_sample_rate=0.1,
                environment=os.environ.get('FLASK_ENV', 'production'),
            )
            logger.info("Sentry enabled")
        except ImportError:
            logger.warning("sentry-sdk not installed, skipping Sentry integration")

    # 注册 metrics 蓝图
    from .utils.metrics import metrics_bp
    app.register_blueprint(metrics_bp)

    # 健康检查
    @app.route('/health')
    def health():
        return {'status': 'ok'}

    # 版本信息
    from .utils.version import get_version_info

    @app.route('/api/version')
    def version():
        return get_version_info()

    # OpenAPI spec 端点
    @app.route('/api/openapi.json')
    def openapi_spec():
        return {
            "openapi": "3.0.3",
            "info": {"title": "MiroConsumer API", "version": "0.7.0"},
            "servers": [{"url": "/", "description": "Current host"}],
            "paths": _openapi_paths(app),
            "components": _openapi_components(),
        }

    # Swagger UI 文档页
    @app.route('/api/docs')
    def api_docs():
        return '<html><head><title>MiroConsumer API Docs</title></head><body><h1>MiroConsumer API Docs</h1><p>OpenAPI spec: <a href="/api/openapi.json">/api/openapi.json</a></p></body></html>'

    if should_log_startup:
        logger.info("MiroConsumer Backend 启动完成")

    return app

