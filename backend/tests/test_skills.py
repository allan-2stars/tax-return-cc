"""
Tests for M5 Skill System.

TDD: all tests written before implementation. Expected to fail until Tasks 2-9 complete.
"""
import asyncio
import logging

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from unittest.mock import MagicMock

from app.db.models import TaxProfile, TaxEvent, Document, Workspace
from app.ai.base import ClassificationResult, EventCandidate


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_profile(
    employment_type: str = "employee",
    has_wfh: bool = False,
    has_private_health: bool = False,
    financial_year: str = "2024-25",
) -> TaxProfile:
    return TaxProfile(
        workspace_id="ws-test",
        financial_year=financial_year,
        employment_type=employment_type,
        has_wfh=has_wfh,
        has_private_health=has_private_health,
    )


def _make_event(
    category: str = "work_expense",
    status: str = "needs_user_review",
    amount: float = 100.0,
) -> TaxEvent:
    return TaxEvent(
        workspace_id="ws-test",
        financial_year="2024-25",
        event_type="deduction",
        category=category,
        description="Test event",
        amount=amount,
        status=status,
    )


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def patch_async_session_local(test_engine, monkeypatch):
    import app.db.base as db_base
    test_maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(db_base, "AsyncSessionLocal", test_maker)


@pytest_asyncio.fixture
async def workspace(db_session):
    ws = Workspace(name="Skills Test WS", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


# ── 1. employee_tax_au activates for employee ─────────────────────────────────

def test_employee_tax_au_activates_for_employee():
    from app.skills.employee_tax_au import EmployeeTaxAU
    skill = EmployeeTaxAU()
    assert skill.should_activate(_make_profile(employment_type="employee"))


# ── 2. employee_tax_au does NOT activate for sole_trader ──────────────────────

def test_employee_tax_au_does_not_activate_for_sole_trader():
    from app.skills.employee_tax_au import EmployeeTaxAU
    skill = EmployeeTaxAU()
    assert not skill.should_activate(_make_profile(employment_type="sole_trader"))


# ── 3. get_missing_evidence returns payg_summary when no PAYG event ───────────

def test_get_missing_evidence_returns_payg_summary_when_no_payg_uploaded():
    from app.skills.employee_tax_au import EmployeeTaxAU
    from app.skills.base import MissingEvidence
    skill = EmployeeTaxAU()
    missing = skill.get_missing_evidence(_make_profile(), events=[])
    assert any(m.requirement_id == "payg_summary" for m in missing)
    assert all(isinstance(m, MissingEvidence) for m in missing)


# ── 4. get_missing_evidence returns wfh_diary only when has_wfh = True ────────

def test_get_missing_evidence_returns_wfh_diary_only_when_has_wfh():
    from app.skills.employee_tax_au import EmployeeTaxAU
    skill = EmployeeTaxAU()

    missing_with_wfh = skill.get_missing_evidence(_make_profile(has_wfh=True), events=[])
    assert any(m.requirement_id == "wfh_diary" for m in missing_with_wfh)

    missing_no_wfh = skill.get_missing_evidence(_make_profile(has_wfh=False), events=[])
    assert not any(m.requirement_id == "wfh_diary" for m in missing_no_wfh)


# ── 5. get_risk_flags returns wfh_no_diary when WFH event claimed ─────────────

def test_get_risk_flags_returns_wfh_no_diary_flag():
    from app.skills.employee_tax_au import EmployeeTaxAU
    from app.skills.base import RiskFlag
    skill = EmployeeTaxAU()
    flags = skill.get_risk_flags([_make_event(category="wfh_deduction")])
    assert any(f.id == "wfh_no_diary" for f in flags)
    assert all(isinstance(f, RiskFlag) for f in flags)


# ── 6. get_review_questions returns questions for a needs_user_review event ───

def test_get_review_questions_for_needs_user_review_event():
    from app.skills.employee_tax_au import EmployeeTaxAU
    from app.skills.base import ReviewQuestion
    skill = EmployeeTaxAU()
    event = _make_event(category="work_expense", status="needs_user_review")
    questions = skill.get_review_questions(event)
    assert len(questions) > 0
    assert all(isinstance(q, ReviewQuestion) for q in questions)


# ── 7. extract_events returns EventCandidates from a mock classification ──────

def test_extract_events_returns_event_candidates_from_classification():
    from app.skills.employee_tax_au import EmployeeTaxAU
    skill = EmployeeTaxAU()
    classification = ClassificationResult(
        document_type="payg_summary",
        confidence=0.95,
        skill_id="employee_tax_au",
        suggested_category="payg_income",
        extracted_amounts=[{"amount": 80000.0, "date": "2025-07-14", "description": "Gross income"}],
    )
    doc = Document(
        workspace_id="ws-test",
        financial_year="2024-25",
        original_filename="payg.pdf",
        storage_key="ws-test/payg.pdf",
        sha256_hash="abc123",
    )
    candidates = skill.extract_events(doc, classification)
    assert len(candidates) > 0
    assert all(isinstance(c, EventCandidate) for c in candidates)
    assert candidates[0].category == "payg_income"


# ── 8. Skill conflict → warning logged + AuditLog written ────────────────────

@pytest.mark.asyncio
async def test_skill_conflict_logged_and_written_to_audit(caplog, db_session, workspace):
    from app.skills.registry import SkillRegistry
    from app.skills.base import TaxSkill

    skill_a = MagicMock(spec=TaxSkill)
    skill_a.skill_id = "mock_skill_a"
    skill_a.owned_categories = ["payg_income"]

    skill_b = MagicMock(spec=TaxSkill)
    skill_b.skill_id = "mock_skill_b"
    skill_b.owned_categories = ["payg_income"]

    registry = SkillRegistry()
    registry.register(skill_a)

    with caplog.at_level(logging.WARNING, logger="app.skills.registry"):
        registry.register(skill_b, workspace_id=workspace.id)

    assert any("payg_income" in r.message for r in caplog.records)

    await asyncio.sleep(0.1)

    from sqlalchemy import select
    from app.db.models import AuditLog
    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.workspace_id == workspace.id,
            AuditLog.action == "skill_conflict",
        )
    )
    log = result.scalar_one()
    assert "mock_skill_a" in (log.note or "")
    assert "mock_skill_b" in (log.note or "")


# ── 10. get_questions exposes required, why, hint from YAML ──────────────────

def test_get_questions_exposes_required_why_hint():
    from app.skills.employee_tax_au import EmployeeTaxAU
    skill = EmployeeTaxAU()
    profile = _make_profile()
    questions = skill.get_questions(profile)
    # All skill questions have required=False in the YAML
    assert all(q.required is False for q in questions)
    # wfh question has a why string
    wfh_q = next(q for q in questions if q.id == "wfh")
    assert wfh_q.why is not None
    assert len(wfh_q.why) > 0
    # wfh_method question has a hint string
    wfh_method_q = next(q for q in questions if q.id == "wfh_method")
    assert wfh_method_q.hint is not None
    assert len(wfh_method_q.hint) > 0
    # wfh_days has no why or hint
    wfh_days_q = next(q for q in questions if q.id == "wfh_days")
    assert wfh_days_q.why is None
    assert wfh_days_q.hint is None


# ── 9. Skill version locked on activation → SkillVersionLock created ─────────

@pytest.mark.asyncio
async def test_skill_version_locked_on_activation(db_session, workspace):
    from app.skills.employee_tax_au import EmployeeTaxAU
    from app.repositories.skills import lock_activated_skills
    from app.db.models import SkillVersionLock
    from sqlalchemy import select

    skill = EmployeeTaxAU()
    await lock_activated_skills(db_session, workspace.id, [skill])

    result = await db_session.execute(
        select(SkillVersionLock).where(SkillVersionLock.workspace_id == workspace.id)
    )
    lock = result.scalar_one()
    assert lock.skill_id == "employee_tax_au"
    assert lock.skill_version == skill.version


def test_crypto_skill_activates_for_has_crypto():
    from app.skills.registry import get_registry
    from app.db.models import TaxProfile

    profile = TaxProfile(
        workspace_id="ws-test",
        financial_year="2024-25",
        employment_type="employee",
        has_crypto=True,
    )
    registry = get_registry()
    activated = registry.load_for_profile(profile)
    skill_ids = [s.skill_id for s in activated]
    assert "crypto_skill_au" in skill_ids
