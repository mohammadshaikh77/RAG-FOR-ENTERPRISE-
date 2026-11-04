import io

from pypdf import PdfReader

from packages.rag.src.rag.parsers.base import ParsedDocument, ParsedSection


class PDFParser:
    """Parses PDF documents, extracting text and tracking page numbers."""

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
            if cleaned_text:
                sections.append(
                    ParsedSection(
                        title=f"Page {page_idx}",
                        content=cleaned_text,
                        section_path=f"{doc_title} > Page {page_idx}",
                        page_number=page_idx,
                    )
                )

        return ParsedDocument(
            title=doc_title,
            file_type="application/pdf",
            sections=sections,
        )
