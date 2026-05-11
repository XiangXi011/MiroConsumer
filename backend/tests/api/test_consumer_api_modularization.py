from pathlib import Path


EXPECTED_CONSUMER_ROUTE_MODULES = {
    "consumer_summary.py",
    "consumer_branches.py",
    "consumer_comparisons.py",
    "consumer_assets.py",
    "consumer_research.py",
    "consumer_operations.py",
}


def test_consumer_api_routes_are_split_into_package_local_modules():
    api_dir = Path(__file__).parents[2] / "app" / "api"
    consumer_module = api_dir / "consumer.py"

    module_names = {path.name for path in api_dir.glob("consumer_*.py")}
    assert EXPECTED_CONSUMER_ROUTE_MODULES.issubset(module_names)

    source = consumer_module.read_text(encoding="utf-8")
    assert "@consumer_bp.route" not in source
    assert len(source.splitlines()) <= 120


def test_consumer_api_split_keeps_registered_routes():
    from flask import Flask

    from app.api import consumer_bp

    app = Flask(__name__)
    app.register_blueprint(consumer_bp, url_prefix="/api/consumer")

    rules = {
        (rule.rule.removeprefix("/api/consumer"), tuple(sorted(rule.methods - {"HEAD", "OPTIONS"})))
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/consumer/")
    }

    expected_rules = {
        ("/simulation/<simulation_id>/consumer-summary", ("GET",)),
        ("/simulations/<simulation_id>/channel-summary", ("GET",)),
        ("/simulations/<simulation_id>/branches", ("GET",)),
        ("/simulations/<simulation_id>/branches", ("POST",)),
        ("/simulations/<simulation_id>/branches/<branch_id>/interventions", ("GET",)),
        ("/simulations/<simulation_id>/branches/<branch_id>/interventions", ("POST",)),
        ("/comparisons", ("GET",)),
        ("/comparisons", ("POST",)),
        ("/research-assets/export", ("POST",)),
        ("/simulations/<simulation_id>/research-actions", ("POST",)),
        ("/simulations/<simulation_id>/interviews", ("POST",)),
        ("/task-queue/dead-letters", ("GET",)),
        ("/personas/export", ("POST",)),
        ("/personas/import", ("POST",)),
    }

    assert expected_rules.issubset(rules)
