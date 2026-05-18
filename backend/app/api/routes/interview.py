from fastapi import APIRouter

router = APIRouter()


@router.get("/workspaces/{workspace_id}/interview")
async def get_interview(workspace_id: str):
    return {"data": {}, "status": "ok"}


@router.post("/workspaces/{workspace_id}/interview/answer")
async def submit_answer(workspace_id: str):
    return {"data": {}, "status": "ok"}


@router.post("/workspaces/{workspace_id}/interview/back")
async def go_back(workspace_id: str):
    return {"data": {}, "status": "ok"}
