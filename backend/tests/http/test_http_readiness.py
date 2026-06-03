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
    freshness = body["data"]["evidence_freshness"]
    assert freshness["freshness_state"] in {"fresh", "reconciling", "stale", "failed"}
    assert "last_reconciled_at" in freshness
    assert "last_attempted_at" in freshness
    assert "last_failure_at" in freshness
    assert "freshness_reason" in freshness
    assert "readiness_2_0" in body["data"]
    r2 = body["data"]["readiness_2_0"]
    assert "overall" in r2 and "journey" in r2 and "review" in r2 and "evidence" in r2
    assert "blocking_reasons" in r2 and "warnings" in r2


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


@pytest.mark.asyncio
async def test_readiness_2_0_journey_incomplete_is_blocked(auth_client, test_engine):
    from app.db.models import InterviewSession

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(
            InterviewSession(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                state="in_progress",
                answers={},
                skipped_steps=[],
                activated_skills=[],
                pending_queue=[],
                completed_steps=[],
            )
        )
        await session.commit()

    response = await auth_client.get("/api/v1/readiness")
    assert response.status_code == 200
    r2 = response.json()["data"]["readiness_2_0"]
    assert r2["journey"]["state"] == "blocked"
    assert any("journey" in reason.lower() for reason in r2["blocking_reasons"])


@pytest.mark.asyncio
async def test_readiness_2_0_required_missing_evidence_is_blocked(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(
            EvidenceObligation(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                source_type="profile",
                obligation_key="private_health_annual_statement",
                category="private_health",
                label="PHI",
                required_level="required",
                status="missing",
            )
        )
        await session.commit()

    response = await auth_client.get("/api/v1/readiness")
    r2 = response.json()["data"]["readiness_2_0"]
    assert r2["evidence"]["state"] == "blocked"
    assert r2["evidence"]["required_missing_count"] == 1
    assert len(r2["evidence"]["blocking_obligations"]) == 1


@pytest.mark.asyncio
async def test_readiness_2_0_candidate_match_counts_as_partial(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        obligation = EvidenceObligation(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            source_type="profile",
            obligation_key="wfh_evidence_log",
            category="wfh",
            label="WFH",
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

    response = await auth_client.get("/api/v1/readiness")
    r2 = response.json()["data"]["readiness_2_0"]
    assert r2["evidence"]["required_partial_count"] == 1
    assert r2["evidence"]["candidate_match_count"] == 1


@pytest.mark.asyncio
async def test_readiness_2_0_accepted_match_improves_evidence(auth_client, test_engine):
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
            status="matched",
        )
        session.add(obligation)
        await session.flush()
        session.add(
            EvidenceMatch(
                workspace_id=auth_client.workspace_id,
                obligation_id=obligation.id,
                match_type="document",
                status="accepted",
            )
        )
        await session.commit()

    response = await auth_client.get("/api/v1/readiness")
    r2 = response.json()["data"]["readiness_2_0"]
    assert r2["evidence"]["required_matched_count"] == 1
    assert r2["evidence"]["accepted_match_count"] == 1
    assert r2["evidence"]["state"] == "ready"


@pytest.mark.asyncio
async def test_readiness_2_0_recommended_missing_is_warning_not_blocker(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(
            EvidenceObligation(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                source_type="tax_event",
                obligation_key="bank_interest_statement",
                category="bank_interest",
                label="Bank interest",
                required_level="recommended",
                status="missing",
            )
        )
        await session.commit()

    response = await auth_client.get("/api/v1/readiness")
    r2 = response.json()["data"]["readiness_2_0"]
    assert r2["evidence"]["state"] == "warning"
    assert r2["evidence"]["recommended_missing_count"] == 1
    assert not any("required evidence" in reason.lower() for reason in r2["blocking_reasons"])
    assert any("recommended evidence" in warning.lower() for warning in r2["warnings"])


@pytest.mark.asyncio
async def test_readiness_2_0_needs_agent_review_is_warning(auth_client, test_engine):
    from app.db.models import TaxEvent

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(
            TaxEvent(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                event_type="income",
                category="payg_income",
                description="PAYG",
                amount=100.0,
                status="needs_agent_review",
                source="manual_entry",
            )
        )
        await session.commit()

    response = await auth_client.get("/api/v1/readiness")
    r2 = response.json()["data"]["readiness_2_0"]
    assert r2["review"]["needs_agent_review_count"] == 1
    assert r2["review"]["state"] == "warning"
    assert any("tax agent review" in warning.lower() for warning in r2["warnings"])
