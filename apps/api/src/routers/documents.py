import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.auth.deps import get_optional_user
from apps.api.src.db.session import get_db
from apps.api.src.models.document import Document
from apps.api.src.models.organization import Organization
from apps.api.src.models.user import User
from packages.rag.src.rag.ingestion import IngestionService

router = APIRouter(prefix="/documents", tags=["Documents"])
ingestion_service = IngestionService()


class DocumentResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    title: str
    file_type: str
    file_hash: str
    status: str
    chunk_count: int
    error_message: str | None = None


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    org_id: uuid.UUID | None = Form(None),
    title: str | None = Form(None),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Uploads a document scoped strictly to the authenticated tenant organization."""
    effective_org_id = current_user.org_id if current_user else org_id
    if not effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required via authentication token or org_id parameter",
        )

    # Ensure organization exists
    org = await db.get(Organization, effective_org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {effective_org_id} not found",
        )

    content_bytes = await file.read()
    filename = file.filename or "uploaded_file"
    doc_title = title or filename

    # Infer file type
    content_type = file.content_type or "text/plain"
    if filename.endswith(".pdf"):
        content_type = "application/pdf"
    elif filename.endswith(".html") or filename.endswith(".htm"):
        content_type = "text/html"

    doc, _ = await ingestion_service.ingest(
        session=db,
        org_id=effective_org_id,
        raw_content=content_bytes,
        file_type=content_type,
        title=doc_title,
    )

    return DocumentResponse(
        id=doc.id,
        org_id=doc.org_id,
        title=doc.title,
        file_type=doc.file_type,
        file_hash=doc.file_hash,
        status=doc.status.value,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    org_id: uuid.UUID | None = None,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """Lists all documents strictly isolated to the requesting tenant."""
    effective_org_id = current_user.org_id if current_user else org_id
    if not effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID required",
        )

    stmt = (
        select(Document)
        .where(Document.org_id == effective_org_id)
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [
        DocumentResponse(
            id=d.id,
            org_id=d.org_id,
            title=d.title,
            file_type=d.file_type,
            file_hash=d.file_hash,
            status=d.status.value,
            chunk_count=d.chunk_count,
            error_message=d.error_message,
        )
        for d in docs
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    org_id: uuid.UUID | None = None,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Fetches document details.
    Enforces tenant boundary inside the query: documents belonging to other orgs return 404!
    """
    effective_org_id = current_user.org_id if current_user else org_id
    if not effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID required",
        )

    stmt = select(Document).where(
        Document.id == document_id,
        Document.org_id == effective_org_id,
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        # Cross-tenant direct access attempt returns 404 to avoid leaking existence
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentResponse(
        id=doc.id,
        org_id=doc.org_id,
        title=doc.title,
        file_type=doc.file_type,
        file_hash=doc.file_hash,
        status=doc.status.value,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
    )
