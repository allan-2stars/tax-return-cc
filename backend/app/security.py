import base64
import hashlib
import json
import os
import secrets

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_PBKDF2_ITERATIONS = 480_000


def generate_dek() -> bytes:
    return os.urandom(32)


def _pbkdf2_fernet(passphrase: str, salt: bytes) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
    return Fernet(key)


def encrypt_dek(dek: bytes, passphrase: str) -> str:
    salt = os.urandom(16)
    token = _pbkdf2_fernet(passphrase, salt).encrypt(dek)
    return base64.urlsafe_b64encode(salt + token).decode()


def decrypt_dek(encrypted_str: str, passphrase: str) -> bytes:
    data = base64.urlsafe_b64decode(encrypted_str.encode())
    salt, token = data[:16], data[16:]
    return _pbkdf2_fernet(passphrase, salt).decrypt(token)


def generate_recovery_key() -> str:
    raw = secrets.token_hex(16).upper()
    segs = [raw[i : i + 4] for i in range(0, 32, 4)]
    return f"{'-'.join(segs[:4])} / {'-'.join(segs[4:])}"


def normalize_recovery_key(key: str) -> str:
    return "".join(c for c in key.upper() if c in "0123456789ABCDEF")


def _server_fernet(secret: str) -> Fernet:
    key = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def make_unlock_token(dek: bytes, secret: str) -> str:
    return _server_fernet(secret).encrypt(dek).decode()


def extract_dek_from_token(token: str, secret: str) -> bytes:
    return _server_fernet(secret).decrypt(token.encode())


def encrypt_for_draft(content: dict, dek: bytes) -> str:
    f = Fernet(base64.urlsafe_b64encode(dek))
    return f.encrypt(json.dumps(content).encode()).decode()


def decrypt_from_draft(encrypted: str, dek: bytes) -> dict:
    f = Fernet(base64.urlsafe_b64encode(dek))
    return json.loads(f.decrypt(encrypted.encode()).decode())
