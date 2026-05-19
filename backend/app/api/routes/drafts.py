from fastapi import APIRouter, Depends

from app.api.dependencies import require_unlock

router = APIRouter()


@router.get("/drafts/{draft_key}")
async def get_draft(draft_key: str, dek: bytes = Depends(require_unlock)):
    return {"status": "ok", "draft_key": draft_key}
