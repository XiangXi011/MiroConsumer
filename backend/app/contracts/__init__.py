"""Shared contract exports for API, domain, and error payload schemas.

This package is the boundary where Flask route handlers, application services,
and consumer-domain modules exchange typed request/response objects. Keeping the
exports centralized prevents route modules from importing concrete persistence
or runtime implementations when they only need a stable contract type.
"""

from __future__ import annotations
