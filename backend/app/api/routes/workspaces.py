import bcrypt

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth, sign_session
from app.config import settings
from app.db.base import get_db
from app.db.models import ReadinessScore, Workspace, WorkspaceSecurity
from app.errors import error_response
from app.repositories import auth as auth_repo
from app.repositories import profiles as profiles_repo
from app.engines.yoy import YoYEngine
from app.services.recovery_policy import RecoveryGuardError, RecoveryPolicyService

router = APIRouter()


def _cookie_secure() -> bool:
    return settings.ENVIRONMENT == "production"


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")


class UpdateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class DeleteWorkspaceRequest(BaseModel):
    password: str


def _ws_dict(ws: Workspace, readiness_pct: float) -> dict:
    return {
        "id": ws.id,
        "name": ws.name,
        "financial_year": ws.financial_year,
        "status": ws.status,
        "readiness_pct": readiness_pct,
    }


@router.post("/workspaces")
async def create_workspace(
    body: CreateWorkspaceRequest,
    response: Response,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    # 1. Check no duplicate FY
    existing = await db.execute(
        select(Workspace).where(Workspace.financial_year == body.financial_year)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail=error_response(
                "already_exists",
                f"A workspace for {body.financial_year} already exists.",
                retryable=False,
            ),
        )

    # 2. Create workspace
    new_ws = Workspace(name=body.name, financial_year=body.financial_year, status="active")
    db.add(new_ws)
    await db.commit()
    await db.refresh(new_ws)

    # 3. Copy TaxProfile basics from current workspace
    current_profile = await profiles_repo.get_by_workspace(db, workspace_id)
    current_security = await auth_repo.get_security(db, workspace_id)
    new_profile = await profiles_repo.get_or_create(db, new_ws.id, body.financial_year)
    if current_profile:
        copy_keys = [
            "employment_type", "resident_status", "user_lodger_type",
            "has_wfh", "has_investments", "has_crypto", "has_property",
            "has_private_health", "has_sole_trader", "has_spouse", "has_dependents",
        ]
        await profiles_repo.update_fields(
            db, new_profile, {k: getattr(current_profile, k) for k in copy_keys}
        )
    if current_security:
        db.add(
            WorkspaceSecurity(
                workspace_id=new_ws.id,
                password_hash=current_security.password_hash,
                password_encrypted_dek=current_security.password_encrypted_dek,
                recovery_key_hash=current_security.recovery_key_hash,
                recovery_encrypted_dek=current_security.recovery_encrypted_dek,
                recovery_confirm_hash=current_security.recovery_confirm_hash,
                setup_confirmed=current_security.setup_confirmed,
            )
        )
        await db.commit()

    # 4. Trigger YoY suggestions (graceful no-op if no prior FY workspace)
    yoy = YoYEngine()
    suggestions = await yoy.generate_suggestions(new_ws.id, db)

    # 5. Re-issue session cookie pointing to the new workspace
    max_age = settings.SESSION_MAX_AGE_DAYS * 86400
    response.set_cookie(
        "session",
        sign_session(new_ws.id),
        max_age=max_age,
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
        path="/",
    )

    # 6. Return
    return {
        "data": {**_ws_dict(new_ws, 0.0), "yoy_count": len(suggestions)},
        "status": "ok",
    }


@router.get("/workspaces")
async def list_workspaces(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(select(Workspace))
    workspaces = rows.scalars().all()

    items = []
    for ws in workspaces:
        score_row = await db.execute(
            select(ReadinessScore)
            .where(ReadinessScore.workspace_id == ws.id)
            .order_by(ReadinessScore.calculated_at.desc())
            .limit(1)
        )
        score = score_row.scalar_one_or_none()
        items.append(_ws_dict(ws, score.percentage if score else 0.0))

    return {"data": {"items": items}, "status": "ok"}


@router.post("/workspaces/{target_id}/select")
async def select_workspace(
    target_id: str,
    response: Response,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    ws = await db.get(Workspace, target_id)
    if not ws or ws.status != "active":
        raise HTTPException(
            status_code=404,
            detail=error_response("not_found", "Workspace not found.", retryable=False),
        )

    max_age = settings.SESSION_MAX_AGE_DAYS * 86400
    response.set_cookie(
        "session",
        sign_session(ws.id),
        max_age=max_age,
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
        path="/",
    )

    score_row = await db.execute(
        select(ReadinessScore)
        .where(ReadinessScore.workspace_id == ws.id)
        .order_by(ReadinessScore.calculated_at.desc())
        .limit(1)
    )
    score = score_row.scalar_one_or_none()
    return {"data": _ws_dict(ws, score.percentage if score else 0.0), "status": "ok"}


@router.patch("/workspaces/{target_id}")
async def update_workspace(
    target_id: str,
    body: UpdateWorkspaceRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    if target_id != workspace_id:
        raise HTTPException(
            status_code=403,
            detail=error_response("forbidden", "Cannot modify another workspace.", retryable=False),
        )
    ws = await db.get(Workspace, target_id)
    if not ws:
        raise HTTPException(
            status_code=404,
            detail=error_response("not_found", "Workspace not found.", retryable=False),
        )
    ws.name = body.name
    await db.commit()
    return {"data": _ws_dict(ws, 0.0), "status": "ok"}


@router.post("/workspaces/{target_id}/archive")
async def archive_workspace(
    target_id: str,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    if target_id != workspace_id:
        raise HTTPException(
            status_code=403,
            detail=error_response("forbidden", "Cannot modify another workspace.", retryable=False),
        )
    ws = await db.get(Workspace, target_id)
    if not ws:
        raise HTTPException(
            status_code=404,
            detail=error_response("not_found", "Workspace not found.", retryable=False),
        )
    policy = RecoveryPolicyService()
    try:
        await policy.require_recent_backup_or_raise(db=db, workspace_id=workspace_id, operation="workspace_archive")
    except RecoveryGuardError as e:
        detail = error_response(e.error_code, e.message, action=e.action, retryable=e.retryable)
        detail["data"] = e.status.to_dict()
        raise HTTPException(status_code=409, detail=detail)
    ws.status = "archived"
    await db.commit()
    return {"data": _ws_dict(ws, 0.0), "status": "ok"}


@router.delete("/workspaces/{target_id}")
async def delete_workspace(
    target_id: str,
    body: DeleteWorkspaceRequest,
    response: Response,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    if target_id != workspace_id:
        raise HTTPException(
            status_code=403,
            detail=error_response("forbidden", "Cannot modify another workspace.", retryable=False),
        )
    ws = await db.get(Workspace, target_id)
    if not ws:
        raise HTTPException(
            status_code=404,
            detail=error_response("not_found", "Workspace not found.", retryable=False),
        )
    sec = await auth_repo.get_security(db, workspace_id)
    if not sec or not bcrypt.checkpw(body.password.encode(), sec.password_hash.encode()):
        raise HTTPException(
            status_code=400,
            detail=error_response("invalid_password", "Incorrect password.", retryable=False),
        )
    policy = RecoveryPolicyService()
    try:
        await policy.require_recent_backup_or_raise(db=db, workspace_id=workspace_id, operation="workspace_delete")
    except RecoveryGuardError as e:
        detail = error_response(e.error_code, e.message, action=e.action, retryable=e.retryable)
        detail["data"] = e.status.to_dict()
        raise HTTPException(status_code=409, detail=detail)
    ws.status = "deleted"
    await db.commit()

    rows = await db.execute(
        select(Workspace)
        .where(Workspace.status == "active", Workspace.id != target_id)
        .order_by(Workspace.created_at.desc())
        .limit(1)
    )
    other = rows.scalar_one_or_none()
    if other:
        max_age = settings.SESSION_MAX_AGE_DAYS * 86400
        response.set_cookie(
            "session",
            sign_session(other.id),
            max_age=max_age,
            httponly=True,
            secure=_cookie_secure(),
            samesite="strict",
            path="/",
        )
        redirect_to = "/journey"
    else:
        response.delete_cookie("session", path="/")
        response.delete_cookie("unlock_session", path="/")
        redirect_to = "/setup"

    return {"data": {"redirect_to": redirect_to}, "status": "ok"}
