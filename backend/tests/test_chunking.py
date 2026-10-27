from backend.app.services.chunking import (
    get_chunker,
    RecursiveChunker,
    SemanticChunker,
    AgenticChunker,
)


def test_recursive_chunker():
    sample_text = (
        "Tesla reported record revenue of $25.2B in Q3 2024.\n\n"
        "The Model Y became the best-selling vehicle globally with 350,000 units sold.\n\n"
        "Supply chain issues caused a 12% increase in production costs."
    )
    chunker = get_chunker(strategy="recursive", chunk_size=80, chunk_overlap=10)
    assert isinstance(chunker, RecursiveChunker)

    chunks = chunker.split_text(sample_text, metadata={"source": "test.txt"})
    assert len(chunks) >= 2
    for c in chunks:
        assert c.metadata.get("source") == "test.txt"
        assert len(c.page_content) > 0


def test_chunker_factory():
    rec = get_chunker("recursive")
    sem = get_chunker("semantic")
    age = get_chunker("agentic")

    assert isinstance(rec, RecursiveChunker)
    assert isinstance(sem, SemanticChunker)
    assert isinstance(age, AgenticChunker)
