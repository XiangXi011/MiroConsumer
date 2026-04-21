"""URL ingestion for Lane A research workspace.

Fetches content from user-provided URLs inside optional_background_materials
and registers them as Lane A research sources with chunked documents.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Callable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .document_ingest import DocumentIngestService
from .models import ConsumerBusinessBrief, ResearchSourceLane, ResearchSourceType
from .source_registry import SourceRegistry


class _TextExtractor(HTMLParser):
    """Strip HTML tags and skip non-content tags."""

    _SKIP_TAGS = frozenset({"script", "style", "nav", "footer", "header", "aside", "svg", "canvas"})

    def __init__(self) -> None:
        super().__init__()
        self._text_parts: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._text_parts.append(data)

    def get_text(self) -> str:
        text = "".join(self._text_parts)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


def is_url(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith(("http://", "https://"))


def _extract_text_from_html(html: str) -> str:
    extractor = _TextExtractor()
    try:
        extractor.feed(html)
    except Exception:
        # Fallback: naive regex strip
        text = re.sub(r"<[^>]+>", "", html)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    return extractor.get_text()


def _default_fetch_url(url: str, timeout: int = 15) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    )
    with urlopen(req, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "").lower()
        data = response.read()

        if "application/pdf" in content_type or url.lower().endswith(".pdf"):
            # PDF support deferred; lightweight HTML/text fetcher only
            return ""

        charset = "utf-8"
        match = re.search(r"charset=([^\s;]+)", content_type)
        if match:
            charset = match.group(1).strip("\"'")

        html = data.decode(charset, errors="replace")
        return _extract_text_from_html(html)


FetchUrlFn = Callable[[str], str]


def ingest_background_url_sources(
    project_id: str,
    brief: ConsumerBusinessBrief,
    upload_root: Optional[str] = None,
    fetch_fn: Optional[FetchUrlFn] = None,
) -> Tuple[List[str], List[str]]:
    """Ingest URL entries from optional_background_materials into Lane A workspace.

    Non-URL entries are ignored so they continue to flow through the plain-text
    brief_background path.

    Returns:
        Tuple of (ingested_urls, skipped_urls).
    """
    urls = [text.strip() for text in brief.optional_background_materials if is_url(text)]
    if not urls:
        return [], []

    registry = SourceRegistry(project_id, upload_root=upload_root)
    ingest = DocumentIngestService(project_id, upload_root=upload_root)
    fetcher = fetch_fn or _default_fetch_url

    ingested: List[str] = []
    skipped: List[str] = []

    for url in urls:
        source = registry.get_or_register_source(
            lane=ResearchSourceLane.LaneA,
            source_type=ResearchSourceType.Url,
            label=f"User URL: {url}",
            uri=url,
        )

        # Idempotency: do not duplicate documents for an already-ingested source
        if ingest.list_documents(source_id=source.source_id):
            ingested.append(url)
            continue

        try:
            text = fetcher(url)
        except Exception:
            skipped.append(url)
            continue

        if not text or not text.strip():
            skipped.append(url)
            continue

        ingest.ingest_text(
            source_id=source.source_id,
            text=text,
            title=url,
        )
        ingested.append(url)

    return ingested, skipped
