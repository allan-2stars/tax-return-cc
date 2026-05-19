import os

from app.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_path: str) -> None:
        self._base = base_path

    def _full_path(self, storage_key: str) -> str:
        return os.path.join(self._base, storage_key)

    def save(self, path: str, data: bytes) -> str:
        full = self._full_path(path)
        if os.path.exists(full):
            raise FileExistsError(f"Storage key already exists (write-once): {path}")
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(data)
        return path

    def get(self, storage_key: str) -> bytes:
        full = self._full_path(storage_key)
        if not os.path.exists(full):
            raise FileNotFoundError(f"Storage key not found: {storage_key}")
        with open(full, "rb") as f:
            return f.read()

    def delete(self, storage_key: str) -> None:
        full = self._full_path(storage_key)
        if os.path.exists(full):
            os.remove(full)

    def exists(self, storage_key: str) -> bool:
        return os.path.exists(self._full_path(storage_key))
