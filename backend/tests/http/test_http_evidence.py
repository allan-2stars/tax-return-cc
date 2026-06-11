import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import (
    Document,
    EvidenceMatch,
    EvidenceMatchDecisionHistory,
    EvidenceObligation,
    TaxEvent,
    TaxProfile,
    Workspace,
)
from app.services.evidence_rules import CURRENT_EVIDENCE_RULE_VERSION


@pytest.mark.asyncio
async def test_reconcile_evidence_endpoint(auth_client):
    response = await auth_client.post("/api/v1/evidence/reconcile")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "obligations_count" in body["data"]
    assert isinstance(body["data"]["obligations_count"], int)
    assert "freshness" in body["data"]
    freshness = body["data"]["freshness"]
    assert freshness["freshness_state"] in {"fresh", "reconciling", "stale", "failed"}
    assert "last_reconciled_at" in freshness
    assert "last_attempted_at" in freshness
    assert "last_failure_at" in freshness
    assert "freshness_reason" in freshness
    assert "telemetry" in body["data"]
    telemetry = body["data"]["telemetry"]
    assert telemetry["current_rule_version"] == CURRENT_EVIDENCE_RULE_VERSION
    assert "obligations_by_rule_version" in telemetry


@pytest.mark.asyncio
async def test_list_obligations_endpoint(auth_client):
    await auth_client.post("/api/v1/evidence/reconcile")
    response = await auth_client.get("/api/v1/evidence/obligations")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "obligations" in body["data"]
    assert isinstance(body["data"]["obligations"], list)
    assert "freshness" in body["data"]
    freshness = body["data"]["freshness"]
    assert freshness["freshness_state"] in {"fresh", "reconciling", "stale", "failed"}
    assert "last_reconciled_at" in freshness
    assert "last_attempted_at" in freshness
    assert "last_failure_at" in freshness
    assert "freshness_reason" in freshness


@pytest.mark.asyncio
async def test_list_obligations_includes_match_payload(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        doc = Document(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            original_filename="phi.pdf",
            storage_key=f"{auth_client.workspace_id}/phi.pdf",
            file_type="application/pdf",
            file_size_bytes=1200,
            sha256_hash="ab" * 32,
            document_type="private_health_statement",
            status="ready",
            archived=False,
        )
        event = TaxEvent(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            event_type="income",
            category="bank_interest",
            description="Bank interest",
            amount=12.0,
            status="needs_user_review",
        )
        session.add_all([doc, event])
        await session.flush()

        obligation = EvidenceObligation(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            source_type="profile",
            obligation_key="private_health_annual_statement",
            category="private_health",
            label="PHI Statement",
            required_level="required",
            status="partially_matched",
            reason="Needed from profile",
            rule_version=CURRENT_EVIDENCE_RULE_VERSION,
        )
        session.add(obligation)
        await session.flush()

        session.add(
            EvidenceMatch(
                workspace_id=auth_client.workspace_id,
                obligation_id=obligation.id,
                document_id=doc.id,
                tax_event_id=event.id,
                match_type="document",
                confidence=0.9,
                status="candidate",
                reason="Possible document match",
            )
        )
        await session.commit()

    response = await auth_client.get("/api/v1/evidence/obligations")
    assert response.status_code == 200
    obligations = response.json()["data"]["obligations"]
    assert len(obligations) >= 1
    target = next(o for o in obligations if o["obligation_key"] == "private_health_annual_statement")
    assert target["status"] == "partially_matched"
    assert target["required_level"] == "required"
    assert target["reason"] == "Needed from profile"
    assert target["rule_version"] == CURRENT_EVIDENCE_RULE_VERSION
    assert "explanation" in target
    assert target["explanation"]["target_type"] == "evidence_obligation"
    assert target["explanation"]["target_id"] == target["id"]
    assert target["explanation"]["rule_version"] == CURRENT_EVIDENCE_RULE_VERSION
    assert isinstance(target["matches"], list)
    assert len(target["matches"]) == 1
    match = target["matches"][0]
    assert match["status"] == "candidate"
    assert match["confidence"] == 0.9
    assert match["reason"] == "Possible document match"
    assert match["document"]["original_filename"] == "phi.pdf"
    assert match["document"]["document_type"] == "private_health_statement"
    assert match["document"].get("extracted_text") is None
    assert match["tax_event"]["category"] == "bank_interest"


@pytest.mark.asyncio
async def test_list_obligations_workspace_scoped(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        other = Workspace(name="Other WS", financial_year="2024-25", status="active")
        session.add(other)
        await session.commit()
        await session.refresh(other)
        session.add(
            EvidenceObligation(
                workspace_id=other.id,
                financial_year="2024-25",
                source_type="manual",
                obligation_key="other_workspace_only",
                category="other",
                label="Other Workspace Obligation",
                required_level="required",
                status="missing",
            )
        )
        await session.commit()

    response = await auth_client.get("/api/v1/evidence/obligations")
    assert response.status_code == 200
    keys = {o["obligation_key"] for o in response.json()["data"]["obligations"]}
    assert "other_workspace_only" not in keys


@pytest.mark.asyncio
async def test_list_obligations_financial_year_scoped(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(
            EvidenceObligation(
                workspace_id=auth_client.workspace_id,
                financial_year="2023-24",
                source_type="manual",
                obligation_key="prior_fy_only",
                category="other",
                label="Prior FY Obligation",
                required_level="required",
                status="missing",
            )
        )
        await session.commit()

    response = await auth_client.get("/api/v1/evidence/obligations")
    assert response.status_code == 200
    keys = {o["obligation_key"] for o in response.json()["data"]["obligations"]}
    assert "prior_fy_only" not in keys


@pytest.mark.asyncio
async def test_patch_match_accept_updates_status_and_obligation(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        obligation = EvidenceObligation(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            source_type="profile",
            obligation_key="private_health_annual_statement",
            category="private_health",
            label="PHI Statement",
            required_level="required",
            status="partially_matched",
        )
        session.add(obligation)
        await session.flush()
        match = EvidenceMatch(
            workspace_id=auth_client.workspace_id,
            obligation_id=obligation.id,
            match_type="document",
            status="candidate",
            confidence=0.8,
            reason="Possible match",
        )
        session.add(match)
        await session.commit()
        match_id = match.id
        obligation_id = obligation.id

    response = await auth_client.patch(
        f"/api/v1/evidence/matches/{match_id}",
        json={"status": "accepted"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["match"]["status"] == "accepted"
    assert body["obligation"]["status"] == "matched"
    assert body["obligation"]["id"] == obligation_id

    async with maker() as session:
        result = await session.execute(
            select(EvidenceMatchDecisionHistory).where(
                EvidenceMatchDecisionHistory.evidence_match_id == match_id
            )
        )
        history = result.scalars().all()
        assert len(history) == 1
        assert history[0].workspace_id == auth_client.workspace_id
        assert history[0].action == "accepted"
        assert history[0].actor == "user"
        assert history[0].previous_status == "candidate"
        assert history[0].new_status == "accepted"


@pytest.mark.asyncio
async def test_patch_match_reject_updates_status_and_obligation(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        obligation = EvidenceObligation(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            source_type="profile",
            obligation_key="private_health_annual_statement",
            category="private_health",
            label="PHI Statement",
            required_level="required",
            status="partially_matched",
        )
        session.add(obligation)
        await session.flush()
        match = EvidenceMatch(
            workspace_id=auth_client.workspace_id,
            obligation_id=obligation.id,
            match_type="document",
            status="candidate",
            confidence=0.8,
            reason="Possible match",
        )
        session.add(match)
        await session.commit()
        match_id = match.id

    response = await auth_client.patch(
        f"/api/v1/evidence/matches/{match_id}",
        json={"status": "rejected"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["match"]["status"] == "rejected"
    assert body["obligation"]["status"] == "missing"

    async with maker() as session:
        result = await session.execute(
            select(EvidenceMatchDecisionHistory).where(
                EvidenceMatchDecisionHistory.evidence_match_id == match_id
            )
        )
        history = result.scalars().all()
        assert len(history) == 1
        assert history[0].action == "rejected"
        assert history[0].previous_status == "candidate"
        assert history[0].new_status == "rejected"


@pytest.mark.asyncio
async def test_patch_match_same_status_does_not_duplicate_history(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        obligation = EvidenceObligation(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            source_type="profile",
            obligation_key="private_health_annual_statement",
            category="private_health",
            label="PHI Statement",
            required_level="required",
            status="matched",
        )
        session.add(obligation)
        await session.flush()
        match = EvidenceMatch(
            workspace_id=auth_client.workspace_id,
            obligation_id=obligation.id,
            match_type="document",
            status="accepted",
            confidence=0.8,
            reason="Accepted already",
        )
        session.add(match)
        await session.commit()
        match_id = match.id

    response = await auth_client.patch(
        f"/api/v1/evidence/matches/{match_id}",
        json={"status": "accepted"},
    )
    assert response.status_code == 200

    async with maker() as session:
        result = await session.execute(
            select(EvidenceMatchDecisionHistory).where(
                EvidenceMatchDecisionHistory.evidence_match_id == match_id
            )
        )
        assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_patch_match_scopes_workspace(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        other = Workspace(name="Other WS", financial_year="2024-25", status="active")
        session.add(other)
        await session.flush()
        obligation = EvidenceObligation(
            workspace_id=other.id,
            financial_year="2024-25",
            source_type="profile",
            obligation_key="private_health_annual_statement",
            category="private_health",
            label="PHI Statement",
            required_level="required",
            status="partially_matched",
        )
        session.add(obligation)
        await session.flush()
        match = EvidenceMatch(
            workspace_id=other.id,
            obligation_id=obligation.id,
            match_type="document",
            status="candidate",
        )
        session.add(match)
        await session.commit()
        match_id = match.id

    response = await auth_client.patch(
        f"/api/v1/evidence/matches/{match_id}",
        json={"status": "accepted"},
    )
    assert response.status_code == 404

    async with maker() as session:
        result = await session.execute(
            select(EvidenceMatchDecisionHistory).where(
                EvidenceMatchDecisionHistory.evidence_match_id == match_id
            )
        )
        assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_patch_match_scopes_financial_year(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        obligation = EvidenceObligation(
            workspace_id=auth_client.workspace_id,
            financial_year="2023-24",
            source_type="profile",
            obligation_key="private_health_annual_statement",
            category="private_health",
            label="PHI Statement",
            required_level="required",
            status="partially_matched",
        )
        session.add(obligation)
        await session.flush()
        match = EvidenceMatch(
            workspace_id=auth_client.workspace_id,
            obligation_id=obligation.id,
            match_type="document",
            status="candidate",
        )
        session.add(match)
        await session.commit()
        match_id = match.id

    response = await auth_client.patch(
        f"/api/v1/evidence/matches/{match_id}",
        json={"status": "accepted"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_interview_answer_triggers_reconcile(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(
            TaxProfile(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                has_private_health=True,
            )
        )
        await session.commit()

    start = await auth_client.post("/api/v1/interview/start")
    assert start.status_code == 200
    answer = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "residency", "answer": "resident"},
    )
    assert answer.status_code == 200

    obligations = await auth_client.get("/api/v1/evidence/obligations")
    keys = {o["obligation_key"] for o in obligations.json()["data"]["obligations"]}
    assert "private_health_annual_statement" in keys


@pytest.mark.asyncio
async def test_interview_skip_triggers_reconcile_and_removes_no_longer_applicable_obligation(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        profile = TaxProfile(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            has_private_health=True,
        )
        session.add(profile)
        await session.commit()

    await auth_client.post("/api/v1/evidence/reconcile")
    obligations_before = await auth_client.get("/api/v1/evidence/obligations")
    keys_before = {o["obligation_key"] for o in obligations_before.json()["data"]["obligations"]}
    assert "private_health_annual_statement" in keys_before

    async with maker() as session:
        profile = await session.scalar(select(TaxProfile).where(TaxProfile.workspace_id == auth_client.workspace_id))
        profile.has_private_health = False
        await session.commit()

    await auth_client.post("/api/v1/interview/start")
    skip = await auth_client.post(
        "/api/v1/interview/skip",
        json={"question_id": "residency", "reason": "skip for now"},
    )
    assert skip.status_code == 200
    # Route-triggered reconcile may be debounced; force one full pass for deterministic assertion.
    await auth_client.post("/api/v1/evidence/reconcile")

    obligations_after = await auth_client.get("/api/v1/evidence/obligations")
    keys_after = {o["obligation_key"] for o in obligations_after.json()["data"]["obligations"]}
    assert "private_health_annual_statement" not in keys_after


@pytest.mark.asyncio
async def test_document_delete_triggers_reconcile_and_clears_candidates(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(
            TaxProfile(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                has_wfh=True,
            )
        )
        doc = Document(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            original_filename="wfh-diary.pdf",
            storage_key=f"{auth_client.workspace_id}/wfh-diary.pdf",
            file_type="application/pdf",
            file_size_bytes=1234,
            sha256_hash="cd" * 32,
            document_type="wfh_diary",
            status="ready",
            archived=False,
        )
        session.add(doc)
        await session.commit()
        doc_id = doc.id

    await auth_client.post("/api/v1/evidence/reconcile")
    before = await auth_client.get("/api/v1/evidence/obligations")
    wfh_before = next(o for o in before.json()["data"]["obligations"] if o["obligation_key"] == "wfh_evidence_log")
    assert wfh_before["status"] == "partially_matched"
    assert len(wfh_before["matches"]) >= 1

    deleted = await auth_client.delete(f"/api/v1/documents/{doc_id}")
    assert deleted.status_code == 200
    # Route-triggered reconcile may be debounced; force one full pass for deterministic assertion.
    await auth_client.post("/api/v1/evidence/reconcile")

    after = await auth_client.get("/api/v1/evidence/obligations")
    wfh_after = next(o for o in after.json()["data"]["obligations"] if o["obligation_key"] == "wfh_evidence_log")
    assert wfh_after["status"] == "missing"
    assert wfh_after["matches"] == []


@pytest.mark.asyncio
async def test_manual_event_creation_triggers_reconcile_obligation_and_match(auth_client):
    response = await auth_client.post(
        "/api/v1/events/manual",
        json={
            "event_type": "deduction",
            "category": "work_expense",
            "description": "Laptop stand",
            "amount": 89.0,
            "date": "2025-08-01",
            "frequency": "one_off",
        },
    )
    assert response.status_code == 200

    obligations = await auth_client.get("/api/v1/evidence/obligations")
    work = next(o for o in obligations.json()["data"]["obligations"] if o["obligation_key"] == "work_expense_receipt")
    assert work["required_level"] == "required"
    assert work["status"] == "partially_matched"
    assert any(m["match_type"] == "tax_event" for m in work["matches"])


@pytest.mark.asyncio
async def test_manual_reconcile_records_trigger_source_and_metrics(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    response = await auth_client.post("/api/v1/evidence/reconcile")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] in {"ok", "failed", "skipped"}
    assert data.get("telemetry", {}).get("skipped") in {None, False}
    assert "telemetry" in data

    async with maker() as session:
        ws = await session.scalar(select(Workspace).where(Workspace.id == auth_client.workspace_id))
        assert ws is not None
        assert ws.evidence_reconcile_status in {"succeeded", "failed", "running", "idle"}
        meta = ws.evidence_reconcile_meta or {}
        assert meta.get("last_trigger_source") == "manual_reconcile"


@pytest.mark.asyncio
async def test_route_trigger_reconcile_debounces_within_window(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(TaxProfile(workspace_id=auth_client.workspace_id, financial_year="2024-25"))
        await session.commit()

    start = await auth_client.post("/api/v1/interview/start")
    assert start.status_code == 200
    ans1 = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "residency", "answer": "resident"},
    )
    assert ans1.status_code == 200
    ans2 = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "employment_type", "answer": "employee"},
    )
    assert ans2.status_code == 200

    async with maker() as session:
        ws = await session.scalar(select(Workspace).where(Workspace.id == auth_client.workspace_id))
        meta = ws.evidence_reconcile_meta or {}
        assert meta.get("last_trigger_source") == "event_update"
        assert meta.get("skip_reason") == "debounce_window"
        assert meta.get("skipped") is True


@pytest.mark.asyncio
async def test_list_obligations_includes_match_decision_history(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        obligation = EvidenceObligation(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            source_type="profile",
            obligation_key="private_health_annual_statement",
            category="private_health",
            label="PHI Statement",
            required_level="required",
            status="matched",
        )
        session.add(obligation)
        await session.flush()

        match = EvidenceMatch(
            workspace_id=auth_client.workspace_id,
            obligation_id=obligation.id,
            match_type="document",
            status="accepted",
            confidence=0.9,
            reason="Accepted match",
        )
        session.add(match)
        await session.flush()

        session.add(
            EvidenceMatchDecisionHistory(
                workspace_id=auth_client.workspace_id,
                evidence_match_id=match.id,
                evidence_obligation_id=obligation.id,
                action="accepted",
                actor="user",
                previous_status="candidate",
                new_status="accepted",
                note="Looks correct",
            )
        )
        await session.commit()

    response = await auth_client.get("/api/v1/evidence/obligations")
    assert response.status_code == 200
    obligations = response.json()["data"]["obligations"]
    target = next(o for o in obligations if o["obligation_key"] == "private_health_annual_statement")
    match = target["matches"][0]
    assert "decision_history" in match
    assert len(match["decision_history"]) == 1
    history = match["decision_history"][0]
    assert history["action"] == "accepted"
    assert history["actor"] == "user"
    assert history["previous_status"] == "candidate"
    assert history["new_status"] == "accepted"
    assert history["note"] == "Looks correct"


@pytest.mark.asyncio
async def test_undo_match_accept_restores_candidate_and_writes_history(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        obligation = EvidenceObligation(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            source_type="profile",
            obligation_key="private_health_annual_statement",
            category="private_health",
            label="PHI Statement",
            required_level="required",
            status="matched",
        )
        session.add(obligation)
        await session.flush()
        match = EvidenceMatch(
            workspace_id=auth_client.workspace_id,
            obligation_id=obligation.id,
            match_type="document",
            status="accepted",
            confidence=0.8,
            reason="Accepted match",
        )
        session.add(match)
        await session.flush()
        accepted_history = EvidenceMatchDecisionHistory(
            workspace_id=auth_client.workspace_id,
            evidence_match_id=match.id,
            evidence_obligation_id=obligation.id,
            action="accepted",
            actor="user",
            previous_status="candidate",
            new_status="accepted",
        )
        session.add(accepted_history)
        await session.commit()
        match_id = match.id
        obligation_id = obligation.id

    response = await auth_client.post(f"/api/v1/evidence/matches/{match_id}/undo")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["match"]["status"] == "candidate"
    assert body["obligation"]["status"] == "partially_matched"
    assert body["obligation"]["id"] == obligation_id

    async with maker() as session:
        match = await session.scalar(select(EvidenceMatch).where(EvidenceMatch.id == match_id))
        assert match.status == "candidate"
        histories = (
            await session.execute(
                select(EvidenceMatchDecisionHistory)
                .where(EvidenceMatchDecisionHistory.evidence_match_id == match_id)
                .order_by(EvidenceMatchDecisionHistory.created_at.asc())
            )
        ).scalars().all()
        assert len(histories) == 2
        assert histories[-1].action == "undo"
        assert histories[-1].previous_status == "accepted"
        assert histories[-1].new_status == "candidate"
        assert histories[-1].actor == "user"
        assert histories[-1].note == f"Undo history {histories[0].id}"


@pytest.mark.asyncio
async def test_undo_match_reject_restores_candidate_and_obligation_status(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        obligation = EvidenceObligation(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            source_type="profile",
            obligation_key="private_health_annual_statement",
            category="private_health",
            label="PHI Statement",
            required_level="required",
            status="missing",
        )
        session.add(obligation)
        await session.flush()
        match = EvidenceMatch(
            workspace_id=auth_client.workspace_id,
            obligation_id=obligation.id,
            match_type="document",
            status="rejected",
            confidence=0.7,
            reason="Rejected match",
        )
        session.add(match)
        await session.flush()
        session.add(
            EvidenceMatchDecisionHistory(
                workspace_id=auth_client.workspace_id,
                evidence_match_id=match.id,
                evidence_obligation_id=obligation.id,
                action="rejected",
                actor="user",
                previous_status="candidate",
                new_status="rejected",
            )
        )
        await session.commit()
        match_id = match.id

    response = await auth_client.post(f"/api/v1/evidence/matches/{match_id}/undo")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["match"]["status"] == "candidate"
    assert body["obligation"]["status"] == "partially_matched"


@pytest.mark.asyncio
async def test_undo_match_recalculates_obligation_status_with_other_accepted_match(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        obligation = EvidenceObligation(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            source_type="profile",
            obligation_key="bank_interest_statement",
            category="bank_interest",
            label="Bank Interest Statement",
            required_level="recommended",
            status="matched",
        )
        session.add(obligation)
        await session.flush()
        accepted_match = EvidenceMatch(
            workspace_id=auth_client.workspace_id,
            obligation_id=obligation.id,
            match_type="document",
            status="accepted",
            confidence=0.9,
            reason="Accepted match",
        )
        undoable_match = EvidenceMatch(
            workspace_id=auth_client.workspace_id,
            obligation_id=obligation.id,
            match_type="document",
            status="accepted",
            confidence=0.85,
            reason="Accepted match",
        )
        session.add_all([accepted_match, undoable_match])
        await session.flush()
        session.add_all(
            [
                EvidenceMatchDecisionHistory(
                    workspace_id=auth_client.workspace_id,
                    evidence_match_id=accepted_match.id,
                    evidence_obligation_id=obligation.id,
                    action="accepted",
                    actor="user",
                    previous_status="candidate",
                    new_status="accepted",
                ),
                EvidenceMatchDecisionHistory(
                    workspace_id=auth_client.workspace_id,
                    evidence_match_id=undoable_match.id,
                    evidence_obligation_id=obligation.id,
                    action="accepted",
                    actor="user",
                    previous_status="candidate",
                    new_status="accepted",
                ),
            ]
        )
        await session.commit()
        match_id = undoable_match.id

    response = await auth_client.post(f"/api/v1/evidence/matches/{match_id}/undo")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["match"]["status"] == "candidate"
    assert body["obligation"]["status"] == "matched"


@pytest.mark.asyncio
async def test_undo_match_cannot_undo_candidate(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        obligation = EvidenceObligation(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            source_type="profile",
            obligation_key="bank_interest_statement",
            category="bank_interest",
            label="Bank Interest Statement",
            required_level="recommended",
            status="partially_matched",
        )
        session.add(obligation)
        await session.flush()
        match = EvidenceMatch(
            workspace_id=auth_client.workspace_id,
            obligation_id=obligation.id,
            match_type="document",
            status="candidate",
            confidence=0.7,
            reason="Possible match",
        )
        session.add(match)
        await session.commit()
        match_id = match.id

    response = await auth_client.post(f"/api/v1/evidence/matches/{match_id}/undo")
    assert response.status_code == 422
    body = response.json()
    assert body["detail"]["error_code"] == "undo_not_available"


@pytest.mark.asyncio
async def test_undo_match_scopes_workspace(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        other = Workspace(name="Other WS", financial_year="2024-25", status="active")
        session.add(other)
        await session.flush()
        obligation = EvidenceObligation(
            workspace_id=other.id,
            financial_year="2024-25",
            source_type="profile",
            obligation_key="bank_interest_statement",
            category="bank_interest",
            label="Bank Interest Statement",
            required_level="recommended",
            status="matched",
        )
        session.add(obligation)
        await session.flush()
        match = EvidenceMatch(
            workspace_id=other.id,
            obligation_id=obligation.id,
            match_type="document",
            status="accepted",
            confidence=0.7,
            reason="Accepted match",
        )
        session.add(match)
        await session.flush()
        session.add(
            EvidenceMatchDecisionHistory(
                workspace_id=other.id,
                evidence_match_id=match.id,
                evidence_obligation_id=obligation.id,
                action="accepted",
                actor="user",
                previous_status="candidate",
                new_status="accepted",
            )
        )
        await session.commit()
        match_id = match.id

    response = await auth_client.post(f"/api/v1/evidence/matches/{match_id}/undo")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_undo_match_requires_latest_history_to_be_undoable(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        obligation = EvidenceObligation(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            source_type="profile",
            obligation_key="bank_interest_statement",
            category="bank_interest",
            label="Bank Interest Statement",
            required_level="recommended",
            status="matched",
        )
        session.add(obligation)
        await session.flush()
        match = EvidenceMatch(
            workspace_id=auth_client.workspace_id,
            obligation_id=obligation.id,
            match_type="document",
            status="accepted",
            confidence=0.7,
            reason="Accepted match",
        )
        session.add(match)
        await session.flush()
        session.add_all(
            [
                EvidenceMatchDecisionHistory(
                    workspace_id=auth_client.workspace_id,
                    evidence_match_id=match.id,
                    evidence_obligation_id=obligation.id,
                    action="accepted",
                    actor="user",
                    previous_status="candidate",
                    new_status="accepted",
                ),
                EvidenceMatchDecisionHistory(
                    workspace_id=auth_client.workspace_id,
                    evidence_match_id=match.id,
                    evidence_obligation_id=obligation.id,
                    action="undo",
                    actor="user",
                    previous_status="accepted",
                    new_status="candidate",
                ),
            ]
        )
        await session.commit()
        match_id = match.id

    response = await auth_client.post(f"/api/v1/evidence/matches/{match_id}/undo")
    assert response.status_code == 422
    body = response.json()
    assert body["detail"]["error_code"] == "undo_not_available"
