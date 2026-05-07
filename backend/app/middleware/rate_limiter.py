import time
from collections import defaultdict
from functools import wraps

from flask import request, jsonify, current_app


_request_timestamps = defaultdict(list)


def rate_limit(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_app.config.get('RATE_LIMIT_ENABLED', False):
            return f(*args, **kwargs)

        ip = request.remote_addr or 'unknown'
        now = time.time()
        window_start = now - 60

        _request_timestamps[ip] = [
            ts for ts in _request_timestamps[ip] if ts > window_start
        ]

        limit = current_app.config.get('RATE_LIMIT_PER_MINUTE', 60)
        if len(_request_timestamps[ip]) >= limit:
            return jsonify({'error': 'Rate limit exceeded'}), 429

        _request_timestamps[ip].append(now)
        return f(*args, **kwargs)

    return decorated
