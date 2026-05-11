"""项目版本管理"""

__version__ = "0.7.0"
__phase__ = "Phase 7 - Productionization"


def get_version_info():
    return {
        "version": __version__,
        "phase": __phase__,
        "api_version": "v1",
    }
