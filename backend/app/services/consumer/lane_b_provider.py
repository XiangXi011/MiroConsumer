"""Real Lane B public-web search provider using the OpenAI Responses API web_search tool.

The provider uses the OpenAI Responses API with web_search tool to perform
actual public-web searches. Results are normalized into the project research
workspace so downstream retrieval and reporting can reuse them with full
provenance.

When ENABLE_LANE_B_WEB_SEARCH is False or no API key is available, the provider
is not built and retrieval falls back to the deterministic repo-local path.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from ...config import Config
from .document_ingest import DocumentIngestService
from .models import DocumentChunk, ResearchSourceLane, ResearchSourceType
from .source_registry import SourceRegistry

logger = logging.getLogger(__name__)


class WebSearchResultItem(BaseModel):
    url: str
    title: str
    snippet: str


class OpenAIWebSearchProvider:
    """OpenAI Responses API web search provider.

    Uses the OpenAI Responses API with web_search tool to retrieve real
    public-web search results. Results are normalized into the project
    research workspace:

    - Sources are registered in Lane B with stable metadata (URL, title, query).
    - Snippets are ingested as document chunks.
    - Duplicate URLs/chunks are skipped on repeat queries for the same project.
    """

    def __init__(
        self,
        project_id: str,
        upload_root: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.project_id = project_id
        self.upload_root = upload_root
        self._registry = SourceRegistry(project_id, upload_root=upload_root)
        self._ingest = DocumentIngestService(project_id, upload_root=upload_root)
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._client = None

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    @staticmethod
    def _stable_source_id(url: str) -> str:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
        return f"src_{digest}"

    @staticmethod
    def _stable_doc_id(url: str) -> str:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
        return f"doc_{digest}"

    @staticmethod
    def _stable_chunk_id(url: str, text: str) -> str:
        digest = hashlib.sha256(f"{url}:{text}".encode("utf-8")).hexdigest()[:12]
        return f"chk_{digest}"

    def __call__(self, query: str, top_k: int) -> List[DocumentChunk]:
        """Execute search, persist sources/chunks to workspace, return chunks."""
        results = self._search(query, top_k)
        chunks: List[DocumentChunk] = []

        for item in results:
            if not item.url or not item.snippet:
                continue
            source_id = self._stable_source_id(item.url)
            doc_id = self._stable_doc_id(item.url)
            chunk_id = self._stable_chunk_id(item.url, item.snippet)

            source = self._registry.get_or_register_source(
                lane=ResearchSourceLane.LaneB,
                source_type=ResearchSourceType.PublicWeb,
                label=item.title or item.url,
                uri=item.url,
                metadata={"query": query, "title": item.title},
                source_id=source_id,
            )

            chunk = DocumentChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                source_id=source.source_id,
                text=item.snippet,
                index=0,
                char_start=0,
                char_end=len(item.snippet),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            chunks.append(chunk)

        if chunks:
            self._ingest.ingest_chunks(chunks)

        return chunks

    def _search(self, query: str, top_k: int) -> List[WebSearchResultItem]:
        client = self._get_client()
        try:
            response = client.responses.create(
                model=self._model,
                input=[{"role": "user", "content": query}],
                tools=[{"type": "web_search"}],
                include=["web_search_call.action.sources"],
            )
        except Exception as exc:
            logger.warning("Lane B web search call failed: %s", exc)
            raise
        return self._parse_response(response, top_k)

    def _parse_response(self, response: Any, top_k: int) -> List[WebSearchResultItem]:
        items: List[WebSearchResultItem] = []
        sources: List[Any] = []
        citations_by_url: Dict[str, List[str]] = {}
        text_parts: List[tuple[str, List[Any]]] = []

        output = getattr(response, "output", None)
        if output is None and isinstance(response, dict):
            output = response.get("output", [])
        if not isinstance(output, list):
            output = []

        # Pass 1: collect sources from the web_search_call item
        for item in output:
            item_type = getattr(item, "type", None)
            if item_type is None and isinstance(item, dict):
                item_type = item.get("type")

            if item_type == "web_search_call":
                action = getattr(item, "action", None)
                if action is None and isinstance(item, dict):
                    action = item.get("action")

                if action:
                    action_sources = getattr(action, "sources", None)
                    if action_sources is None and isinstance(action, dict):
                        action_sources = action.get("sources", [])
                    if action_sources:
                        sources.extend(action_sources)
                        break

                search_results = getattr(item, "search_results", None)
                if search_results is None and isinstance(item, dict):
                    search_results = item.get("search_results", [])
                if search_results:
                    sources.extend(search_results)
                    break

        # Pass 2: collect output text and url_citation annotations from message items
        for item in output:
            item_type = getattr(item, "type", None)
            if item_type is None and isinstance(item, dict):
                item_type = item.get("type")

            if item_type != "message":
                continue

            content = getattr(item, "content", None)
            if content is None and isinstance(item, dict):
                content = item.get("content", [])
            if not isinstance(content, list):
                continue

            for part in content:
                part_type = getattr(part, "type", None)
                if part_type is None and isinstance(part, dict):
                    part_type = part.get("type")
                if part_type != "text":
                    continue

                text = getattr(part, "text", None)
                if text is None and isinstance(part, dict):
                    text = part.get("text", "")
                if not text:
                    continue

                annotations = getattr(part, "annotations", None)
                if annotations is None and isinstance(part, dict):
                    annotations = part.get("annotations", [])
                text_parts.append((str(text), annotations if isinstance(annotations, list) else []))

        for text, annotations in text_parts:
            for ann in annotations:
                ann_type = getattr(ann, "type", None)
                if ann_type is None and isinstance(ann, dict):
                    ann_type = ann.get("type")
                if ann_type != "url_citation":
                    continue

                ann_url = getattr(ann, "url", None)
                if ann_url is None and isinstance(ann, dict):
                    ann_url = ann.get("url")
                start = getattr(ann, "start_index", None)
                if start is None and isinstance(ann, dict):
                    start = ann.get("start_index")
                end = getattr(ann, "end_index", None)
                if end is None and isinstance(ann, dict):
                    end = ann.get("end_index")

                if ann_url and start is not None and end is not None:
                    try:
                        cited_text = text[int(start):int(end)]
                        if cited_text.strip():
                            citations_by_url.setdefault(str(ann_url), []).append(cited_text)
                    except (ValueError, TypeError):
                        pass

        # Fallback output_text from the response itself
        output_text = ""
        response_output_text = getattr(response, "output_text", None)
        if response_output_text:
            output_text = str(response_output_text)
        elif isinstance(response, dict):
            response_output_text = response.get("output_text", "")
            if response_output_text:
                output_text = str(response_output_text)

        if not output_text and text_parts:
            output_text = " ".join(t for t, _ in text_parts)

        for src in sources[:top_k]:
            if isinstance(src, dict):
                url = str(src.get("url", "")).strip()
                title = str(src.get("title", "")).strip()
                snippet = str(src.get("snippet", "") or "").strip()
            else:
                url = str(getattr(src, "url", "") or "").strip()
                title = str(getattr(src, "title", "") or "").strip()
                snippet = str(getattr(src, "snippet", "") or "").strip()

            if not url:
                continue

            if not snippet:
                cited_texts = citations_by_url.get(url, [])
                if cited_texts:
                    snippet = " ".join(cited_texts)
                elif output_text:
                    snippet = output_text[:800].strip()

            if snippet:
                items.append(WebSearchResultItem(url=url, title=title, snippet=snippet))

        return items


def build_lane_b_provider(
    project_id: str,
    upload_root: Optional[str] = None,
) -> Optional[OpenAIWebSearchProvider]:
    """Build a Lane B provider if enabled and configured, else None.

    Returns None when:
    - ENABLE_LANE_B_WEB_SEARCH is False (default)
    - LLM_API_KEY is not configured
    """
    if not getattr(Config, "ENABLE_LANE_B_WEB_SEARCH", False):
        return None
    if not Config.LLM_API_KEY:
        return None
    return OpenAIWebSearchProvider(
        project_id=project_id,
        upload_root=upload_root,
        api_key=Config.LLM_API_KEY,
        base_url=Config.LLM_BASE_URL,
        model=getattr(Config, "LANE_B_SEARCH_MODEL", Config.LLM_MODEL_NAME),
    )
