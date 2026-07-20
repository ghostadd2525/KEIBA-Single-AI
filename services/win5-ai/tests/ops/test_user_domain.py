# -*- coding: utf-8 -*-
"""User Domain API tests — Phase U-1."""
from __future__ import annotations

import unittest

from tests.ops.helpers import http_json, isolated_env, running_server


class UserDomainRepositoryTest(unittest.TestCase):
    def test_create_user_profile_favorites(self):
        with isolated_env():
            from app.user.service import UserService

            svc = UserService()
            out = svc.setup_user(
                login_id="testuser01",
                password="password123",
                display_name="Test User",
                terms_version="2026-07-20",
            )
            self.assertTrue(out.get("access_token"))
            user = out["user"]
            uid = user["user_id"]

            fav = svc.add_favorite(
                uid,
                {
                    "race_id": "20260719_hanshin_11",
                    "place": "阪神 11R",
                    "name": "テストレース",
                },
            )
            self.assertEqual(len(fav["favorites"]), 1)

            patched = svc.patch_me(uid, {"display_name": "Updated Name"})
            self.assertEqual(patched["profile"]["display_name"], "Updated Name")

            svc.record_prediction_view(
                uid,
                race_id="20260719_hanshin_11",
                engine_source="real_ai",
                feature_source="db",
            )
            hist = svc.list_history(uid)
            self.assertEqual(hist["count"], 1)

            svc.persist_chat_turn(
                user_id=uid,
                session_id="chat-test-1",
                user_message="予想して",
                assistant_reply="本命は7番です",
                race_id="20260719_hanshin_11",
                intent="predict_race",
            )
            chat = svc.list_chat(uid)
            self.assertEqual(chat["count"], 1)
            msgs = svc.list_chat(uid, session_id="chat-test-1")
            self.assertEqual(len(msgs["messages"]), 2)


class UserDomainHttpTest(unittest.TestCase):
    def test_users_me_and_favorites_http(self):
        with running_server() as base:
            from app.user.service import UserService

            svc = UserService()
            created = svc.setup_user(
                login_id="httptest01",
                password="password123",
                display_name="HTTP User",
            )
            token = created["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            status, body = http_json(f"{base}/v1/users/me", headers=headers)
            self.assertEqual(status, 200)
            self.assertTrue(body.get("ok"))
            self.assertEqual(body["data"]["profile"]["display_name"], "HTTP User")

            status, body = http_json(
                f"{base}/v1/favorites",
                method="POST",
                body={"race_id": "20260719_hanshin_11", "place": "阪神 11R"},
                headers=headers,
            )
            self.assertEqual(status, 200)
            self.assertEqual(len(body["data"]["favorites"]), 1)

            status, body = http_json(f"{base}/v1/favorites", headers=headers)
            self.assertEqual(status, 200)
            self.assertEqual(len(body["data"]["favorites"]), 1)

            status, body = http_json(
                f"{base}/v1/users/me",
                method="PATCH",
                body={"display_name": "Patched"},
                headers=headers,
            )
            self.assertEqual(status, 200)
            self.assertEqual(body["data"]["profile"]["display_name"], "Patched")

            status, body = http_json(f"{base}/v1/history", headers=headers)
            self.assertEqual(status, 200)
            self.assertIn("items", body["data"])

            status, body = http_json(f"{base}/v1/chat", headers=headers)
            self.assertEqual(status, 200)
            self.assertIn("sessions", body["data"])

    def test_unauthorized_without_token(self):
        with running_server() as base:
            status, _ = http_json(f"{base}/v1/users/me")
            self.assertEqual(status, 401)


if __name__ == "__main__":
    unittest.main()
