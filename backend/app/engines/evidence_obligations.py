from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, EvidenceMatch, EvidenceObligation, TaxEvent, TaxProfile
from app.services.evidence_rules import CURRENT_EVIDENCE_RULE_VERSION


@dataclass(frozen=True)
class ObligationRule:
    obligation_key: str
    category: str
    label: str
    description: str
    required_level: str
    source_type: str
    reason: str


@dataclass(frozen=True)
class CandidateMatch:
    match_type: str
    document_id: str | None
    tax_event_id: str | None
    confidence: float
    reason: str


def _new_rule(
    *,
    obligation_key: str,
    category: str,
    label: str,
    description: str,
    required_level: str,
    source_type: str,
    reason: str,
) -> ObligationRule:
    return ObligationRule(
        obligation_key=obligation_key,
        category=category,
        label=label,
        description=description,
        required_level=required_level,
        source_type=source_type,
        reason=reason,
    )


def _doc_type(doc: Document) -> str:
    return (doc.document_type or "").strip().lower()


def _event_category(event: TaxEvent) -> str:
    return (event.category or "").strip().lower()


def _event_type(event: TaxEvent) -> str:
    return (event.event_type or "").strip().lower()


def _candidate_identity(match_type: str, document_id: str | None, tax_event_id: str | None) -> tuple[str, str | None, str | None]:
    return (match_type, document_id, tax_event_id)


def _build_candidates(
    obligation_key: str,
    docs: list[Document],
    events: list[TaxEvent],
) -> list[CandidateMatch]:
    candidates: list[CandidateMatch] = []

    if obligation_key == "private_health_annual_statement":
        for doc in docs:
            if _doc_type(doc) in {"private_health_statement", "phi_statement"} and doc.status == "ready":
                candidates.append(
                    CandidateMatch(
                        match_type="document",
                        document_id=doc.id,
                        tax_event_id=None,
                        confidence=0.9,
                        reason="Document type indicates private health statement.",
                    )
                )

    elif obligation_key == "wfh_evidence_log":
        for doc in docs:
            if _doc_type(doc) in {"wfh_diary", "timesheet", "wfh_evidence", "work_from_home_diary"} and doc.status == "ready":
                candidates.append(
                    CandidateMatch(
                        match_type="document",
                        document_id=doc.id,
                        tax_event_id=None,
                        confidence=0.8,
                        reason="Document type indicates work-from-home evidence.",
                    )
                )
        for event in events:
            if _event_category(event) in {"wfh_deduction", "work_from_home", "wfh"}:
                candidates.append(
                    CandidateMatch(
                        match_type="tax_event",
                        document_id=event.document_id,
                        tax_event_id=event.id,
                        confidence=0.7,
                        reason="Tax event category indicates work-from-home activity.",
                    )
                )

    elif obligation_key == "donation_receipt":
        for doc in docs:
            if _doc_type(doc) in {"donation_receipt", "receipt", "invoice"} and doc.status == "ready":
                candidates.append(
                    CandidateMatch(
                        match_type="document",
                        document_id=doc.id,
                        tax_event_id=None,
                        confidence=0.7,
                        reason="Document type may support donation evidence.",
                    )
                )
        for event in events:
            if _event_category(event) == "donation":
                candidates.append(
                    CandidateMatch(
                        match_type="tax_event",
                        document_id=event.document_id,
                        tax_event_id=event.id,
                        confidence=0.8,
                        reason="Donation tax event indicates receipt evidence is expected.",
                    )
                )

    elif obligation_key == "work_expense_receipt":
        for doc in docs:
            if _doc_type(doc) in {"work_expense_receipt", "receipt", "invoice"} and doc.status == "ready":
                candidates.append(
                    CandidateMatch(
                        match_type="document",
                        document_id=doc.id,
                        tax_event_id=None,
                        confidence=0.7,
                        reason="Document type may support work expense evidence.",
                    )
                )
        for event in events:
            if _event_category(event) == "work_expense" or _event_type(event) in {"deduction", "wfh"}:
                candidates.append(
                    CandidateMatch(
                        match_type="tax_event",
                        document_id=event.document_id,
                        tax_event_id=event.id,
                        confidence=0.8,
                        reason="Work-related tax event indicates receipt evidence is expected.",
                    )
                )

    elif obligation_key == "bank_interest_statement":
        for doc in docs:
            if _doc_type(doc) in {"bank_statement", "bank_interest_statement"} and doc.status == "ready":
                candidates.append(
                    CandidateMatch(
                        match_type="document",
                        document_id=doc.id,
                        tax_event_id=None,
                        confidence=0.8,
                        reason="Document type indicates bank-interest supporting statement.",
                    )
                )
        for event in events:
            if _event_category(event) == "bank_interest":
                candidates.append(
                    CandidateMatch(
                        match_type="tax_event",
                        document_id=event.document_id,
                        tax_event_id=event.id,
                        confidence=0.8,
                        reason="Bank interest tax event indicates statement evidence.",
                    )
                )

    # Deduplicate deterministically by identity and keep first reason/confidence.
    seen: set[tuple[str, str | None, str | None]] = set()
    deduped: list[CandidateMatch] = []
    for candidate in candidates:
        ident = _candidate_identity(candidate.match_type, candidate.document_id, candidate.tax_event_id)
        if ident in seen:
            continue
        seen.add(ident)
        deduped.append(candidate)
    return deduped


async def reconcile_evidence_obligations(
    workspace_id: str,
    financial_year: str,
    db: AsyncSession,
) -> list[EvidenceObligation]:
    profile = await db.scalar(
        select(TaxProfile).where(TaxProfile.workspace_id == workspace_id)
    )
    events = (
        await db.execute(
            select(TaxEvent).where(
                TaxEvent.workspace_id == workspace_id,
                TaxEvent.financial_year == financial_year,
            )
        )
    ).scalars().all()
    docs = (
        await db.execute(
            select(Document).where(
                Document.workspace_id == workspace_id,
                Document.financial_year == financial_year,
                Document.archived.is_(False),
            )
        )
    ).scalars().all()

    rules: list[ObligationRule] = []
    if profile and profile.has_private_health:
        rules.append(
            _new_rule(
                obligation_key="private_health_annual_statement",
                category="private_health",
                label="Private Health Insurance Annual Statement",
                description="Provide your annual private health insurance statement.",
                required_level="required",
                source_type="profile",
                reason="Private Health Insurance is enabled in your profile.",
            )
        )
    if profile and profile.has_wfh:
        rules.append(
            _new_rule(
                obligation_key="wfh_evidence_log",
                category="wfh",
                label="WFH Hours or Diary Evidence",
                description="Provide WFH hours records, diary, or timesheet evidence.",
                required_level="required",
                source_type="profile",
                reason="Work from home is enabled in your profile.",
            )
        )
    if any(e.category == "donation" for e in events):
        rules.append(
            _new_rule(
                obligation_key="donation_receipt",
                category="donation",
                label="Donation Receipt",
                description="Provide receipts for donation claims.",
                required_level="required",
                source_type="tax_event",
                reason="Donation events are present.",
            )
        )
    if any(e.category == "work_expense" for e in events):
        rules.append(
            _new_rule(
                obligation_key="work_expense_receipt",
                category="work_expense",
                label="Work-Related Expense Receipt",
                description="Provide receipt or invoice evidence for work-related expenses.",
                required_level="required",
                source_type="tax_event",
                reason="Work-related expense events are present.",
            )
        )
    if any(e.category == "bank_interest" for e in events):
        rules.append(
            _new_rule(
                obligation_key="bank_interest_statement",
                category="bank_interest",
                label="Bank Interest Statement",
                description="A bank statement helps validate bank interest entries.",
                required_level="recommended",
                source_type="tax_event",
                reason="Bank interest events are present.",
            )
        )

    existing = (
        await db.execute(
            select(EvidenceObligation).where(
                EvidenceObligation.workspace_id == workspace_id,
                EvidenceObligation.financial_year == financial_year,
            )
        )
    ).scalars().all()
    by_key = {o.obligation_key: o for o in existing}
    expected_keys = {r.obligation_key for r in rules}

    for obligation in existing:
        if obligation.obligation_key not in expected_keys:
            await db.execute(
                delete(EvidenceMatch).where(EvidenceMatch.obligation_id == obligation.id)
            )
            await db.delete(obligation)

    obligations: list[EvidenceObligation] = []
    for rule in rules:
        obligation = by_key.get(rule.obligation_key)
        if obligation is None:
            obligation = EvidenceObligation(
                workspace_id=workspace_id,
                financial_year=financial_year,
                source_type=rule.source_type,
                obligation_key=rule.obligation_key,
                category=rule.category,
                label=rule.label,
                description=rule.description,
                required_level=rule.required_level,
                status="missing",
                reason=rule.reason,
                rule_version=CURRENT_EVIDENCE_RULE_VERSION,
                metadata_json={},
            )
            db.add(obligation)
            await db.flush()
        else:
            obligation.source_type = rule.source_type
            obligation.category = rule.category
            obligation.label = rule.label
            obligation.description = rule.description
            obligation.required_level = rule.required_level
            obligation.reason = rule.reason
            obligation.rule_version = CURRENT_EVIDENCE_RULE_VERSION

        existing_matches = (
            await db.execute(
                select(EvidenceMatch).where(
                    EvidenceMatch.workspace_id == workspace_id,
                    EvidenceMatch.obligation_id == obligation.id,
                )
            )
        ).scalars().all()

        # Preserve manual decisions and clear only generated candidates.
        kept_identities: set[tuple[str, str | None, str | None]] = set()
        for match in existing_matches:
            if match.status in {"accepted", "rejected"}:
                kept_identities.add(
                    _candidate_identity(match.match_type, match.document_id, match.tax_event_id)
                )

        await db.execute(
            delete(EvidenceMatch).where(
                EvidenceMatch.workspace_id == workspace_id,
                EvidenceMatch.obligation_id == obligation.id,
                EvidenceMatch.status == "candidate",
            )
        )

        for candidate in _build_candidates(obligation.obligation_key, docs, events):
            identity = _candidate_identity(
                candidate.match_type, candidate.document_id, candidate.tax_event_id
            )
            if identity in kept_identities:
                continue
            db.add(
                EvidenceMatch(
                    workspace_id=workspace_id,
                    obligation_id=obligation.id,
                    document_id=candidate.document_id,
                    tax_event_id=candidate.tax_event_id,
                    match_type=candidate.match_type,
                    confidence=candidate.confidence,
                    status="candidate",
                    reason=candidate.reason,
                    metadata_json={},
                )
            )

        await db.flush()
        all_matches = (
            await db.execute(
                select(EvidenceMatch).where(
                    EvidenceMatch.workspace_id == workspace_id,
                    EvidenceMatch.obligation_id == obligation.id,
                )
            )
        ).scalars().all()

        has_accepted = any(m.status == "accepted" for m in all_matches)
        has_candidate = any(m.status == "candidate" for m in all_matches)
        if has_accepted:
            obligation.status = "matched"
        elif has_candidate:
            obligation.status = "partially_matched"
        else:
            obligation.status = "missing"
        obligations.append(obligation)

    await db.commit()
    for obligation in obligations:
        await db.refresh(obligation)
    return obligations
