"""President Lobster API routes."""

from flask import g, jsonify, request

from . import api_error_payload, openclaw_bp
from ..auth.middleware import require_permission
from ..auth.tenant_guard import TenantAccessDenied, TenantGuard
from ..services.application.openclaw_orchestrator import (
    OpenClawOrchestrator,
    OpenClawProjectTaskMismatch,
    _resolve_project_status_target,
)
from ..services.application.openclaw_session_store import OpenClawSessionStore
from ..utils.request_validator import safe_get_json

_session_store = OpenClawSessionStore()
_search_provider = None


def _orchestrator():
    return OpenClawOrchestrator(
        store=_session_store, search_provider=_search_provider
    )


def _session_response(session):
    return jsonify({"success": True, "data": session.to_dict()})


def _error_response(message, status_code):
    return jsonify(api_error_payload(str(message))), status_code


def _request_owner_context():
    current_user = getattr(g, "current_user", None)
    user_id = str(getattr(current_user, "user_id", "") or "").strip()
    tenant_id = (
        getattr(current_user, "tenant_id", None)
        or getattr(g, "current_tenant", None)
        or ""
    )
    return user_id, str(tenant_id or "").strip()


def _assert_session_access(session):
    TenantGuard.require_same_tenant(
        getattr(session, "tenant_id", None),
        getattr(g, "current_user", None),
        target_type="openclaw_session",
        target_id=getattr(session, "research_session_id", None),
    )


def _get_authorized_session(research_session_id):
    session = _orchestrator().get_session(research_session_id)
    _assert_session_access(session)
    return session


def _assert_project_status_access(project_id, task_id):
    from ..models.project import ProjectManager

    current_user = getattr(g, "current_user", None)
    if project_id:
        project = ProjectManager.get_project(project_id)
        if project is not None:
            TenantGuard.assert_project_access(project, current_user)

    try:
        project, _ = _resolve_project_status_target(project_id, task_id)
    except OpenClawProjectTaskMismatch as exc:
        TenantGuard.assert_project_access(
            exc.task_project,
            current_user,
        )
        raise KeyError(str(exc)) from exc
    TenantGuard.assert_project_access(
        project,
        current_user,
    )


@openclaw_bp.route("/sessions", methods=["POST"])
@require_permission("project.write")
def create_session():
    data = safe_get_json()
    if isinstance(data, tuple):
        return data

    user_goal = str(data.get("user_goal", "")).strip()
    if not user_goal:
        return _error_response("user_goal is required", 400)

    user_id, tenant_id = _request_owner_context()
    session = _orchestrator().create_session(
        user_goal,
        user_id=user_id,
        tenant_id=tenant_id,
    )
    return _session_response(session)


@openclaw_bp.route("/sessions", methods=["GET"])
@require_permission("project.read")
def list_sessions():
    limit = request.args.get("limit", 10)
    user_id, tenant_id = _request_owner_context()
    sessions = _orchestrator().list_recent_sessions(
        limit=limit,
        user_id=user_id or None,
        tenant_id=tenant_id or None,
    )
    return jsonify({"success": True, "data": {"sessions": sessions}})


@openclaw_bp.route("/sessions/<research_session_id>", methods=["GET"])
@require_permission("project.read")
def get_session(research_session_id):
    try:
        session = _get_authorized_session(research_session_id)
    except KeyError as exc:
        return _error_response(exc, 404)
    except TenantAccessDenied as exc:
        return _error_response(exc, 403)
    return _session_response(session)


@openclaw_bp.route("/sessions/<research_session_id>/workspace", methods=["GET"])
@require_permission("project.read")
def get_session_workspace(research_session_id):
    try:
        _get_authorized_session(research_session_id)
        data = _orchestrator().get_workspace_snapshot(research_session_id)
    except KeyError as exc:
        return _error_response(exc, 404)
    except TenantAccessDenied as exc:
        return _error_response(exc, 403)
    return jsonify({"success": True, "data": data})


@openclaw_bp.route("/sessions/<research_session_id>/explain", methods=["GET"])
@require_permission("project.read")
def explain_session(research_session_id):
    try:
        _get_authorized_session(research_session_id)
        data = _orchestrator().explain_session_status(research_session_id)
    except KeyError as exc:
        return _error_response(exc, 404)
    except TenantAccessDenied as exc:
        return _error_response(exc, 403)
    return jsonify({"success": True, "data": data})


@openclaw_bp.route("/sessions/<research_session_id>/confirm", methods=["POST"])
@require_permission("project.write")
def confirm_action(research_session_id):
    data = safe_get_json()
    if isinstance(data, tuple):
        return data

    action_type = str(data.get("action_type", "")).strip()
    if not action_type:
        return _error_response("action_type is required", 400)

    try:
        _get_authorized_session(research_session_id)
        session = _orchestrator().confirm_action(
            research_session_id,
            action_type=action_type,
            payload=data.get("payload"),
        )
    except KeyError as exc:
        return _error_response(exc, 404)
    except TenantAccessDenied as exc:
        return _error_response(exc, 403)
    except ValueError as exc:
        return _error_response(exc, 400)
    except PermissionError as exc:
        return _error_response(exc, 403)
    return _session_response(session)


@openclaw_bp.route("/sessions/<research_session_id>/explore", methods=["POST"])
@require_permission("project.write")
def explore_session(research_session_id):
    data = safe_get_json(required=False)
    if isinstance(data, tuple):
        return data
    if not isinstance(data, dict):
        return _error_response("request body must be a JSON object", 400)
    strategy = str(data.get("strategy") or "retry_refined").strip() or "retry_refined"
    try:
        _get_authorized_session(research_session_id)
        session = _orchestrator().execute_external_exploration(
            research_session_id,
            strategy=strategy,
        )
    except KeyError as exc:
        return _error_response(exc, 404)
    except TenantAccessDenied as exc:
        return _error_response(exc, 403)
    except ValueError as exc:
        return _error_response(exc, 400)
    except PermissionError as exc:
        return _error_response(exc, 403)
    except Exception:
        return _error_response("external exploration failed", 500)
    return _session_response(session)


@openclaw_bp.route("/sessions/<research_session_id>/brief", methods=["POST"])
@require_permission("project.write")
def prepare_brief(research_session_id):
    try:
        _get_authorized_session(research_session_id)
        session = _orchestrator().prepare_consumer_brief(research_session_id)
    except KeyError as exc:
        return _error_response(exc, 404)
    except TenantAccessDenied as exc:
        return _error_response(exc, 403)
    except PermissionError as exc:
        return _error_response(exc, 403)
    except Exception:
        return _error_response("brief preparation failed", 500)
    return _session_response(session)


@openclaw_bp.route("/sessions/<research_session_id>/project", methods=["POST"])
@require_permission("project.write")
def start_project(research_session_id):
    try:
        _get_authorized_session(research_session_id)
        session = _orchestrator().start_project(research_session_id, background=True)
    except KeyError as exc:
        return _error_response(exc, 404)
    except TenantAccessDenied as exc:
        return _error_response(exc, 403)
    except PermissionError as exc:
        return _error_response(exc, 403)
    except NotImplementedError:
        return _error_response("project start is not available yet", 501)
    except Exception:
        return _error_response("project start failed", 500)
    return _session_response(session)


@openclaw_bp.route("/status/explain", methods=["GET"])
@require_permission("project.read")
def explain_status():
    project_id = str(request.args.get("project_id", "")).strip()
    task_id = str(request.args.get("task_id", "")).strip()
    if not project_id and not task_id:
        return _error_response("project_id or task_id is required", 400)

    try:
        _assert_project_status_access(project_id or None, task_id or None)
        data = _orchestrator().explain_project_status(
            project_id=project_id or None,
            task_id=task_id or None,
        )
    except KeyError as exc:
        return _error_response(exc, 404)
    except TenantAccessDenied as exc:
        return _error_response(exc, 403)
    return jsonify({"success": True, "data": data})
