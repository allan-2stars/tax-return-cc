from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    def save(self, path: str, data: bytes) -> str: ...

    @abstractmethod
    def load(self, path: str) -> bytes: ...

    @abstractmethod
    def delete(self, path: str) -> None: ...

    @abstractmethod
    def exists(self, path: str) -> bool: ...
