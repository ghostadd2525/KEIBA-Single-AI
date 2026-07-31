# -*- coding: utf-8 -*-
"""AI Challenge compare service (V7 / V8.9.1+ / V9.0 Benchmark Layer).

AI monthly theoretical P&L is a shared monthly-reset benchmark (same for all users).
User ledger is personal: only races on/after users.created_at for that user_id.
User cumulative points/levels are NOT managed here.

V9.0 (feature flag V9_BENCHMARK_LAYER):
  - Official AI = ◎単勝1点 (Prediction performance)
  - Purchase Lab = research ticket variants (collapsed UI only)
  - User Challenge unchanged

Does not touch Prediction Engine — only reads stored predictions + race_results.
race_evaluations are intentionally NOT used (heatmap / Miss research only).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from ..data.db import connect
from ..user.progress import progress_payload
from ..user.race_result_settle import build_purchase_snapshot, settle_strategy
from ..user.repository import UserProgressRepository, UserRaceResultRepository
from ..user.service import _load_official_result, _week_of_month

# Default AI「買い目攻略」book for V8.9 (independent of user purchase)
AI_DEFAULT_BET_TYPES = ["馬連", "ワイド", "三連複", "三連単"]
AI_DEFAULT_UNIT_STAKE = 100

# V9.0 official AI Benchmark — Prediction performance only
BENCHMARK_BET_TYPES = ["単勝"]
BENCHMARK_STRATEGY = {
    "id": "win_axis_1pt",
    "label": "◎単勝1点",
    "bet_types": list(BENCHMARK_BET_TYPES),
    "unit_stake": AI_DEFAULT_UNIT_STAKE,
    "version": "9.0",
    "since": "2026-07",
    "last_updated": "2026-07-27",
    "purpose": "ai_prediction_performance",
    "status": "production_standard",
}

# Research-only purchase variants (not default Challenge UI)
PURCHASE_LAB_STRATEGIES: list[dict[str, Any]] = [
    {
        "id": "sanrentan",
        "label": "三連単",
        "bet_types": ["三連単"],
    },
    {
        "id": "umaren",
        "label": "馬連",
        "bet_types": ["馬連"],
    },
    {
        "id": "wide",
        "label": "ワイド",
        "bet_types": ["ワイド"],
    },
    {
        "id": "place",
        "label": "複勝",
        "bet_types": ["複勝"],
    },
    {
        "id": "win_place",
        "label": "単勝＋複勝",
        "bet_types": ["単勝", "複勝"],
    },
]

SCHEMA_V89 = "expect-challenge-compare/1.1"
SCHEMA_V9 = "expect-challenge-compare/2.0"


def v9_benchmark_layer_enabled() -> bool:
    """Feature flag V9_BENCHMARK_LAYER.

    Production Standard (V9.0 promotion): default ON when unset.
    Explicit 0/false/no/off keeps V8.9 legacy book for rollback.
    """
    raw = os.environ.get("V9_BENCHMARK_LAYER", None)
    if raw is None or str(raw).strip() == "":
        return True
    v = str(raw).strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    return v in ("1", "true", "yes", "on")


def benchmark_strategy_meta() -> dict[str, Any]:
    """Ops / API metadata for Benchmark Strategy card."""
    return {
        "current_strategy": BENCHMARK_STRATEGY["label"],
        "version": BENCHMARK_STRATEGY["version"],
        "since": BENCHMARK_STRATEGY["since"],
        "last_updated": BENCHMARK_STRATEGY["last_updated"],
        "status": BENCHMARK_STRATEGY.get("status") or "production_standard",
        "bet_types": list(BENCHMARK_STRATEGY["bet_types"]),
        "unit_stake": BENCHMARK_STRATEGY["unit_stake"],
        "feature_flag": "V9_BENCHMARK_LAYER",
        "enabled": v9_benchmark_layer_enabled(),
    }


def _empty_side() -> dict[str, Any]:
    return {
        "purchase_amount": 0,
        "payout_amount": 0,
        "profit": 0,
        "recovery_rate": None,
        "hit_rate": None,
        "race_count": 0,
        "hit_count": 0,
        "weeks": [
            {"week": w, "profit": 0, "races": 0, "hits": 0, "purchase": 0, "payout": 0}
            for w in range(1, 6)
        ],
    }


def _finalize_side(side: dict[str, Any]) -> dict[str, Any]:
    purchase = int(side["purchase_amount"] or 0)
    payout = int(side["payout_amount"] or 0)
    races = int(side["race_count"] or 0)
    hits = int(side["hit_count"] or 0)
    side["recovery_rate"] = round((payout / purchase) * 100) if purchase > 0 else None
    side["hit_rate"] = round((hits / races) * 100) if races > 0 else None
    return side


def _runner_num(r: dict[str, Any] | None) -> int | None:
    if not r:
        return None
    try:
        n = int(r.get("horse_number") or r.get("num"))
        return n if n >= 1 else None
    except (TypeError, ValueError):
        return None


def axis_rivals_from_bundle(bundle: dict[str, Any] | None) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Extract ◎○▲△ from stored PredictionBundle (read-only)."""
    if not bundle:
        return None, []
    runners = ((bundle.get("evaluation") or {}).get("runners")) or []
    by_mark: dict[str, dict[str, Any]] = {}
    ordered = sorted(
        [r for r in runners if isinstance(r, dict)],
        key=lambda r: int(r.get("model_rank") or 999),
    )
    for r in ordered:
        mark = str(r.get("mark") or "")
        if mark and mark not in by_mark and mark != "none":
            by_mark[mark] = r
    honmei = by_mark.get("honmei") or (ordered[0] if ordered else None)
    axis_n = _runner_num(honmei)
    if axis_n is None:
        return None, []
    axis = {
        "num": axis_n,
        "name": (honmei or {}).get("horse_name"),
        "role": "本命軸",
    }
    rivals: list[dict[str, Any]] = []
    for mark, role in (("taikou", "対抗"), ("ana", "単穴"), ("chuuken", "連下")):
        r = by_mark.get(mark)
        n = _runner_num(r)
        if n is None or n == axis_n:
            continue
        rivals.append({"num": n, "name": (r or {}).get("horse_name"), "role": role})
    # fallback: next ranks
    if len(rivals) < 2:
        for r in ordered[1:]:
            n = _runner_num(r)
            if n is None or n == axis_n:
                continue
            if any(x["num"] == n for x in rivals):
                continue
            rivals.append({"num": n, "name": r.get("horse_name"), "role": "相手"})
            if len(rivals) >= 3:
                break
    return axis, rivals


def latest_prediction_bundle(race_id: str) -> dict[str, Any] | None:
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT bundle_json FROM predictions
            WHERE race_id=?
            ORDER BY created_at DESC, id DESC LIMIT 1
            """,
            (race_id,),
        ).fetchone()
        if row:
            raw = row["bundle_json"]
            if isinstance(raw, dict):
                return raw
            try:
                return json.loads(raw or "{}")
            except Exception:
                pass
    except Exception:
        pass
    finally:
        conn.close()
    # Production: predictions may live on PI until RA caches them.
    try:
        from ..ops.netkeiba_results import fetch_pi_prediction_bundle

        bundle = fetch_pi_prediction_bundle(race_id)
        if not bundle:
            return None
        # best-effort cache for subsequent Challenge / RA reads
        try:
            conn = connect()
            conn.execute(
                """
                INSERT INTO predictions(
                  race_id, engine_source, fallback_reason, model_version, bundle_json, created_at
                ) VALUES (?,?,?,?,?,?)
                """,
                (
                    race_id,
                    "real_ai",
                    None,
                    bundle.get("model_version"),
                    json.dumps(bundle, ensure_ascii=False),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return bundle
    except Exception:
        return None


def list_race_ids_for_month(month: str) -> list[dict[str, Any]]:
    """month YYYY-MM → race_results rows in that month."""
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT race_id, race_date, venue, winner_horse_number, result_json
            FROM race_results
            WHERE race_date IS NOT NULL AND substr(race_date, 1, 7)=?
            ORDER BY race_date, race_id
            """,
            (month,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _settle_theory(
    *,
    race_id: str,
    official: dict[str, Any],
    bundle: dict[str, Any] | None,
    axis: dict[str, Any],
    rivals: list[dict[str, Any]],
    bet_types: list[str],
    unit_stake: int = AI_DEFAULT_UNIT_STAKE,
) -> dict[str, Any] | None:
    """Settle one race for a given bet book (Prediction Bundle + official result only)."""
    snap = build_purchase_snapshot(
        axis=axis,
        rivals=rivals,
        bet_types=list(bet_types),
        unit_stake=unit_stake,
        prediction_version=(bundle or {}).get("prediction_version"),
    )
    if not snap.get("purchase_amount"):
        return None
    settled = settle_strategy(
        snap,
        finish_order=official.get("finish_order") or [],
        payouts=official.get("payouts") or {},
    )
    return {
        "race_id": race_id,
        "race_date": official.get("race_date"),
        "source": "prediction_bundle",
        "purchase_amount": settled["purchase_amount"],
        "payout_amount": settled["payout_amount"],
        "profit": settled["profit"],
        "hit": bool(settled.get("hit")),
        "settled": bool(settled.get("settled")),
        "strategy_snapshot": snap,
        "bet_results": settled.get("bet_results") or {},
        "marks_result": settled.get("marks_result"),
        "finish_order": settled.get("finish_order") or official.get("finish_order") or [],
        "bet_types": list(bet_types),
    }


def settle_ai_theory_for_race(
    race_id: str,
    bet_types: list[str] | None = None,
) -> dict[str, Any] | None:
    """AI理論 settle（ユーザー購入は見ない）。

    Prediction Bundle（snapshot）+ race_results のみで計算する。
    bet_types 未指定時は V8.9 デフォルト4券種（互換）。
    """
    official = _load_official_result(race_id)
    if not official or not (official.get("finish_order") or []):
        return None
    bundle = latest_prediction_bundle(race_id)
    axis, rivals = axis_rivals_from_bundle(bundle)
    if not axis:
        return None
    return _settle_theory(
        race_id=race_id,
        official=official,
        bundle=bundle,
        axis=axis,
        rivals=rivals,
        bet_types=list(bet_types) if bet_types is not None else list(AI_DEFAULT_BET_TYPES),
    )


def _user_joined_meta(user_id: str) -> tuple[str | None, str | None]:
    """Return (joined_at_iso, eligible_from YYYY-MM-DD) from users.created_at|joined_at.

    User ledger must never include races before this date (no shared-history reuse).
    """
    from ..user.repository import UserRepository

    row = UserRepository().get_by_id(str(user_id or "").strip())
    if not row:
        return None, None
    joined = row.get("created_at") or row.get("joined_at")
    if not joined:
        return None, None
    day = str(joined)[:10]
    if len(day) != 10 or day[4] != "-" or day[7] != "-":
        return str(joined), None
    return str(joined), day


def _accumulate_theory(side: dict[str, Any], theory: dict[str, Any], row: dict[str, Any]) -> None:
    purchase = int(theory["purchase_amount"] or 0)
    payout = int(theory["payout_amount"] or 0)
    profit = int(theory["profit"] or 0)
    hit = 1 if theory.get("hit") else 0
    side["purchase_amount"] += purchase
    side["payout_amount"] += payout
    side["profit"] += profit
    side["race_count"] += 1
    side["hit_count"] += hit
    w = _week_of_month(theory.get("race_date") or row.get("race_date"))
    bucket = side["weeks"][w - 1]
    bucket["purchase"] += purchase
    bucket["payout"] += payout
    bucket["profit"] += profit
    bucket["races"] += 1
    bucket["hits"] += hit


def _race_out(theory: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    return {
        "race_id": theory.get("race_id") or row.get("race_id"),
        "race_date": theory.get("race_date") or row.get("race_date"),
        "profit": int(theory.get("profit") or 0),
        "hit": bool(theory.get("hit")),
        "settled": theory.get("settled"),
        "purchase_amount": int(theory.get("purchase_amount") or 0),
        "payout_amount": int(theory.get("payout_amount") or 0),
    }


class ChallengeCompareService:
    """AI shared benchmark vs per-user personal ledger (since join)."""

    SCHEMA = SCHEMA_V89

    def __init__(self) -> None:
        self.user_results = UserRaceResultRepository()
        self.progress = UserProgressRepository()

    def ai_monthly(
        self,
        month: str,
        bet_types: list[str] | None = None,
        *,
        scope: str | None = None,
        book_label: str | None = None,
    ) -> dict[str, Any]:
        """Shared monthly-reset AI aggregate for a bet book."""
        types = list(bet_types) if bet_types is not None else list(AI_DEFAULT_BET_TYPES)
        side = _empty_side()
        races_out: list[dict[str, Any]] = []
        for row in list_race_ids_for_month(month):
            rid = str(row.get("race_id") or "")
            if not rid:
                continue
            theory = settle_ai_theory_for_race(rid, bet_types=types)
            if not theory:
                continue
            _accumulate_theory(side, theory, row)
            races_out.append(_race_out(theory, row))
        default_scope = (
            "ai_shared_benchmark_monthly"
            if types == AI_DEFAULT_BET_TYPES
            else "ai_theory_book_monthly"
        )
        return {
            "schema_version": self.SCHEMA,
            "month": month,
            "scope": scope or default_scope,
            "shared": True,
            "resets_monthly": True,
            "summary": _finalize_side(side),
            "weeks": side["weeks"],
            "races": races_out,
            "book": {
                "bet_types": types,
                "unit_stake": AI_DEFAULT_UNIT_STAKE,
                "label": book_label,
            },
        }

    def benchmark_monthly(self, month: str) -> dict[str, Any]:
        """Official V9 AI Benchmark: ◎単勝1点 only."""
        payload = self.ai_monthly(
            month,
            bet_types=list(BENCHMARK_BET_TYPES),
            scope="ai_official_benchmark_win",
            book_label=BENCHMARK_STRATEGY["label"],
        )
        payload["strategy"] = dict(BENCHMARK_STRATEGY)
        payload["official"] = True
        return payload

    def purchase_lab_monthly(self, month: str) -> dict[str, Any]:
        """Research purchase variants — not the official Challenge KPI."""
        # One race loop; settle each lab strategy without re-fetching marks.
        sides: dict[str, dict[str, Any]] = {
            s["id"]: _empty_side() for s in PURCHASE_LAB_STRATEGIES
        }
        for row in list_race_ids_for_month(month):
            rid = str(row.get("race_id") or "")
            if not rid:
                continue
            official = _load_official_result(rid)
            if not official or not (official.get("finish_order") or []):
                continue
            bundle = latest_prediction_bundle(rid)
            axis, rivals = axis_rivals_from_bundle(bundle)
            if not axis:
                continue
            for strat in PURCHASE_LAB_STRATEGIES:
                theory = _settle_theory(
                    race_id=rid,
                    official=official,
                    bundle=bundle,
                    axis=axis,
                    rivals=rivals,
                    bet_types=list(strat["bet_types"]),
                )
                if not theory:
                    continue
                _accumulate_theory(sides[strat["id"]], theory, row)

        strategies_out: list[dict[str, Any]] = []
        for strat in PURCHASE_LAB_STRATEGIES:
            side = _finalize_side(sides[strat["id"]])
            strategies_out.append(
                {
                    "id": strat["id"],
                    "label": strat["label"],
                    "bet_types": list(strat["bet_types"]),
                    "unit_stake": AI_DEFAULT_UNIT_STAKE,
                    "summary": {
                        "profit": side["profit"],
                        "recovery_rate": side["recovery_rate"],
                        "hit_rate": side["hit_rate"],
                        "purchase_amount": side["purchase_amount"],
                        "payout_amount": side["payout_amount"],
                        "race_count": side["race_count"],
                        "hit_count": side["hit_count"],
                    },
                    "weeks": side["weeks"],
                }
            )
        return {
            "visible_by_default": False,
            "purpose": "research_purchase_formation",
            "month": month,
            "strategies": strategies_out,
        }

    def user_monthly(self, user_id: str, month: str) -> dict[str, Any]:
        """Per-user ledger for month — only races on/after users.created_at date.

        Never mixes other users. Never reuses pre-registration / shared history.
        """
        uid = str(user_id or "").strip()
        joined_at, eligible_from = _user_joined_meta(uid)
        raw = self.user_results.list_for_month(uid, month) if uid else []
        items: list[dict[str, Any]] = []
        for i in raw:
            if not i.get("purchase_registered"):
                continue
            # Hard isolation: must belong to this user_id (repo already filters; assert)
            if str(i.get("user_id") or "") != uid:
                continue
            if not eligible_from:
                # No join date → do not invent history from shared past
                continue
            rd = str(i.get("race_date") or "")[:10]
            if not rd or rd < eligible_from:
                continue
            items.append(i)

        side = _empty_side()
        for i in items:
            purchase = int(i.get("purchase_amount") or 0)
            payout = int(i.get("payout_amount") or 0)
            profit = int(i.get("profit") or 0)
            hit = 1 if i.get("hit") else 0
            side["purchase_amount"] += purchase
            side["payout_amount"] += payout
            side["profit"] += profit
            side["race_count"] += 1
            side["hit_count"] += hit
            w = _week_of_month(i.get("race_date"))
            bucket = side["weeks"][w - 1]
            bucket["purchase"] += purchase
            bucket["payout"] += payout
            bucket["profit"] += profit
            bucket["races"] += 1
            bucket["hits"] += hit
        return {
            "schema_version": self.SCHEMA,
            "month": month,
            "user_id": uid,
            "joined_at": joined_at,
            "eligible_from": eligible_from,
            "scope": "user_personal_ledger_since_join",
            "shared": False,
            "resets_monthly": False,
            "summary": _finalize_side(side),
            "weeks": side["weeks"],
            "races": [
                {
                    "race_id": i.get("race_id"),
                    "race_date": i.get("race_date"),
                    "race_label": i.get("race_label"),
                    "profit": int(i.get("profit") or 0),
                    "hit": bool(i.get("hit")),
                    "settled": bool(i.get("settled")),
                    "purchase_amount": int(i.get("purchase_amount") or 0),
                    "payout_amount": int(i.get("payout_amount") or 0),
                }
                for i in items
            ],
        }

    def compare(self, user_id: str, month: str) -> dict[str, Any]:
        """Return Challenge payload. V9 flag ON → layered shape; OFF → V8.9 shape."""
        if v9_benchmark_layer_enabled():
            return self._compare_v9(user_id, month)
        return self._compare_v89(user_id, month)

    def _comparison_block(
        self,
        *,
        ai_profit: int,
        user_profit: int,
        ai_scope: str | None,
        user_scope: str | None,
        user_eligible_from: str | None,
        source: str,
    ) -> dict[str, Any]:
        diff = user_profit - ai_profit  # positive => user ahead (challenge cleared)
        if diff > 0:
            status = "achieved"
            challenge_message = "今月のAIチャレンジ達成！"
            kaoba = "すごい！\n今月は私より成績がいいね！"
            home_kaoba = "今月は私を超えたね！"
        elif diff < 0:
            status = "behind"
            need = abs(diff)
            challenge_message = f"あと{need:,}円でAIを超えます！"
            kaoba = "来週は一緒に逆転しよう！"
            home_kaoba = "あと少しで追いつけるよ！"
        else:
            status = "tied"
            challenge_message = "いい勝負だね！"
            kaoba = "いい勝負だね！"
            home_kaoba = "今月も一緒に頑張ろう！"
        return {
            "ai_profit": ai_profit,
            "benchmark_profit": ai_profit,
            "user_profit": user_profit,
            "profit_diff": diff,
            "status": status,  # achieved | behind | tied
            "challenge_message": challenge_message,
            "kaoba_message": kaoba,
            "home_kaoba_message": home_kaoba,
            "ai_scope": ai_scope,
            "user_scope": user_scope,
            "user_eligible_from": user_eligible_from,
            "source": source,
        }

    def _weeks_compare(self, ai: dict[str, Any], user: dict[str, Any]) -> list[dict[str, Any]]:
        weeks = []
        for w in range(1, 6):
            aw = (ai.get("weeks") or [{}])[w - 1]
            uw = (user.get("weeks") or [{}])[w - 1]
            weeks.append(
                {
                    "week": w,
                    "ai_profit": int(aw.get("profit") or 0),
                    "user_profit": int(uw.get("profit") or 0),
                    "ai_races": int(aw.get("races") or 0),
                    "user_races": int(uw.get("races") or 0),
                }
            )
        return weeks

    def _compare_v89(self, user_id: str, month: str) -> dict[str, Any]:
        """V8.9.1 response shape (flag OFF)."""
        ai = self.ai_monthly(month)
        user = self.user_monthly(user_id, month)
        ai_profit = int((ai.get("summary") or {}).get("profit") or 0)
        user_profit = int((user.get("summary") or {}).get("profit") or 0)
        ai_summary = ai.get("summary") or {}
        user_summary = user.get("summary") or {}
        return {
            "schema_version": SCHEMA_V89,
            "design_policy": "v891_ai_shared_user_personal_since_join",
            "feature_flags": {"v9_benchmark_layer": False},
            "month": month,
            "ai": ai,
            "user": user,
            "ai_summary": ai_summary,
            "user_summary": user_summary,
            "ai_weeks": ai.get("weeks"),
            "user_weeks": user.get("weeks"),
            "weeks_compare": self._weeks_compare(ai, user),
            "ai_races": ai.get("races"),
            "user_races": user.get("races"),
            "comparison": self._comparison_block(
                ai_profit=ai_profit,
                user_profit=user_profit,
                ai_scope=ai.get("scope"),
                user_scope=user.get("scope"),
                user_eligible_from=user.get("eligible_from"),
                source="ai_legacy_book",
            ),
            "progress": self._safe_progress(user_id),
            "ai_book": ai.get("book"),
            "benchmark_strategy": benchmark_strategy_meta(),
        }

    def _compare_v9(self, user_id: str, month: str) -> dict[str, Any]:
        """V9.0 layered response: benchmark / user / purchase_lab / comparison."""
        benchmark = self.benchmark_monthly(month)
        user = self.user_monthly(user_id, month)
        purchase_lab = self.purchase_lab_monthly(month)
        bm_profit = int((benchmark.get("summary") or {}).get("profit") or 0)
        user_profit = int((user.get("summary") or {}).get("profit") or 0)
        bm_summary = benchmark.get("summary") or {}
        user_summary = user.get("summary") or {}
        comparison = self._comparison_block(
            ai_profit=bm_profit,
            user_profit=user_profit,
            ai_scope=benchmark.get("scope"),
            user_scope=user.get("scope"),
            user_eligible_from=user.get("eligible_from"),
            source="benchmark",
        )
        return {
            "schema_version": SCHEMA_V9,
            "design_policy": "v9_benchmark_layer",
            "feature_flags": {"v9_benchmark_layer": True},
            "month": month,
            # Canonical V9 sections
            "benchmark": benchmark,
            "user": user,
            "purchase_lab": purchase_lab,
            "comparison": comparison,
            "benchmark_strategy": benchmark_strategy_meta(),
            # Compat aliases: treat official AI as benchmark for older consumers
            "ai": benchmark,
            "ai_summary": bm_summary,
            "user_summary": user_summary,
            "ai_weeks": benchmark.get("weeks"),
            "user_weeks": user.get("weeks"),
            "weeks_compare": self._weeks_compare(benchmark, user),
            "ai_races": benchmark.get("races"),
            "user_races": user.get("races"),
            "ai_book": benchmark.get("book"),
            "progress": self._safe_progress(user_id),
        }

    def _safe_progress(self, user_id: str) -> dict[str, Any]:
        try:
            return progress_payload(self.progress.ensure(user_id))
        except Exception:
            return progress_payload(None)


_service: ChallengeCompareService | None = None


def get_challenge_service() -> ChallengeCompareService:
    global _service
    if _service is None:
        _service = ChallengeCompareService()
    return _service
