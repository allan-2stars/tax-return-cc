from app.db.models import YoySuggestion
from app.repositories import yoy as yoy_repo


def _prev_fy(financial_year: str) -> str:
    """'2024-25' → '2023-24'"""
    start = int(financial_year.split("-")[0])
    return f"{start - 1}-{str(start)[-2:]}"


class YoYEngine:

    async def generate_suggestions(
        self, current_workspace_id: str, db
    ) -> list[YoySuggestion]:
        from sqlalchemy import select
        from app.db.models import TaxEvent, Workspace

        # Find current workspace's FY
        ws_result = await db.execute(
            select(Workspace).where(Workspace.id == current_workspace_id)
        )
        current_ws = ws_result.scalar_one_or_none()
        if current_ws is None:
            return []

        prev_fy = _prev_fy(current_ws.financial_year)

        # Find previous FY workspace
        prev_ws_result = await db.execute(
            select(Workspace).where(Workspace.financial_year == prev_fy)
        )
        prev_ws = prev_ws_result.scalar_one_or_none()
        if prev_ws is None:
            return []

        # Get confirmed deduction events from previous FY workspace
        prev_events_result = await db.execute(
            select(TaxEvent).where(
                TaxEvent.workspace_id == prev_ws.id,
                TaxEvent.status == "confirmed",
                TaxEvent.event_type.in_(["deduction", "wfh"]),
            )
        )
        prev_events = list(prev_events_result.scalars().all())

        if not prev_events:
            return []

        # Get current FY categories (to exclude already-present ones)
        current_events_result = await db.execute(
            select(TaxEvent.category).where(
                TaxEvent.workspace_id == current_workspace_id,
            )
        )
        current_categories = {row[0] for row in current_events_result.all()}

        # Build suggestions, one per category (de-duplicated)
        seen_categories: set[str] = set()
        suggestions: list[YoySuggestion] = []
        for ev in prev_events:
            if ev.category in current_categories:
                continue
            if ev.category in seen_categories:
                continue
            seen_categories.add(ev.category)
            suggestions.append(YoySuggestion(
                workspace_id=current_workspace_id,
                source_workspace_id=prev_ws.id,
                financial_year=current_ws.financial_year,
                category=ev.category,
                description=ev.description,
                amount_last_year=ev.amount,
                frequency="annual",
                status="pending",
            ))

        return await yoy_repo.create_suggestions(db, suggestions)

    async def process_action(
        self, suggestion_id: str, action: str, db
    ) -> YoySuggestion:
        valid = ("confirmed", "dismissed", "not_applicable")
        if action not in valid:
            raise ValueError(f"Invalid action {action!r}. Must be one of: {valid}")
        return await yoy_repo.update_action(db, suggestion_id, action)
