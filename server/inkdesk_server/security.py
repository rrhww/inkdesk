from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

import bcrypt as bcrypt_lib
from fastapi import Cookie, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from inkdesk_server.core.config import Settings, get_settings
from inkdesk_server.db import get_db
from inkdesk_server.models import User, Workspace


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class InvalidCredentialsError(ApiError):
    def __init__(self):
        super().__init__(401, "INVALID_CREDENTIALS", "Invalid email or password.")


class ResourceNotFoundError(ApiError):
    def __init__(self, message: str):
        super().__init__(404, "NOT_FOUND", message)


@dataclass(frozen=True)
class VerifiedOwnerSession:
    user_id: str
    username: str


class OwnerSessionService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.signing_key = settings.auth_secret.encode("utf-8")

    def create_session_token(self, user: User) -> str:
        expires_at = int((datetime.now(UTC) + self.settings.auth_session_duration).timestamp() * 1000)
        session_version = int(user.updated_at.timestamp() * 1000)
        payload = f"{user.id}:{expires_at}:{session_version}"
        signature = self._encode(self._sign(payload))
        return f"{self._encode(payload.encode('utf-8'))}.{signature}"

    def verify_session_token(self, token: str, db: Session) -> VerifiedOwnerSession | None:
        if self.settings.auth_allow_legacy_owner_cookie and token == "owner":
            user = db.scalar(select(User).where(User.username == "owner"))
            if user:
                return VerifiedOwnerSession(user_id=user.id, username=user.username)

        parts = token.split(".")
        if len(parts) != 2:
            return None
        try:
            payload_bytes = self._decode(parts[0])
            provided_signature = self._decode(parts[1])
        except Exception:
            return None

        expected_signature = self._sign(payload_bytes.decode("utf-8"))
        if not hmac.compare_digest(expected_signature, provided_signature):
            return None

        payload = payload_bytes.decode("utf-8").split(":")
        if len(payload) != 3:
            return None
        try:
            expires_at = int(payload[1])
            session_version = int(payload[2])
        except ValueError:
            return None
        if int(datetime.now(UTC).timestamp() * 1000) > expires_at:
            return None
        user = db.get(User, payload[0])
        if not user or user.status.upper() != "ACTIVE":
            return None
        if int(user.updated_at.timestamp() * 1000) != session_version:
            return None
        return VerifiedOwnerSession(user_id=user.id, username=user.username)

    def invalidate_session(self, username: str, db: Session) -> None:
        user = db.scalar(select(User).where(User.username == username))
        if user:
            user.updated_at = datetime.now(UTC)
            db.add(user)
            db.commit()

    def _sign(self, payload: str) -> bytes:
        return hmac.new(self.signing_key, payload.encode("utf-8"), hashlib.sha256).digest()

    def _encode(self, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")

    def _decode(self, value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)


def verify_password(raw_password: str, password_hash: str) -> bool:
    return bcrypt_lib.checkpw(raw_password.encode("utf-8"), password_hash.encode("utf-8"))


def get_session_service(settings: Settings = Depends(get_settings)) -> OwnerSessionService:
    return OwnerSessionService(settings)


def require_owner(
    db: Annotated[Session, Depends(get_db)],
    session_service: Annotated[OwnerSessionService, Depends(get_session_service)],
    owner_session: Annotated[str | None, Cookie(alias="inkdesk_owner_session")] = None,
) -> VerifiedOwnerSession:
    if not owner_session:
        raise ApiError(401, "UNAUTHORIZED", "Owner authentication required.")
    verified = session_service.verify_session_token(owner_session, db)
    if not verified:
        raise ApiError(401, "UNAUTHORIZED", "Owner authentication required.")
    return verified


def get_current_workspace(db: Session, username: str) -> Workspace:
    user = db.scalar(select(User).where(User.username == username))
    if not user:
        raise ResourceNotFoundError(f"Owner profile not found for username: {username}")
    workspace = db.scalar(select(Workspace).where(Workspace.owner_user_id == user.id))
    if not workspace:
        raise ResourceNotFoundError(f"Workspace not found for owner: {user.id}")
    return workspace
