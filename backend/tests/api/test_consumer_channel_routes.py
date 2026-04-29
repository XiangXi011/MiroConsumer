from unittest.mock import patch

from app import create_app
from app.services.consumer.society.state_store import SocietyStateStore
from app.services.simulation_manager import SimulationStatus


def _consumer_state(project_type="consumer_test"):
    return type(
        "State",
        (),
        {
            "status": SimulationStatus.READY,
            "project_id": "p1",
            "graph_id": "g1",
            "project_type": project_type,
            "consumer_mode": project_type == "consumer_test",
        },
    )()


def test_start_simulation_rejects_illegal_consumer_channel_id():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with patch("app.services.application.simulation_app_service.SimulationAppService._simulation_repo") as repo:
            repo.get_simulation.return_value = _consumer_state()
            resp = client.post(
                "/api/simulation/start",
                json={
                    "simulation_id": "sim-channel-bad",
                    "society_mode": "standard",
                    "enabled_channels": ["xiaohongshu", "twitter"],
                },
            )

    assert resp.status_code == 400
    assert "Unsupported channel id" in resp.get_json()["error"]


def test_start_simulation_passes_channel_config_to_runner():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with patch("app.services.application.simulation_app_service.SimulationAppService._simulation_repo") as repo, patch(
            "app.services.application.simulation_app_service.SimulationRunner.start_simulation"
        ) as start:
            repo.get_simulation.return_value = _consumer_state()
            start.return_value.to_dict.return_value = {"simulation_id": "sim-channel-ok", "runner_status": "running"}
            resp = client.post(
                "/api/simulation/start",
                json={
                    "simulation_id": "sim-channel-ok",
                    "society_mode": "standard",
                    "enabled_channels": ["xiaohongshu", "douyin", "wechat_group"],
                    "channel_seed": 99,
                },
            )

    assert resp.status_code == 200
    config = start.call_args.kwargs["society_config"]
    assert config["enabled_channels"] == ["xiaohongshu", "douyin", "wechat_group"]
    assert config["channel_seed"] == 99


def test_channel_summary_events_and_paths_routes_return_store_payload(tmp_path):
    store = SocietyStateStore(base_dir=tmp_path)
    store.write_channel_metrics(
        "sim-channel-api",
        {
            "channels": {"xiaohongshu": {"fit_score": 0.66}},
            "cross_channel_spread": 0.1,
            "best_launch_channel": "xiaohongshu",
            "highest_misread_channel": "douyin",
            "highest_evidence_demand_channel": "zhihu_qa",
            "highest_price_resistance_channel": "ecommerce_review",
        },
    )
    store.write_channel_events(
        "sim-channel-api",
        [
            {
                "event_id": "e1",
                "consumer_event_type": "FIRST_IMPRESSION",
                "channel_id": "xiaohongshu",
                "round_index": 0,
                "actor_id": "agent-1",
                "strength": 0.5,
                "cross_channel": False,
                "source_channel_id": "",
                "target_channel_id": "",
            }
        ],
    )
    store.write_propagation_paths(
        "sim-channel-api",
        [{"source_channel_id": "douyin", "target_channel_id": "wechat_group"}],
    )

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with patch("app.services.application.consumer_app_service.ConsumerAppService._simulation_repo") as repo, patch(
            "app.services.application.consumer_app_service.ChannelReportAdapter"
        ) as adapter_cls, patch(
            "app.services.application.consumer_app_service.SocietyStateStore"
        ) as store_cls:
            repo.get_simulation.return_value = _consumer_state()
            adapter_cls.return_value.build_report_context.return_value = {
                "channel_metrics": store.read_channel_metrics("sim-channel-api"),
                "channel_fit_scores": {"xiaohongshu": 0.66},
                "channel_misread_summary": {},
                "channel_evidence_summary": {},
                "channel_price_summary": {},
                "cross_channel_paths": store.read_propagation_paths("sim-channel-api"),
            }
            store_cls.return_value.read_channel_events.return_value = store.read_channel_events("sim-channel-api")
            store_cls.return_value.read_propagation_paths.return_value = store.read_propagation_paths("sim-channel-api")

            summary = client.get("/api/consumer/simulations/sim-channel-api/channel-summary")
            events = client.get("/api/consumer/simulations/sim-channel-api/channel-events")
            paths = client.get("/api/consumer/simulations/sim-channel-api/propagation-paths")

    assert summary.status_code == 200
    assert summary.get_json()["data"]["channel_fit_scores"]["xiaohongshu"] == 0.66
    assert events.status_code == 200
    assert events.get_json()["data"]["events"][0]["event_id"] == "e1"
    assert paths.status_code == 200
    assert paths.get_json()["data"]["paths"][0]["target_channel_id"] == "wechat_group"
