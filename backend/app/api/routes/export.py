from fastapi import APIRouter

router = APIRouter()


@router.post("/workspaces/{workspace_id}/export/generate")
async def generate_export(workspace_id: str):
    return {"data": {}, "status": "ok"}


@router.get("/workspaces/{workspace_id}/export/{export_id}/status")
async def export_status(workspace_id: str, export_id: str):
    return {"data": {}, "status": "ok"}


@router.get("/workspaces/{workspace_id}/export/{export_id}/download")
async def download_export(workspace_id: str, export_id: str):
    return {"data": {}, "status": "ok"}
