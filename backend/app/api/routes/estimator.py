from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.db.base import get_db
from app.engines.estimator import TaxEstimator

router = APIRouter()

_estimator = TaxEstimator()


# ── GET /estimator/summary ────────────────────────────────────────────────────

@router.get("/estimator/summary")
async def get_summary(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    summary = await _estimator.get_summary(workspace_id, db)
    return {
        "data": {
            "gross_income": str(summary.gross_income),
            "total_deductions": str(summary.total_deductions),
            "taxable_income": str(summary.taxable_income),
            "payg_withheld": str(summary.payg_withheld),
            "confirmed_only": summary.confirmed_only,
            "pending_count": summary.pending_count,
            "ato_calculator_url": summary.ato_calculator_url,
            "disclaimer": summary.disclaimer,
        }
    }
