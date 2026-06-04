from types import SimpleNamespace

from app.models.project import ProjectStatus
from app.services.application import graph_app_service as graph_module
from app.services.application.graph_app_service import _build_consumer_graph
from app.services.consumer.models import GraphVisibility, ResearchFinding


class _Repo:
    def __init__(self):
        self.graph_payloads = {}
        self.saved_projects = []

    def save_consumer_graph_payload(self, project_id, graph_payload):
        self.graph_payloads[project_id] = graph_payload

    def save_project(self, project):
        self.saved_projects.append(project)


def test_openclaw_source_evidence_skips_second_live_research_pass(monkeypatch, tmp_path):
    """OpenClaw projects already have explored evidence; graph build should not search again."""
    monkeypatch.setattr(graph_module.Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))

    def fail_if_live_lane_b_is_built(*_args, **_kwargs):
        raise AssertionError("live Lane B provider should not be built for OpenClaw evidence")

    monkeypatch.setattr(graph_module, "build_lane_b_provider", fail_if_live_lane_b_is_built)

    captured = {}
    finding = ResearchFinding(
        finding_id="f_evidence",
        finding_type="category_context",
        summary="Parents need safety proof before buying.",
        evidence_snippets=["Safety proof matters for children's toothpaste."],
        source_label="ingested_document",
        visibility=GraphVisibility.Initial,
        confidence=0.8,
    )

    def fake_resolve(brief, **kwargs):
        captured["resolve"] = kwargs
        return [finding]

    def fake_snapshot(project_id, **kwargs):
        captured["snapshot"] = kwargs
        return SimpleNamespace(
            snapshot_id="snap_1",
            sources=[],
            documents=[],
            chunks=[],
            findings=[finding],
            retrieval_traces=[],
        )

    class _Registry:
        def resolve_selection(self, _selection):
            return []

        def get_pack(self, _pack_id):
            return None

    class _Builder:
        def build(self, **kwargs):
            captured["builder"] = kwargs
            return {"graph_id": "consumer_proj_openclaw", "node_count": 1, "edge_count": 0}

    monkeypatch.setattr(graph_module, "resolve_research_findings", fake_resolve)
    monkeypatch.setattr(graph_module, "build_research_snapshot", fake_snapshot)
    monkeypatch.setattr(graph_module, "persist_findings", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(graph_module, "persist_snapshot", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(graph_module, "build_source_quality_summary", lambda _sources: {"status": "sufficient"})
    monkeypatch.setattr(graph_module, "get_registry", lambda **_kwargs: _Registry())
    monkeypatch.setattr(graph_module, "ConsumerGraphBuilder", _Builder)

    project = SimpleNamespace(
        project_id="proj_openclaw_evidence",
        consumer_brief={
            "task_type": "concept_test",
            "product_concept_assets": ["舒客宝贝魔法变色牙膏"],
            "claims": ["魔法变色提升刷牙兴趣"],
            "target_audience": ["3-8岁儿童家长"],
            "research_goal": "验证安全感和购买转化",
            "research_mode": "auto_enrich",
            "enable_lane_b": True,
            "source_evidence_spans": [
                {
                    "title": "Parent safety discussion",
                    "url": "https://example.com/safety",
                    "snippet": "外部探索证据片段",
                    "evidence_type": "consumer_discussion",
                    "confidence": 0.8,
                    "query": "儿童牙膏 家长 安全",
                }
            ],
        },
        status=ProjectStatus.ONTOLOGY_GENERATED,
        graph_id=None,
        consumer_context=None,
    )
    repo = _Repo()

    graph = _build_consumer_graph(project, "OpenClaw explored evidence", repo)

    assert graph["graph_id"] == "consumer_proj_openclaw"
    assert captured["resolve"]["provider"] is None
    assert captured["resolve"]["enable_lane_b"] is False
    assert captured["resolve"]["lane_b_provider"] is None
    assert captured["snapshot"]["provider"] is None
    assert captured["snapshot"]["enable_lane_b"] is False
    assert captured["builder"]["research_findings"] == [finding]
    assert project.status == ProjectStatus.GRAPH_COMPLETED
    assert project.consumer_context["enable_lane_b"] is True
    assert project.consumer_context["live_lane_b_used"] is False
    assert project.consumer_context["source_evidence_span_count"] == 1
