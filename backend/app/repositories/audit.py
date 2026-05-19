from app.ai.base import AIResponse
from app.db.models import AuditLog


async def log_skill_conflict(
    workspace_id: str,
    category: str,
    skill_a_id: str,
    skill_b_id: str,
) -> None:
    """Fire-and-forget: write a skill_conflict AuditLog entry via its own session."""
    import app.db.base as db_base
    try:
        async with db_base.AsyncSessionLocal() as db:
            log = AuditLog(
                workspace_id=workspace_id,
                action="skill_conflict",
                actor="system",
                note=f"Category '{category}' claimed by both {skill_a_id} and {skill_b_id}",
            )
            db.add(log)
            await db.commit()
    except Exception:
        pass

# Claude Sonnet pricing (approximate, for tracking only)
_INPUT_COST_PER_TOKEN = 3.0 / 1_000_000   # $3 per 1M input tokens
_OUTPUT_COST_PER_TOKEN = 15.0 / 1_000_000  # $15 per 1M output tokens


async def log_ai_call(
    db,
    workspace_id: str,
    operation: str,
    response: AIResponse,
    duration_ms: int,
    success: bool,
) -> None:
    cost = (
        response.input_tokens * _INPUT_COST_PER_TOKEN
        + response.output_tokens * _OUTPUT_COST_PER_TOKEN
        if success
        else 0.0
    )
    log = AuditLog(
        workspace_id=workspace_id,
        action="ai_interaction",
        actor="ai",
        ai_operation=operation,
        ai_provider=response.provider,
        ai_model=response.model,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cost_usd=cost,
        duration_ms=duration_ms,
        ai_success=success,
    )
    db.add(log)
    await db.commit()
