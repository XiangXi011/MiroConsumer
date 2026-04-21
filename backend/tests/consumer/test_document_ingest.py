from app.services.consumer.document_ingest import DocumentIngestService, _simple_chunk_text
from app.services.consumer.models import DocumentChunk


def test_simple_chunk_text_splits_and_overlaps():
    text = "This is sentence one. This is sentence two. This is sentence three."
    chunks = _simple_chunk_text(text, chunk_size=30, overlap=5)

    assert len(chunks) > 0
    for chunk_text, start, end in chunks:
        assert chunk_text
        assert 0 <= start < end <= len(text)


def test_ingest_text_creates_document_and_chunks(tmp_path):
    service = DocumentIngestService("proj_test", upload_root=str(tmp_path / "uploads"))

    result = service.ingest_text(
        source_id="src_001",
        text="This is a test document. It has multiple sentences for chunking.",
        title="Test Doc",
        chunk_size=20,
        chunk_overlap=5,
    )

    assert result["source_id"] == "src_001"
    assert result["chunk_count"] > 0
    assert result["word_count"] == 11

    docs = service.list_documents()
    assert len(docs) == 1
    assert docs[0].title == "Test Doc"
    assert docs[0].source_id == "src_001"

    chunks = service.load_chunks(doc_id=result["doc_id"])
    assert len(chunks) == result["chunk_count"]


def test_load_chunks_filters_by_source_id(tmp_path):
    service = DocumentIngestService("proj_test", upload_root=str(tmp_path / "uploads"))

    service.ingest_text(source_id="src_a", text="Document A content here.", chunk_size=10)
    service.ingest_text(source_id="src_b", text="Document B content here.", chunk_size=10)

    chunks_a = service.load_chunks(source_id="src_a")
    chunks_b = service.load_chunks(source_id="src_b")

    assert all(c.source_id == "src_a" for c in chunks_a)
    assert all(c.source_id == "src_b" for c in chunks_b)


def test_remove_document_deletes_chunks(tmp_path):
    service = DocumentIngestService("proj_test", upload_root=str(tmp_path / "uploads"))

    result = service.ingest_text(source_id="src_001", text="Document to remove.", chunk_size=10)
    doc_id = result["doc_id"]

    assert service.remove_document(doc_id) is True
    assert service.get_document(doc_id) is None
    assert service.load_chunks(doc_id=doc_id) == []
    assert service.remove_document(doc_id) is False


def test_clear_all_empties_workspace(tmp_path):
    service = DocumentIngestService("proj_test", upload_root=str(tmp_path / "uploads"))

    service.ingest_text(source_id="src_001", text="Doc one.", chunk_size=10)
    service.ingest_text(source_id="src_002", text="Doc two.", chunk_size=10)

    assert service.stats()["document_count"] == 2

    service.clear_all()
    assert service.stats()["document_count"] == 0
    assert service.stats()["chunk_count"] == 0


def test_stats_returns_counts(tmp_path):
    service = DocumentIngestService("proj_test", upload_root=str(tmp_path / "uploads"))

    service.ingest_text(source_id="src_001", text="One two three.", chunk_size=10)
    service.ingest_text(source_id="src_002", text="Four five six seven.", chunk_size=10)

    stats = service.stats()
    assert stats["project_id"] == "proj_test"
    assert stats["document_count"] == 2
    assert stats["chunk_count"] > 0
    assert stats["total_word_count"] == 7


def test_chunk_indices_are_sequential(tmp_path):
    service = DocumentIngestService("proj_test", upload_root=str(tmp_path / "uploads"))

    text = "Line one. Line two. Line three. Line four. Line five."
    result = service.ingest_text(source_id="src_001", text=text, chunk_size=15, chunk_overlap=3)

    chunks = service.load_chunks(doc_id=result["doc_id"])
    indices = [c.index for c in chunks]
    assert indices == list(range(len(indices)))


def test_document_chunk_model():
    chunk = DocumentChunk(
        chunk_id="chk_001",
        doc_id="doc_001",
        source_id="src_001",
        text="Hello world",
        index=0,
        char_start=0,
        char_end=11,
    )
    assert chunk.chunk_id == "chk_001"
    assert chunk.text == "Hello world"


def test_ingest_chunks_skips_duplicates(tmp_path):
    service = DocumentIngestService("proj_dedup", upload_root=str(tmp_path / "uploads"))

    chunks = [
        DocumentChunk(
            chunk_id="chk_a",
            doc_id="doc_1",
            source_id="src_1",
            text="First chunk",
            index=0,
            char_start=0,
            char_end=11,
        ),
        DocumentChunk(
            chunk_id="chk_b",
            doc_id="doc_1",
            source_id="src_1",
            text="Second chunk",
            index=1,
            char_start=12,
            char_end=24,
        ),
    ]

    inserted = service.ingest_chunks(chunks)
    assert inserted == 2
    assert len(service.load_chunks()) == 2

    # Re-ingest same chunks
    inserted = service.ingest_chunks(chunks)
    assert inserted == 0
    assert len(service.load_chunks()) == 2

    # Add one new chunk
    new_chunks = [
        DocumentChunk(
            chunk_id="chk_c",
            doc_id="doc_1",
            source_id="src_1",
            text="Third chunk",
            index=2,
            char_start=25,
            char_end=36,
        ),
    ]
    inserted = service.ingest_chunks(new_chunks)
    assert inserted == 1
    assert len(service.load_chunks()) == 3


def test_ingest_chunks_empty_list(tmp_path):
    service = DocumentIngestService("proj_empty", upload_root=str(tmp_path / "uploads"))
    assert service.ingest_chunks([]) == 0
