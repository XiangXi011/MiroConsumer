"""Dual-lane retrieval for project-scoped research workspaces.

Lane A: uploaded / user-provided materials (higher trust)
Lane B: public-web supplemental sources (lower trust, gap-filling)

The default behavior is deterministic and repo-local so tests stay
stable without external API keys.  A provider hook is exposed for
future real public-web search integration.
"""

from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .document_ingest import DocumentIngestService
from .finding_distiller import build_retrieval_trace
from .models import DocumentChunk, ResearchFinding, ResearchSourceLane, RetrievalTrace
from .source_registry import SourceRegistry


RESEARCH_DIR_NAME = "research"
RETRIEVAL_TRACES_FILE_NAME = "retrieval_traces.jsonl"


PublicWebSearchProvider = Callable[[str, int], List[DocumentChunk]]
"""Contract for external public-web search providers.

Args:
    query: The search query string.
    top_k: Maximum number of chunks to return.

Returns:
    List of DocumentChunk objects representing public-web results.
    The caller is responsible for assigning meaningful source_id values.
"""


def _get_research_dir(project_id: str, upload_root: Optional[str] = None) -> Path:
    root = Path(upload_root) if upload_root else Path(__file__).resolve().parents[3] / "uploads"
    return root / "projects" / project_id / RESEARCH_DIR_NAME


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokenize(text: str) -> List[str]:
    """Simple deterministic tokenizer."""
    return [t.strip(".,!?;:") for t in text.lower().split() if t.strip(".,!?;:")]


def _score_chunk(query: str, chunk: DocumentChunk) -> float:
    """Deterministic overlap score between query and chunk text.

    Uses a simplified BM25-style term-frequency scoring that is:
    - fully deterministic (no randomness)
    - repo-local (no external dependencies)
    - suitable for tests (same input -> same ranked output)
    """
    query_terms = _tokenize(query)
    if not query_terms:
        return 0.0

    chunk_terms = _tokenize(chunk.text)
    if not chunk_terms:
        return 0.0

    term_freq: Dict[str, int] = {}
    for term in chunk_terms:
        term_freq[term] = term_freq.get(term, 0) + 1

    overlap = 0
    for term in query_terms:
        if term in term_freq:
            # Sublinear TF scaling (log(1 + tf)) for BM25-like behavior
            overlap += math.log1p(term_freq[term])

    # Normalize by query length and chunk length
    idf_factor = len(query_terms)
    chunk_len_factor = math.log1p(len(chunk_terms))
    score = overlap / (idf_factor * chunk_len_factor + 1e-6)

    return round(score, 6)


def _rank_chunks(query: str, chunks: List[DocumentChunk]) -> List[Tuple[DocumentChunk, float]]:
    """Score and rank chunks deterministically."""
    scored = [(chunk, _score_chunk(query, chunk)) for chunk in chunks]
    # Sort by score descending, then chunk_id ascending for determinism
    scored.sort(key=lambda x: (-x[1], x[0].chunk_id))
    return scored


class RetrievalService:
    """Retrieve and rank document chunks across Lane A and Lane B.

    Persists retrieval traces to the project research workspace for
    auditability and downstream provenance.
    """

    def __init__(self, project_id: str, upload_root: Optional[str] = None):
        self.project_id = project_id
        self._dir = _get_research_dir(project_id, upload_root)
        self._traces_path = self._dir / RETRIEVAL_TRACES_FILE_NAME
        self._ingest = DocumentIngestService(project_id, upload_root=upload_root)
        self._registry = SourceRegistry(project_id, upload_root=upload_root)
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    def _lane_source_ids(self, lane: ResearchSourceLane) -> set[str]:
        return {s.source_id for s in self._registry.list_sources(lane=lane)}

    def retrieve_lane_a(self, query: str, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        """Retrieve top-k chunks from Lane A (user-provided materials)."""
        lane_a_ids = self._lane_source_ids(ResearchSourceLane.LaneA)
        if not lane_a_ids:
            return []
        all_chunks = self._ingest.load_chunks()
        lane_chunks = [c for c in all_chunks if c.source_id in lane_a_ids]
        return _rank_chunks(query, lane_chunks)[:top_k]

    def retrieve_lane_b(
        self,
        query: str,
        top_k: int = 5,
        provider: Optional[PublicWebSearchProvider] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        """Retrieve top-k chunks from Lane B (public-web supplemental).

        If a provider is supplied, it is invoked first.  The provider is
        expected to normalize its own results into the project workspace.
        If the provider raises an exception, we gracefully fall back to the
        deterministic repo-local fallback.  When no provider is supplied (or
        it is None), the deterministic fallback searches any Lane B sources
        already present in the workspace.  If no Lane B corpus exists,
        returns an empty list (still traceable).
        """
        if provider is not None:
            try:
                chunks = provider(query, top_k)
                return _rank_chunks(query, chunks)[:top_k]
            except Exception:
                # Graceful fallback: continue to deterministic workspace search
                pass

        # Deterministic fallback: search within workspace Lane B corpus
        lane_b_ids = self._lane_source_ids(ResearchSourceLane.LaneB)
        if not lane_b_ids:
            return []
        all_chunks = self._ingest.load_chunks()
        lane_chunks = [c for c in all_chunks if c.source_id in lane_b_ids]
        return _rank_chunks(query, lane_chunks)[:top_k]

    def retrieve_dual(
        self,
        query: str,
        top_k_a: int = 5,
        top_k_b: int = 5,
        provider: Optional[PublicWebSearchProvider] = None,
    ) -> Dict[str, any]:
        """Retrieve from both lanes and persist traces.

        Returns a dict with:
        - lane_a: List[Tuple[DocumentChunk, float]]
        - lane_b: List[Tuple[DocumentChunk, float]]
        - traces: List[RetrievalTrace]
        """
        lane_a_results = self.retrieve_lane_a(query, top_k_a)
        lane_b_results = self.retrieve_lane_b(query, top_k_b, provider=provider)

        trace_a = build_retrieval_trace(
            query=query,
            lane=ResearchSourceLane.LaneA,
            chunk_ids=[c.chunk_id for c, _ in lane_a_results],
            scores=[float(s) for _, s in lane_a_results],
            trace_id=f"trace_{uuid.uuid4().hex[:12]}",
        )
        trace_b = build_retrieval_trace(
            query=query,
            lane=ResearchSourceLane.LaneB,
            chunk_ids=[c.chunk_id for c, _ in lane_b_results],
            scores=[float(s) for _, s in lane_b_results],
            trace_id=f"trace_{uuid.uuid4().hex[:12]}",
        )

        self.persist_trace(trace_a)
        self.persist_trace(trace_b)

        return {
            "lane_a": lane_a_results,
            "lane_b": lane_b_results,
            "traces": [trace_a, trace_b],
        }

    def persist_trace(self, trace: RetrievalTrace) -> None:
        """Append a retrieval trace to the project workspace."""
        with self._traces_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(trace.model_dump(), ensure_ascii=False))
            f.write("\n")

    def load_traces(
        self,
        lane: Optional[ResearchSourceLane] = None,
    ) -> List[RetrievalTrace]:
        """Load persisted retrieval traces, optionally filtered by lane."""
        traces: List[RetrievalTrace] = []
        if not self._traces_path.exists():
            return traces
        with self._traces_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if lane is not None and data.get("lane") != lane.value:
                    continue
                traces.append(RetrievalTrace(**data))
        return traces

    def clear_traces(self) -> None:
        """Remove all persisted retrieval traces."""
        if self._traces_path.exists():
            self._traces_path.unlink()

    def stats(self) -> Dict[str, any]:
        """Return retrieval stats for the project."""
        traces = self.load_traces()
        return {
            "project_id": self.project_id,
            "trace_count": len(traces),
            "lane_a_trace_count": sum(1 for t in traces if t.lane == ResearchSourceLane.LaneA),
            "lane_b_trace_count": sum(1 for t in traces if t.lane == ResearchSourceLane.LaneB),
        }


__all__ = [
    "RetrievalService",
    "PublicWebSearchProvider",
    "_score_chunk",
    "_rank_chunks",
]