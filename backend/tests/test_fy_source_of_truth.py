import asyncio
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_manual_event_uses_workspace_financial_year(client, patch_password):
    """
    Regression: /events/manual must use Workspace.financial_year, even if TaxProfile is missing.
    """
    from app.security import normalize_recovery_key
    from app.db.models import TaxEvent
    from sqlalchemy import select

    fy = "2025-26"

    setup_resp = await client.post(
        "/api/v1/auth/setup",
        json={"password": "test-password-m2", "financial_year": fy},
    )
    assert setup_resp.status_code == 200, setup_resp.text
    workspace_id = setup_resp.json()["data"]["workspace_id"]
    recovery_key = setup_resp.json()["data"]["recovery_key"]

    last_8 = normalize_recovery_key(recovery_key)[-8:]
    confirm_resp = await client.post(
        "/api/v1/auth/setup/confirm",
        json={"confirmation": f"{last_8[:4]}-{last_8[4:]}"},
    )
    assert confirm_resp.status_code == 200, confirm_resp.text

    login_resp = await client.post("/api/v1/auth/login", json={"password": "test-password-m2"})
    assert login_resp.status_code == 200, login_resp.text

    resp = await client.post(
        "/api/v1/events/manual",
        json={
            "event_type": "deduction",
            "category": "work_expense",
            "description": "Test FY deduction",
            "amount": 10.0,
            "date": "2025-07-01",
            "frequency": "one_off",
        },
    )
    assert resp.status_code == 200, resp.text

    # Verify persisted FY (not just response shape).
    from app.db.base import get_db

    override = client.app.dependency_overrides[get_db]
    async for db in override():  # type: ignore
        row = await db.execute(
            select(TaxEvent).where(TaxEvent.workspace_id == workspace_id).limit(1)
        )
        ev = row.scalar_one()
        assert ev.financial_year == fy


@pytest.mark.asyncio
async def test_export_engine_uses_workspace_financial_year_when_profile_missing(test_engine):
    """
    Regression: ExportEngine.generate() must use Workspace.financial_year when TaxProfile is missing.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from app.db.models import Workspace, TaxEvent, InterviewSession, ExportRecord
    from app.engines.export import ExportEngine

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as db:
        ws = Workspace(name="FY WS", financial_year="2025-26", status="active")
        db.add(ws)
        await db.commit()
        await db.refresh(ws)

        # Meet minimal export prerequisites for this test's data paths.
        db.add(InterviewSession(workspace_id=ws.id, financial_year=ws.financial_year, state="complete", answers={}, activated_skills=[], pending_queue=[], completed_steps=[]))
        db.add(TaxEvent(workspace_id=ws.id, financial_year=ws.financial_year, event_type="income", category="payg_income", description="Confirmed", amount=1.0, status="confirmed"))
        await db.commit()

        def _close_task(coro):
            coro.close()
            return None

        # Prevent background task from running in this unit test.
        with patch("app.engines.export.asyncio.create_task", side_effect=_close_task):
            engine = ExportEngine()
            record = await engine.generate(ws.id, "pw", db)

        row = await db.execute(select(ExportRecord).where(ExportRecord.id == record.id))
        saved = row.scalar_one()
        assert saved.financial_year == ws.financial_year
