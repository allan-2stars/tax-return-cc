import os
import pytest

from app.storage.local import LocalStorageBackend


@pytest.fixture
def storage(tmp_path):
    return LocalStorageBackend(base_path=str(tmp_path))


def test_save_and_get_round_trip(storage):
    data = b"hello storage"
    key = storage.save("ws1/doc1/original.pdf", data)
    assert storage.get(key) == data


def test_save_returns_storage_key(storage):
    key = storage.save("ws1/doc1/original.pdf", b"data")
    assert key == "ws1/doc1/original.pdf"


def test_exists_returns_false_for_missing_key(storage):
    assert storage.exists("ws1/nope/original.pdf") is False


def test_exists_returns_true_after_save(storage):
    storage.save("ws1/doc2/original.pdf", b"abc")
    assert storage.exists("ws1/doc2/original.pdf") is True


def test_delete_removes_file(storage):
    storage.save("ws1/doc3/original.pdf", b"xyz")
    storage.delete("ws1/doc3/original.pdf")
    assert storage.exists("ws1/doc3/original.pdf") is False


def test_write_once_raises_on_duplicate_path(storage):
    storage.save("ws1/doc4/original.pdf", b"first")
    with pytest.raises(FileExistsError):
        storage.save("ws1/doc4/original.pdf", b"second")


def test_write_once_does_not_overwrite_on_error(storage):
    storage.save("ws1/doc5/original.pdf", b"original")
    try:
        storage.save("ws1/doc5/original.pdf", b"overwrite")
    except FileExistsError:
        pass
    assert storage.get("ws1/doc5/original.pdf") == b"original"


def test_get_raises_for_missing_key(storage):
    with pytest.raises(FileNotFoundError):
        storage.get("ws1/nope/original.pdf")


def test_creates_nested_directories(storage, tmp_path):
    storage.save("deep/a/b/c/file.pdf", b"nested")
    assert os.path.exists(os.path.join(str(tmp_path), "deep/a/b/c/file.pdf"))


def test_factory_returns_local_backend(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    from app.storage import get_storage_backend
    backend = get_storage_backend()
    assert isinstance(backend, LocalStorageBackend)
