"""PII Redaction Guardrail for Cite Platform.

Detects and masks common Personally Identifiable Information (PII) including
emails, phone numbers, SSN/ID numbers, and credit/debit card numbers in both
uploaded document text and model-generated answers.
"""

import re
import uuid

import structlog

logger = structlog.get_logger(__name__)

# Compile regex patterns for efficient reuse
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b",
    re.IGNORECASE,
)

# Standard international and US phone number formats
PHONE_PATTERN = re.compile(
    r"(?:(?:\+?1\s*(?:[.-]\s*)?)?(?:\(\s*([2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9])\s*\)|([2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9]))\s*(?:[.-]\s*)?)?([2-9]1[02-9]|[2-9][02-9]1|[2-9][02-9]{2})\s*(?:[.-]\s*)?([0-9]{4})(?:\s*(?:#|x\.?|ext\.?|extension)\s*(\d+))?\b"
)

# Social Security Numbers and national ID-like patterns (XXX-XX-XXXX)
SSN_PATTERN = re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")

# Credit/debit card numbers (13 to 19 digits with optional hyphens or spaces)
CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b(?:\d{4}[-\s]?){2}\d{4}[-\s]?\d{3}\b")


class PIIRedactor:
    """Configurable PII detection and masking service."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def redact(
        self,
        text: str,
        org_id: uuid.UUID | str | None = None,
        source: str = "text",
    ) -> tuple[str, int, dict[str, int]]:
        """Redacts sensitive PII from text.

        Returns:
            (redacted_text, total_redacted_count, breakdown_dict)
        """
        if not self.enabled or not text:
            return text, 0, {}

        redacted = text
        counts = {
            "emails": 0,
            "phones": 0,
            "ssn_ids": 0,
            "cards": 0,
        }

        # 1. Redact Emails
        redacted, counts["emails"] = EMAIL_PATTERN.subn("[REDACTED_EMAIL]", redacted)

        # 2. Redact SSN / IDs
        redacted, counts["ssn_ids"] = SSN_PATTERN.subn("[REDACTED_ID]", redacted)

        # 3. Redact Credit / Card Numbers
        redacted, counts["cards"] = CARD_PATTERN.subn("[REDACTED_CARD]", redacted)

        # 4. Redact Phone Numbers
        redacted, counts["phones"] = PHONE_PATTERN.subn("[REDACTED_PHONE]", redacted)

        total_redacted = sum(counts.values())

        if total_redacted > 0:
            logger.info(
                "PII redacted successfully",
                org_id=str(org_id) if org_id else None,
                source=source,
                total_redacted=total_redacted,
                counts=counts,
            )

        return redacted, total_redacted, counts


def redact_pii(
    text: str,
    enabled: bool = True,
    org_id: uuid.UUID | str | None = None,
    source: str = "text",
) -> tuple[str, int]:
    """Convenience helper function to redact PII from text."""
    redactor = PIIRedactor(enabled=enabled)
    redacted_text, count, _ = redactor.redact(text, org_id=org_id, source=source)
    return redacted_text, count
