from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InterviewSession, TaxEvent
from app.repositories import interview as interview_repo
from app.repositories import profiles as profile_repo
from app.repositories import skills as skills_repo
from app.skills.base import Question


# ── Platform questions ────────────────────────────────────────────────────────

PLATFORM_QUESTIONS: list[Question] = [
    Question(
        id="fy_confirm",
        ask="Which financial year are you preparing?",
        type="single_choice",
        options=["2024-25", "2023-24", "2022-23"],
    ),
    Question(
        id="residency",
        ask="What is your residency status for tax purposes?",
        type="single_choice",
        options=["resident", "non_resident", "part_year"],
        hint="This is your tax residency, not your visa status.",
        why="Your residency status determines which tax rates and offsets apply to you. Most people who live in Australia are Australian residents for tax purposes.",
    ),
    Question(
        id="employment_type",
        ask="What best describes your work situation?",
        type="single_choice",
        options=["employee", "sole_trader", "both"],
    ),
    Question(
        id="has_spouse",
        ask="Do you have a spouse or de facto partner?",
        type="single_choice",
        options=["yes", "no"],
        branches={
            "yes": ["spouse_income_range", "spouse_novated_lease"],
            "no":  [],
        },
    ),
    Question(
        id="has_dependents",
        ask="Do you have any dependent children?",
        type="single_choice",
        options=["yes", "no"],
        branches={
            "yes": ["dependent_count"],
            "no":  [],
        },
    ),
    Question(
        id="lodger_type",
        ask="How are you planning to lodge your return?",
        type="single_choice",
        options=["self", "agent", "unknown"],
        hint="Self-lodgers have an October 31 deadline. Tax agents have until May 15.",
        why="This helps us show you the right deadline reminders. If you use a registered tax agent, you usually get more time to lodge.",
    ),
]

BRANCH_QUESTIONS: list[Question] = [
    Question(
        id="spouse_income_range",
        ask="What is your spouse's approximate income range?",
        type="single_choice",
        options=["under_18200", "18200_45000", "45000_120000", "over_120000"],
        hint="Include salary, wages, and investment income. An estimate is fine.",
        why="Your spouse's income affects your Medicare Levy Surcharge threshold and Private Health Insurance rebate. We only need an approximate range.",
    ),
    Question(
        id="spouse_novated_lease",
        ask="Does your spouse have a novated lease through their employer?",
        type="single_choice",
        options=["yes", "no", "not_sure"],
        branches={
            "yes":      ["spouse_rfba_amount"],
            "no":       [],
            "not_sure": [],
        },
    ),
    Question(
        id="spouse_rfba_amount",
        ask="What is your spouse's Reportable Fringe Benefits Amount?",
        type="number",
        hint="This appears on your spouse's PAYG Payment Summary from their employer.",
        why="Reportable Fringe Benefits count toward your combined family income. This affects your Medicare Levy Surcharge and Private Health Insurance rebate calculations.",
        currency=True,
        required=False,
    ),
    Question(
        id="dependent_count",
        ask="How many dependent children do you have?",
        type="number",
    ),
]

# Mutable: skill questions are registered here at activation time
_QUESTION_BY_ID: dict[str, Question] = {
    q.id: q for q in PLATFORM_QUESTIONS + BRANCH_QUESTIONS
}

_PLATFORM_IDS: list[str] = [q.id for q in PLATFORM_QUESTIONS]
_PLATFORM_ID_SET: frozenset[str] = frozenset(_PLATFORM_IDS)

_PROFILE_FIELD_MAP: dict[str, str | None] = {
    "residency":            "resident_status",
    "employment_type":      "employment_type",
    "lodger_type":          "user_lodger_type",
    "spouse_income_range":  "spouse_income_range",
    "spouse_rfba_amount":   "spouse_rfba_amount",
    "dependent_count":      "dependent_count",
}


def _build_profile_updates(question_id: str, answer: Any) -> dict:
    if question_id == "has_spouse":
        return {"has_spouse": answer == "yes"}
    if question_id == "has_dependents":
        return {"has_dependents": answer == "yes"}
    if question_id == "spouse_novated_lease":
        return {"spouse_has_novated_lease": answer == "yes"}
    if question_id == "spouse_rfba_amount":
        return {"spouse_rfba_amount": float(answer) if answer else None}
    if question_id == "dependent_count":
        return {"dependent_count": int(answer) if answer else None}
    field = _PROFILE_FIELD_MAP.get(question_id)
    if field:
        return {field: answer}
    return {}


def _root_question_ids(questions: list[Question]) -> list[str]:
    """Return IDs for questions that are not branch-targets of any other question in the list."""
    branch_targets: set[str] = set()
    for q in questions:
        if q.branches:
            for targets in q.branches.values():
                branch_targets.update(targets)
    return [q.id for q in questions if q.id not in branch_targets]


# ── InlineQuestion ────────────────────────────────────────────────────────────

@dataclass
class InlineQuestion:
    id: str
    ask: str
    type: str = "text"
    options: list[str] | None = None


# ── Lightweight ref for check_activation_delta ───────────────────────────────

class _SkillRef:
    """Carries only skill_id so check_activation_delta can filter already-active skills."""
    def __init__(self, skill_id: str) -> None:
        self.skill_id = skill_id


# ── InterviewEngine ───────────────────────────────────────────────────────────

class InterviewEngine:
    def __init__(self, registry=None, readiness_engine=None) -> None:
        if registry is None:
            from app.skills.registry import get_registry
            registry = get_registry()
        self._registry = registry
        if readiness_engine is None:
            from app.engines.readiness import ReadinessEngine
            readiness_engine = ReadinessEngine()
        self._readiness_engine = readiness_engine

    async def start(
        self,
        workspace_id: str,
        financial_year: str,
        db: AsyncSession,
    ) -> tuple[InterviewSession, Question]:
        session = await interview_repo.create(db, workspace_id, financial_year)
        await profile_repo.get_or_create(db, workspace_id, financial_year)

        first_id = _PLATFORM_IDS[0]
        session.pending_queue = list(_PLATFORM_IDS[1:])
        session.current_step = {"id": first_id}
        session = await interview_repo.save(db, session)
        return session, _QUESTION_BY_ID[first_id]

    async def process_answer(
        self,
        session_id: str,
        question_id: str,
        answer: Any,
        db: AsyncSession,
    ) -> tuple[InterviewSession, Question | None]:
        session = await interview_repo.get_by_id(db, session_id)
        profile = await profile_repo.get_by_workspace(db, session.workspace_id)

        current_id = (session.current_step or {}).get("id")
        if current_id != question_id:
            raise ValueError(f"Expected answer for {current_id!r}, got {question_id!r}")

        # Persist answer
        answers = dict(session.answers or {})
        answers[question_id] = answer
        session.answers = answers

        # Update TaxProfile fields
        updates = _build_profile_updates(question_id, answer)
        if updates and profile:
            await profile_repo.update_fields(db, profile, updates)

        # Branch questions triggered by this answer
        current_q = _QUESTION_BY_ID.get(question_id)
        branches_triggered: list[str] = (
            list((current_q.branches or {}).get(answer, []))
            if (current_q and current_q.branches)
            else []
        )

        # Check for newly activated skills
        current_skill_refs = [_SkillRef(sid) for sid in (session.activated_skills or [])]
        new_skills = self._registry.check_activation_delta(answers, current_skill_refs)

        # Register all skill questions in lookup; only root questions go into queue
        skill_q_ids: list[str] = []
        for skill in new_skills:
            questions = skill.get_questions(None)
            for q in questions:
                _QUESTION_BY_ID[q.id] = q
            skill_q_ids.extend(_root_question_ids(questions))

        # Record undo entry
        branch_path = list(session.branch_path or [])
        branch_path.append({
            "question_id":              question_id,
            "branches_inserted":        branches_triggered,
            "skill_questions_inserted": skill_q_ids,
            "skills_activated":         [s.skill_id for s in new_skills],
        })
        session.branch_path = branch_path

        # Rebuild queue:
        #   branches  → front (conversational context)
        #   skill qs  → after last remaining platform question
        pending = list(session.pending_queue or [])
        pending = branches_triggered + pending

        if skill_q_ids:
            last_platform_idx = -1
            for i, qid in enumerate(pending):
                if qid in _PLATFORM_ID_SET:
                    last_platform_idx = i
            insert_at = last_platform_idx + 1
            pending = pending[:insert_at] + skill_q_ids + pending[insert_at:]

        # Lock newly activated skills (idempotent)
        if new_skills:
            activated = list(session.activated_skills or [])
            activated.extend(s.skill_id for s in new_skills)
            session.activated_skills = activated
            await skills_repo.lock_activated_skills(db, session.workspace_id, new_skills)

        completed = list(session.completed_steps or [])
        completed.append(question_id)
        session.completed_steps = completed

        # Edit mode: target question just answered
        if session.edit_mode and question_id == session.edit_target:
            session.edit_target = None
            if not branches_triggered:
                # No new branches → return to completion immediately
                session.state = "awaiting_evidence"
                session.edit_mode = False
                session.current_step = None
                session.pending_queue = []
                session = await interview_repo.save(db, session)
                await self._readiness_engine.mark_stale(session.workspace_id, db)
                return session, None
            else:
                # New branches triggered → replace pending with ONLY those branches.
                # The remaining original queue is discarded so we return to summary
                # as soon as the branch questions are exhausted.
                pending = list(branches_triggered)

        # Advance
        if pending:
            next_id = pending.pop(0)
            # Re-register skill questions if missing (handles server restart where
            # _QUESTION_BY_ID is in-memory and does not survive process restarts)
            if next_id not in _QUESTION_BY_ID:
                for skill_id in (session.activated_skills or []):
                    skill = self._registry.get_skill(skill_id)
                    if skill:
                        for sq in skill.get_questions(None):
                            _QUESTION_BY_ID[sq.id] = sq
            next_q = _QUESTION_BY_ID.get(next_id)
            if next_q is None:
                raise ValueError(f"Unknown question in queue: {next_id!r}")
            session.current_step = {"id": next_id}
            session.pending_queue = pending
            session = await interview_repo.save(db, session)
            await self._readiness_engine.mark_stale(session.workspace_id, db)
            return session, next_q

        # Edit mode: branch queue exhausted → return to completion
        if session.edit_mode:
            session.state = "awaiting_evidence"
            session.edit_mode = False
            session.edit_target = None

        session.current_step = None
        session.pending_queue = []
        session = await interview_repo.save(db, session)
        await self._readiness_engine.mark_stale(session.workspace_id, db)
        return session, None

    async def go_back(
        self,
        session_id: str,
        db: AsyncSession,
    ) -> tuple[InterviewSession, Question]:
        session = await interview_repo.get_by_id(db, session_id)

        branch_path = list(session.branch_path or [])
        if not branch_path:
            raise ValueError("Nothing to go back to")

        entry = branch_path.pop()
        question_id = entry["question_id"]
        all_to_remove = (
            set(entry.get("branches_inserted", []))
            | set(entry.get("skill_questions_inserted", []))
        )
        skills_to_deactivate: list[str] = entry.get("skills_activated", [])

        # Rebuild pending: restore current_step to front, strip inserted items
        pending = list(session.pending_queue or [])
        current_id = (session.current_step or {}).get("id")
        if current_id:
            pending = [current_id] + pending
        pending = [qid for qid in pending if qid not in all_to_remove]

        # Undo skill activations and delete locks
        activated = list(session.activated_skills or [])
        for skill_id in skills_to_deactivate:
            if skill_id in activated:
                activated.remove(skill_id)
            await skills_repo.delete_skill_lock(db, session.workspace_id, skill_id)
        session.activated_skills = activated

        # Remove the answer
        answers = dict(session.answers or {})
        answers.pop(question_id, None)
        session.answers = answers

        completed = list(session.completed_steps or [])
        if question_id in completed:
            completed.remove(question_id)
        session.completed_steps = completed

        session.current_step = {"id": question_id}
        session.pending_queue = pending
        session.branch_path = branch_path

        session = await interview_repo.save(db, session)
        return session, _QUESTION_BY_ID[question_id]

    async def skip(
        self,
        session_id: str,
        question_id: str,
        reason: str,
        db: AsyncSession,
    ) -> tuple[InterviewSession, Question | None]:
        session = await interview_repo.get_by_id(db, session_id)

        skipped = list(session.skipped_steps or [])
        skipped.append({"question_id": question_id, "reason": reason})
        session.skipped_steps = skipped

        pending = list(session.pending_queue or [])
        if pending:
            next_id = pending.pop(0)
            session.current_step = {"id": next_id}
            session.pending_queue = pending
            session = await interview_repo.save(db, session)
            return session, _QUESTION_BY_ID[next_id]

        session.current_step = None
        session.pending_queue = []
        session = await interview_repo.save(db, session)
        return session, None

    async def pause(self, session_id: str, db: AsyncSession) -> InterviewSession:
        session = await interview_repo.get_by_id(db, session_id)
        session.state = "paused"
        session = await interview_repo.save(db, session)
        return session

    async def resume(
        self, session_id: str, db: AsyncSession
    ) -> tuple[InterviewSession, Question]:
        session = await interview_repo.get_by_id(db, session_id)
        session.state = "in_progress"
        session = await interview_repo.save(db, session)
        current_id = (session.current_step or {}).get("id")
        if not current_id:
            raise ValueError("No current question to resume")
        return session, _QUESTION_BY_ID[current_id]

    async def complete(self, session_id: str, db: AsyncSession) -> InterviewSession:
        import asyncio
        session = await interview_repo.get_by_id(db, session_id)
        session.state = "awaiting_evidence"
        session.completed_at = datetime.now(timezone.utc)
        session = await interview_repo.save(db, session)
        asyncio.create_task(self._readiness_engine.recalculate(session.workspace_id))
        return session

    async def jump(
        self,
        session_id: str,
        question_id: str,
        db: AsyncSession,
        edit_mode: bool = False,
    ) -> tuple[InterviewSession, Question]:
        session = await interview_repo.get_by_id(db, session_id)

        if question_id not in (session.completed_steps or []):
            raise ValueError(f"Question {question_id!r} not in completed steps")

        # Re-register skill questions that may be absent after a server restart.
        # _QUESTION_BY_ID is only populated lazily during process_answer(); after
        # restart it only contains platform + branch questions.
        for skill_id in (session.activated_skills or []):
            skill_obj = self._registry.get_skill(skill_id)
            if skill_obj:
                for q in skill_obj.get_questions(None):
                    _QUESTION_BY_ID[q.id] = q

        # Iteratively call go_back until current_step == question_id
        max_steps = len(session.branch_path or []) + 1
        try:
            for _ in range(max_steps):
                if (session.current_step or {}).get("id") == question_id:
                    break
                session, _ = await self.go_back(session_id, db)
            else:
                raise ValueError(
                    f"Could not reach {question_id!r} after {max_steps} steps"
                )
        except (ValueError, KeyError) as exc:
            raise ValueError(
                f"Cannot reach question {question_id!r}: {exc}"
            ) from exc

        session.state = "in_progress"
        session.edit_mode = edit_mode
        session.edit_target = question_id if edit_mode else None
        session = await interview_repo.save(db, session)
        q = _QUESTION_BY_ID.get(question_id)
        if q is None:
            raise ValueError(f"Question {question_id!r} not found in question registry")
        return session, q

    async def check_inline_questions(
        self,
        workspace_id: str,
        events: list[TaxEvent],
        db: AsyncSession,
    ) -> list[tuple[TaxEvent, list[InlineQuestion]]]:
        results = []
        for event in events:
            skill = self._registry.get_owner(event.category)
            if skill is None:
                continue
            review_questions = skill.get_review_questions(event)
            if not review_questions:
                continue
            results.append((event, [
                InlineQuestion(id=rq.id, ask=rq.ask, type=rq.type, options=rq.options)
                for rq in review_questions
            ]))
        return results
