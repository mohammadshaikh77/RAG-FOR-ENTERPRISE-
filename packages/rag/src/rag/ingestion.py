import hashlib
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.config import get_settings
from apps.api.src.logging import get_logger
from apps.api.src.models.chunk import DocumentChunk
from apps.api.src.models.document import Document, DocumentStatus
from apps.api.src.models.drug_metadata import DrugMetadata
from packages.llm.src.llm.vision import VisionCaptioner, get_vision_captioner
from packages.rag.src.rag.chunker import StructureAwareChunker
from packages.rag.src.rag.embeddings import Embedder, get_embedder
from packages.rag.src.rag.parsers.base import ParsedDocument
from packages.rag.src.rag.parsers.fda_parser import FDALabelParser
from packages.rag.src.rag.parsers.html_parser import HTMLParser
from packages.rag.src.rag.parsers.image_extractor import PDFImageExtractor
from packages.rag.src.rag.parsers.pdf_parser import PDFParser
from packages.rag.src.rag.parsers.text_parser import TextParser

logger = get_logger("cite.rag.ingestion")
settings = get_settings()


class IngestionService:
    """End-to-end idempotent document ingestion pipeline."""

    def __init__(
        self,
        embedder: Embedder | None = None,
        chunker: StructureAwareChunker | None = None,
        vision_captioner: VisionCaptioner | None = None,
    ) -> None:
        self.embedder = embedder or get_embedder()
        self.chunker = chunker or StructureAwareChunker()
        self.text_parser = TextParser()
        self.html_parser = HTMLParser()
        self.pdf_parser = PDFParser()
        self.fda_parser = FDALabelParser()
        self.image_extractor = PDFImageExtractor(
            min_dimension=settings.multimodal_min_dimension,
            max_images_per_doc=settings.multimodal_max_images_per_doc,
        )
        self.vision_captioner = vision_captioner or get_vision_captioner()

    def compute_hash(self, content: bytes | str) -> str:
        """Computes SHA-256 hash for idempotency checking."""
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content
        return hashlib.sha256(content_bytes).hexdigest()

    def parse_content(
        self,
        content: bytes | str | dict[str, Any],
        file_type: str,
        title: str = "Untitled Document",
    ) -> ParsedDocument:
        """Dispatches to appropriate parser based on file type."""
        normalized_type = file_type.lower()

        if "fda" in normalized_type or isinstance(content, dict):
            assert isinstance(content, dict)
            return self.fda_parser.parse(content)
        elif "pdf" in normalized_type or (
            isinstance(content, bytes) and content.startswith(b"%PDF")
        ):
            assert isinstance(content, bytes)
            return self.pdf_parser.parse(content, title=title)
        elif "html" in normalized_type or "htm" in normalized_type:
            text_content = content.decode("utf-8") if isinstance(content, bytes) else str(content)
            return self.html_parser.parse(text_content, title=title)
        else:
            text_content = content.decode("utf-8") if isinstance(content, bytes) else str(content)
            return self.text_parser.parse(text_content, title=title)

    async def ingest(
        self,
        session: AsyncSession,
        org_id: uuid.UUID,
        raw_content: bytes | str | dict[str, Any],
        file_type: str,
        title: str,
        source_url: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> tuple[Document, bool]:
        """
        Parses, chunks, embeds, and persists document and chunks.
        Returns (Document, is_duplicate).
        """
        if isinstance(raw_content, dict):
            import json

            serialized = json.dumps(raw_content, sort_keys=True)
            file_hash = self.compute_hash(serialized)
        else:
            file_hash = self.compute_hash(raw_content)

        # 1. Idempotency Check
        stmt = select(Document).where(
            Document.org_id == org_id,
            Document.file_hash == file_hash,
        )
        result = await session.execute(stmt)
        existing_doc = result.scalar_one_or_none()

        if existing_doc and existing_doc.status == DocumentStatus.COMPLETED:
            logger.info(
                "Document already exists and completed. Skipping re-ingestion.",
                document_id=str(existing_doc.id),
                org_id=str(org_id),
                file_hash=file_hash,
            )
            return existing_doc, True

        # Create or update document record
        if existing_doc:
            doc = existing_doc
            doc.status = DocumentStatus.PROCESSING
            doc.error_message = None
        else:
            doc = Document(
                id=uuid.uuid4(),
                org_id=org_id,
                title=title,
                source_url=source_url,
                file_type=file_type,
                file_hash=file_hash,
                status=DocumentStatus.PROCESSING,
                doc_metadata=extra_metadata or {},
            )
            session.add(doc)
            await session.flush()

        try:
            # 2. Parse
            parsed = self.parse_content(raw_content, file_type=file_type, title=title)
            merged_metadata = {**doc.doc_metadata, **parsed.metadata}
            doc.doc_metadata = merged_metadata
            doc.title = parsed.title or title

            # 3. Chunk
            chunk_items = self.chunker.chunk(parsed)
            if not chunk_items:
                doc.status = DocumentStatus.COMPLETED
                doc.chunk_count = 0
                await session.commit()
                return doc, False

            # 4. Embed
            texts_to_embed = [c.content for c in chunk_items]
            embeddings = self.embedder.embed_texts(texts_to_embed)

            # 5. Persist Chunks
            chunks_to_insert: list[DocumentChunk] = []
            for item, emb in zip(chunk_items, embeddings, strict=False):
                chunk = DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=doc.id,
                    org_id=org_id,
                    chunk_index=item.chunk_index,
                    section_title=item.section_title,
                    section_path=item.section_path,
                    page_number=item.page_number,
                    content=item.content,
                    token_count=item.token_count,
                    chunk_metadata={
                        **item.metadata,
                        "embedding_model": self.embedder.model_name,
                    },
                    embedding=emb,
                )
                chunks_to_insert.append(chunk)

            # 6. Optional Multimodal Diagram Extraction and Vision Captioning
            if (
                settings.multimodal_enabled
                and isinstance(raw_content, bytes)
                and raw_content.startswith(b"%PDF")
            ):
                try:
                    figures = self.image_extractor.extract_figures(raw_content)
                    if figures:
                        logger.info("Processing document figures with vision captioner", count=len(figures))
                        figure_texts: list[str] = []
                        figure_metas: list[dict[str, Any]] = []

                        start_idx = len(chunks_to_insert)
                        for fig in figures:
                            caption = await self.vision_captioner.caption_image(
                                image_bytes=fig.image_bytes,
                                image_hash=fig.image_hash,
                                image_format=fig.image_format,
                                caption_hint=fig.caption_hint,
                            )
                            if fig.caption_hint:
                                chunk_text = f"Figure on Page {fig.page_number}: {fig.caption_hint}\nVisual Description: {caption}"
                            else:
                                chunk_text = f"Figure on Page {fig.page_number}\nVisual Description: {caption}"

                            figure_texts.append(chunk_text)
                            figure_metas.append({
                                "is_figure": True,
                                "image_hash": fig.image_hash,
                                "page_number": fig.page_number,
                                "caption_hint": fig.caption_hint,
                                "width": fig.width,
                                "height": fig.height,
                                "embedding_model": self.embedder.model_name,
                            })

                        if figure_texts:
                            fig_embeddings = self.embedder.embed_texts(figure_texts)
                            for i, (txt, emb, f_meta) in enumerate(
                                zip(figure_texts, fig_embeddings, figure_metas, strict=False)
                            ):
                                fig_chunk = DocumentChunk(
                                    id=uuid.uuid4(),
                                    document_id=doc.id,
                                    org_id=org_id,
                                    chunk_index=start_idx + i,
                                    section_title=f"Figure (Page {f_meta['page_number']})",
                                    section_path=f"{doc.title} > Figure (Page {f_meta['page_number']})",
                                    page_number=f_meta["page_number"],
                                    content=txt,
                                    token_count=len(txt.split()),
                                    chunk_metadata=f_meta,
                                    embedding=emb,
                                )
                                chunks_to_insert.append(fig_chunk)

                except Exception as mm_err:
                    logger.warning(
                        "Multimodal figure extraction error; continuing with text chunks",
                        error=str(mm_err),
                    )

            session.add_all(chunks_to_insert)
            doc.chunk_count = len(chunks_to_insert)

            # Extract and persist structured drug metadata if available
            if "drug_name" in merged_metadata or "generic_name" in merged_metadata:
                raw_class = merged_metadata.get("drug_class") or merged_metadata.get("drug_classes")
                if isinstance(raw_class, list):
                    drug_class_str = raw_class[0] if raw_class else "Unknown Class"
                else:
                    drug_class_str = str(raw_class or "Unknown Class")

                boxed_warning_summary = None
                if parsed.sections:
                    for s in parsed.sections:
                        if "boxed warning" in s.title.lower():
                            boxed_warning_summary = s.content[:500]
                            break

                routes = merged_metadata.get("routes")
                route_str = (
                    routes[0]
                    if (isinstance(routes, list) and routes)
                    else (str(routes) if routes else None)
                )
                ndcs = merged_metadata.get("ndc")
                ndc_str = (
                    ndcs[0] if (isinstance(ndcs, list) and ndcs) else (str(ndcs) if ndcs else None)
                )

                drug_meta = DrugMetadata(
                    id=uuid.uuid4(),
                    org_id=org_id,
                    document_id=doc.id,
                    drug_name=merged_metadata.get("drug_name", doc.title),
                    brand_name=merged_metadata.get("drug_name", doc.title),
                    generic_name=merged_metadata.get("generic_name", doc.title),
                    drug_class=drug_class_str,
                    has_boxed_warning=bool(merged_metadata.get("boxed_warning_present", False)),
                    route=route_str,
                    product_ndc=ndc_str,
                    manufacturer_name=merged_metadata.get("manufacturer"),
                    boxed_warning_summary=boxed_warning_summary,
                )
                session.add(drug_meta)

            doc.status = DocumentStatus.COMPLETED
            await session.commit()
            await session.refresh(doc)

            logger.info(
                "Document ingested successfully",
                document_id=str(doc.id),
                chunks_created=len(chunks_to_insert),
                embedding_model=self.embedder.model_name,
            )
            return doc, False

        except Exception as e:
            await session.rollback()
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            logger.error("Document ingestion failed", error=str(e), document_id=str(doc.id))
            raise
