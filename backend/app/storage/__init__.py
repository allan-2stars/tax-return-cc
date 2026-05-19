from app.config import settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorageBackend


def get_storage_backend() -> StorageBackend:
    backend = settings.STORAGE_BACKEND
    if backend == "local":
        return LocalStorageBackend(base_path=settings.STORAGE_PATH)
    raise ValueError(f"Unknown STORAGE_BACKEND: {backend!r}")
