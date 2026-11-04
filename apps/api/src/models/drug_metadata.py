"""SQLAlchemy model for structured drug label clinical metadata."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.src.models.base import Base


class DrugMetadata(Base):
    """Structured clinical and regulatory drug metadata extracted from labels."""

    __tablename__ = "drug_metadata"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    drug_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    generic_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    drug_class: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    has_boxed_warning: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    route: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product_ndc: Mapped[str | None] = mapped_column(String(100), nullable=True)
    manufacturer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    substance_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    boxed_warning_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_drug_metadata_org_class", "org_id", "drug_class"),
        Index("ix_drug_metadata_org_boxed", "org_id", "has_boxed_warning"),
    )
