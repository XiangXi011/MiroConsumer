from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _source(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_simulation_security_sensitive_routes_require_permissions():
    source = _source("app/api/simulation.py")
    for snippet in [
        "@simulation_bp.route('/prepare', methods=['POST'])\n@require_permission('simulation.run')",
        "@simulation_bp.route('/prepare/status', methods=['POST'])\n@require_permission('simulation.read')",
        "@simulation_bp.route('/<simulation_id>', methods=['GET'])\n@require_permission('simulation.read')",
        "@simulation_bp.route('/list', methods=['GET'])\n@require_permission('simulation.read')",
        "@simulation_bp.route('/history', methods=['GET'])\n@require_permission('simulation.read')",
        "@simulation_bp.route('/<simulation_id>/export', methods=['GET'])\n@require_permission('report.export')",
        "@simulation_bp.route('/start', methods=['POST'])\n@require_permission('simulation.run')",
        "@simulation_bp.route('/stop', methods=['POST'])\n@require_permission('simulation.run')",
    ]:
        assert snippet in source


def test_report_and_project_routes_require_expected_permissions():
    report_source = _source("app/api/report.py")
    graph_source = _source("app/api/graph.py")

    assert "@report_bp.route('/generate', methods=['POST'])\n@require_permission('report.generate')" in report_source
    assert "@report_bp.route('/generate/status', methods=['POST'])\n@require_permission('report.read')" in report_source
    assert "@report_bp.route('/list', methods=['GET'])\n@require_permission('report.read')" in report_source
    assert "@graph_bp.route('/project/list', methods=['GET'])\n@require_permission('project.read')" in graph_source
    assert "@graph_bp.route('/ontology/generate', methods=['POST'])\n@require_permission('project.write')" in graph_source
