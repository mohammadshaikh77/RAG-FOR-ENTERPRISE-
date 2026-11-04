# ADR 0003: Multi-Tenancy Architecture, JWT Authentication, and Query-Level Isolation

## Status
Accepted

## Context
Cite is an enterprise document-intelligence and retrieval platform serving multiple client organizations (tenants). A primary security and regulatory non-negotiable is strict tenant isolation: under no circumstances may one organization's users view, search, cite, or verify documents or agent traces belonging to another organization.

Furthermore, authentication and authorization must run with zero paid external services (e.g. Auth0, Okta, Clerk) while upholding industry-standard cryptographic practices (bcrypt salted password hashing, stateless signed JWTs, RBAC).

## Decisions

### 1. Cryptographic Password Hashing: Direct `bcrypt`
- **Choice**: Direct `bcrypt` package implementation (`bcrypt.hashpw`, `bcrypt.gensalt`, `bcrypt.checkpw`).
- **Alternatives Considered**: `passlib[bcrypt]`.
- **Why**: Passlib is unmaintained and incompatible with `bcrypt >= 4.1.0` due to internal `__about__` removals causing runtime `AttributeError`. Direct `bcrypt` is lightweight, robust, and free from deprecation friction.

### 2. Authentication: Stateless Signed JWTs with Dual Org/User Claims
- **Choice**: Standard HMAC-SHA256 JWTs carrying `sub` (user_id), `org_id`, `role`, and expiration timestamps (`exp`).
- **Why**: Allows fast, stateless verification on every incoming request without repeated roundtrips to the database. Tokens can be revoked or rotated via `JWT_SECRET_KEY` rotation or short lifetimes.

### 3. Query-Level Isolation Inside Retrieval
- **Choice**: Multi-tenancy isolation is enforced deep inside the SQL generation layer (`document_chunks.c.org_id == org_id`), not solely at the API controller or gateway level.
- **Why**: Relying purely on API-level path or body filtering is fragile and susceptible to filter spoofing or developer oversight. The retrieval engine requires `org_id: UUID` as a mandatory parameter in every execution method (`search`, `vector_search`, `keyword_search`). Any API request attempting to supply an `org_id` different from the authenticated JWT token is immediately rejected with HTTP 403 Forbidden.

### 4. Cross-Tenant ID Probing Mitigation
- **Choice**: Direct access to another organization's document ID returns HTTP 404 Not Found rather than HTTP 403 Forbidden.
- **Why**: Returning 403 leaks the existence of sensitive document UUIDs or foreign tenant IDs to unauthorized attackers. Returning 404 prevents tenant enumeration and probing attacks.

## Consequences
- Every retrieval query strictly scopes vectors and full-text searches to the caller's tenant.
- Zero risk of cross-tenant data leakage in hybrid search or agent tool executions.
- Comprehensive adversarial tests in `test_multi_tenancy.py` run continuously in CI to prevent regression.
