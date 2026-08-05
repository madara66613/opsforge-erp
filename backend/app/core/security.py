from __future__ import annotations

import hashlib
import secrets

from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()
_dummy_password_hash = password_hasher.hash("not-a-real-opsforge-password")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    candidate_hash = password_hash or _dummy_password_hash
    verified = password_hasher.verify(password, candidate_hash)
    return verified and password_hash is not None


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
