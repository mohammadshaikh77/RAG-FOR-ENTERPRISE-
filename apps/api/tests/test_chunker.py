from packages.rag.src.rag.chunker import StructureAwareChunker
from packages.rag.src.rag.parsers.base import ParsedDocument, ParsedSection


def test_chunker_basic_structure() -> None:
    doc = ParsedDocument(
        title="Test Drug",
        file_type="text/markdown",
        sections=[
            ParsedSection(
                title="Indications",
                content="This drug is indicated for the treatment of hypertension.",
                section_path="Test Drug > Indications",
                page_number=1,
            ),
            ParsedSection(
                title="Contraindications",
                content="Do not administer to patients with severe hypersensitivity.",
                section_path="Test Drug > Contraindications",
                page_number=2,
            ),
        ],
    )

    chunker = StructureAwareChunker(max_tokens=100, overlap_tokens=10)
    chunks = chunker.chunk(doc)

    assert len(chunks) == 2
    assert chunks[0].section_title == "Indications"
    assert chunks[0].page_number == 1
    assert "hypertension" in chunks[0].content
    assert chunks[1].section_title == "Contraindications"
    assert chunks[1].page_number == 2


def test_chunker_large_section_splitting() -> None:
    long_text = " ".join([f"Sentence {i} describing adverse reactions." for i in range(100)])
    doc = ParsedDocument(
        title="Long Drug Label",
        file_type="text/markdown",
        sections=[
            ParsedSection(
                title="Adverse Reactions",
                content=long_text,
                section_path="Long Drug Label > Adverse Reactions",
                page_number=1,
            )
        ],
    )

    chunker = StructureAwareChunker(max_tokens=50, overlap_tokens=10)
    chunks = chunker.chunk(doc)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.section_title == "Adverse Reactions"
        assert chunk.token_count <= 60


def test_chunker_empty_document() -> None:
    doc = ParsedDocument(
        title="Empty",
        file_type="text/markdown",
        sections=[],
    )
    chunker = StructureAwareChunker()
    assert chunker.chunk(doc) == []
