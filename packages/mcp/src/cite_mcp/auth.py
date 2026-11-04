"""Authentication and tenant resolution utilities for the Cite MCP server."""

import os
import uuid

import structlog
from jose import JWTError, jwt

from apps.api.src.config import get_settings

logger = structlog.get_logger(__name__)


def resolve_tenant_id(
    provided_tenant_id: str | None = None,
    default_tenant_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Resolves and validates the target tenant organization UUID for an MCP tool invocation.

    Priority:
    1. Explicit provided_tenant_id parameter
    2. Default configured tenant_id on the server instance
    3. CITE_TENANT_ID environment variable
    4. CITE_AUTH_TOKEN / CITE_API_KEY environment variable (JWT bearer token or org UUID)

    Raises:
        PermissionError: If no valid tenant identity can be established.
    """
    raw_id: str | None = provided_tenant_id

    # 1. Fallback to default tenant if set
    if not raw_id and default_tenant_id:
        return default_tenant_id

    # 2. Check environment variable CITE_TENANT_ID
    if not raw_id:
        raw_id = os.getenv("CITE_TENANT_ID")

    # 3. Check CITE_AUTH_TOKEN or CITE_API_KEY
    if not raw_id:
        token = os.getenv("CITE_AUTH_TOKEN") or os.getenv("CITE_API_KEY")
        if token:
            raw_id = _extract_org_id_from_token(token)

    if not raw_id:
        raise PermissionError(
            "Authentication required: No valid tenant organization specified. "
            "Please provide 'tenant_id' argument or configure CITE_TENANT_ID / CITE_AUTH_TOKEN."
        )

    try:
        return uuid.UUID(str(raw_id).strip())
    except ValueError as e:
        raise PermissionError(f"Invalid tenant organization ID format: {raw_id}") from e


def _extract_org_id_from_token(token: str) -> str | None:
    """Attempts to decode a JWT token to extract the tenant 'org_id' claim."""
    clean_token = token.strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()

    # First check if the token itself is already a raw UUID
    try:
        uuid.UUID(clean_token)
        return clean_token
    except ValueError:
        pass

    # Attempt JWT decode
    settings = get_settings()
    try:
        payload = jwt.decode(
            clean_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        org_id: str | None = payload.get("org_id")
        return org_id
    except JWTError as e:
        logger.warning("Failed to decode tenant JWT in MCP auth", error=str(e))
        return None
