from __future__ import annotations

from dataclasses import dataclass


CURRENT_BACKUP_FORMAT_VERSION = "2026.1"


@dataclass
class CompatibilityResult:
    blockers: list[str]
    warnings: list[str]
    notes: list[str]

    @property
    def can_restore(self) -> bool:
        return len(self.blockers) == 0


def evaluate_restore_compatibility(manifest: dict) -> CompatibilityResult:
    blockers: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    backup_format_version = str(manifest.get("backup_format_version") or "").strip()
    if not backup_format_version:
        blockers.append("Backup metadata is missing required fields.")
        return CompatibilityResult(blockers=blockers, warnings=warnings, notes=notes)

    current_major = CURRENT_BACKUP_FORMAT_VERSION.split(".", 1)[0]
    backup_major = backup_format_version.split(".", 1)[0]
    if backup_major != current_major:
        blockers.append("Unsupported backup format major version.")
    else:
        notes.append("Backup format version is compatible.")

    if not manifest.get("db_schema_version"):
        warnings.append("Database schema version is unknown; restore compatibility needs extra review.")
    if not manifest.get("app_version") or str(manifest.get("app_version")).strip().lower() == "unknown":
        warnings.append("Application version is unknown; restore compatibility needs extra review.")

    return CompatibilityResult(blockers=blockers, warnings=warnings, notes=notes)
