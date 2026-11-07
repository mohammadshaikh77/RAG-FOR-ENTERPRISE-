import io
import re
from typing import Any

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


class PDFParser:
    """Parses PDF documents, extracting structure-aware sections and headings with page tracking."""

    def parse(self, pdf_bytes: bytes, title: str = "Untitled PDF") -> ParsedDocument:
        stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(stream)

        sections: list[ParsedSection] = []
        doc_title = title

        # Check metadata for document title
        if reader.metadata and reader.metadata.title:
            doc_title = str(reader.metadata.title).strip()

        for page_idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if not text:
                continue

            cleaned_text = text.strip()
            if not cleaned_text:
                continue

            # Identify section headings on this page
            matches = list(SECTION_HEADING_REGEX.finditer(cleaned_text))
            if not matches:
                # No explicit heading found; preserve page section
                sections.append(
                    ParsedSection(
                        title=f"Page {page_idx}",
                        content=cleaned_text,
                        section_path=f"{doc_title} > Page {page_idx}",
                        page_number=page_idx,
                    )
                )
                continue

            # Split page text according to detected section headings
            last_end = 0
            current_title = f"Page {page_idx}"

            for match in matches:
                start, end = match.start(), match.end()
                raw_heading = match.group(1).strip()

                # Clean heading title (first line if multi-line)
                first_heading_line = raw_heading.split("\n")[0].strip()
                if "is contraindicated in patients with" in first_heading_line.lower():
                    heading_title = "4 CONTRAINDICATIONS"
                else:
                    heading_title = first_heading_line

                # Text preceding the heading
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

            # Trailing text for the final heading on this page
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

        return ParsedDocument(
            title=doc_title,
            file_type="application/pdf",
            sections=sections,
        )
