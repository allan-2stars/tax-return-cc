from app.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    def save(self, path: str, data: bytes) -> str:
        raise NotImplementedError

    def load(self, path: str) -> bytes:
        raise NotImplementedError

    def delete(self, path: str) -> None:
        raise NotImplementedError

    def exists(self, path: str) -> bool:
        raise NotImplementedError
