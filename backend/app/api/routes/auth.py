from fastapi import APIRouter

router = APIRouter()


@router.post("/auth/login")
async def login():
    return {"data": {}, "status": "ok"}


@router.post("/auth/logout")
async def logout():
    return {"data": {}, "status": "ok"}


@router.get("/auth/session")
async def session():
    return {"data": {}, "status": "ok"}
