"""Citation extraction, verification against retrieved chunks, and refusal detection."""

import re
from typing import Any

from pydantic import BaseModel


class Citation(BaseModel):
    """Structured citation referencing supporting clinical text."""

    document_title: str
    section_title: str
    quoted_span: str
    document_id: str | None = None
    is_verified: bool = False


# Matches patterns like:
# [Document: Lisinopril FDA Label | Section: Boxed Warning | "When used in pregnancy..."]
# or [Lisinopril | Boxed Warning | "When used in pregnancy..."]
CITATION_REGEX = re.compile(
    r"\[(?:Document:\s*)?([^|]+?)\s*\|\s*(?:Section:\s*)?([^|]+?)\s*\|\s*[\"“]([\s\S]+?)[\"”]\s*\]",
    re.IGNORECASE,
)

REFUSAL_PHRASES = [
    "i cannot answer this",
    "i do not have sufficient evidence",
    "cannot be answered based on the provided",
    "no relevant evidence was found",
    "not mentioned in the provided",
    "provided documents do not contain",
    "insufficient evidence",
    "i am unable to answer",
    "couldn't find enough information",
    "could not find enough information",
    "not found in your documents",
    "no information available",
]


def is_refusal(text: str) -> bool:
    """Checks whether the response constitutes an explicit refusal."""
    normalized = text.lower()
    return any(phrase in normalized for phrase in REFUSAL_PHRASES)


def extract_citations(
    text: str, retrieved_chunks: list[dict[str, Any]] | None = None
) -> list[Citation]:
    """Extracts citation markers from answer text and verifies them against retrieved content."""
    matches = CITATION_REGEX.findall(text)
    citations: list[Citation] = []

    for doc_title, sec_title, span in matches:
        doc_title_clean = doc_title.strip()
        sec_title_clean = sec_title.strip()
        span_clean = span.strip()

        # Check if the quoted span exists in retrieved chunks
        is_verified = False
        doc_id: str | None = None

        if retrieved_chunks:
            span_lower = span_clean.lower()
            for chunk in retrieved_chunks:
                chunk_content = chunk.get("content", "").lower()
                # Exact or substantial substring match (first 30 characters)
                if span_lower in chunk_content or (
                    len(span_lower) > 30 and span_lower[:30] in chunk_content
                ):
                    is_verified = True
                    doc_id = chunk.get("document_id")
                    break

        citations.append(
            Citation(
                document_title=doc_title_clean,
                section_title=sec_title_clean,
                quoted_span=span_clean,
                document_id=doc_id,
                is_verified=is_verified,
            )
        )

    return citations
