import time
from collections import defaultdict
from functools import wraps

from flask import request, jsonify, current_app, g


_rate_limit_store = defaultdict(list)


def rate_limit(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_app.config.get('RATE_LIMIT_ENABLED', False):
            return f(*args, **kwargs)

        now = time.time()
        minute_ago = now - 60
        max_requests = current_app.config.get('RATE_LIMIT_PER_MINUTE', 60)

        # 三层 key
        ip = request.remote_addr or 'unknown'
        user_id = getattr(g, 'current_user', None)
        user_id = user_id.user_id if user_id else 'anon'
        tenant_id = getattr(g, 'current_tenant', 'default') or 'default'

        keys = [f"ip:{ip}", f"user:{user_id}", f"tenant:{tenant_id}"]

        for key in keys:
            _rate_limit_store[key] = [ts for ts in _rate_limit_store[key] if ts > minute_ago]
            if len(_rate_limit_store[key]) >= max_requests:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {max_requests} requests per minute',
                    'limit_type': key.split(':')[0]
                }), 429

        for key in keys:
            _rate_limit_store[key].append(now)

        return f(*args, **kwargs)
    return decorated


_export_rate_limit_store = defaultdict(list)


def export_rate_limit(f):
    """导出接口专用限流（每分钟10次）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_app.config.get('RATE_LIMIT_ENABLED', False):
            return f(*args, **kwargs)

        now = time.time()
        minute_ago = now - 60
        ip = request.remote_addr or 'unknown'
        key = f"export:{ip}"

        _export_rate_limit_store[key] = [ts for ts in _export_rate_limit_store[key] if ts > minute_ago]
        if len(_export_rate_limit_store[key]) >= 10:
            return jsonify({'error': 'Export rate limit exceeded', 'message': 'Maximum 10 exports per minute'}), 429

        _export_rate_limit_store[key].append(now)
        return f(*args, **kwargs)
    return decorated
