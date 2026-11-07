import pymupdf

from packages.rag.src.rag.parsers.pdf_parser import PDFParser


def test_pdf_parser_digital_text():
    # Create an in-memory PDF with digital text
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 100), "1 CLINICAL PHARMACOLOGY\nThis drug is indicated for renal cell carcinoma.")
    pdf_bytes = doc.tobytes()
    doc.close()

    parser = PDFParser()
    parsed = parser.parse(pdf_bytes, title="Nexavar_Prescribing_Info.pdf")

    assert parsed.title == "Nexavar_Prescribing_Info.pdf"
    assert parsed.metadata["page_count"] == 1
    assert parsed.metadata["has_text"] is True
    assert parsed.metadata["is_scanned"] is False
    assert len(parsed.sections) > 0


def test_pdf_parser_scanned_pdf_detection():
    # Create an in-memory PDF with only an image (no digital text)
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    # Insert an empty drawing or dummy image pixmap
    pix = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 100, 100), 0)
    page.insert_image(page.rect, pixmap=pix)
    pdf_bytes = doc.tobytes()
    doc.close()

    parser = PDFParser()
    parsed = parser.parse(pdf_bytes, title="021923_s000_Nexavar_BioPharmR.pdf")

    assert parsed.title == "021923_s000_Nexavar_BioPharmR.pdf"
    assert parsed.metadata["page_count"] == 1
    assert parsed.metadata["has_text"] is False
    assert parsed.metadata["is_scanned"] is True
    assert len(parsed.sections) == 0


def test_pdf_parser_generic_title_override_prevented():
    # PDF with internal metadata title "CPY Document"
    doc = pymupdf.open()
    doc.set_metadata({"title": "CPY Document"})
    page = doc.new_page()
    page.insert_text((50, 50), "Sample Text")
    pdf_bytes = doc.tobytes()
    doc.close()

    parser = PDFParser()
    # When uploaded with a human filename, "CPY Document" must NOT overwrite it
    parsed = parser.parse(pdf_bytes, title="021923_s000_Nexavar_BioPharmR.pdf")
    assert parsed.title == "021923_s000_Nexavar_BioPharmR.pdf"
