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
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from ...config import Config
from .document_ingest import DocumentIngestService
from .models import DocumentChunk, ResearchSourceLane, ResearchSourceType
from .source_registry import SourceRegistry

logger = logging.getLogger(__name__)


class WebSearchResultItem(BaseModel):
    url: str
    title: str
    snippet: str


class GovernanceDecision(BaseModel):
    """Record of a single chunk's governance evaluation."""

    chunk_id: str
    status: str  # "accepted" or "rejected"
    reasons: List[str] = Field(default_factory=list)
    downgraded: bool = False


class GovernedDocumentChunk(DocumentChunk):
    """DocumentChunk extended with Lane B governance metadata."""

    governance_status: str = "accepted"
    governance_reasons: List[str] = Field(default_factory=list)
    downgraded: bool = False


class LaneBGovernance:
    """Govern public-web search results before they become findings.

    Responsibilities:
    - Enforce minimum snippet quality (length, non-empty content)
    - Suppress duplicate or near-duplicate results
    - Downgrade sources with weak provenance
    - Return accepted chunks + full decision log
    """

    def __init__(self, min_snippet_length: int = 20):
        self.min_snippet_length = min_snippet_length

    def evaluate(
        self, chunks: List[DocumentChunk]
    ) -> Tuple[List[GovernedDocumentChunk], List[GovernanceDecision]]:
        """Evaluate chunks and return (accepted_chunks, all_decisions)."""
        accepted: List[GovernedDocumentChunk] = []
        decisions: List[GovernanceDecision] = []
        seen_texts: set[str] = set()

        for chunk in chunks:
            reasons: List[str] = []
            status = "accepted"
            downgraded = False

            text = chunk.text.strip()

            # Minimum snippet quality check
            if len(text) < self.min_snippet_length:
                status = "rejected"
                reasons.append(f"Failed minimum snippet length ({len(text)} < {self.min_snippet_length})")

            # Duplicate suppression check
            normalized = text.casefold()
            if normalized in seen_texts:
                status = "rejected"
                reasons.append("Duplicate or near-duplicate content")
            else:
                seen_texts.add(normalized)

            # Weak provenance / source downgrade rule
            if status == "accepted" and self._is_weak_provenance(text):
                downgraded = True
                reasons.append("Weak provenance: vague or low-detail snippet")

            gov_chunk = GovernedDocumentChunk(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                source_id=chunk.source_id,
                text=chunk.text,
                index=chunk.index,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                created_at=chunk.created_at,
                governance_status=status,
                governance_reasons=list(reasons),
                downgraded=downgraded,
            )

            decisions.append(
                GovernanceDecision(
                    chunk_id=chunk.chunk_id,
                    status=status,
                    reasons=list(reasons),
                    downgraded=downgraded,
                )
            )

            if status == "accepted":
                accepted.append(gov_chunk)

        return accepted, decisions

    @staticmethod
    def _is_weak_provenance(text: str) -> bool:
        """Heuristic: short-ish, vague, or low-detail snippets are weak provenance."""
        stripped = text.strip()
        # If under 30 chars it's vague regardless
        if len(stripped) < 30:
            return True
        # For longer text, downgrade only if it lacks any specificity markers
        # AND is under 60 chars
        if len(stripped) >= 60:
            return False
        has_specificity = any(c.isdigit() for c in stripped)
        has_specificity = has_specificity or any(
            marker in stripped.casefold()
            for marker in (
                "%",
                "$",
                "study",
                "report",
                "survey",
                "according to",
                "said",
                "found",
                "data",
                "research",
            )
        )
        return not has_specificity


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
        self._last_governance_decisions: List[GovernanceDecision] = []

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
        raw_chunks: List[DocumentChunk] = []

        for item in results:
            if not item.url:
                continue
            source_id = self._stable_source_id(item.url)
            doc_id = self._stable_doc_id(item.url)
            chunk_id = self._stable_chunk_id(item.url, item.snippet or "")

            source = self._registry.get_or_register_source(
                lane=ResearchSourceLane.LaneB,
                source_type=ResearchSourceType.PublicWeb,
                label=item.title or item.url,
                uri=item.url,
                metadata={"query": query, "title": item.title},
                source_id=source_id,
            )

            snippet_text = item.snippet.strip() if item.snippet else ""
            if not snippet_text:
                continue

            chunk = DocumentChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                source_id=source.source_id,
                text=snippet_text,
                index=0,
                char_start=0,
                char_end=len(snippet_text),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            raw_chunks.append(chunk)

        # Apply Lane B governance
        governance = LaneBGovernance()
        accepted_chunks, decisions = governance.evaluate(raw_chunks)
        self._last_governance_decisions = decisions

        if accepted_chunks:
            self._ingest.ingest_chunks(accepted_chunks)

        return accepted_chunks

    def last_governance(self) -> List[GovernanceDecision]:
        """Return governance decisions from the last search call."""
        return list(self._last_governance_decisions)

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
