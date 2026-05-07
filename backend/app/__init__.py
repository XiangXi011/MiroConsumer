"""
MiroConsumer Backend - Flask应用工厂
"""

import os
import warnings

# 抑制 multiprocessing resource_tracker 的警告（来自第三方库如 transformers）
# 需要在所有其他导入之前设置
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # SECRET_KEY 校验（非 DEBUG 模式必须配置）
    if not app.debug and not app.config.get('SECRET_KEY'):
        raise RuntimeError('SECRET_KEY is required in production. Set SECRET_KEY in .env')
    
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
    
    # 注册模拟进程清理函数（确保服务器关闭时终止所有模拟进程）
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("已注册模拟进程清理函数")
    
    # 请求日志中间件
    @app.before_request
    def log_request():
        logger = get_logger('miroconsumer.request')
        logger.debug(f"请求: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"请求体: {request.get_json(silent=True)}")
    
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
        return response
    
    # 注册蓝图
    from .api import graph_bp, simulation_bp, report_bp, consumer_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    app.register_blueprint(consumer_bp, url_prefix='/api/consumer')
    
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
            "paths": {}
        }

    # Swagger UI 文档页
    @app.route('/api/docs')
    def api_docs():
        return '<html><head><title>MiroConsumer API Docs</title></head><body><h1>MiroConsumer API Docs</h1><p>OpenAPI spec: <a href="/api/openapi.json">/api/openapi.json</a></p></body></html>'

    if should_log_startup:
        logger.info("MiroConsumer Backend 启动完成")

    return app

