"""Security utilities: password hashing and JWT."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
import bcrypt

from src.auth.schemas import TokenData
from src.utils.config import load_config


def get_settings() -> dict:
    cfg = load_config()
    return cfg.get("auth", {})


def hash_password(password: str) -> str:
    """Hash a password with bcrypt. Returns the encoded hash string."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    secret_key = settings.get("secret_key", "corvus-dev-secret-change-in-production")
    algorithm = settings.get("algorithm", "HS256")
    expire_minutes = int(settings.get("access_token_expire_minutes", 30))

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def decode_token(token: str) -> TokenData | None:
    settings = get_settings()
    secret_key = settings.get("secret_key", "corvus-dev-secret-change-in-production")
    algorithm = settings.get("algorithm", "HS256")
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        user_id: int | None = payload.get("sub")
        role: str | None = payload.get("role")
        if user_id is None:
            return None
        return TokenData(user_id=user_id, role=role)
    except JWTError:
        return None
