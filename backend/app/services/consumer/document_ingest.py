"""Document ingestion and chunking for project-scoped research workspaces."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import DocumentChunk, IngestedDocument


RESEARCH_DIR_NAME = "research"
DOCUMENTS_FILE_NAME = "documents.json"
CHUNKS_FILE_NAME = "chunks.jsonl"

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50


def _get_research_dir(project_id: str, upload_root: Optional[str] = None) -> Path:
    root = Path(upload_root) if upload_root else Path(__file__).resolve().parents[3] / "uploads"
    return root / "projects" / project_id / RESEARCH_DIR_NAME


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _simple_chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[tuple[str, int, int]]:
    """Split text into overlapping chunks. Returns list of (chunk_text, start, end)."""
    chunks: List[tuple[str, int, int]] = []
    if not text:
        return chunks

    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        # Try to break at a newline or space for cleaner chunks
        if end < length:
            for delimiter in ("\n\n", "\n", ". ", " "):
                pos = text.rfind(delimiter, start, end)
                if pos != -1 and pos > start:
                    end = pos + len(delimiter.rstrip())
                    break
        chunk_text = text[start:end]
        chunks.append((chunk_text, start, end))
        advance = end - start - overlap
        if advance <= 0:
            advance = max(1, (end - start) // 2)
        start = start + advance
        if start >= end:
            break

    return chunks


class DocumentIngestService:
    """Ingest documents, chunk them, and persist to the project research workspace."""

    def __init__(self, project_id: str, upload_root: Optional[str] = None):
        self.project_id = project_id
        self._dir = _get_research_dir(project_id, upload_root)
        self._docs_path = self._dir / DOCUMENTS_FILE_NAME
        self._chunks_path = self._dir / CHUNKS_FILE_NAME
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    def _load_documents(self) -> List[IngestedDocument]:
        if not self._docs_path.exists():
            return []
        with self._docs_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return [IngestedDocument(**item) for item in data.get("documents", [])]

    def _save_documents(self, documents: List[IngestedDocument]) -> None:
        payload = {
            "project_id": self.project_id,
            "updated_at": _now_iso(),
            "documents": [d.model_dump() for d in documents],
        }
        with self._docs_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _append_chunks(self, chunks: List[DocumentChunk]) -> None:
        with self._chunks_path.open("a", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk.model_dump(), ensure_ascii=False))
                f.write("\n")

    def ingest_text(
        self,
        source_id: str,
        text: str,
        title: str = "",
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> Dict[str, Any]:
        """Ingest raw text, chunk it, and persist."""
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        words = text.split()
        document = IngestedDocument(
            doc_id=doc_id,
            source_id=source_id,
            title=title or doc_id,
            raw_text=text,
            word_count=len(words),
            ingested_at=_now_iso(),
        )

        documents = self._load_documents()
        documents.append(document)
        self._save_documents(documents)

        raw_chunks = _simple_chunk_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
        chunks: List[DocumentChunk] = []
        for idx, (chunk_text, start, end) in enumerate(raw_chunks):
            chunk = DocumentChunk(
                chunk_id=f"chk_{uuid.uuid4().hex[:12]}",
                doc_id=doc_id,
                source_id=source_id,
                text=chunk_text,
                index=idx,
                char_start=start,
                char_end=end,
                created_at=_now_iso(),
            )
            chunks.append(chunk)

        self._append_chunks(chunks)

        return {
            "doc_id": doc_id,
            "source_id": source_id,
            "chunk_count": len(chunks),
            "word_count": len(words),
        }

    def list_documents(self, source_id: Optional[str] = None) -> List[IngestedDocument]:
        documents = self._load_documents()
        if source_id is None:
            return documents
        return [d for d in documents if d.source_id == source_id]

    def get_document(self, doc_id: str) -> Optional[IngestedDocument]:
        for d in self._load_documents():
            if d.doc_id == doc_id:
                return d
        return None

    def load_chunks(self, doc_id: Optional[str] = None, source_id: Optional[str] = None) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        if not self._chunks_path.exists():
            return chunks
        with self._chunks_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if doc_id and data.get("doc_id") != doc_id:
                    continue
                if source_id and data.get("source_id") != source_id:
                    continue
                chunks.append(DocumentChunk(**data))
        return chunks

    def remove_document(self, doc_id: str) -> bool:
        documents = self._load_documents()
        filtered = [d for d in documents if d.doc_id != doc_id]
        if len(filtered) == len(documents):
            return False
        self._save_documents(filtered)
        # Rewrite chunks file without this doc's chunks
        all_chunks = self.load_chunks()
        kept = [c for c in all_chunks if c.doc_id != doc_id]
        with self._chunks_path.open("w", encoding="utf-8") as f:
            for chunk in kept:
                f.write(json.dumps(chunk.model_dump(), ensure_ascii=False))
                f.write("\n")
        return True

    def clear_all(self) -> None:
        if self._docs_path.exists():
            self._docs_path.unlink()
        if self._chunks_path.exists():
            self._chunks_path.unlink()

    def stats(self) -> Dict[str, Any]:
        documents = self._load_documents()
        chunks = self.load_chunks()
        return {
            "project_id": self.project_id,
            "document_count": len(documents),
            "chunk_count": len(chunks),
            "total_word_count": sum(d.word_count for d in documents),
        }
