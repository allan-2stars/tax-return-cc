# READINESS_2_0.md

## Purpose

Define a next-generation readiness model that composes three dimensions already present in the platform:
- Journey state (interview completeness/incompleteness)
- Review state (tax event confirmation quality)
- Evidence state (obligation and match completeness)

This is a design-only document. No runtime behavior changes are included here.

---

## 1) Current Readiness Data Flow

## Backend
1. `GET /api/v1/readiness` returns:
   - legacy score data (`percentage`, skill `breakdown`, `missing_items_count`, `review_items_count`, `agent_items_count`, `is_stale`)
   - additive evidence summary (`evidence_obligation_summary`)
   - evidence freshness (`evidence_freshness`)
2. Legacy score is produced by `ReadinessEngine.calculate()` in `backend/app/engines/readiness.py`:
   - skill requirements -> weighted score
   - derives review/agent counts from `TaxEvent.status`
3. Evidence summary in readiness route is separately computed from `EvidenceObligation` status counts.
4. Journey incompleteness is currently consumed in UI via `GET /api/v1/interview/session` (`has_incomplete_questions`), not integrated into readiness score itself.

## Export relationship (current)
1. `GET /api/v1/export/eligibility` now includes evidence preview and soft-block messaging.
2. Export hard blockers still come from existing eligibility checks (journey complete, confirmed events, document processing, etc.).
3. Evidence currently influences warnings/preview but does not hard-block export.

## Frontend
1. Readiness page uses `useReadiness()` + interview session query.
2. Journey incomplete warning is rendered from interview session data.
3. Evidence readiness mini-summary is rendered from readiness evidence summary.
4. Overall readiness ring still reflects legacy skill-weighted score.

---

## 2) Current Readiness Weaknesses

1. **Split truth model**:
   - Journey completeness is not first-class in readiness payload and score semantics.
2. **Single aggregate percentage ambiguity**:
   - users interpret one number as “export ready”, but it currently mixes legacy skill logic with separate evidence counters.
3. **Review dimension under-modeled**:
   - only count-level visibility (`review_items_count`/`agent_items_count`), no explicit review readiness state object.
4. **Evidence matching semantics are richer than score**:
   - accepted/candidate/rejected match decisions are not surfaced as a structured readiness state beyond status counts.
5. **Blocking policy is distributed**:
   - journey blocking exists in export engine checks;
   - evidence soft-block exists in export preview;
   - readiness has warning UI but no explicit blocking contract object.

---

## 3) Proposed Response Schema (Readiness 2.0)

Additive schema under `readiness_2_0` in `GET /readiness`:

```json
{
  "readiness_2_0": {
    "overall": {
      "state": "blocked|warning|ready",
      "score": 0,
      "label": "Not Ready|Needs Attention|Ready"
    },
    "journey": {
      "is_complete": false,
      "has_incomplete_questions": true,
      "required_blockers_count": 2,
      "incomplete_questions": [
        { "question_id": "wfh_days", "question_label": "...", "editable": true }
      ],
      "state": "blocked|warning|ready"
    },
    "review": {
      "unconfirmed_total": 0,
      "needs_user_review_count": 0,
      "needs_agent_review_count": 0,
      "confirmed_count": 0,
      "rejected_or_flagged_count": 0,
      "state": "blocked|warning|ready"
    },
    "evidence": {
      "required_missing_count": 0,
      "required_partial_count": 0,
      "required_matched_count": 0,
      "recommended_missing_count": 0,
      "candidate_match_count": 0,
      "accepted_match_count": 0,
      "rejected_match_count": 0,
      "blocking_obligations": [],
      "state": "blocked|warning|ready",
      "current_rule_version": "2026.1"
    },
    "blocking_reasons": [],
    "warnings": [],
    "last_calculated_at": "..."
  }
}
```

Notes:
- Keep existing readiness fields for compatibility.
- `readiness_2_0` is additive and can be feature-flagged.

---

## 4) Proposed Scoring Model

Use multi-axis composition, not a single direct merge of legacy score.

1. **Dimension scores (0-100)**
   - Journey score:
     - 100 if complete and no required incomplete questions
     - else proportional by `(required_answered / required_total)` with floor 0
   - Review score:
     - weighted by event status:
       - confirmed = 1.0
       - needs_user_review = 0.5
       - needs_agent_review = 0.25
       - flagged/rejected unresolved = 0.0
   - Evidence score:
       - required matched = 1.0
       - required partial = 0.5
       - required missing = 0.0
       - recommended affects warning severity, not hard blocking score floor

2. **Overall score**
   - Default weighted average:
     - journey 40%
     - review 30%
     - evidence 30%
   - Clamp to blocked tier if any hard blocker exists.

3. **State derivation**
   - `blocked`: any hard blocker in journey/review/evidence policy
   - `warning`: no blockers but warnings exist
   - `ready`: no blockers and low-warning threshold

---

## 5) Blocking vs Warning Rules

## Hard blockers (for readiness state; export hard gate remains separate for now)
1. Journey:
   - required incomplete questions > 0 -> blocked
2. Review:
   - policy option A (recommended): `needs_agent_review_count > 0` => warning (not blocked)
   - policy option B (strict): unresolved high-risk/agent-required => blocked
3. Evidence:
   - required missing/partial -> blocked in readiness state (even if export still soft-block for now)

## Warnings
1. Recommended evidence missing.
2. Candidate-only matches without acceptance.
3. Pending review items not critical.

This keeps readiness strict as a preparation signal while export remains backward compatible during transition.

---

## 6) UI Changes Needed

1. Readiness page:
   - replace single implicit interpretation with explicit 3 cards:
     - Journey readiness
     - Review readiness
     - Evidence readiness
2. Keep existing ring during migration, but label as “Overall preparation score”.
3. Show explicit blockers list with direct actions:
   - Journey -> `/journey`
   - Review -> `/review`
   - Evidence -> `/readiness/checklist`
4. Distinguish warnings vs blockers visually.
5. Show evidence freshness timestamp and reconcile status near evidence card.

---

## 7) Export Eligibility Relationship

1. Short-term:
   - Export continues using existing hard checks.
   - Evidence remains soft-block in export eligibility response.
2. Mid-term:
   - Export eligibility can consume `readiness_2_0.blocking_reasons` as additive context.
3. Long-term:
   - Optional convergence: export hard gate can adopt evidence hard-block once product approves.

Key rule: Do not couple rollout of readiness model with immediate export hard-gating changes.

---

## 8) Migration / Backward Compatibility Plan

1. Add `readiness_2_0` response object additively.
2. Keep all existing readiness fields unchanged.
3. Maintain old frontend consumers.
4. Incrementally migrate UI to new fields behind feature flag.
5. Deprecate legacy-only interpretations after telemetry confirms adoption.

No DB schema change is required for phase 1; model can be assembled from existing:
- interview session state
- tax events/review statuses
- evidence obligations/matches

---

## 9) Test Matrix

## Backend API tests
1. `GET /readiness` includes `readiness_2_0`.
2. Journey incomplete => `journey.state=blocked`, blocker listed.
3. Review unresolved counts map to review state correctly.
4. Evidence required missing/partial reflected with blocking obligations.
5. Candidate vs accepted/rejected matches update evidence sub-counts.
6. Backward compatibility: legacy readiness fields still present and valid.

## Frontend tests
1. Readiness page renders 3-dimension cards and blocker/warning sections.
2. Journey blocker links to `/journey`.
3. Review warnings/blocks link to `/review`.
4. Evidence blocker/warning links to `/readiness/checklist`.
5. Legacy ring still renders during migration.

## Integration tests
1. Skip required journey question -> readiness journey blocked.
2. Confirm review items -> review dimension improves.
3. Accept evidence matches -> evidence dimension improves.
4. Export eligibility still unchanged for hard-gate behavior.

---

## 10) Recommended Implementation Order

1. **Phase 1 (Backend additive)**
   - add `readiness_2_0` object to readiness route
   - no UI switch yet
2. **Phase 2 (Frontend additive UI)**
   - render three dimensions + blocker/warning panels
3. **Phase 3 (Policy tuning)**
   - finalize review blocker semantics (warning vs block)
4. **Phase 4 (Export alignment)**
   - decide whether/when evidence soft-block becomes hard gate
5. **Phase 5 (Legacy cleanup)**
   - retire ambiguous single-score messaging

---

## Recommendation

Proceed next with **12B-2 Backend additive readiness_2_0 payload** first.  
It has the lowest risk and unlocks UI iteration without forcing export gating decisions.

