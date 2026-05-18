from fastapi import APIRouter

router = APIRouter()


@router.get("/workspaces/{workspace_id}/events")
async def list_events(workspace_id: str):
    return {"data": [], "status": "ok"}


@router.post("/workspaces/{workspace_id}/events")
async def create_event(workspace_id: str):
    return {"data": {}, "status": "ok"}


@router.patch("/workspaces/{workspace_id}/events/{event_id}")
async def update_event(workspace_id: str, event_id: str):
    return {"data": {}, "status": "ok"}
