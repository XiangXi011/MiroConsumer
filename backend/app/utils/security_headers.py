"""Security response header helpers."""

DEFAULT_CSP_DIRECTIVES = (
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "upgrade-insecure-requests",
)


def build_content_security_policy(config_class) -> str:
    """Return the configured CSP policy or the strict default."""
    configured_policy = getattr(config_class, "CSP_POLICY", "")
    if configured_policy:
        return configured_policy
    return "; ".join(DEFAULT_CSP_DIRECTIVES)


def apply_security_headers(response, config_class):
    """Apply standard security headers to a Flask response."""
    if not getattr(config_class, "SECURITY_HEADERS_ENABLED", True):
        return response

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = build_content_security_policy(config_class)
    return response
