# Phase 3: Multi-Tenancy, Authentication, and Query-Level Isolation

## 1. Overview
Phase 3 establishes enterprise-grade multi-tenancy and cryptographic authentication for Cite. Every document, chunk, vector embedding, search query, agent trace, and eval run carries an immutable `org_id`.

## 2. Implemented Features
- **Data Models**:
  - `User`: Stored with salted bcrypt password hash, role (`admin` or `member`), and foreign key cascade to `organizations.id`.
  - `UserRole`: Enum defining role permissions. Admins can register new users to their organization; members can upload, ingest, and search documents.
- **Authentication & Security (`apps/api/src/auth/`)**:
  - `security.py`: Direct `bcrypt` password hashing and verification; HMAC-SHA256 JWT encoding and decoding.
  - `deps.py`: Fast dependency injection (`get_current_user`, `get_current_org`, `require_admin`, `get_optional_user`).
- **Auth Endpoints (`apps/api/src/routers/auth.py`)**:
  - `POST /auth/register`: Atomic registration of a new organization and its initial administrator user.
  - `POST /auth/login`: Issues bearer JWT tokens with embedded `org_id` and `role`.
  - `GET /auth/me`: Inspect authenticated identity, organization details, and permissions.
  - `POST /auth/users`: Admin-only endpoint to onboard new members into their own organization.
- **Query-Level Tenant Isolation**:
  - `retrieval.py`: Both vector similarity and PostgreSQL full-text search enforce `WHERE org_id = :org_id` at the database level.
  - Cross-tenant spoofing attempts (e.g. Org A token providing Org B in query parameter) trigger explicit HTTP 403 Forbidden.
  - `documents.py`: Fetching or downloading documents belonging to another tenant yields HTTP 404 Not Found to prevent document existence enumeration.

## 3. Verification & Adversarial Test Suite
The automated test suite in `apps/api/tests/test_multi_tenancy.py` executes 6 comprehensive adversarial scenarios:
1. **Direct Document Snooping**: Org B authenticated user attempts to fetch Org A's uploaded document by UUID $\rightarrow$ Returns HTTP 404.
2. **Search Leakage & Cross-Contamination**: Org B runs retrieval with keywords and semantic queries present only in Org A's documents $\rightarrow$ Returns 0 results.
3. **Explicit Tenant Spoofing**: Org B sends `org_id=Org_A` in retrieval payload $\rightarrow$ Intercepted by auth layer and rejected with HTTP 403 Forbidden.
4. **Metadata Filter Injection**: Org B passes document ID filter pointing to Org A $\rightarrow$ Returns 0 results.
5. **RBAC Boundary Enforcement**: Member attempts to add new users $\rightarrow$ Rejected with HTTP 403 Forbidden.
6. **Multi-Tenant Retrieval Verification**: Org A searches for its own document $\rightarrow$ Returns rank 1 match with exact score and citation metadata.

All 18 tests pass in the project CI suite.

