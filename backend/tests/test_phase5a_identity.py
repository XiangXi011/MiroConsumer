"""
Phase 5A Identity Regression Tests
Verifies active-product branding cleanup: graph_id prefix, config defaults, logger namespaces.
"""

from pathlib import Path
import sys
import inspect

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# 1. Graph ID prefix
# ---------------------------------------------------------------------------

def test_graph_builder_uses_miroconsumer_prefix():
    from app.services.graph_builder import GraphBuilderService

    builder = GraphBuilderService()
    builder.client = MagicMock()
    builder.client.graph.create = MagicMock()

    graph_id = builder.create_graph(name="Test Graph")

    assert graph_id.startswith("miroconsumer_"), f"Expected miroconsumer_ prefix, got {graph_id}"
    assert len(graph_id) == len("miroconsumer_") + 16  # prefix + 16 hex chars

    builder.client.graph.create.assert_called_once()
    call_kwargs = builder.client.graph.create.call_args.kwargs
    assert call_kwargs["graph_id"] == graph_id
    assert "MiroConsumer" in call_kwargs["description"]


# ---------------------------------------------------------------------------
# 2. Config default SECRET_KEY
# ---------------------------------------------------------------------------

def test_config_secret_key_empty_by_default():
    from app.config import Config

    source = inspect.getsource(Config)
    assert "os.environ.get('SECRET_KEY', '')" in source
    assert "mirofish-secret-key" not in source


def test_config_requires_secret_key_in_production(monkeypatch):
    from app.config import Config

    monkeypatch.setattr(Config, "DEBUG", False)
    monkeypatch.setattr(Config, "SECRET_KEY", "")
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep")
    monkeypatch.setattr(Config, "_db_url_cache", "", raising=False)
    monkeypatch.setattr(Config, "_queue_backend_cache", "thread", raising=False)
    monkeypatch.setattr(Config, "_storage_backend_cache", "local", raising=False)

    assert "SECRET_KEY is required in production" in Config.validate()


def test_api_error_payload_hides_traceback_outside_debug(monkeypatch):
    from app.config import Config
    from app.api import api_error_payload

    monkeypatch.setattr(Config, "DEBUG", False)
    try:
        raise RuntimeError("hidden")
    except RuntimeError:
        payload = api_error_payload("hidden")

    assert payload == {"success": False, "error": "hidden"}


def test_api_error_payload_includes_traceback_in_debug(monkeypatch):
    from app.config import Config
    from app.api import api_error_payload

    monkeypatch.setattr(Config, "DEBUG", True)
    try:
        raise RuntimeError("visible")
    except RuntimeError:
        payload = api_error_payload("visible")

    assert payload["success"] is False
    assert payload["error"] == "visible"
    assert "RuntimeError: visible" in payload["traceback"]


# ---------------------------------------------------------------------------
# 3. Logger namespaces
# ---------------------------------------------------------------------------

LOGGER_MODULE_MAP = {
    "app.services.simulation_manager": "miroconsumer.simulation",
    "app.services.simulation_runner": "miroconsumer.simulation_runner",
    "app.services.simulation_ipc": "miroconsumer.simulation_ipc",
    "app.services.zep_tools": "miroconsumer.zep_tools",
    "app.services.zep_entity_reader": "miroconsumer.zep_entity_reader",
    "app.services.zep_graph_memory_updater": "miroconsumer.zep_graph_memory_updater",
    "app.services.oasis_profile_generator": "miroconsumer.oasis_profile",
    "app.services.simulation_config_generator": "miroconsumer.simulation_config",
    "app.services.report_agent": "miroconsumer.report_agent",
    "app.utils.zep_paging": "miroconsumer.zep_paging",
    "app.utils.retry": "miroconsumer.retry",
}


def test_all_service_loggers_use_miroconsumer_namespace():
    import importlib

    failures = []
    for module_name, expected_namespace in LOGGER_MODULE_MAP.items():
        try:
            mod = importlib.import_module(module_name)
        except Exception as exc:
            failures.append(f"{module_name}: import error ({exc})")
            continue

        logger = getattr(mod, "logger", None)
        if logger is None:
            failures.append(f"{module_name}: no 'logger' attribute")
            continue

        actual_name = logger.name if hasattr(logger, "name") else str(logger)
        if actual_name != expected_namespace:
            failures.append(
                f"{module_name}: expected '{expected_namespace}', got '{actual_name}'"
            )

    if failures:
        raise AssertionError("Logger namespace mismatch:\n" + "\n".join(failures))


def test_app_request_loggers_use_miroconsumer_namespace():
    """app/__init__.py creates loggers inside before_request / after_request."""
    import app

    source = inspect.getsource(app)
    assert "get_logger('miroconsumer.request')" in source
    assert "get_logger('mirofish.request')" not in source


def test_report_logger_attaches_miroconsumer_loggers():
    from app.services import report_agent

    source = inspect.getsource(report_agent)
    assert "'miroconsumer.report_agent'" in source
    assert "'miroconsumer.zep_tools'" in source
    assert "'mirofish.report_agent'" not in source
    assert "'mirofish.zep_tools'" not in source


def test_no_mirofish_logger_namespaces_in_service_code():
    """Source-level check: no 'mirofish.' should remain in active service/util modules."""
    import importlib

    modules_to_check = list(LOGGER_MODULE_MAP.keys()) + ["app"]
    for module_name in modules_to_check:
        mod = importlib.import_module(module_name)
        try:
            source = inspect.getsource(mod)
        except (TypeError, OSError):
            continue
        assert "mirofish." not in source, f"{module_name} still contains 'mirofish.'"


# ---------------------------------------------------------------------------
# 4. Active product docs must not contain "MiroFish" branding residues
# ---------------------------------------------------------------------------

ACTIVE_DOC_PATHS = [
    BACKEND_ROOT.parent / "PRD.md",
    BACKEND_ROOT.parent / "README.md",
    BACKEND_ROOT.parent / "README-ZH.md",
    BACKEND_ROOT / "app" / "config.py",
]


def test_active_product_docs_do_not_contain_mirofish():
    """
    PRD.md, README.md, README-ZH.md and backend/app/config.py are active product
    documents / runtime-facing files.  They must not contain 'MiroFish'.
    (Archival docs under docs/superpowers are allowed to keep historical wording.)
    """
    failures = []
    for path in ACTIVE_DOC_PATHS:
        text = path.read_text(encoding="utf-8")
        if "MiroFish" in text:
            # Report every offending line so the fix is easy to locate
            for i, line in enumerate(text.splitlines(), start=1):
                if "MiroFish" in line:
                    failures.append(f"{path}:{i}: {line.strip()}")
    if failures:
        raise AssertionError(
            "'MiroFish' found in active product docs/runtime files:\n"
            + "\n".join(failures)
        )


# ---------------------------------------------------------------------------
# 5. Backend source files must not contain "MiroFish" product references
# ---------------------------------------------------------------------------

ALLOWED_MiroFish_PATHS = {
    # Archival / historical docs are exempt
    "docs/superpowers",
    # Test file may mention the old name in assertions or comments
    "tests/test_phase5a_identity.py",
    # Phase7G explicitly reintroduces native profile capability naming while
    # keeping the consumer runtime/product identity separate.
    "app/services/consumer/society/mirofish_profile_adapter.py",
    "app/services/consumer/society/profile_generator.py",
    "tests/consumer/society/test_consumer_profile_generator.py",
    "tests/consumer/society/test_mirofish_profile_adapter.py",
}

SKIPPED_SOURCE_SCAN_PARTS = {
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
}


def test_backend_source_files_do_not_contain_mirofish():
    """
    Any .py file under backend/ (outside tests and exempt paths) must not
    contain the string 'MiroFish'.  This catches comment residues, string
    literals, docstrings and hidden defaults that earlier narrowly-scoped
    tests missed.
    """
    failures = []
    backend_dir = BACKEND_ROOT
    for py_path in backend_dir.rglob("*.py"):
        # Skip exempt paths
        rel = py_path.relative_to(backend_dir).as_posix()
        if any(part in SKIPPED_SOURCE_SCAN_PARTS for part in py_path.relative_to(backend_dir).parts):
            continue
        if any(exempt in rel for exempt in ALLOWED_MiroFish_PATHS):
            continue
        text = py_path.read_text(encoding="utf-8")
        if "MiroFish" in text:
            for i, line in enumerate(text.splitlines(), start=1):
                if "MiroFish" in line:
                    failures.append(f"{py_path}:{i}: {line.strip()}")
    if failures:
        raise AssertionError(
            "'MiroFish' found in backend source files:\n" + "\n".join(failures)
        )
