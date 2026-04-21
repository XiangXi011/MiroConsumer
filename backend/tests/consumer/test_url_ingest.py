from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.consumer.brief_adapter import ConsumerBriefAdapter
from app.services.consumer.document_ingest import DocumentIngestService
from app.services.consumer.models import ResearchSourceLane, ResearchSourceType
from app.services.consumer.source_registry import SourceRegistry
from app.services.consumer.url_ingest import (
    is_url,
    _extract_text_from_html,
    ingest_background_url_sources,
)


def test_is_url_detects_http_and_https():
    assert is_url("http://example.com")
    assert is_url("https://example.com/page")
    assert is_url("  https://example.com  ")
    assert not is_url("Just a plain note")
    assert not is_url("www.example.com")
    assert not is_url("")


def test_extract_text_from_html_strips_tags():
    html = "<html><body><p>Hello world</p><script>alert('x')</script></body></html>"
    text = _extract_text_from_html(html)
    assert "Hello world" in text
    assert "alert" not in text


def test_extract_text_from_html_skips_nav_and_footer():
    html = (
        "<html><nav>Menu</nav><main><p>Article content</p></main>"
        "<footer>Copyright</footer></html>"
    )
    text = _extract_text_from_html(html)
    assert "Article content" in text
    assert "Menu" not in text
    assert "Copyright" not in text


def test_ingest_background_url_sources_registers_lane_a_source(tmp_path):
    root = str(tmp_path / "uploads")
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein bar"],
            "research_goal": "Find signals",
            "optional_background_materials": [
                "Plain note",
                "https://example.com/article",
            ],
        }
    )

    def fake_fetch(url):
        return "This is the article content."

    ingested, skipped = ingest_background_url_sources(
        "proj_url_1",
        brief,
        upload_root=root,
        fetch_fn=fake_fetch,
    )

    assert ingested == ["https://example.com/article"]
    assert skipped == []

    registry = SourceRegistry("proj_url_1", upload_root=root)
    sources = registry.list_sources(lane=ResearchSourceLane.LaneA)
    assert len(sources) == 1
    assert sources[0].source_type == ResearchSourceType.Url
    assert sources[0].uri == "https://example.com/article"

    ingest = DocumentIngestService("proj_url_1", upload_root=root)
    docs = ingest.list_documents(source_id=sources[0].source_id)
    assert len(docs) == 1
    assert docs[0].raw_text == "This is the article content."


def test_ingest_background_url_sources_skips_failed_fetches(tmp_path):
    root = str(tmp_path / "uploads")
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein bar"],
            "research_goal": "Find signals",
            "optional_background_materials": [
                "https://example.com/good",
                "https://example.com/bad",
            ],
        }
    )

    def fake_fetch(url):
        if "bad" in url:
            raise RuntimeError("Network error")
        return "Good content."

    ingested, skipped = ingest_background_url_sources(
        "proj_url_2",
        brief,
        upload_root=root,
        fetch_fn=fake_fetch,
    )

    assert ingested == ["https://example.com/good"]
    assert skipped == ["https://example.com/bad"]


def test_ingest_background_url_sources_is_idempotent(tmp_path):
    root = str(tmp_path / "uploads")
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein bar"],
            "research_goal": "Find signals",
            "optional_background_materials": ["https://example.com/article"],
        }
    )

    call_count = 0

    def fake_fetch(url):
        nonlocal call_count
        call_count += 1
        return "Article content."

    ingest_background_url_sources(
        "proj_url_3",
        brief,
        upload_root=root,
        fetch_fn=fake_fetch,
    )
    ingest_background_url_sources(
        "proj_url_3",
        brief,
        upload_root=root,
        fetch_fn=fake_fetch,
    )

    # fetch_fn should only be called once because the second call sees existing docs
    assert call_count == 1

    registry = SourceRegistry("proj_url_3", upload_root=root)
    assert registry.source_count(lane=ResearchSourceLane.LaneA) == 1

    ingest = DocumentIngestService("proj_url_3", upload_root=root)
    assert len(ingest.list_documents()) == 1
    assert len(ingest.load_chunks()) >= 1


def test_ingest_background_url_sources_preserves_non_url_materials(tmp_path):
    root = str(tmp_path / "uploads")
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein bar"],
            "research_goal": "Find signals",
            "optional_background_materials": [
                "Plain note",
                "https://example.com/article",
            ],
        }
    )

    def fake_fetch(url):
        return "Article content."

    ingest_background_url_sources(
        "proj_url_4",
        brief,
        upload_root=root,
        fetch_fn=fake_fetch,
    )

    # Non-URL materials are not touched by this function
    assert brief.optional_background_materials == [
        "Plain note",
        "https://example.com/article",
    ]


def test_ingest_background_url_sources_graceful_on_empty_materials(tmp_path):
    root = str(tmp_path / "uploads")
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein bar"],
            "research_goal": "Find signals",
        }
    )

    ingested, skipped = ingest_background_url_sources(
        "proj_url_empty",
        brief,
        upload_root=root,
    )

    assert ingested == []
    assert skipped == []
