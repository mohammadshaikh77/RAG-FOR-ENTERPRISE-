"""Integration tests for Agent API endpoints and multi-tenant trace isolation."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.src.auth.security import create_access_token, get_password_hash
from apps.api.src.db.session import async_session_maker
from apps.api.src.main import app
from apps.api.src.models.organization import Organization
from apps.api.src.models.user import User, UserRole


@pytest.mark.asyncio
async def test_agent_api_end_to_end_and_isolation() -> None:
    # 1. Setup two distinct tenants: Org A and Org B
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()

    async with async_session_maker() as session:
        org_a = Organization(id=org_a_id, name="Agent Test Org A", slug=f"agent-a-{org_a_id}")
        org_b = Organization(id=org_b_id, name="Agent Test Org B", slug=f"agent-b-{org_b_id}")
        session.add_all([org_a, org_b])
        await session.flush()

        user_a = User(
            id=user_a_id,
            org_id=org_a_id,
            email=f"alice-{user_a_id}@org-a.com",
            full_name="Alice Admin",
            hashed_password=get_password_hash("Password123!"),
            role=UserRole.ADMIN,
        )
        user_b = User(
            id=user_b_id,
            org_id=org_b_id,
            email=f"bob-{user_b_id}@org-b.com",
            full_name="Bob Member",
            hashed_password=get_password_hash("Password123!"),
            role=UserRole.MEMBER,
        )
        session.add_all([user_a, user_b])
        await session.commit()

    token_a = create_access_token(
        data={"sub": str(user_a_id), "org_id": str(org_a_id), "role": UserRole.ADMIN.value}
    )
    token_b = create_access_token(
        data={"sub": str(user_b_id), "org_id": str(org_b_id), "role": UserRole.MEMBER.value}
    )

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 2. Org A queries agent
        query_payload = {
            "query": "What are the indications for Lisinopril?",
            "max_steps": 3,
            "session_id": "test-session-1",
        }
        resp = await client.post("/agent/query", json=query_payload, headers=headers_a)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "final_answer" in data
        assert "trace_id" in data
        trace_id = data["trace_id"]
        assert data["steps_count"] >= 1
        assert data["tokens_total"] > 0

        # 3. Org A lists traces
        list_resp = await client.get("/agent/traces", headers=headers_a)
        assert list_resp.status_code == 200
        traces_a = list_resp.json()
        assert len(traces_a) >= 1
        assert any(t["id"] == trace_id for t in traces_a)

        # 4. Org A inspects trace details
        detail_resp = await client.get(f"/agent/traces/{trace_id}", headers=headers_a)
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["id"] == trace_id
        assert len(detail_data["steps"]) >= 1

        # 5. Adversarial Check: Org B attempts to inspect Org A's trace
        cross_resp = await client.get(f"/agent/traces/{trace_id}", headers=headers_b)
        assert cross_resp.status_code == 404, "Org B should receive 404 Not Found for Org A's trace"

        # 6. Org B's trace list should be empty
        list_b_resp = await client.get("/agent/traces", headers=headers_b)
        assert list_b_resp.status_code == 200
        traces_b = list_b_resp.json()
        assert len(traces_b) == 0
