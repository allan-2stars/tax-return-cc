from fastapi import APIRouter

router = APIRouter()


@router.post("/workspaces/{workspace_id}/documents")
async def upload_document(workspace_id: str):
    return {"data": {}, "status": "ok"}


@router.get("/workspaces/{workspace_id}/documents")
async def list_documents(workspace_id: str):
    return {"data": [], "status": "ok"}


@router.delete("/workspaces/{workspace_id}/documents/{document_id}")
async def delete_document(workspace_id: str, document_id: str):
    return {"data": {}, "status": "ok"}
