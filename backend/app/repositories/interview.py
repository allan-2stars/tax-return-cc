from datetime import datetime, timezone

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InterviewSession


async def create(
    db: AsyncSession,
    workspace_id: str,
    financial_year: str,
) -> InterviewSession:
    session = InterviewSession(
        workspace_id=workspace_id,
        financial_year=financial_year,
        state="in_progress",
        answers={},
        pending_queue=[],
        completed_steps=[],
        skipped_steps=[],
        branch_path=[],
        activated_skills=[],
        started_at=datetime.now(timezone.utc),
        last_active_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_by_id(db: AsyncSession, session_id: str) -> InterviewSession | None:
    result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    return result.scalar_one_or_none()


async def get_active_by_workspace(
    db: AsyncSession, workspace_id: str
) -> InterviewSession | None:
    state_priority = case(
        (InterviewSession.state == "in_progress", 0),
        (InterviewSession.state == "paused", 1),
        (InterviewSession.state == "awaiting_evidence", 2),
        (InterviewSession.state == "not_started", 3),
        else_=4,
    )
    current_step_priority = case(
        (InterviewSession.current_step.is_not(None), 0),
        else_=1,
    )
    result = await db.execute(
        select(InterviewSession)
        .where(
            InterviewSession.workspace_id == workspace_id,
            InterviewSession.state.in_(
                ["not_started", "in_progress", "paused", "awaiting_evidence"]
            ),
        )
        .order_by(
            state_priority.asc(),
            current_step_priority.asc(),
            InterviewSession.last_active_at.desc(),
            InterviewSession.created_at.desc(),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def save(db: AsyncSession, session: InterviewSession) -> InterviewSession:
    session.last_active_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session
