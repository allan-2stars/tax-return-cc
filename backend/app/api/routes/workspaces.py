from fastapi import APIRouter

router = APIRouter()


@router.get("/workspaces")
async def list_workspaces():
    return {"data": [], "status": "ok"}


@router.post("/workspaces")
async def create_workspace():
    return {"data": {}, "status": "ok"}


@router.get("/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str):
    return {"data": {}, "status": "ok"}
