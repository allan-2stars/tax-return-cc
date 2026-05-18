from fastapi import APIRouter

router = APIRouter()


@router.get("/readiness")
async def get_readiness():
    return {"data": {}, "status": "ok"}


@router.post("/readiness/recalculate")
async def recalculate_readiness():
    return {"data": {}, "status": "ok"}
