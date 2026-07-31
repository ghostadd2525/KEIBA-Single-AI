# -*- coding: utf-8 -*-
"""User Service authentication — stub token compatible with BFF."""
from __future__ import annotations

import base64
import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

from .repository import SessionRepository, UserRepository


@dataclass
class AuthContext:
    user_id: str
    session_id: str | None = None
    purpose: str = "access"


def _b64url_decode(raw: str) -> bytes:
    pad = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + pad)


def parse_stub_token(token: str, *, purpose: str = "access") -> dict[str, Any] | None:
    """Parse BFF stub token: stub.<base64url(payload)>.<exp>"""
    if not token or not token.startswith("stub."):
        return None
    parts = token.split(".")
    if len(parts) < 3:
        return None
    try:
        payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
        sub = str(payload.get("sub") or "")
        if not sub:
            return None
        exp = int(payload.get("exp") or parts[-1])
        if exp < int(time.time()):
            return None
        tok_purpose = str(payload.get("purpose") or "access")
        if tok_purpose != purpose:
            return None
        return {"user_id": sub, "exp": exp, "purpose": tok_purpose}
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def make_access_token(user_id: str, expires_in: int = 86400) -> str:
    exp = int(time.time()) + int(expires_in)
    payload = {"sub": user_id, "exp": exp, "purpose": "access"}
    encoded = (
        base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    return f"stub.{encoded}.{exp}"


class UserAuth:
    def __init__(self) -> None:
        self.users = UserRepository()
        self.sessions = SessionRepository()

    def authenticate(self, authorization: str | None) -> AuthContext | None:
        if not authorization:
            return None
        token = authorization
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        if not token:
            return None

        parsed = parse_stub_token(token, purpose="access")
        if not parsed:
            return None
        user_id = parsed["user_id"]
        user = self.users.get_by_id(user_id)
        # BFF stub ログイン済みで AI SQLite に未ミラーのユーザーは最小 UPSERT（V8.9.1）
        if not user:
            try:
                user = self.users.ensure_stub_mirror(
                    user_id,
                    display_name=user_id,
                    role="USER",
                )
            except Exception:
                user = None
            if not user:
                # Mirror failed — still allow read paths; progress.ensure is FK-safe.
                return AuthContext(user_id=user_id, session_id=None)
        if user.get("status") != "active":
            return None

        sess = self.sessions.get_by_token_hash(token_hash(token))
        session_id = sess["session_id"] if sess else None
        if sess:
            self.sessions.touch(session_id)
        return AuthContext(user_id=user_id, session_id=session_id)

    def login(self, login_id: str, password: str) -> dict[str, Any] | None:
        from .password import verify_password

        user = self.users.get_by_login_id(login_id.strip())
        if not user or user.get("status") != "active":
            return None
        if not verify_password(password, user.get("password_hash") or ""):
            return None
        token = make_access_token(user["user_id"])
        session_id = str(uuid.uuid4())
        self.sessions.create(
            session_id=session_id,
            user_id=user["user_id"],
            token_hash=token_hash(token),
            expires_in=86400,
        )
        return {"access_token": token, "user_id": user["user_id"], "session_id": session_id}

    def logout(self, authorization: str | None) -> bool:
        ctx = self.authenticate(authorization)
        if not ctx:
            return False
        if ctx.session_id:
            self.sessions.revoke(ctx.session_id)
        return True
