# -*- coding: utf-8 -*-
"""User Service — auth, profile, favorites, history, chat (AI-independent)."""
from __future__ import annotations

from typing import Any

from .auth import UserAuth
from .password import hash_password, is_strong_enough_password, is_valid_login_id
from .repository import (
    ChatRepository,
    FavoriteRepository,
    NotificationRepository,
    PredictionHistoryRepository,
    ProfileRepository,
    SubscriptionRepository,
    UserRepository,
)


class UserService:
    SCHEMA = "expect-user/1.0"

    def __init__(self) -> None:
        self.auth = UserAuth()
        self.users = UserRepository()
        self.profiles = ProfileRepository()
        self.favorites = FavoriteRepository()
        self.history = PredictionHistoryRepository()
        self.chat = ChatRepository()
        self.notifications = NotificationRepository()
        self.subscriptions = SubscriptionRepository()

    def setup_user(
        self,
        *,
        login_id: str,
        password: str,
        display_name: str | None = None,
        invite_id: str | None = None,
        terms_version: str | None = None,
    ) -> dict[str, Any]:
        if not is_valid_login_id(login_id):
            raise ValueError("invalid login_id")
        if not is_strong_enough_password(password):
            raise ValueError("password too weak")
        if self.users.get_by_login_id(login_id):
            raise ValueError("login_id taken")
        user = self.users.create(
            login_id=login_id.strip(),
            password_hash=hash_password(password),
            invite_id=invite_id,
            terms_version=terms_version,
        )
        self.profiles.upsert(
            user["user_id"],
            {"display_name": display_name or login_id, "locale": "ja"},
        )
        login = self.auth.login(login_id, password)
        return {
            "schema_version": self.SCHEMA,
            "user": self.get_me(user["user_id"]),
            "access_token": login["access_token"] if login else None,
        }

    def login(self, login_id: str, password: str) -> dict[str, Any]:
        result = self.auth.login(login_id, password)
        if not result:
            raise PermissionError("invalid credentials")
        profile = self.profiles.get(result["user_id"])
        return {
            "schema_version": self.SCHEMA,
            "access_token": result["access_token"],
            "token_type": "bearer",
            "expires_in": 86400,
            "user": {
                "id": result["user_id"],
                "display_name": (profile or {}).get("display_name") or login_id,
            },
            "favorites": self._favorites_payload(result["user_id"]),
        }

    def logout(self, authorization: str | None) -> dict[str, Any]:
        self.auth.logout(authorization)
        return {"schema_version": self.SCHEMA, "logged_out": True}

    def get_me(self, user_id: str) -> dict[str, Any]:
        user = self.users.get_by_id(user_id)
        if not user:
            raise LookupError("user not found")
        profile = self.profiles.get(user_id) or {}
        sub = self.subscriptions.get_active(user_id)
        return {
            "schema_version": self.SCHEMA,
            "user_id": user["user_id"],
            "login_id": user["login_id"],
            "status": user["status"],
            "terms_version": user.get("terms_version"),
            "terms_accepted_at": user.get("terms_accepted_at"),
            "created_at": user.get("created_at"),
            "profile": {
                "display_name": profile.get("display_name"),
                "avatar_url": profile.get("avatar_url"),
                "locale": profile.get("locale") or "ja",
                "preferences": profile.get("preferences") or {},
            },
            "subscription": (
                {
                    "plan_id": sub.get("plan_id"),
                    "status": sub.get("status"),
                    "started_at": sub.get("started_at"),
                    "expires_at": sub.get("expires_at"),
                }
                if sub
                else None
            ),
        }

    def patch_me(self, user_id: str, body: dict[str, Any]) -> dict[str, Any]:
        profile_fields: dict[str, Any] = {}
        if "display_name" in body:
            profile_fields["display_name"] = body["display_name"]
        if "avatar_url" in body:
            profile_fields["avatar_url"] = body["avatar_url"]
        if "locale" in body:
            profile_fields["locale"] = body["locale"]
        if "preferences" in body:
            profile_fields["preferences"] = body["preferences"]
        if profile_fields:
            self.profiles.upsert(user_id, profile_fields)
        user_fields: dict[str, Any] = {}
        if "terms_version" in body:
            user_fields["terms_version"] = body["terms_version"]
            from .repository import _now

            user_fields["terms_accepted_at"] = _now()
        if user_fields:
            self.users.update(user_id, user_fields)
        return self.get_me(user_id)

    def list_favorites(self, user_id: str) -> dict[str, Any]:
        return self._favorites_payload(user_id)

    def add_favorite(self, user_id: str, body: dict[str, Any]) -> dict[str, Any]:
        if body.get("remove") and body.get("race_id"):
            items = self.favorites.remove(user_id, str(body["race_id"]))
        else:
            items = self.favorites.upsert(user_id, body)
        return {
            "schema_version": self.SCHEMA,
            "favorites": items,
            "limit": FavoriteRepository.MAX_FAVORITES,
        }

    def list_history(self, user_id: str, *, limit: int = 50) -> dict[str, Any]:
        items = self.history.list_for_user(user_id, limit=limit)
        return {"schema_version": self.SCHEMA, "items": items, "count": len(items)}

    def record_prediction_view(
        self,
        user_id: str,
        *,
        race_id: str,
        engine_source: str | None = None,
        feature_source: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        self.history.record(
            user_id=user_id,
            race_id=race_id,
            engine_source=engine_source,
            feature_source=feature_source,
            meta=meta,
        )

    def list_chat(
        self,
        user_id: str,
        *,
        session_id: str | None = None,
        limit: int = 30,
    ) -> dict[str, Any]:
        if session_id:
            messages = self.chat.list_messages(session_id)
            return {
                "schema_version": self.SCHEMA,
                "session_id": session_id,
                "messages": messages,
            }
        sessions = self.chat.list_sessions(user_id, limit=limit)
        return {"schema_version": self.SCHEMA, "sessions": sessions, "count": len(sessions)}

    def persist_chat_turn(
        self,
        *,
        user_id: str | None,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        race_id: str | None = None,
        intent: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        if not user_id:
            return
        title = (user_message or "")[:40] or "Chat"
        self.chat.ensure_session(
            session_id=session_id,
            user_id=user_id,
            race_id=race_id,
            title=title,
        )
        self.chat.append_message(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=user_message,
            race_id=race_id,
        )
        self.chat.append_message(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=assistant_reply,
            intent=intent,
            race_id=race_id,
            meta=meta,
        )

    def admin_summary(self) -> dict[str, Any]:
        users = self.users.list_users(limit=200)
        return {
            "schema_version": self.SCHEMA,
            "user_count": len(users),
            "users": users,
        }

    def _favorites_payload(self, user_id: str) -> dict[str, Any]:
        items = self.favorites.list_for_user(user_id)
        return {
            "schema_version": self.SCHEMA,
            "favorites": items,
            "limit": FavoriteRepository.MAX_FAVORITES,
        }


_service = UserService()


def get_service() -> UserService:
    return _service
