import pytest
from app.security import (
    generate_dek,
    encrypt_dek,
    decrypt_dek,
    generate_recovery_key,
    normalize_recovery_key,
    make_unlock_token,
    extract_dek_from_token,
    encrypt_for_draft,
    decrypt_from_draft,
)


def test_generate_dek_is_32_bytes():
    dek = generate_dek()
    assert len(dek) == 32
    assert isinstance(dek, bytes)


def test_generate_dek_is_random():
    assert generate_dek() != generate_dek()


def test_encrypt_decrypt_dek_roundtrip():
    dek = generate_dek()
    encrypted = encrypt_dek(dek, "my-passphrase")
    assert decrypt_dek(encrypted, "my-passphrase") == dek


def test_decrypt_dek_wrong_passphrase_raises():
    dek = generate_dek()
    encrypted = encrypt_dek(dek, "correct")
    with pytest.raises(Exception):
        decrypt_dek(encrypted, "wrong")


def test_recovery_key_format():
    key = generate_recovery_key()
    parts = key.split(" / ")
    assert len(parts) == 2
    for part in parts:
        segments = part.split("-")
        assert len(segments) == 4
        for seg in segments:
            assert len(seg) == 4
            assert all(c in "0123456789ABCDEF" for c in seg)


def test_normalize_recovery_key():
    key = "ABCD-EF01-2345-6789 / ABCD-EF01-2345-6789"
    assert normalize_recovery_key(key) == "ABCDEF0123456789ABCDEF0123456789"


def test_encrypt_decrypt_dek_with_recovery_key():
    dek = generate_dek()
    rk = generate_recovery_key()
    normalized = normalize_recovery_key(rk)
    encrypted = encrypt_dek(dek, normalized)
    assert decrypt_dek(encrypted, normalized) == dek


def test_unlock_token_roundtrip():
    dek = generate_dek()
    token = make_unlock_token(dek, "server-secret-key")
    assert extract_dek_from_token(token, "server-secret-key") == dek


def test_unlock_token_wrong_secret_raises():
    dek = generate_dek()
    token = make_unlock_token(dek, "correct-secret")
    with pytest.raises(Exception):
        extract_dek_from_token(token, "wrong-secret")


def test_draft_encrypt_decrypt_roundtrip():
    dek = generate_dek()
    content = {"field": "value", "amount": 123}
    encrypted = encrypt_for_draft(content, dek)
    assert decrypt_from_draft(encrypted, dek) == content


def test_draft_decrypt_wrong_dek_raises():
    dek = generate_dek()
    encrypted = encrypt_for_draft({"x": 1}, dek)
    with pytest.raises(Exception):
        decrypt_from_draft(encrypted, generate_dek())
