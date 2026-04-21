from unittest.mock import MagicMock

from app.services.consumer.document_ingest import DocumentIngestService
from app.services.consumer.lane_b_provider import OpenAIWebSearchProvider, WebSearchResultItem, build_lane_b_provider
from app.services.consumer.models import ResearchSourceLane, ResearchSourceType
from app.services.consumer.source_registry import SourceRegistry


def test_stable_ids_are_consistent():
    provider = OpenAIWebSearchProvider("proj_stable", upload_root="/tmp/fake")
    url = "https://example.com/article"
    text = "Some snippet text"

    assert provider._stable_source_id(url) == provider._stable_source_id(url)
    assert provider._stable_doc_id(url) == provider._stable_doc_id(url)
    assert provider._stable_chunk_id(url, text) == provider._stable_chunk_id(url, text)


def test_provider_persists_sources_and_chunks(tmp_path):
    root = str(tmp_path / "uploads")
    provider = OpenAIWebSearchProvider("proj_persist", upload_root=root)

    # Mock _search to avoid real API calls
    provider._search = lambda query, top_k: [
        WebSearchResultItem(
            url="https://example.com/news",
            title="Example News",
            snippet="A competitor launched a new product line.",
        )
    ]

    chunks = provider("competitor news", top_k=3)

    assert len(chunks) == 1
    assert chunks[0].text == "A competitor launched a new product line."

    # Verify source was registered
    registry = SourceRegistry("proj_persist", upload_root=root)
    sources = registry.list_sources(lane=ResearchSourceLane.LaneB)
    assert len(sources) == 1
    assert sources[0].uri == "https://example.com/news"
    assert sources[0].source_type == ResearchSourceType.PublicWeb

    # Verify chunk was ingested
    ingest = DocumentIngestService("proj_persist", upload_root=root)
    loaded = ingest.load_chunks()
    assert len(loaded) == 1
    assert loaded[0].text == "A competitor launched a new product line."


def test_provider_dedupes_on_repeat_query(tmp_path):
    root = str(tmp_path / "uploads")
    provider = OpenAIWebSearchProvider("proj_dedup", upload_root=root)

    provider._search = lambda query, top_k: [
        WebSearchResultItem(
            url="https://example.com/news",
            title="Example News",
            snippet="A competitor launched a new product line.",
        )
    ]

    # First call
    chunks1 = provider("competitor news", top_k=3)
    assert len(chunks1) == 1

    # Second call with same query and result
    chunks2 = provider("competitor news", top_k=3)
    assert len(chunks2) == 1

    # Source should not be duplicated
    registry = SourceRegistry("proj_dedup", upload_root=root)
    assert registry.source_count(lane=ResearchSourceLane.LaneB) == 1

    # Chunks should not be duplicated
    ingest = DocumentIngestService("proj_dedup", upload_root=root)
    assert len(ingest.load_chunks()) == 1


def test_provider_returns_multiple_results(tmp_path):
    root = str(tmp_path / "uploads")
    provider = OpenAIWebSearchProvider("proj_multi", upload_root=root)

    provider._search = lambda query, top_k: [
        WebSearchResultItem(url="https://a.com", title="A", snippet="Snippet A"),
        WebSearchResultItem(url="https://b.com", title="B", snippet="Snippet B"),
    ]

    chunks = provider("query", top_k=3)
    assert len(chunks) == 2

    registry = SourceRegistry("proj_multi", upload_root=root)
    assert registry.source_count(lane=ResearchSourceLane.LaneB) == 2


def test_provider_skips_results_without_url_or_snippet(tmp_path):
    root = str(tmp_path / "uploads")
    provider = OpenAIWebSearchProvider("proj_skip", upload_root=root)

    provider._search = lambda query, top_k: [
        WebSearchResultItem(url="", title="Empty URL", snippet="Has snippet but no URL"),
        WebSearchResultItem(url="https://valid.com", title="Valid", snippet="Valid snippet"),
        WebSearchResultItem(url="https://no-snippet.com", title="No Snippet", snippet=""),
    ]

    chunks = provider("query", top_k=3)
    assert len(chunks) == 1
    assert chunks[0].text == "Valid snippet"


def test_provider_raises_on_search_failure(tmp_path):
    root = str(tmp_path / "uploads")
    provider = OpenAIWebSearchProvider("proj_fail", upload_root=root)

    provider._search = lambda query, top_k: (_ for _ in ()).throw(RuntimeError("search timeout"))

    try:
        provider("query", top_k=3)
        assert False, "Expected RuntimeError"
    except RuntimeError:
        pass


def test_build_lane_b_provider_when_disabled(monkeypatch):
    monkeypatch.setattr("app.services.consumer.lane_b_provider.Config.ENABLE_LANE_B_WEB_SEARCH", False)
    monkeypatch.setattr("app.services.consumer.lane_b_provider.Config.LLM_API_KEY", "sk-test")
    assert build_lane_b_provider("proj") is None


def test_build_lane_b_provider_when_no_key(monkeypatch):
    monkeypatch.setattr("app.services.consumer.lane_b_provider.Config.ENABLE_LANE_B_WEB_SEARCH", True)
    monkeypatch.setattr("app.services.consumer.lane_b_provider.Config.LLM_API_KEY", None)
    assert build_lane_b_provider("proj") is None


def test_build_lane_b_provider_when_enabled(monkeypatch):
    monkeypatch.setattr("app.services.consumer.lane_b_provider.Config.ENABLE_LANE_B_WEB_SEARCH", True)
    monkeypatch.setattr("app.services.consumer.lane_b_provider.Config.LLM_API_KEY", "sk-test")
    monkeypatch.setattr("app.services.consumer.lane_b_provider.Config.LLM_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setattr("app.services.consumer.lane_b_provider.Config.LLM_MODEL_NAME", "gpt-4o-mini")
    provider = build_lane_b_provider("proj", upload_root="/tmp/fake")
    assert provider is not None
    assert isinstance(provider, OpenAIWebSearchProvider)
    assert provider.project_id == "proj"


def test_parse_response_with_object_sources():
    provider = OpenAIWebSearchProvider("proj_parse", upload_root="/tmp/fake")

    mock_source = MagicMock()
    mock_source.url = "https://a.com"
    mock_source.title = "A"
    mock_source.snippet = "Snippet A"

    mock_action = MagicMock()
    mock_action.sources = [mock_source]

    mock_item = MagicMock()
    mock_item.type = "web_search_call"
    mock_item.action = mock_action

    mock_response = MagicMock()
    mock_response.output = [mock_item]

    result = provider._parse_response(mock_response, top_k=5)
    assert len(result) == 1
    assert result[0].url == "https://a.com"
    assert result[0].title == "A"
    assert result[0].snippet == "Snippet A"


def test_parse_response_with_dict_sources():
    provider = OpenAIWebSearchProvider("proj_parse_dict", upload_root="/tmp/fake")

    mock_response = {
        "output": [
            {
                "type": "web_search_call",
                "action": {
                    "sources": [
                        {"url": "https://b.com", "title": "B", "snippet": "Snippet B"},
                        {"url": "", "title": "Empty", "snippet": ""},
                    ]
                },
            }
        ]
    }

    result = provider._parse_response(mock_response, top_k=5)
    assert len(result) == 1
    assert result[0].url == "https://b.com"


def test_parse_response_with_search_results_fallback():
    provider = OpenAIWebSearchProvider("proj_parse_fb", upload_root="/tmp/fake")

    mock_item = MagicMock()
    mock_item.type = "web_search_call"
    mock_item.action = None
    mock_item.search_results = [
        MagicMock(url="https://c.com", title="C", snippet="Snippet C"),
    ]

    mock_response = MagicMock()
    mock_response.output = [mock_item]

    result = provider._parse_response(mock_response, top_k=5)
    assert len(result) == 1
    assert result[0].url == "https://c.com"


def test_parse_response_empty_when_no_web_search_call():
    provider = OpenAIWebSearchProvider("proj_parse_empty", upload_root="/tmp/fake")

    mock_response = MagicMock()
    mock_response.output = [{"type": "message"}]

    result = provider._parse_response(mock_response, top_k=5)
    assert result == []


def test_parse_response_respects_top_k():
    provider = OpenAIWebSearchProvider("proj_parse_topk", upload_root="/tmp/fake")

    sources = [
        {"url": f"https://{i}.com", "title": f"T{i}", "snippet": f"S{i}"}
        for i in range(10)
    ]

    mock_response = {
        "output": [
            {
                "type": "web_search_call",
                "action": {"sources": sources},
            }
        ]
    }

    result = provider._parse_response(mock_response, top_k=3)
    assert len(result) == 3


def test_web_search_result_item_model():
    item = WebSearchResultItem(url="https://x.com", title="X", snippet="Snippet")
    assert item.url == "https://x.com"


def test_parse_response_missing_snippet_uses_citations():
    provider = OpenAIWebSearchProvider("proj_cite", upload_root="/tmp/fake")

    mock_response = {
        "output": [
            {
                "type": "web_search_call",
                "action": {
                    "sources": [
                        {"url": "https://a.com", "title": "A", "snippet": ""},
                    ]
                },
            },
            {
                "type": "message",
                "content": [
                    {
                        "type": "text",
                        "text": "According to the report, sales grew 42% in Q3.",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": "https://a.com",
                                "title": "A",
                                "start_index": 25,
                                "end_index": 46,
                            }
                        ],
                    }
                ],
            },
        ]
    }

    result = provider._parse_response(mock_response, top_k=5)
    assert len(result) == 1
    assert result[0].url == "https://a.com"
    assert result[0].snippet == "sales grew 42% in Q3."


def test_parse_response_missing_snippet_uses_output_text_fallback():
    provider = OpenAIWebSearchProvider("proj_fallback", upload_root="/tmp/fake")

    mock_response = {
        "output": [
            {
                "type": "web_search_call",
                "action": {
                    "sources": [
                        {"url": "https://b.com", "title": "B", "snippet": ""},
                    ]
                },
            },
            {
                "type": "message",
                "content": [
                    {"type": "text", "text": "The market expanded rapidly this quarter."}
                ],
            },
        ],
        "output_text": "The market expanded rapidly this quarter.",
    }

    result = provider._parse_response(mock_response, top_k=5)
    assert len(result) == 1
    assert result[0].url == "https://b.com"
    assert result[0].snippet == "The market expanded rapidly this quarter."


def test_parse_response_missing_snippet_uses_text_parts_when_no_output_text():
    provider = OpenAIWebSearchProvider("proj_textparts", upload_root="/tmp/fake")

    mock_response = {
        "output": [
            {
                "type": "web_search_call",
                "action": {
                    "sources": [
                        {"url": "https://c.com", "title": "C", "snippet": ""},
                    ]
                },
            },
            {
                "type": "message",
                "content": [
                    {"type": "text", "text": "Revenue hit an all-time high."}
                ],
            },
        ]
    }

    result = provider._parse_response(mock_response, top_k=5)
    assert len(result) == 1
    assert result[0].url == "https://c.com"
    assert result[0].snippet == "Revenue hit an all-time high."


def test_parse_response_output_text_bounded_fallback():
    provider = OpenAIWebSearchProvider("proj_bounded", upload_root="/tmp/fake")

    long_text = "x" * 2000
    mock_response = {
        "output": [
            {
                "type": "web_search_call",
                "action": {
                    "sources": [
                        {"url": "https://d.com", "title": "D", "snippet": ""},
                    ]
                },
            },
        ],
        "output_text": long_text,
    }

    result = provider._parse_response(mock_response, top_k=5)
    assert len(result) == 1
    assert result[0].url == "https://d.com"
    assert len(result[0].snippet) == 800
    assert result[0].snippet == "x" * 800


def test_provider_full_flow_with_snippetless_sources(tmp_path):
    root = str(tmp_path / "uploads")
    provider = OpenAIWebSearchProvider("proj_flow", upload_root=root)

    mock_client = MagicMock()
    mock_response = {
        "output": [
            {
                "type": "web_search_call",
                "action": {
                    "sources": [
                        {"url": "https://example.com/news", "title": "Example News", "snippet": ""},
                    ]
                },
            },
            {
                "type": "message",
                "content": [
                    {"type": "text", "text": "A competitor launched a new product line."}
                ],
            },
        ],
        "output_text": "A competitor launched a new product line.",
    }
    mock_client.responses.create.return_value = mock_response
    provider._client = mock_client

    chunks = provider("competitor news", top_k=3)

    assert len(chunks) == 1
    assert chunks[0].text == "A competitor launched a new product line."

    registry = SourceRegistry("proj_flow", upload_root=root)
    sources = registry.list_sources(lane=ResearchSourceLane.LaneB)
    assert len(sources) == 1
    assert sources[0].uri == "https://example.com/news"

    ingest = DocumentIngestService("proj_flow", upload_root=root)
    loaded = ingest.load_chunks()
    assert len(loaded) == 1
    assert loaded[0].text == "A competitor launched a new product line."
