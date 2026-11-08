import base64
import hashlib
import hmac
import json
import os
import time

import jwt
from cryptography.fernet import Fernet
from fastapi import HTTPException, status

from app.config import settings

ALGORITHM = "HS256"
PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        _algo, iterations, salt_b64, digest_b64 = encoded.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), base64.b64decode(salt_b64), int(iterations)
        )
        return hmac.compare_digest(digest, base64.b64decode(digest_b64))
    except Exception:
        return False


def create_access_token(subject: str, role: str) -> str:
    now = int(time.time())
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + settings.access_token_expire_minutes * 60,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


_fernet: Fernet | None = None


def _load_vault_key() -> bytes:
    key = settings.vault_key
    if not key:
        path = ".vault_key"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                key = handle.read().strip()
        else:
            key = Fernet.generate_key().decode("ascii")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(key)
            os.chmod(path, 0o600)
    return key.encode("ascii") if isinstance(key, str) else key


def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_load_vault_key())
    return _fernet


def encrypt_secret(data: dict) -> str:
    return get_fernet().encrypt(json.dumps(data).encode("utf-8")).decode("ascii")


def decrypt_secret(blob: str) -> dict:
    return json.loads(get_fernet().decrypt(blob.encode("ascii")).decode("utf-8"))
