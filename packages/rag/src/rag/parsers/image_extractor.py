"""Lightweight, memory-safe PDF diagram and image extraction using PyMuPDF (fitz)."""

import hashlib
import re
from dataclasses import dataclass

import fitz
import structlog

logger = structlog.get_logger(__name__)

# Pattern to locate nearby figure or table labels on the same page
FIGURE_HINT_PATTERN = re.compile(
    r"(?:Figure|Fig\.|Chart|Diagram|Graph|Structure|Scheme)\s+[0-9A-Za-z\.\-\:]+[^\n]{0,120}",
    re.IGNORECASE,
)


@dataclass
class ExtractedFigure:
    """Represents a candidate diagram or figure extracted from a document page."""

    page_number: int
    image_bytes: bytes
    image_hash: str
    image_format: str
    width: int
    height: int
    caption_hint: str = ""


class PDFImageExtractor:
    """Extracts, filters, and deduplicates diagrams and figures from PDF bytes."""

    def __init__(
        self,
        min_dimension: int = 150,
        max_images_per_doc: int = 10,
        max_pixels: int = 1024,
    ) -> None:
        self.min_dimension = min_dimension
        self.max_images_per_doc = max_images_per_doc
        self.max_pixels = max_pixels

    def extract_figures(self, pdf_bytes: bytes) -> list[ExtractedFigure]:
        """Extracts high-signal diagrams, skipping tiny icons, lines, and duplicates."""
        figures: list[ExtractedFigure] = []
        seen_hashes: set[str] = set()

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            logger.error("Failed to open PDF with PyMuPDF", error=str(e))
            return []

        try:
            for page_idx in range(len(doc)):
                if len(figures) >= self.max_images_per_doc:
                    break

                page = doc[page_idx]
                page_num = page_idx + 1

                # Gather potential figure captions from the text on this page
                page_text = page.get_text() or ""
                caption_hints = FIGURE_HINT_PATTERN.findall(page_text)
                caption_hint = caption_hints[0].strip() if caption_hints else ""

                # Scan embedded raster images
                image_list = page.get_images(full=True)
                for img_info in image_list:
                    if len(figures) >= self.max_images_per_doc:
                        break

                    xref = img_info[0]
                    try:
                        base_image = doc.extract_image(xref)
                    except Exception as e:
                        logger.debug("Failed to extract image xref", xref=xref, error=str(e))
                        continue

                    if not base_image:
                        continue

                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)
                    img_bytes = base_image.get("image", b"")
                    img_ext = base_image.get("ext", "png")

                    # Filter 1: Dimension check (skip icons, bullets, tiny logos)
                    if width < self.min_dimension or height < self.min_dimension:
                        continue

                    # Filter 2: Aspect ratio check (skip thin divider lines or banners)
                    aspect = max(width, height) / max(min(width, height), 1)
                    if aspect > 8.0:
                        continue

                    # Filter 3: Deduplication via SHA-256 hash (skip repeated company logos)
                    img_hash = hashlib.sha256(img_bytes).hexdigest()
                    if img_hash in seen_hashes:
                        continue
                    seen_hashes.add(img_hash)

                    # Downscale to max_pixels if excessively large to keep memory low
                    processed_bytes = img_bytes
                    if max(width, height) > self.max_pixels:
                        try:
                            pix = fitz.Pixmap(img_bytes)
                            scale = self.max_pixels / max(width, height)
                            # Create scaled down pixmap
                            target_w = max(1, int(width * scale))
                            target_h = max(1, int(height * scale))
                            scaled_pix = fitz.Pixmap(
                                pix.colorspace, (0, 0, target_w, target_h), pix.alpha
                            )
                            # Export as png bytes
                            processed_bytes = scaled_pix.tobytes(output="png")
                            img_ext = "png"
                            width, height = target_w, target_h
                            del scaled_pix
                            del pix
                        except Exception as scale_err:
                            logger.debug("Downscale failed, keeping original", error=str(scale_err))

                    figures.append(
                        ExtractedFigure(
                            page_number=page_num,
                            image_bytes=processed_bytes,
                            image_hash=img_hash,
                            image_format=img_ext,
                            width=width,
                            height=height,
                            caption_hint=caption_hint,
                        )
                    )

            logger.info("Extracted document figures", total=len(figures))
            return figures

        finally:
            doc.close()
