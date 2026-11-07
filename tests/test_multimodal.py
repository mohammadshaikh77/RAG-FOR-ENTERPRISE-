import pytest
import pymupdf

from packages.rag.src.rag.parsers.image_extractor import PDFImageExtractor
from packages.llm.src.llm.vision import VisionCaptioner


def create_synthetic_pdf_with_figures() -> bytes:
    """Creates an in-memory PDF with 1 large diagram, 1 tiny icon, and caption text."""
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=400)

    # 1. Caption text
    page.insert_text((50, 40), "Figure 1: Mean Blood Pressure Reduction Over Time", fontsize=12)

    # 2. Large diagram (200x200)
    page.draw_rect([50, 60, 250, 260], color=(0, 0, 0), width=2)
    page.insert_text((70, 160), "Active Drug: -14.2 mmHg", fontsize=10)

    # Convert to pixmap and insert as image so get_images() finds it
    large_pix = page.get_pixmap(clip=[50, 60, 250, 260], dpi=100)
    # Tiny icon (30x30)
    tiny_pix = page.get_pixmap(clip=[50, 60, 80, 90], dpi=50)

    page2 = doc.new_page(width=400, height=400)
    page2.insert_image([50, 50, 250, 250], pixmap=large_pix)
    page2.insert_image([300, 300, 330, 330], pixmap=tiny_pix)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_pdf_image_extractor_filters_small_images():
    pdf_bytes = create_synthetic_pdf_with_figures()
    extractor = PDFImageExtractor(min_dimension=150, max_images_per_doc=5)
    figures = extractor.extract_figures(pdf_bytes)

    # Should have extracted the large diagram (200x200), skipping the 30x30 tiny icon
    assert len(figures) == 1
    assert figures[0].width >= 150
    assert figures[0].height >= 150
    assert figures[0].image_format in ["png", "jpeg"]
    assert len(figures[0].image_bytes) > 0
    assert len(figures[0].image_hash) == 64  # Valid SHA-256


def test_pdf_image_extractor_deduplication():
    # If same PDF has duplicate image on multiple pages, hash deduplication skips it
    doc = pymupdf.open()
    page1 = doc.new_page(width=300, height=300)
    page1.draw_rect([50, 50, 250, 250], color=(0, 0, 0), width=2)
    pix = page1.get_pixmap(clip=[50, 50, 250, 250], dpi=100)

    page2 = doc.new_page(width=300, height=300)
    page2.insert_image([50, 50, 250, 250], pixmap=pix)

    page3 = doc.new_page(width=300, height=300)
    page3.insert_image([50, 50, 250, 250], pixmap=pix)

    pdf_bytes = doc.tobytes()
    doc.close()

    extractor = PDFImageExtractor(min_dimension=100)
    figures = extractor.extract_figures(pdf_bytes)
    # Even though inserted on 2 pages, hash deduplication ensures only 1 entry
    assert len(figures) == 1


@pytest.mark.asyncio
async def test_vision_captioner_graceful_fallback():
    # When disabled or unavailable, returns the nearby caption hint without crashing
    captioner = VisionCaptioner(api_key="")
    caption = await captioner.caption_image(
        image_bytes=b"fake-bytes",
        image_hash="fake-hash",
        caption_hint="Figure 1: Systolic Pressure",
    )
    assert caption == "Figure 1: Systolic Pressure"
