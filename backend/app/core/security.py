import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import HTTPException

from app.core.config import get_settings

_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
_dummy_hash: str | None = None


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def dummy_password_hash() -> str:
    """Spend the same hash time when the username does not exist."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password("gd-os-dummy-password")
    return _dummy_hash


def require_jwt_secret() -> str:
    secret = get_settings().jwt_secret
    if secret == "change-me" or len(secret) < 16:
        raise HTTPException(status_code=503, detail="JWT_SECRET is not configured")
    return secret


def create_access_token(user_id: uuid.UUID, *, kind: str) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.jwt_ttl_hours * 3600
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    token = jwt.encode(
        {"sub": str(user_id), "kind": kind, "exp": expires_at},
        require_jwt_secret(),
        algorithm="HS256",
    )
    return token, expires_in


def decode_subject(token: str, *, expected_kind: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, require_jwt_secret(), algorithms=["HS256"])
        if payload.get("kind") != expected_kind:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return uuid.UUID(payload["sub"])
    except HTTPException:
        raise
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
