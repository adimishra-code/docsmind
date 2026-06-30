"""Cryptographic primitives: password hashing and JWT issuance/verification.

Design choices worth noting for reviewers:

* **Access vs refresh tokens** carry a ``type`` claim so a refresh token can
  never be replayed as an access token (and vice-versa).
* Every token has a ``jti`` (unique id) so individual refresh tokens can be
  revoked/rotated via a denylist in Redis (implemented in the auth service).
* ``sub`` is a string per the JWT spec; we store the user's UUID there.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
import bcrypt

from app.core.config import settings
from app.core.exceptions import AuthenticationError

TokenType = Literal["access", "refresh"]


# --------------------------------------------------------------------------- #
# Passwords
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------- #
# JSON Web Tokens
# --------------------------------------------------------------------------- #
def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> tuple[str, str]:
    """Return ``(encoded_jwt, jti)``."""
    now = datetime.now(UTC)
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
    }
    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded, jti


def create_access_token(subject: str | uuid.UUID) -> str:
    token, _ = _create_token(
        str(subject), "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return token


def create_refresh_token(subject: str | uuid.UUID) -> tuple[str, str]:
    """Return ``(token, jti)`` — the jti is persisted so the token can be rotated."""
    return _create_token(
        str(subject), "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )


def decode_token(token: str, *, expected_type: TokenType) -> dict[str, Any]:
    """Decode and validate a JWT, enforcing signature, expiry, and token type.

    Raises :class:`AuthenticationError` on any failure so callers never have to
    reason about the underlying ``jwt`` exception zoo.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "type", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired.", code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid authentication token.") from exc

    if payload.get("type") != expected_type:
        raise AuthenticationError(
            f"Expected a {expected_type} token.", code="wrong_token_type"
        )
    return payload
