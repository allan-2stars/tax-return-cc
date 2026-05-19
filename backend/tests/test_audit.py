import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.base import AIResponse
from app.repositories import audit as audit_repo


@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def workspace(db_session):
    from app.db.models import Workspace
    ws = Workspace(name="Audit Test WS", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest.mark.asyncio
async def test_log_ai_call_writes_correct_fields(db_session, workspace):
    response = AIResponse(
        content='{"document_type": "receipt"}',
        input_tokens=100,
        output_tokens=50,
        provider="claude",
        model="claude-sonnet-4-6",
    )

    await audit_repo.log_ai_call(
        db=db_session,
        workspace_id=workspace.id,
        operation="classify",
        response=response,
        duration_ms=420,
        success=True,
    )

    from sqlalchemy import select
    from app.db.models import AuditLog
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.workspace_id == workspace.id)
    )
    log = result.scalar_one()

    assert log.action == "ai_interaction"
    assert log.actor == "ai"
    assert log.ai_operation == "classify"
    assert log.ai_provider == "claude"
    assert log.ai_model == "claude-sonnet-4-6"
    assert log.input_tokens == 100
    assert log.output_tokens == 50
    assert log.duration_ms == 420
    assert log.ai_success is True
    assert log.cost_usd is not None
    assert log.cost_usd > 0


@pytest.mark.asyncio
async def test_log_ai_call_cost_calculation(db_session, workspace):
    # 1M input tokens = $3, 1M output tokens = $15
    # 1000 input + 500 output → (1000/1_000_000)*3 + (500/1_000_000)*15
    #                         = 0.003 + 0.0075 = 0.0105
    response = AIResponse(
        content="",
        input_tokens=1000,
        output_tokens=500,
        provider="claude",
        model="claude-sonnet-4-6",
    )
    await audit_repo.log_ai_call(
        db=db_session,
        workspace_id=workspace.id,
        operation="explain",
        response=response,
        duration_ms=200,
        success=True,
    )

    from sqlalchemy import select
    from app.db.models import AuditLog
    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.workspace_id == workspace.id,
            AuditLog.ai_operation == "explain",
        )
    )
    log = result.scalar_one()
    assert abs(log.cost_usd - 0.0105) < 0.0001


@pytest.mark.asyncio
async def test_log_ai_call_failed_operation(db_session, workspace):
    response = AIResponse(content="", input_tokens=0, output_tokens=0, provider="claude", model="claude-sonnet-4-6")
    await audit_repo.log_ai_call(
        db=db_session,
        workspace_id=workspace.id,
        operation="classify",
        response=response,
        duration_ms=15001,
        success=False,
    )

    from sqlalchemy import select
    from app.db.models import AuditLog
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.workspace_id == workspace.id)
    )
    log = result.scalar_one()
    assert log.ai_success is False
    assert log.cost_usd == 0.0
