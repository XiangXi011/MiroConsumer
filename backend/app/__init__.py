"""
MiroConsumer Backend - Flask应用工厂
"""

import os
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
        # 安全响应头
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
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
            "paths": {
                "/health": {"get": {"summary": "Health check", "responses": {"200": {"description": "OK"}}}},
                "/api/auth/register": {"post": {"summary": "Register user", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"username": {"type": "string"}, "email": {"type": "string"}, "role": {"type": "string"}}}}}}, "responses": {"201": {"description": "Created"}}}},
                "/api/auth/login": {"post": {"summary": "Login", "responses": {"200": {"description": "Token returned"}}}},
                "/api/auth/me": {"get": {"summary": "Current user info", "responses": {"200": {"description": "User info"}}}},
                "/api/v1/consumer/simulation/{simulation_id}/consumer-summary": {"get": {"summary": "Consumer propagation summary", "parameters": [{"name": "simulation_id", "in": "path", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "Summary data"}}}},
                "/api/v1/consumer/simulations/{simulation_id}/channel-summary": {"get": {"summary": "Channel metrics summary", "responses": {"200": {"description": "Channel data"}}}},
                "/api/v1/consumer/simulations/{simulation_id}/branches": {"get": {"summary": "List branches", "responses": {"200": {"description": "Branch list"}}, "post": {"summary": "Create branch", "responses": {"201": {"description": "Branch created"}}}}},
                "/api/v1/consumer/simulations/{simulation_id}/interventions": {"get": {"summary": "List interventions", "responses": {"200": {"description": "Intervention list"}}}},
                "/api/v1/consumer/comparisons": {"get": {"summary": "List comparisons", "responses": {"200": {"description": "Comparison list"}}, "post": {"summary": "Create comparison", "responses": {"201": {"description": "Comparison created"}}}}},
                "/api/v1/consumer/research-assets": {"get": {"summary": "List research assets", "responses": {"200": {"description": "Asset list"}}}},
                "/api/v1/consumer/simulations/{simulation_id}/interviews": {"post": {"summary": "Run consumer interview", "responses": {"200": {"description": "Interview result"}}}},
                "/api/v1/consumer/simulations/{simulation_id}/focus-groups": {"post": {"summary": "Run focus group", "responses": {"200": {"description": "Focus group result"}}}},
                "/api/v1/report/generate": {"post": {"summary": "Generate report", "responses": {"200": {"description": "Task ID returned"}}}},
                "/api/v1/simulation/entities/{graph_id}": {"get": {"summary": "Get graph entities", "responses": {"200": {"description": "Entity list"}}}},
                "/api/v1/graph/projects": {"get": {"summary": "List projects", "responses": {"200": {"description": "Project list"}}}}
            }
        }

    # Swagger UI 文档页
    @app.route('/api/docs')
    def api_docs():
        return '<html><head><title>MiroConsumer API Docs</title></head><body><h1>MiroConsumer API Docs</h1><p>OpenAPI spec: <a href="/api/openapi.json">/api/openapi.json</a></p></body></html>'

    if should_log_startup:
        logger.info("MiroConsumer Backend 启动完成")

    return app

