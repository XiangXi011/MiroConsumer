"""
配置管理
统一从项目根目录的 .env 文件加载配置
"""

import os
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
# 路径: 项目根目录/.env (相对于 backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # 如果根目录没有 .env，尝试加载环境变量（用于生产环境）
    load_dotenv(override=True)


class _ClassProperty:
    """Descriptor that allows property-like access on a class (no instance required)."""

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, obj, cls=None):
        if cls is None:
            cls = type(obj)
        return self.fget(cls)


WEAK_SECRET_KEYS = {'dev-only-change-me', 'dev-secret', 'secret', 'change-me', 'miroconsumer', 'miro-secret-key-change-in-production'}


class Config:
    """Flask配置类"""

    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', '')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:3000')

    # JSON配置 - 禁用ASCII转义，让中文直接显示（而不是 \uXXXX 格式）
    JSON_AS_ASCII = False

    # LLM配置（统一使用OpenAI格式）
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')

    # Zep配置
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')

    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'false').lower() == 'true'
    RATE_LIMIT_PER_MINUTE = int(os.environ.get('RATE_LIMIT_PER_MINUTE', '60'))
    LOG_FORMAT = os.environ.get('LOG_FORMAT', 'json')
    SECURITY_HEADERS_ENABLED = os.environ.get('SECURITY_HEADERS_ENABLED', 'true').lower() == 'true'
    ENABLE_REASONING_TRACE = os.environ.get('ENABLE_REASONING_TRACE', 'true').lower() == 'true'
    SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}

    # 文本处理配置
    DEFAULT_CHUNK_SIZE = 500  # 默认切块大小
    DEFAULT_CHUNK_OVERLAP = 50  # 默认重叠大小

    # OASIS模拟配置
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')

    # OASIS平台可用动作配置
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]

    # Report Agent配置
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    # Lane B public-web search configuration
    ENABLE_LANE_B_WEB_SEARCH = os.environ.get('ENABLE_LANE_B_WEB_SEARCH', 'False').lower() == 'true'
    LANE_B_SEARCH_MODEL = os.environ.get('LANE_B_SEARCH_MODEL', LLM_MODEL_NAME)

    # Queue configuration
    _queue_backend_cache = None
    _redis_url_cache = None
    _queue_retry_limit_cache = None
    _queue_visibility_timeout_cache = None

    # Database configuration caches (for test monkeypatching)
    _db_url_cache = None
    _db_pool_size_cache = None
    _db_max_overflow_cache = None
    _db_statement_timeout_cache = None

    # Phase 7D / 7E operational configuration caches
    _llm_budget_limit_cache = None
    _llm_deep_reasoning_ratio_cache = None
    _max_agents_cache = None
    _max_rounds_cache = None
    _deterministic_fallback_cache = None
    _storage_backend_cache = None
    _s3_endpoint_cache = None
    _s3_bucket_cache = None
    _s3_access_key_cache = None
    _s3_secret_key_cache = None
    _s3_region_cache = None

    @_ClassProperty
    def QUEUE_BACKEND(cls):
        if cls._queue_backend_cache is not None:
            return cls._queue_backend_cache
        return os.environ.get('QUEUE_BACKEND', 'thread')

    @_ClassProperty
    def REDIS_URL(cls):
        if cls._redis_url_cache is not None:
            return cls._redis_url_cache
        return os.environ.get('REDIS_URL', '')

    @_ClassProperty
    def QUEUE_RETRY_LIMIT(cls):
        if cls._queue_retry_limit_cache is not None:
            return cls._queue_retry_limit_cache
        return int(os.environ.get('QUEUE_RETRY_LIMIT', '3'))

    @_ClassProperty
    def QUEUE_VISIBILITY_TIMEOUT_SECONDS(cls):
        if cls._queue_visibility_timeout_cache is not None:
            return cls._queue_visibility_timeout_cache
        return int(os.environ.get('QUEUE_VISIBILITY_TIMEOUT_SECONDS', '900'))

    @_ClassProperty
    def DB_URL(cls):
        if cls._db_url_cache is not None:
            return cls._db_url_cache
        return os.environ.get('DB_URL', '')

    @_ClassProperty
    def DB_POOL_SIZE(cls):
        if cls._db_pool_size_cache is not None:
            return cls._db_pool_size_cache
        return int(os.environ.get('DB_POOL_SIZE', '5'))

    @_ClassProperty
    def DB_MAX_OVERFLOW(cls):
        if cls._db_max_overflow_cache is not None:
            return cls._db_max_overflow_cache
        return int(os.environ.get('DB_MAX_OVERFLOW', '10'))

    @_ClassProperty
    def DB_STATEMENT_TIMEOUT_SECONDS(cls):
        if cls._db_statement_timeout_cache is not None:
            return cls._db_statement_timeout_cache
        return int(os.environ.get('DB_STATEMENT_TIMEOUT_SECONDS', '30'))

    @_ClassProperty
    def LLM_BUDGET_LIMIT(cls):
        if cls._llm_budget_limit_cache is not None:
            return cls._llm_budget_limit_cache
        return int(os.environ.get('LLM_BUDGET_LIMIT', '500'))

    @_ClassProperty
    def LLM_DEEP_REASONING_RATIO(cls):
        if cls._llm_deep_reasoning_ratio_cache is not None:
            return cls._llm_deep_reasoning_ratio_cache
        return float(os.environ.get('LLM_DEEP_REASONING_RATIO', '0.1'))

    @_ClassProperty
    def MAX_AGENTS(cls):
        if cls._max_agents_cache is not None:
            return cls._max_agents_cache
        return int(os.environ.get('MAX_AGENTS', '1000'))

    @_ClassProperty
    def MAX_ROUNDS(cls):
        if cls._max_rounds_cache is not None:
            return cls._max_rounds_cache
        return int(os.environ.get('MAX_ROUNDS', '10'))

    @_ClassProperty
    def ENABLE_DETERMINISTIC_FALLBACK(cls):
        if cls._deterministic_fallback_cache is not None:
            return cls._deterministic_fallback_cache
        return os.environ.get('ENABLE_DETERMINISTIC_FALLBACK', 'true').lower() == 'true'

    @_ClassProperty
    def STORAGE_BACKEND(cls):
        if cls._storage_backend_cache is not None:
            return cls._storage_backend_cache
        return os.environ.get('STORAGE_BACKEND', 'local')

    @_ClassProperty
    def S3_ENDPOINT(cls):
        if cls._s3_endpoint_cache is not None:
            return cls._s3_endpoint_cache
        return os.environ.get('S3_ENDPOINT', '')

    @_ClassProperty
    def S3_BUCKET(cls):
        if cls._s3_bucket_cache is not None:
            return cls._s3_bucket_cache
        return os.environ.get('S3_BUCKET', '')

    @_ClassProperty
    def S3_ACCESS_KEY(cls):
        if cls._s3_access_key_cache is not None:
            return cls._s3_access_key_cache
        return os.environ.get('S3_ACCESS_KEY', '')

    @_ClassProperty
    def S3_SECRET_KEY(cls):
        if cls._s3_secret_key_cache is not None:
            return cls._s3_secret_key_cache
        return os.environ.get('S3_SECRET_KEY', '')

    @_ClassProperty
    def S3_REGION(cls):
        if cls._s3_region_cache is not None:
            return cls._s3_region_cache
        return os.environ.get('S3_REGION', 'us-east-1')

    @classmethod
    def validate(cls):
        """验证必要配置"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY 未配置")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY 未配置")

        db_url = cls.DB_URL
        if db_url:
            valid_schemes = ('sqlite:///', 'postgresql+psycopg://')
            if not any(db_url.startswith(scheme) for scheme in valid_schemes):
                errors.append(f"DB_URL unsupported scheme: {db_url.split('://')[0] if '://' in db_url else db_url}")

        queue_backend = cls.QUEUE_BACKEND
        valid_backends = ('thread', 'sqlite', 'rq')
        if queue_backend not in valid_backends:
            errors.append(f"QUEUE_BACKEND must be one of {valid_backends}, got: {queue_backend}")

        if queue_backend == 'rq' and not cls.REDIS_URL:
            errors.append("REDIS_URL is required when QUEUE_BACKEND=rq")

        if not cls.DEBUG:
            sk = cls.SECRET_KEY
            if not sk:
                errors.append("SECRET_KEY is required in production")
            elif sk in WEAK_SECRET_KEYS:
                errors.append("SECRET_KEY must not use a default/weak value")
            elif len(sk) < 32:
                errors.append(f"SECRET_KEY must be >= 32 bytes, got {len(sk)}")

        storage_backend = cls.STORAGE_BACKEND
        valid_storage_backends = ('local', 's3')
        if storage_backend not in valid_storage_backends:
            errors.append(f"STORAGE_BACKEND must be one of {valid_storage_backends}, got: {storage_backend}")
        if storage_backend == 's3':
            missing = [
                name for name, value in (
                    ('S3_ENDPOINT', cls.S3_ENDPOINT),
                    ('S3_BUCKET', cls.S3_BUCKET),
                    ('S3_ACCESS_KEY', cls.S3_ACCESS_KEY),
                    ('S3_SECRET_KEY', cls.S3_SECRET_KEY),
                )
                if not value
            ]
            if missing:
                errors.append(f"STORAGE_BACKEND=s3 requires: {', '.join(missing)}")

        return errors

