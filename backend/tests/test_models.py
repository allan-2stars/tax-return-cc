import pytest
from sqlalchemy import inspect


@pytest.mark.asyncio
async def test_all_20_tables_created(test_engine):
    async with test_engine.connect() as conn:
        table_names = set(
            await conn.run_sync(lambda c: inspect(c).get_table_names())
        )
    expected = {
        "workspaces", "tax_profiles", "interview_sessions", "documents",
        "tax_events", "review_items", "readiness_scores", "export_records",
        "workspace_security", "audit_logs", "yoy_suggestions",
        "skill_version_locks", "feature_flags", "background_jobs",
        "tax_deadline_reminders", "encrypted_drafts",
        "evidence_obligations", "evidence_matches",
        "evidence_match_decision_history",
        "review_decision_history",
    }
    assert expected == table_names
