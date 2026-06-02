import json
import os

import pytest
import pyzipper
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.db.models import Workspace
from app.services.recovery import (
    ENCRYPTION_MODE_RECOVERY_KEY_DERIVED,
    ENCRYPTION_MODE_SERVER_DERIVED,
    REQUIRED_MANIFEST_FIELDS,
    RecoveryService,
)


@pytest.mark.asyncio
async def test_manifest_generation_contains_required_metadata(test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))
    monkeypatch.setattr(settings, "SECRET_KEY", "recovery-test-secret")

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        ws = Workspace(name="Recovery WS", financial_year="2024-25", status="active")
        session.add(ws)
        await session.commit()
        await session.refresh(ws)

        service = RecoveryService(backup_path=settings.BACKUP_PATH)
        result = await service.create_backup(workspace_id=ws.id, db=session)

        verify = service.verify_backup_file(workspace_id=ws.id, backup_id=result.backup_id)
        assert verify.ok is True
        summary = verify.manifest_summary or {}
        assert summary["backup_id"] == result.backup_id
        assert summary["financial_year"] == "2024-25"

        # Validate raw encrypted manifest fields.
        backup_path = os.path.join(settings.BACKUP_PATH, ws.id, f"{result.backup_id}.trb")
        with pyzipper.AESZipFile(
            backup_path,
            "r",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as zf:
            zf.setpassword(service._password_for_workspace(ws.id))
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert REQUIRED_MANIFEST_FIELDS.issubset(set(manifest.keys()))
        assert manifest["encryption_mode"] == ENCRYPTION_MODE_SERVER_DERIVED


@pytest.mark.asyncio
async def test_recovery_key_derived_backup_manifest_mode(test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))
    monkeypatch.setattr(settings, "SECRET_KEY", "recovery-test-secret")

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        ws = Workspace(name="Recovery WS", financial_year="2024-25", status="active")
        session.add(ws)
        await session.commit()
        await session.refresh(ws)

    # Create auth setup for this workspace to establish recovery key hash.
    from app.repositories import auth as auth_repo
    from app.security import encrypt_dek, normalize_recovery_key
    import bcrypt

    recovery_key = "ABCD-EFGH-IJKL-MNOP-QRST-UVWX"
    normalized = normalize_recovery_key(recovery_key)
    password = "test-pass-123"
    async with maker() as session:
        ws = await session.get(Workspace, ws.id)
        await auth_repo.create_security(
            session,
            workspace_id=ws.id,
            password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode(),
            password_encrypted_dek=encrypt_dek(b"dek", password),
            recovery_key_hash=bcrypt.hashpw(normalized.encode(), bcrypt.gensalt(rounds=4)).decode(),
            recovery_encrypted_dek=encrypt_dek(b"dek", normalized),
            recovery_confirm_hash=bcrypt.hashpw(b"UVWX", bcrypt.gensalt(rounds=4)).decode(),
        )
        service = RecoveryService(backup_path=settings.BACKUP_PATH)
        result = await service.create_backup(
            workspace_id=ws.id,
            db=session,
            encryption_mode=ENCRYPTION_MODE_RECOVERY_KEY_DERIVED,
            recovery_key=recovery_key,
        )

        backup_path = os.path.join(settings.BACKUP_PATH, ws.id, f"{result.backup_id}.trb")
        with pyzipper.AESZipFile(
            backup_path,
            "r",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as zf:
            zf.setpassword(service._password_for_recovery_key(recovery_key))
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest["encryption_mode"] == ENCRYPTION_MODE_RECOVERY_KEY_DERIVED


@pytest.mark.asyncio
async def test_restore_preview_blocks_incompatible_backup_format_version(test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))
    monkeypatch.setattr(settings, "SECRET_KEY", "recovery-test-secret")

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        ws = Workspace(name="Recovery WS", financial_year="2024-25", status="active")
        session.add(ws)
        await session.commit()
        await session.refresh(ws)

        service = RecoveryService(backup_path=settings.BACKUP_PATH)
        result = await service.create_backup(workspace_id=ws.id, db=session)
        backup_path = os.path.join(settings.BACKUP_PATH, ws.id, f"{result.backup_id}.trb")
        with pyzipper.AESZipFile(
            backup_path,
            "r",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as zf:
            zf.setpassword(service._password_for_workspace(ws.id))
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            sections = {
                name: zf.read(name)
                for name in zf.namelist()
                if name != "manifest.json"
            }
        manifest["backup_format_version"] = "9999.1"
        with pyzipper.AESZipFile(
            backup_path,
            "w",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as zf:
            zf.setpassword(service._password_for_workspace(ws.id))
            for name, payload in sections.items():
                zf.writestr(name, payload)
            zf.writestr("manifest.json", json.dumps(manifest).encode("utf-8"))

        preview = await service.preview_backup(workspace_id=ws.id, backup_id=result.backup_id, db=session)
        assert preview.can_restore is False
        assert any("unsupported backup format major version" in item.lower() for item in preview.blockers)


@pytest.mark.asyncio
async def test_restore_preview_blocks_missing_required_metadata(test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))
    monkeypatch.setattr(settings, "SECRET_KEY", "recovery-test-secret")

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        ws = Workspace(name="Recovery WS", financial_year="2024-25", status="active")
        session.add(ws)
        await session.commit()
        await session.refresh(ws)

        service = RecoveryService(backup_path=settings.BACKUP_PATH)
        result = await service.create_backup(workspace_id=ws.id, db=session)
        backup_path = os.path.join(settings.BACKUP_PATH, ws.id, f"{result.backup_id}.trb")
        with pyzipper.AESZipFile(
            backup_path,
            "r",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as zf:
            zf.setpassword(service._password_for_workspace(ws.id))
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            sections = {
                name: zf.read(name)
                for name in zf.namelist()
                if name != "manifest.json"
            }
        manifest.pop("financial_year", None)
        with pyzipper.AESZipFile(
            backup_path,
            "w",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as zf:
            zf.setpassword(service._password_for_workspace(ws.id))
            for name, payload in sections.items():
                zf.writestr(name, payload)
            zf.writestr("manifest.json", json.dumps(manifest).encode("utf-8"))

        preview = await service.preview_backup(workspace_id=ws.id, backup_id=result.backup_id, db=session)
        assert preview.can_restore is False
        assert any("missing required fields" in item.lower() for item in preview.blockers)
