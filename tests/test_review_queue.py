"""Unit and integration tests for Phase 7 Human Review Queue & Tenant Isolation."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.src.auth.security import create_access_token
from apps.api.src.db.session import async_session_maker
from apps.api.src.main import app
from apps.api.src.models.organization import Organization
from apps.api.src.models.review_queue import ReviewQueueItem
from apps.api.src.models.user import User, UserRole


@pytest.fixture
async def setup_tenants() -> tuple[Organization, Organization, User, User]:
    """Sets up two isolated organizations and users for testing multi-tenancy."""
    async with async_session_maker() as session:
        org_a = Organization(
            id=uuid.uuid4(),
            name=f"Org Alpha {uuid.uuid4().hex[:6]}",
            slug=f"alpha-{uuid.uuid4().hex[:6]}",
        )
        org_b = Organization(
            id=uuid.uuid4(),
            name=f"Org Beta {uuid.uuid4().hex[:6]}",
            slug=f"beta-{uuid.uuid4().hex[:6]}",
        )
        session.add_all([org_a, org_b])
        await session.flush()

        user_a = User(
            id=uuid.uuid4(),
            org_id=org_a.id,
            email=f"reviewer_a_{uuid.uuid4().hex[:6]}@alpha.org",
            hashed_password="mock_hash",
            full_name="Reviewer Alpha",
            role=UserRole.ADMIN,
        )
        user_b = User(
            id=uuid.uuid4(),
            org_id=org_b.id,
            email=f"reviewer_b_{uuid.uuid4().hex[:6]}@beta.org",
            hashed_password="mock_hash",
            full_name="Reviewer Beta",
            role=UserRole.ADMIN,
        )
        session.add_all([user_a, user_b])
        await session.commit()

        return org_a, org_b, user_a, user_b


@pytest.mark.asyncio
async def test_review_queue_lifecycle_and_tenant_isolation(
    setup_tenants: tuple[Organization, Organization, User, User],
) -> None:
    org_a, org_b, user_a, user_b = setup_tenants

    # 1. Seed review queue item for Org A
    item_a_id = uuid.uuid4()
    async with async_session_maker() as session:
        item_a = ReviewQueueItem(
            id=item_a_id,
            org_id=org_a.id,
            query="Is Lisinopril indicated for COVID-19?",
            answer="I cannot answer this question based on the provided documents.",
            retrieved_chunks=[{"chunk_id": str(uuid.uuid4()), "content": "Sample content"}],
            trigger_reason="unexpected_refusal",
            confidence_score=0.45,
            status="pending",
        )
        session.add(item_a)
        await session.commit()

    # Generate JWT tokens
    token_a = create_access_token({"sub": str(user_a.id), "org_id": str(org_a.id)})
    token_b = create_access_token({"sub": str(user_b.id), "org_id": str(org_b.id)})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 2. Org A lists review queue -> finds item_a
        resp_a = await client.get(
            "/review-queue",
            headers={"Authorization": f"Bearer {token_a}", "X-Org-ID": str(org_a.id)},
        )
        assert resp_a.status_code == 200
        items_a = resp_a.json()
        assert any(i["id"] == str(item_a_id) for i in items_a)

        # 3. Org B lists review queue -> CANNOT see item_a (tenant isolation)
        resp_b = await client.get(
            "/review-queue",
            headers={"Authorization": f"Bearer {token_b}", "X-Org-ID": str(org_b.id)},
        )
        assert resp_b.status_code == 200
        items_b = resp_b.json()
        assert not any(i["id"] == str(item_a_id) for i in items_b)

        # 4. Org B tries to access item_a by ID -> 404 Not Found (tenant isolation)
        resp_b_detail = await client.get(
            f"/review-queue/{item_a_id}",
            headers={"Authorization": f"Bearer {token_b}", "X-Org-ID": str(org_b.id)},
        )
        assert resp_b_detail.status_code == 404

        # 5. Org A accepts the item
        action_resp = await client.post(
            f"/review-queue/{item_a_id}/action",
            headers={"Authorization": f"Bearer {token_a}", "X-Org-ID": str(org_a.id)},
            json={"action": "accept", "notes": "Verified refusal is clinically correct"},
        )
        assert action_resp.status_code == 200
        data = action_resp.json()
        assert data["status"] == "accepted"
        assert data["reviewed_by"] == user_a.email

        # 6. Org A edits the answer
        edit_resp = await client.post(
            f"/review-queue/{item_a_id}/action",
            headers={"Authorization": f"Bearer {token_a}", "X-Org-ID": str(org_a.id)},
            json={
                "action": "edit",
                "edited_answer": "Clinical consensus: Lisinopril is NOT approved for COVID-19.",
            },
        )
        assert edit_resp.status_code == 200
        edit_data = edit_resp.json()
        assert edit_data["status"] == "edited"
        assert (
            edit_data["edited_answer"]
            == "Clinical consensus: Lisinopril is NOT approved for COVID-19."
        )
