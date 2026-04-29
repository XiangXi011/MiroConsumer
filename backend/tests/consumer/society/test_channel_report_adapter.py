from app.services.consumer.society.channel_report_adapter import (
    EMPTY_CHANNEL_CONTEXT,
    ChannelReportAdapter,
)
from app.services.consumer.society.state_store import SocietyStateStore


def test_channel_report_adapter_returns_empty_context_without_files(tmp_path):
    context = ChannelReportAdapter(base_dir=tmp_path).build_report_context("sim-missing")

    assert context == EMPTY_CHANNEL_CONTEXT


def test_channel_report_adapter_builds_all_required_context_fields(tmp_path):
    store = SocietyStateStore(base_dir=tmp_path)
    store.write_channel_metrics(
        "sim-channel",
        {
            "channels": {
                "xiaohongshu": {
                    "fit_score": 0.72,
                    "misread_risk": 0.1,
                    "evidence_demand": 0.2,
                    "price_resistance": 0.3,
                },
                "douyin": {
                    "fit_score": 0.42,
                    "misread_risk": 0.6,
                    "evidence_demand": 0.1,
                    "price_resistance": 0.2,
                },
            },
            "cross_channel_spread": 0.25,
            "best_launch_channel": "xiaohongshu",
            "highest_misread_channel": "douyin",
            "highest_evidence_demand_channel": "xiaohongshu",
            "highest_price_resistance_channel": "xiaohongshu",
        },
    )
    store.write_channel_events(
        "sim-channel",
        [
            {
                "event_id": "e1",
                "consumer_event_type": "MISREAD_CLAIM",
                "channel_id": "douyin",
                "round_index": 1,
                "actor_id": "agent-1",
                "quote": "quote",
                "strength": 0.8,
                "cross_channel": False,
                "source_channel_id": "",
                "target_channel_id": "",
            }
        ],
    )
    store.write_propagation_paths(
        "sim-channel",
        [
            {
                "source_channel_id": "douyin",
                "target_channel_id": "wechat_group",
                "trigger_metric": "negative_cascade_probability",
            }
        ],
    )

    context = ChannelReportAdapter(base_dir=tmp_path).build_report_context("sim-channel")

    assert set(EMPTY_CHANNEL_CONTEXT).issubset(context)
    assert context["channel_fit_scores"]["xiaohongshu"] == 0.72
    assert context["channel_misread_summary"]["douyin"] == 0.6
    assert context["channel_evidence_summary"]["xiaohongshu"] == 0.2
    assert context["channel_price_summary"]["xiaohongshu"] == 0.3
    assert context["cross_channel_paths"][0]["source_channel_id"] == "douyin"
