import io
import re
from typing import Any

import pymupdf
from pypdf import PdfReader

from packages.rag.src.rag.parsers.base import ParsedDocument, ParsedSection

# Standard clinical section & document heading regex
SECTION_HEADING_REGEX = re.compile(
    r"(?:^|\n)("
    r"(?:[0-9]{1,2}(?:\.[0-9]{1,2})*\s+[A-Za-z][A-Za-z0-9\s,\-\/\(\)]+)|"
    r"(?:BOXED WARNING|WARNINGS? AND PRECAUTIONS?|CONTRAINDICATIONS?|INDICATIONS? AND USAGE|ADVERSE REACTIONS?|DRUG INTERACTIONS?|USE IN SPECIFIC POPULATIONS?|OVERDOSAGE|CLINICAL PHARMACOLOGY|NONCLINICAL TOXICOLOGY|CLINICAL STUDIES|DOSAGE AND ADMINISTRATION|DOSAGE FORMS AND STRENGTHS|DESCRIPTION)|"
    r"(?:[A-Za-z0-9\s]+ is contraindicated in patients with:?)"
    r")(?:\n|$)",
    re.IGNORECASE,
)

GENERIC_SCANNER_TITLES = {
    "cpy document",
    "untitled",
    "untitled document",
    "untitled pdf",
    "document",
    "scan",
    "scanned document",
    "image",
}


class PDFParser:
    """
    Parses PDF documents, extracting structure-aware sections and headings with page tracking.
    Uses PyMuPDF as high-performance primary engine with pypdf fallback.
    Detects scanned image PDFs that lack embedded digital text layers.
    """

    def parse(self, pdf_bytes: bytes, title: str = "Untitled PDF") -> ParsedDocument:
        sections: list[ParsedSection] = []
        doc_title = title
        total_pages = 0
        is_scanned = False

        # Determine if caller provided a generic placeholder title
        is_generic_title = (
            not title
            or title.strip().lower() in GENERIC_SCANNER_TITLES
            or title == "Untitled PDF"
        )

        # 1. Primary Engine: PyMuPDF
        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            total_pages = len(doc)

            # Metadata inspection for title
            if is_generic_title and doc.metadata:
                raw_meta_title = (doc.metadata.get("title") or "").strip()
                if (
                    raw_meta_title
                    and raw_meta_title.lower() not in GENERIC_SCANNER_TITLES
                    and not raw_meta_title.lower().startswith("microsoft word")
                ):
                    doc_title = raw_meta_title

            # Page-by-page text extraction
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_num = page_idx + 1
                page_text = page.get_text("text") or ""
                cleaned_text = page_text.strip()
                if not cleaned_text:
                    continue

                page_sections = self._extract_page_sections(
                    cleaned_text, page_idx=page_num, doc_title=doc_title
                )
                sections.extend(page_sections)

            doc.close()
        except Exception:
            # 2. Fallback Engine: pypdf
            try:
                stream = io.BytesIO(pdf_bytes)
                reader = PdfReader(stream)
                total_pages = len(reader.pages)

                if is_generic_title and reader.metadata and reader.metadata.title:
                    raw_meta_title = str(reader.metadata.title).strip()
                    if (
                        raw_meta_title
                        and raw_meta_title.lower() not in GENERIC_SCANNER_TITLES
                        and not raw_meta_title.lower().startswith("microsoft word")
                    ):
                        doc_title = raw_meta_title

                for p_idx, pypdf_page in enumerate(reader.pages, start=1):
                    page_text = pypdf_page.extract_text() or ""
                    cleaned_text = page_text.strip()
                    if not cleaned_text:
                        continue

                    page_sections = self._extract_page_sections(
                        cleaned_text, page_idx=p_idx, doc_title=doc_title
                    )
                    sections.extend(page_sections)
            except Exception:
                pass

        # Detect whether the PDF is a scanned image document without digital text
        if total_pages > 0 and len(sections) == 0:
            is_scanned = True

        metadata: dict[str, Any] = {
            "page_count": total_pages,
            "has_text": bool(sections),
            "is_scanned": is_scanned,
        }

        return ParsedDocument(
            title=doc_title,
            file_type="application/pdf",
            sections=sections,
            metadata=metadata,
        )

    def _extract_page_sections(
        self, cleaned_text: str, page_idx: int, doc_title: str
    ) -> list[ParsedSection]:
        """Splits page text into structure-aware parsed sections."""
        matches = list(SECTION_HEADING_REGEX.finditer(cleaned_text))
        if not matches:
            return [
                ParsedSection(
                    title=f"Page {page_idx}",
                    content=cleaned_text,
                    section_path=f"{doc_title} > Page {page_idx}",
                    page_number=page_idx,
                )
            ]

        sections: list[ParsedSection] = []
        last_end = 0
        current_title = f"Page {page_idx}"

        for match in matches:
            start = match.start()
            raw_heading = match.group(1).strip()
            first_heading_line = raw_heading.split("\n")[0].strip()

            if "is contraindicated in patients with" in first_heading_line.lower():
                heading_title = "4 CONTRAINDICATIONS"
            else:
                heading_title = first_heading_line

            preceding_text = cleaned_text[last_end:start].strip()
            if preceding_text:
                sections.append(
                    ParsedSection(
                        title=current_title,
                        content=preceding_text,
                        section_path=f"{doc_title} > {current_title}",
                        page_number=page_idx,
                    )
                )

            current_title = heading_title
            last_end = start

        trailing_text = cleaned_text[last_end:].strip()
        if trailing_text:
            sections.append(
                ParsedSection(
                    title=current_title,
                    content=trailing_text,
                    section_path=f"{doc_title} > {current_title}",
                    page_number=page_idx,
                )
            )

        return sections
