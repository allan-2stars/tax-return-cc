from fastapi import APIRouter

router = APIRouter()


@router.get("/workspaces/{workspace_id}/review")
async def get_review_queue(workspace_id: str):
    return {"data": [], "status": "ok"}


@router.post("/workspaces/{workspace_id}/review/{item_id}/action")
async def take_action(workspace_id: str, item_id: str):
    return {"data": {}, "status": "ok"}
