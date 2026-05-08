"""
Consumer bounded-context API route registrar.

Owns consumer-specific endpoint registration. Concrete route handlers live in
package-local consumer_* modules so each module has a focused responsibility.
"""

from . import consumer_assets  # noqa: F401
from . import consumer_branches  # noqa: F401
from . import consumer_comparisons  # noqa: F401
from . import consumer_operations  # noqa: F401
from . import consumer_research  # noqa: F401
from . import consumer_summary  # noqa: F401
from ..services.application.consumer_app_service import ConsumerAppService
from ..services.application.consumer_research_action_service import (
    ConsumerResearchActionService,
)

__all__ = [
    "ConsumerAppService",
    "ConsumerResearchActionService",
]
