"""HTTP smoke tests for /readiness route group."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import EvidenceMatch, EvidenceObligation


@pytest.mark.asyncio
async def test_get_readiness(auth_client):
    """GET /readiness returns 200 with percentage field under data."""
    resp = await auth_client.get("/api/v1/readiness")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "percentage" in body["data"]
    assert isinstance(body["data"]["percentage"], int)
    assert "evidence_obligation_summary" in body["data"]
    assert "evidence_freshness" in body["data"]


@pytest.mark.asyncio
async def test_get_missing(auth_client):
    """GET /readiness/missing returns 200 with available_now and available_after_fy keys."""
    resp = await auth_client.get("/api/v1/readiness/missing")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "available_now" in body["data"]
    assert "available_after_fy" in body["data"]
    assert isinstance(body["data"]["available_now"], list)
    assert isinstance(body["data"]["available_after_fy"], list)


@pytest.mark.asyncio
async def test_recalculate(auth_client):
    """POST /readiness/recalculate returns 200 with status=recalculating."""
    resp = await auth_client.post("/api/v1/readiness/recalculate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "recalculating"


@pytest.mark.asyncio
async def test_get_readiness_includes_evidence_obligation_summary(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add_all(
            [
                EvidenceObligation(
                    workspace_id=auth_client.workspace_id,
                    financial_year="2024-25",
                    source_type="profile",
                    obligation_key="private_health_annual_statement",
                    category="private_health",
                    label="PHI",
                    required_level="required",
                    status="missing",
                ),
                EvidenceObligation(
                    workspace_id=auth_client.workspace_id,
                    financial_year="2024-25",
                    source_type="profile",
                    obligation_key="wfh_evidence_log",
                    category="wfh",
                    label="WFH",
                    required_level="required",
                    status="partially_matched",
                ),
                EvidenceObligation(
                    workspace_id=auth_client.workspace_id,
                    financial_year="2024-25",
                    source_type="tax_event",
                    obligation_key="work_expense_receipt",
                    category="work_expense",
                    label="Work expense",
                    required_level="required",
                    status="matched",
                ),
                EvidenceObligation(
                    workspace_id=auth_client.workspace_id,
                    financial_year="2024-25",
                    source_type="tax_event",
                    obligation_key="bank_interest_statement",
                    category="bank_interest",
                    label="Bank interest",
                    required_level="recommended",
                    status="missing",
                ),
            ]
        )
        await session.commit()

    response = await auth_client.get("/api/v1/readiness")
    assert response.status_code == 200
    summary = response.json()["data"]["evidence_obligation_summary"]
    assert summary["total_obligations"] == 4
    assert summary["required_missing"] == 1
    assert summary["required_partially_matched"] == 1
    assert summary["required_matched"] == 1
    assert summary["recommended_missing"] == 1
    assert summary["recommended_partially_matched"] == 0
    assert summary["recommended_matched"] == 0
    assert len(summary["blocking_evidence_obligations"]) == 2
    assert {b["status"] for b in summary["blocking_evidence_obligations"]} == {"missing", "partially_matched"}
    assert all(b["required_level"] == "required" for b in summary["blocking_evidence_obligations"])


@pytest.mark.asyncio
async def test_get_readiness_candidate_and_accepted_affect_counts(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        obligation = EvidenceObligation(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            source_type="profile",
            obligation_key="private_health_annual_statement",
            category="private_health",
            label="PHI",
            required_level="required",
            status="partially_matched",
        )
        session.add(obligation)
        await session.flush()
        session.add(
            EvidenceMatch(
                workspace_id=auth_client.workspace_id,
                obligation_id=obligation.id,
                match_type="document",
                status="candidate",
            )
        )
        await session.commit()

    resp = await auth_client.get("/api/v1/readiness")
    assert resp.status_code == 200
    summary = resp.json()["data"]["evidence_obligation_summary"]
    assert summary["required_partially_matched"] == 1
    assert summary["required_missing"] == 0

    async with maker() as session:
        ob = (
            await session.execute(
                select(EvidenceObligation).where(
                    EvidenceObligation.workspace_id == auth_client.workspace_id,
                    EvidenceObligation.obligation_key == "private_health_annual_statement",
                )
            )
        ).scalar_one()
        ob.status = "matched"
        await session.commit()

    resp2 = await auth_client.get("/api/v1/readiness")
    summary2 = resp2.json()["data"]["evidence_obligation_summary"]
    assert summary2["required_matched"] == 1
    assert summary2["required_partially_matched"] == 0


@pytest.mark.asyncio
async def test_get_readiness_obligation_summary_scoped_by_workspace_and_fy(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add_all(
            [
                EvidenceObligation(
                    workspace_id=auth_client.workspace_id,
                    financial_year="2023-24",
                    source_type="profile",
                    obligation_key="prior_fy_obligation",
                    category="other",
                    label="Prior FY",
                    required_level="required",
                    status="missing",
                ),
            ]
        )
        await session.commit()

    response = await auth_client.get("/api/v1/readiness")
    assert response.status_code == 200
    summary = response.json()["data"]["evidence_obligation_summary"]
    assert summary["total_obligations"] == 0
