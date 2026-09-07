# -*- coding: utf-8 -*-
"""User Service — auth, profile, favorites, history, chat (AI-independent)."""
from __future__ import annotations

import json
from typing import Any

from .auth import UserAuth
from .password import hash_password, is_strong_enough_password, is_valid_login_id
from .progress import points_from_profit, progress_payload
from .race_result_settle import (
    build_purchase_snapshot,
    normalize_strategy_snapshot,
    settle_strategy,
)
from .repository import (
    AppSettingsRepository,
    ChatRepository,
    FavoriteRepository,
    NotificationRepository,
    PredictionHistoryRepository,
    ProfileRepository,
    PurchaseAuditRepository,
    SubscriptionRepository,
    UserProgressRepository,
    UserRaceResultRepository,
    UserRepository,
)


def _week_of_month(race_date: str | None) -> int:
    """1-based calendar week bucket within month (day 1-7 → 1, ...)."""
    if not race_date or len(race_date) < 10:
        return 1
    try:
        day = int(race_date[8:10])
    except ValueError:
        return 1
    return min(5, max(1, ((day - 1) // 7) + 1))


def _load_official_result(race_id: str) -> dict[str, Any] | None:
    """Read race_results row and normalize finish_order / payouts (no PE changes)."""
    from ..data.db import connect

    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM race_results WHERE race_id=?",
            (race_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        raw = d.get("result_json") or "{}"
        try:
            result_json = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except Exception:
            result_json = {}
        finish_order = result_json.get("finish_order") or result_json.get("chakujun") or []
        if not finish_order and result_json.get("by_number"):
            # by_number: { "5": 1, "3": 2, ... } place → sort by place
            try:
                pairs = []
                for hn, place in (result_json.get("by_number") or {}).items():
                    pairs.append((int(place), int(hn)))
                pairs.sort()
                finish_order = [hn for _, hn in pairs]
            except (TypeError, ValueError):
                pass
        if not finish_order and d.get("winner_horse_number") is not None:
            try:
                finish_order = [int(d["winner_horse_number"])]
            except (TypeError, ValueError):
                finish_order = []
        payouts = result_json.get("payouts") or result_json.get("haraimodoshi") or {}
        return {
            "race_id": d.get("race_id"),
            "race_date": d.get("race_date"),
            "venue": d.get("venue"),
            "winner_horse_number": d.get("winner_horse_number"),
            "field_size": d.get("field_size"),
            "finish_order": finish_order,
            "payouts": payouts,
            "result_json": result_json,
            "source": d.get("source"),
            "finalized_at": d.get("finalized_at"),
        }
    finally:
        conn.close()


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
        self.race_results = UserRaceResultRepository()
        self.progress = UserProgressRepository()
        self.audit = PurchaseAuditRepository()
        self.settings = AppSettingsRepository()

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
            "progress": progress_payload(self.progress.ensure(user_id)),
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

    def save_race_strategy_snapshot(self, user_id: str, body: dict[str, Any]) -> dict[str, Any]:
        """Legacy draft save — prefer register_purchase for ledger."""
        race_id = str(body.get("race_id") or "").strip()
        if not race_id:
            raise ValueError("race_id required")
        snap = normalize_strategy_snapshot(body.get("strategy_snapshot") or body)
        purchase = int(snap.get("purchase_amount") or body.get("purchase_amount") or 0)
        row = self.race_results.upsert_snapshot(
            user_id,
            race_id=race_id,
            race_date=(body.get("race_date") or None),
            race_label=(body.get("race_label") or None),
            prediction_version=(
                body.get("prediction_version")
                or snap.get("prediction_version")
            ),
            strategy_snapshot=snap,
            purchase_amount=purchase,
            purchase_registered=0,
        )
        return {"schema_version": self.SCHEMA, "item": row}

    def register_purchase(
        self,
        user_id: str,
        body: dict[str, Any],
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Explicit purchase registration from strategy UI (anti-fraud checks)."""
        race_id = str(body.get("race_id") or "").strip()
        if not race_id:
            raise ValueError("race_id required")

        unit_stake = int(body.get("unit_stake") or body.get("purchase_unit") or 0)
        if unit_stake < 100 or unit_stake % 100 != 0:
            raise ValueError("unit_stake must be a multiple of 100 (min 100)")

        max_amount = int(self.settings.get("max_purchase_amount_per_race", 50000) or 50000)
        bet_types = body.get("bet_types") or body.get("selected_bet_types") or []
        if not isinstance(bet_types, list) or not bet_types:
            raise ValueError("bet_types required")

        axis = body.get("axis") or (body.get("strategy_snapshot") or {}).get("axis")
        rivals = body.get("rivals") or (body.get("strategy_snapshot") or {}).get("rivals")
        snap = build_purchase_snapshot(
            axis=axis if isinstance(axis, dict) else {},
            rivals=rivals if isinstance(rivals, list) else [],
            bet_types=[str(t) for t in bet_types],
            unit_stake=unit_stake,
            prediction_version=body.get("prediction_version"),
        )
        purchase = int(snap.get("purchase_amount") or 0)
        theoretical = int(snap.get("theoretical_amount") or purchase)
        if purchase <= 0:
            raise ValueError("no tickets expanded from selected bet_types")
        if purchase > max_amount:
            raise ValueError(f"purchase_amount exceeds max ({max_amount})")

        divergence_ratio = float(self.settings.get("purchase_amount_divergence_ratio", 3) or 3)
        override_amount = body.get("override_purchase_amount")
        if override_amount is not None:
            try:
                override_amount = int(override_amount)
            except (TypeError, ValueError):
                raise ValueError("override_purchase_amount invalid") from None
            if override_amount > max_amount:
                raise ValueError(f"purchase_amount exceeds max ({max_amount})")
            # Scale ticket stakes proportionally to override total
            if purchase > 0 and override_amount != purchase:
                ratio = override_amount / purchase
                for spec in (snap.get("bets") or {}).values():
                    for t in spec.get("tickets") or []:
                        t["stake"] = max(100, int(round(int(t.get("stake") or 0) * ratio / 100) * 100))
                    spec["amount"] = sum(int(t.get("stake") or 0) for t in (spec.get("tickets") or []))
                snap["purchase_amount"] = sum(
                    int(s.get("amount") or 0) for s in (snap.get("bets") or {}).values()
                )
                purchase = int(snap["purchase_amount"])

        needs_confirm = False
        if theoretical > 0 and purchase > theoretical * divergence_ratio:
            needs_confirm = True
            if not body.get("confirm_divergence"):
                return {
                    "schema_version": self.SCHEMA,
                    "needs_confirmation": True,
                    "message": (
                        f"AI買い目 {snap.get('ticket_points')}点 / "
                        f"理論額 ¥{theoretical:,} に対し登録金額 ¥{purchase:,} です。"
                        "この購入金額で登録しますか？"
                    ),
                    "theoretical_amount": theoretical,
                    "ticket_points": snap.get("ticket_points"),
                    "purchase_amount": purchase,
                    "unit_stake": unit_stake,
                }

        row = self.race_results.upsert_snapshot(
            user_id,
            race_id=race_id,
            race_date=(body.get("race_date") or None),
            race_label=(body.get("race_label") or None),
            prediction_version=body.get("prediction_version") or snap.get("prediction_version"),
            strategy_snapshot=snap,
            purchase_amount=purchase,
            purchase_registered=1,
            unit_stake=unit_stake,
            selected_bet_types=list(snap.get("selected_bet_types") or bet_types),
            client_meta={
                "confirm_divergence": bool(body.get("confirm_divergence")),
                "needs_confirm_flag": needs_confirm,
                "theoretical_amount": theoretical,
            },
        )
        self.audit.append(
            {
                "user_id": user_id,
                "race_id": race_id,
                "event_type": "purchase",
                "purchase_amount": purchase,
                "payout_amount": 0,
                "profit": 0,
                "points_awarded": 0,
                "ai_strategy": snap,
                "user_bets": snap.get("bets"),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "meta": {
                    "unit_stake": unit_stake,
                    "theoretical_amount": theoretical,
                    "confirm_divergence": bool(body.get("confirm_divergence")),
                },
            }
        )
        return {
            "schema_version": self.SCHEMA,
            "item": row,
            "progress": progress_payload(self.progress.ensure(user_id)),
        }

    def get_progress(self, user_id: str) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA,
            "progress": progress_payload(self.progress.ensure(user_id)),
            "settings": {
                "max_purchase_amount_per_race": int(
                    self.settings.get("max_purchase_amount_per_race", 50000) or 50000
                ),
            },
        }

    def get_race_result(self, user_id: str, race_id: str) -> dict[str, Any]:
        row = self.race_results.get(user_id, race_id)
        official = _load_official_result(race_id)
        # 全ユーザー共通: Prediction Bundle + race_results から AI 理論を算出
        # （ユーザー購入登録の有無に依存しない）
        ai_theory = None
        try:
            from ..challenge.service import settle_ai_theory_for_race

            ai_theory = settle_ai_theory_for_race(race_id)
        except Exception:
            ai_theory = None
        # フォールバック: Bundle が無いがユーザー snapshot がある場合のみ
        if (
            not ai_theory
            and row
            and row.get("strategy_snapshot")
            and official
            and official.get("finish_order")
        ):
            try:
                settled = settle_strategy(
                    row.get("strategy_snapshot") or {},
                    finish_order=official.get("finish_order") or [],
                    payouts=official.get("payouts") or {},
                )
                ai_theory = {
                    "race_id": race_id,
                    "race_date": official.get("race_date") or row.get("race_date"),
                    "source": "user_strategy_snapshot",
                    "purchase_amount": settled.get("purchase_amount"),
                    "payout_amount": settled.get("payout_amount"),
                    "profit": settled.get("profit"),
                    "hit": bool(settled.get("hit")),
                    "settled": bool(settled.get("settled")),
                    "strategy_snapshot": settled.get("strategy_snapshot")
                    or row.get("strategy_snapshot"),
                    "bet_results": settled.get("bet_results") or {},
                    "marks_result": settled.get("marks_result"),
                    "finish_order": settled.get("finish_order")
                    or official.get("finish_order")
                    or [],
                }
            except Exception:
                ai_theory = None

        registered = bool(row and row.get("purchase_registered"))
        return {
            "schema_version": self.SCHEMA,
            "item": row,
            "official": official,
            "ai_theory": ai_theory,
            # 購入ユーザー向けカード用（未登録時は null）
            "user_result": row if registered else None,
        }

    def settle_race_result(
        self,
        user_id: str,
        race_id: str,
        body: dict[str, Any] | None = None,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        body = body or {}
        row = self.race_results.get(user_id, race_id)
        if not row:
            raise LookupError("purchase not found — register from 買い目戦略 first")
        if not row.get("purchase_registered") and not body.get("allow_unregistered"):
            return {
                "schema_version": self.SCHEMA,
                "item": row,
                "pending": True,
                "reason": "purchase not registered",
            }
        if row.get("settled") and not body.get("force"):
            return {
                "schema_version": self.SCHEMA,
                "item": row,
                "already_settled": True,
                "progress": progress_payload(self.progress.ensure(user_id)),
            }

        official = _load_official_result(race_id) or {}
        finish_order = body.get("finish_order") or official.get("finish_order") or []
        payouts = body.get("payouts") or official.get("payouts") or {}
        if not finish_order:
            return {
                "schema_version": self.SCHEMA,
                "item": row,
                "pending": True,
                "reason": "official finish_order not available",
                "official": official or None,
            }

        settled = settle_strategy(
            row.get("strategy_snapshot") or {},
            finish_order=finish_order,
            payouts=payouts,
        )
        updated = self.race_results.apply_settlement(
            user_id,
            race_id,
            purchase_amount=settled["purchase_amount"],
            payout_amount=settled["payout_amount"],
            profit=settled["profit"],
            hit=settled["hit"],
            settled=settled["settled"],
            finish_order=settled["finish_order"],
            payouts=payouts,
            bet_results=settled["bet_results"],
            marks_result=settled["marks_result"],
            official_result=official or {"finish_order": finish_order, "payouts": payouts},
            race_date=body.get("race_date") or official.get("race_date") or row.get("race_date"),
            race_label=body.get("race_label") or row.get("race_label"),
        )

        points_awarded = 0
        anomaly = False
        if settled.get("settled") and not int(row.get("points_awarded") or 0):
            profit = int(settled.get("profit") or 0)
            points_awarded = points_from_profit(profit)
            self.progress.add_profit_and_points(
                user_id, profit_delta=profit, points_delta=points_awarded
            )
            self.race_results.mark_points_awarded(user_id, race_id, points_awarded)

            purchase = int(settled.get("purchase_amount") or 0)
            payout = int(settled.get("payout_amount") or 0)
            mult = float(self.settings.get("purchase_anomaly_payout_multiple", 200) or 200)
            if purchase > 0 and payout >= purchase * mult:
                anomaly = True
                self.audit.append(
                    {
                        "user_id": user_id,
                        "race_id": race_id,
                        "event_type": "anomaly_payout",
                        "purchase_amount": purchase,
                        "payout_amount": payout,
                        "profit": profit,
                        "points_awarded": points_awarded,
                        "ai_strategy": row.get("strategy_snapshot"),
                        "user_bets": (row.get("strategy_snapshot") or {}).get("bets"),
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "meta": {
                            "multiple": round(payout / purchase, 2) if purchase else None,
                            "threshold_multiple": mult,
                        },
                    }
                )

            self.audit.append(
                {
                    "user_id": user_id,
                    "race_id": race_id,
                    "event_type": "settle",
                    "purchase_amount": purchase,
                    "payout_amount": payout,
                    "profit": profit,
                    "points_awarded": points_awarded,
                    "ai_strategy": row.get("strategy_snapshot"),
                    "user_bets": settled.get("bet_results"),
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "meta": {"anomaly": anomaly},
                }
            )
            updated = self.race_results.get(user_id, race_id)

        return {
            "schema_version": self.SCHEMA,
            "item": updated,
            "pending": not bool(settled.get("settled")),
            "settlement": settled,
            "points_awarded": points_awarded,
            "anomaly": anomaly,
            "progress": progress_payload(self.progress.ensure(user_id)),
        }

    def settle_pending_race_results(
        self,
        user_id: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        items = self.race_results.list_unsettled(user_id)
        results = []
        for it in items:
            rid = it.get("race_id")
            if not rid:
                continue
            if not it.get("purchase_registered"):
                continue
            try:
                results.append(
                    self.settle_race_result(
                        user_id,
                        str(rid),
                        ip_address=ip_address,
                        user_agent=user_agent,
                    )
                )
            except Exception as exc:
                results.append({"race_id": rid, "error": str(exc)})
        return {
            "schema_version": self.SCHEMA,
            "count": len(results),
            "results": results,
            "progress": progress_payload(self.progress.ensure(user_id)),
        }

    def settle_for_race_date(
        self,
        race_date: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """
        ResultAutomation 用: 指定開催日の購入済み未確定を一括 settle。
        ポイント・レベル更新は既存 settle_race_result 内で実施。
        """
        items = self.race_results.list_unsettled_for_date(race_date)
        results: list[dict[str, Any]] = []
        settled_count = 0
        pending_count = 0
        error_count = 0
        points_total = 0
        users_touched: set[str] = set()
        level_before: dict[str, int] = {}
        level_after: dict[str, int] = {}

        for it in items:
            uid = str(it.get("user_id") or "")
            rid = it.get("race_id")
            if not uid or not rid:
                continue
            if uid not in level_before:
                prog = progress_payload(self.progress.ensure(uid))
                level_before[uid] = int(prog.get("level") or 1)
            try:
                out = self.settle_race_result(
                    uid,
                    str(rid),
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                results.append(
                    {
                        "user_id": uid,
                        "race_id": rid,
                        "pending": bool(out.get("pending")),
                        "already_settled": bool(out.get("already_settled")),
                        "points_awarded": int(out.get("points_awarded") or 0),
                        "profit": (out.get("item") or {}).get("profit"),
                        "payout_amount": (out.get("item") or {}).get("payout_amount"),
                    }
                )
                users_touched.add(uid)
                points_total += int(out.get("points_awarded") or 0)
                if out.get("pending"):
                    pending_count += 1
                elif out.get("error"):
                    error_count += 1
                else:
                    settled_count += 1
                prog_after = out.get("progress") or progress_payload(
                    self.progress.ensure(uid)
                )
                level_after[uid] = int(prog_after.get("level") or 1)
            except Exception as exc:
                error_count += 1
                results.append(
                    {"user_id": uid, "race_id": rid, "error": str(exc)}
                )

        leveled_up = sum(
            1
            for uid in users_touched
            if level_after.get(uid, 0) > level_before.get(uid, 0)
        )
        purchased = self.race_results.list_purchased_for_date(race_date)
        return {
            "schema_version": self.SCHEMA,
            "race_date": race_date,
            "candidates": len(items),
            "settled": settled_count,
            "pending": pending_count,
            "errors": error_count,
            "points_awarded_total": points_total,
            "users_touched": len(users_touched),
            "users_leveled_up": leveled_up,
            "purchased_total": len(purchased),
            "purchased_settled": sum(1 for p in purchased if p.get("settled")),
            "results": results,
        }

    def _month_summary(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        purchase = sum(int(i.get("purchase_amount") or 0) for i in items)
        payout = sum(int(i.get("payout_amount") or 0) for i in items)
        profit = sum(int(i.get("profit") or 0) for i in items)
        race_count = len(items)
        hit_count = sum(1 for i in items if i.get("hit"))
        recovery = round((payout / purchase) * 100) if purchase > 0 else None
        hit_rate = round((hit_count / race_count) * 100) if race_count > 0 else None
        return {
            "purchase_amount": purchase,
            "payout_amount": payout,
            "profit": profit,
            "recovery_rate": recovery,
            "hit_rate": hit_rate,
            "race_count": race_count,
            "hit_count": hit_count,
        }

    def monthly_race_results(self, user_id: str, month: str) -> dict[str, Any]:
        """Aggregate user P&L for YYYY-MM (household ledger)."""
        month = (month or "").strip()
        if len(month) != 7 or month[4] != "-":
            raise ValueError("month must be YYYY-MM")
        self.settle_pending_race_results(user_id)
        items = [
            i
            for i in self.race_results.list_for_month(user_id, month)
            if i.get("purchase_registered")
        ]
        summary = self._month_summary(items)

        weeks: dict[int, dict[str, Any]] = {
            w: {"week": w, "purchase": 0, "payout": 0, "profit": 0, "races": 0, "hits": 0}
            for w in range(1, 6)
        }
        for i in items:
            w = _week_of_month(i.get("race_date"))
            bucket = weeks[w]
            bucket["purchase"] += int(i.get("purchase_amount") or 0)
            bucket["payout"] += int(i.get("payout_amount") or 0)
            bucket["profit"] += int(i.get("profit") or 0)
            bucket["races"] += 1
            if i.get("hit"):
                bucket["hits"] += 1

        return {
            "schema_version": self.SCHEMA,
            "month": month,
            "summary": summary,
            "weeks": [weeks[w] for w in range(1, 6)],
            "races": items,
            "progress": progress_payload(self.progress.ensure(user_id)),
        }

    def purchase_history(self, user_id: str) -> dict[str, Any]:
        """Month-grouped purchase history for accordion UI."""
        self.settle_pending_race_results(user_id)
        items = self.race_results.list_purchased(user_id)
        by_month: dict[str, list[dict[str, Any]]] = {}
        for i in items:
            key = str(i.get("race_date") or "")[:7]
            if len(key) != 7:
                continue
            by_month.setdefault(key, []).append(i)
        months = []
        for key in sorted(by_month.keys(), reverse=True):
            races = by_month[key]
            months.append(
                {
                    "month": key,
                    "summary": self._month_summary(races),
                    "races": races,
                }
            )
        return {
            "schema_version": self.SCHEMA,
            "view": "history",
            "months": months,
            "progress": progress_payload(self.progress.ensure(user_id)),
        }

    def official_race_result(self, race_id: str) -> dict[str, Any]:
        official = _load_official_result(race_id)
        if not official:
            raise LookupError("official result not found")
        return {"schema_version": self.SCHEMA, "official": official}


_service = UserService()


def get_service() -> UserService:
    return _service
