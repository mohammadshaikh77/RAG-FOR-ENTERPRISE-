import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.src.db.session import async_session_maker
from apps.api.src.main import app
from packages.rag.src.rag.embeddings import MockEmbedder
from packages.rag.src.rag.ingestion import IngestionService


@pytest.mark.asyncio
async def test_multi_tenant_isolation_and_auth() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Register Tenant Alpha (Org A)
        unique_a = uuid.uuid4().hex[:6]
        reg_a_payload = {
            "org_name": f"Pharma Alpha {unique_a}",
            "org_slug": f"alpha-{unique_a}",
            "email": f"admin@{unique_a}.com",
            "password": "Password123!",
            "full_name": "Dr. Alpha Admin",
        }
        resp_a = await client.post("/auth/register", json=reg_a_payload)
        assert resp_a.status_code == 201
        data_a = resp_a.json()
        token_a = data_a["access_token"]
        user_a = data_a["user"]
        org_a_id = uuid.UUID(user_a["org_id"])
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # 2. Register Tenant Beta (Org B)
        unique_b = uuid.uuid4().hex[:6]
        reg_b_payload = {
            "org_name": f"Biotech Beta {unique_b}",
            "org_slug": f"beta-{unique_b}",
            "email": f"admin@{unique_b}.com",
            "password": "Password123!",
            "full_name": "Dr. Beta Admin",
        }
        resp_b = await client.post("/auth/register", json=reg_b_payload)
        assert resp_b.status_code == 201
        data_b = resp_b.json()
        token_b = data_b["access_token"]
        user_b = data_b["user"]
        org_b_id = uuid.UUID(user_b["org_id"])
        headers_b = {"Authorization": f"Bearer {token_b}"}

        assert org_a_id != org_b_id

        # 3. Ingest confidential document into Tenant Alpha
        ingestion_service = IngestionService(embedder=MockEmbedder())
        async with async_session_maker() as session:
            doc_a, _ = await ingestion_service.ingest(
                session=session,
                org_id=org_a_id,
                raw_content="""# TOP SECRET CLINICAL PROTOCOL
Compound XYZ-9988 exhibits high affinity binding.
Recommended secret dosage is 250mg intravenously once daily.
""",
                file_type="text/markdown",
                title="Confidential Compound XYZ-9988",
            )
            doc_a_id = doc_a.id

            # Ingest standard document into Tenant Beta
            doc_b, _ = await ingestion_service.ingest(
                session=session,
                org_id=org_b_id,
                raw_content="""# PUBLIC GUIDELINE
Standard aspirin dosage is 81mg orally daily.
""",
                file_type="text/markdown",
                title="Public Aspirin Protocol",
            )
            assert doc_b.id is not None

        # =========================================================================
        # ADVERSARIAL TEST 1: Direct ID Access Across Tenants
        # User Beta attempts to fetch Document Alpha by direct UUID
        # =========================================================================
        resp_leak_direct = await client.get(f"/documents/{doc_a_id}", headers=headers_b)
        assert resp_leak_direct.status_code == 404, (
            "Security Breach: Tenant B accessed Tenant A's document via direct UUID"
        )

        # Confirm User Alpha CAN access Document Alpha
        resp_valid_a = await client.get(f"/documents/{doc_a_id}", headers=headers_a)
        assert resp_valid_a.status_code == 200
        assert resp_valid_a.json()["title"] == "Confidential Compound XYZ-9988"

        # =========================================================================
        # ADVERSARIAL TEST 2: Semantic / Keyword Retrieval Leakage
        # User Beta searches specifically for Tenant Alpha's confidential secrets
        # =========================================================================
        search_leak_payload = {
            "query": "Secret compound XYZ-9988 250mg intravenously",
            "mode": "hybrid",
            "top_k": 5,
        }
        resp_leak_search = await client.post(
            "/retrieval/search",
            json=search_leak_payload,
            headers=headers_b,
        )
        assert resp_leak_search.status_code == 200
        search_data_b = resp_leak_search.json()
        for item in search_data_b["results"]:
            assert item["document_id"] != str(doc_a_id), (
                "Security Breach: Tenant B retrieved Tenant A's chunk via search query!"
            )
            assert "XYZ-9988" not in item["content"]

        # =========================================================================
        # ADVERSARIAL TEST 3: Cross-Tenant Org ID Forgery Attempt
        # User Beta explicitly specifies org_id of Tenant Alpha in request payload
        # =========================================================================
        forged_payload = {
            "query": "Compound XYZ-9988",
            "org_id": str(org_a_id),  # Maliciously targeting Org A
            "mode": "hybrid",
            "top_k": 5,
        }
        resp_forged = await client.post(
            "/retrieval/search",
            json=forged_payload,
            headers=headers_b,
        )
        assert resp_forged.status_code == 403, (
            "Security Breach: System did not reject cross-tenant org_id spoofing attempt"
        )
        assert "Cross-tenant access forbidden" in resp_forged.json()["detail"]

        # =========================================================================
        # ADVERSARIAL TEST 4: Document Filter Spoofing
        # User Beta tries to filter by doc_a_id without specifying org_id
        # =========================================================================
        filter_spoof_payload = {
            "query": "XYZ-9988",
            "document_id": str(doc_a_id),
            "mode": "vector",
            "top_k": 5,
        }
        resp_filter_spoof = await client.post(
            "/retrieval/search",
            json=filter_spoof_payload,
            headers=headers_b,
        )
        assert resp_filter_spoof.status_code == 200
        assert resp_filter_spoof.json()["total_results"] == 0

        # =========================================================================
        # ADVERSARIAL TEST 5: Role-Based Access Control (Admin vs Member)
        # =========================================================================
        # Admin B creates a Member B user
        create_member_payload = {
            "email": f"member@{unique_b}.com",
            "password": "MemberPassword123!",
            "full_name": "Junior Researcher",
            "role": "member",
        }
        resp_member_create = await client.post(
            "/auth/users",
            json=create_member_payload,
            headers=headers_b,
        )
        assert resp_member_create.status_code == 201

        # Login as Member B
        login_member_payload = {
            "email": f"member@{unique_b}.com",
            "password": "MemberPassword123!",
        }
        resp_member_login = await client.post("/auth/login", json=login_member_payload)
        assert resp_member_login.status_code == 200
        member_token = resp_member_login.json()["access_token"]
        headers_member_b = {"Authorization": f"Bearer {member_token}"}

        # Member B attempts to perform Admin action (create another user) -> Expect 403
        resp_unauthorized_action = await client.post(
            "/auth/users",
            json={
                "email": f"another@{unique_b}.com",
                "password": "Password123!",
                "full_name": "Unauthorized User",
                "role": "member",
            },
            headers=headers_member_b,
        )
        assert resp_unauthorized_action.status_code == 403
        assert "administrative privileges" in resp_unauthorized_action.json()["detail"]
