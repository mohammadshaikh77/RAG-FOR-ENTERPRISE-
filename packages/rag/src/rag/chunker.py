import re
from dataclasses import dataclass, field
from typing import Any

from packages.rag.src.rag.parsers.base import ParsedDocument, ParsedSection


@dataclass
class ChunkItem:
    """Represents an embedded unit with contextual metadata."""

    chunk_index: int
    content: str
    section_title: str | None
    section_path: str | None
    page_number: int | None
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


class StructureAwareChunker:
    """Chunks documents respecting section boundaries, headings, and page context."""

    def __init__(self, max_tokens: int = 220, overlap_tokens: int = 30) -> None:
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def _estimate_tokens(self, text: str) -> int:
        """Approximates token count via whitespace splitting."""
        return len(text.split())

    def _split_into_paragraphs(self, text: str) -> list[str]:
        return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    def _split_into_sentences(self, text: str) -> list[str]:
        # Simple sentence splitter on punctuation followed by space
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _chunk_section(self, section: ParsedSection, start_index: int) -> list[ChunkItem]:
        paragraphs = self._split_into_paragraphs(section.content)
        if not paragraphs:
            return []

        chunks: list[ChunkItem] = []
        current_chunk_words: list[str] = []
        current_chunk_tokens = 0
        chunk_idx = start_index

        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)

            if current_chunk_tokens + para_tokens <= self.max_tokens:
                current_chunk_words.append(para)
                current_chunk_tokens += para_tokens
            else:
                # If a single paragraph exceeds max_tokens, split into sentences
                if para_tokens > self.max_tokens:
                    sentences = self._split_into_sentences(para)
                    for sentence in sentences:
                        sent_tokens = self._estimate_tokens(sentence)
                        if current_chunk_tokens + sent_tokens <= self.max_tokens:
                            current_chunk_words.append(sentence)
                            current_chunk_tokens += sent_tokens
                        else:
                            if current_chunk_words:
                                chunk_text = "\n\n".join(current_chunk_words).strip()
                                chunks.append(
                                    ChunkItem(
                                        chunk_index=chunk_idx,
                                        content=chunk_text,
                                        section_title=section.title,
                                        section_path=section.section_path,
                                        page_number=section.page_number,
                                        token_count=current_chunk_tokens,
                                        metadata=dict(section.metadata),
                                    )
                                )
                                chunk_idx += 1
                                # Overlap from end of current chunk
                                overlap_words = current_chunk_words[-1].split()[
                                    -self.overlap_tokens :
                                ]
                                current_chunk_words = (
                                    [" ".join(overlap_words)] if overlap_words else []
                                )
                                current_chunk_tokens = len(overlap_words)

                            current_chunk_words.append(sentence)
                            current_chunk_tokens += sent_tokens
                else:
                    # Flush accumulated paragraphs
                    chunk_text = "\n\n".join(current_chunk_words).strip()
                    chunks.append(
                        ChunkItem(
                            chunk_index=chunk_idx,
                            content=chunk_text,
                            section_title=section.title,
                            section_path=section.section_path,
                            page_number=section.page_number,
                            token_count=current_chunk_tokens,
                            metadata=dict(section.metadata),
                        )
                    )
                    chunk_idx += 1
                    overlap_words = current_chunk_words[-1].split()[-self.overlap_tokens :]
                    current_chunk_words = (
                        [" ".join(overlap_words), para] if overlap_words else [para]
                    )
                    current_chunk_tokens = len(overlap_words) + para_tokens

        # Flush final remaining words
        if current_chunk_words:
            chunk_text = "\n\n".join(current_chunk_words).strip()
            if chunk_text:
                chunks.append(
                    ChunkItem(
                        chunk_index=chunk_idx,
                        content=chunk_text,
                        section_title=section.title,
                        section_path=section.section_path,
                        page_number=section.page_number,
                        token_count=self._estimate_tokens(chunk_text),
                        metadata=dict(section.metadata),
                    )
                )

        return chunks

    def chunk(self, parsed_doc: ParsedDocument) -> list[ChunkItem]:
        """Processes all sections into indexed chunks preserving hierarchy."""
        all_chunks: list[ChunkItem] = []
        current_index = 0

        for section in parsed_doc.sections:
            section_chunks = self._chunk_section(section, start_index=current_index)
            all_chunks.extend(section_chunks)
            current_index = len(all_chunks)

        return all_chunks
