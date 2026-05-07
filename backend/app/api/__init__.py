"""
API路由模块
"""

import traceback

from flask import Blueprint

from ..config import Config

graph_bp = Blueprint('graph', __name__)
simulation_bp = Blueprint('simulation', __name__)
report_bp = Blueprint('report', __name__)
consumer_bp = Blueprint('consumer', __name__)


def api_error_payload(message: str) -> dict:
    """Build a JSON error payload; include traceback only when Config.DEBUG is true."""
    payload = {"success": False, "error": message}
    if Config.DEBUG:
        payload["traceback"] = traceback.format_exc()
    return payload


from . import graph  # noqa: E402, F401
from . import simulation  # noqa: E402, F401
from . import report  # noqa: E402, F401
from . import consumer  # noqa: E402, F401
