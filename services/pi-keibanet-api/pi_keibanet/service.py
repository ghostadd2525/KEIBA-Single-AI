# -*- coding: utf-8 -*-
"""Resolve race + build Collector / Web GUI JSON payloads."""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from .venues import COURSE_NAME_TO_CODE, collector_race_id
from .race_catalog import (
    assign_venue_label_nos,
    build_race_summary,
    group_races_by_course,
    make_win5_race_id,
    parse_race_id_ref,
    race_label,
)
from .netkeiba.client import NetkeibaClient, NetkeibaFetchError
from .netkeiba.parse import (
    find_numeric_race_id,
    parse_entries_from_shutuba,
    parse_jra_win_odds_payload,
    parse_list_races_from_race_list,
    parse_meetings_from_race_list,
    parse_odds_from_entries,
    parse_race_meta_from_shutuba,
    parse_track_condition,
    shutuba_has_race,
)
from .netkeiba.horse_history import (
    build_history_rows,
    fetch_horse_history,
)

# 単勝オッズ / board メモリキャッシュ（netkeiba 負荷抑制・既定 5 分）
_ODDS_CACHE_TTL_SEC = float(os.environ.get("PI_ODDS_CACHE_TTL_SEC", "300"))
_BOARD_CACHE_TTL_SEC = float(os.environ.get("PI_BOARD_CACHE_TTL_SEC", "300"))
_HORSE_HISTORY_TTL_SEC = float(os.environ.get("PI_HORSE_HISTORY_TTL_SEC", "3600"))
_HORSE_HISTORY_WORKERS = int(os.environ.get("PI_HORSE_HISTORY_WORKERS", "6"))
_ODDS_SERIES_MIN_GAP_SEC = float(os.environ.get("PI_ODDS_SERIES_MIN_GAP_SEC", "300"))
_ODDS_SERIES_MAX_POINTS = int(os.environ.get("PI_ODDS_SERIES_MAX_POINTS", "48"))
_ODDS_SERIES_DIR = Path(
    os.environ.get(
        "PI_ODDS_SERIES_DIR",
        str(Path(__file__).resolve().parents[1] / "data" / "odds_series"),
    )
)
_odds_cache: dict[str, tuple[float, list[dict[str, Any]], str]] = {}
_board_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_horse_history_cache: dict[str, tuple[float, Any]] = {}
# Ready Prediction 応答キャッシュ（PE/CE 非変更・配信最適化のみ）
_PRED_CACHE_TTL_SEC = float(os.environ.get("PI_PRED_CACHE_TTL_SEC", "120"))
_prediction_cache: dict[str, tuple[float, dict[str, Any]]] = {}
# numeric_race_id → [{ts, odds: {horse_number: win}}, ...]
_odds_series: dict[str, list[dict[str, Any]]] = {}

class RaceNotFoundError(LookupError):
    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message


def _resolve_ai_platform_root() -> Path | None:
    for key in ("PI_AI_PLATFORM_ROOT", "AI_PLATFORM_ROOT"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            root = Path(raw)
            if root.is_dir():
                return root
    for candidate in (Path(r"C:\win5-ai"), Path("/opt/expect-ai/platform")):
        if candidate.is_dir():
            return candidate
    return None


def _resolve_prediction_data_root() -> Path | None:
    for key in ("PI_DATA_ROOT", "EXPECT_AI_DATA_ROOT"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            root = Path(raw)
            if root.is_dir():
                return root
    platform_root = _resolve_ai_platform_root()
    if platform_root is not None:
        data = platform_root / "data"
        if data.is_dir():
            return data
    win_data = Path(r"C:\win5-ai\data")
    if win_data.is_dir():
        return win_data
    return None


class PiKeibaNetService:
    def __init__(self, client: NetkeibaClient | None = None) -> None:
        self.client = client or NetkeibaClient()

    def resolve(self, *, date: str, venue: str, race_no: int) -> tuple[str, str]:
        if venue not in COURSE_NAME_TO_CODE:
            raise RaceNotFoundError(
                "venue_name_mismatch",
                f"unknown venue: {venue!r}",
            )

        list_html = self.client.fetch_race_list(date)
        numeric = find_numeric_race_id(list_html, date=date, venue=venue, race_no=race_no)
        if not numeric:
            listed = parse_list_races_from_race_list(list_html)
            meetings = parse_meetings_from_race_list(list_html)
            raise RaceNotFoundError(
                "race_no_mismatch",
                (
                    f"race_id not resolved: date={date} venue={venue} race_no={race_no}; "
                    f"listed_races={len(listed)} meetings={[(m.venue, m.kai, m.day) for m in meetings]}"
                ),
            )

        shutuba_html = self.client.fetch_shutuba(numeric)
        if not shutuba_has_race(shutuba_html):
            raise RaceNotFoundError(
                "shutuba_empty",
                f"shutuba has no race content: race_id={numeric} date={date} venue={venue} race_no={race_no}",
            )
        return numeric, shutuba_html

    def list_races(self, *, date: str) -> dict[str, Any]:
        """
        GET /v1/races?date=YYYY-MM-DD

        Returns venues → races tree for GUI selection (published races only).
        """
        if not date or len(date) < 10:
            raise ValueError("date is required (YYYY-MM-DD)")

        list_html = self.client.fetch_race_list(date)
        meetings = parse_meetings_from_race_list(list_html)
        listed = parse_list_races_from_race_list(list_html)

        venues_present = sorted({m.venue for m in meetings} | {r.venue for r in listed})
        meeting_order = [m.venue for m in meetings]
        venue_labels = assign_venue_label_nos(venues_present, preferred_order=meeting_order)

        races: list[dict[str, Any]] = []
        for r in listed:
            win5_id = make_win5_race_id(date, r.venue, r.race_no, venue_labels)
            extra: dict[str, Any] = {
                "collector_race_id": collector_race_id(date, r.venue, r.race_no),
            }
            post_time = getattr(r, "post_time", "") or ""
            if post_time:
                extra["post_time"] = post_time
            races.append(
                build_race_summary(
                    race_id=win5_id,
                    race_date=date,
                    course=r.venue,
                    race_number=r.race_no,
                    race_name=getattr(r, "race_name", "") or "",
                    numeric_race_id=r.race_id,
                    status="published",
                    extra=extra,
                )
            )

        races.sort(key=lambda x: (
            venue_labels.get(str(x.get("course")), 99),
            int(x.get("race_number") or 0),
        ))

        return {
            "date": date,
            "meetings": [
                {
                    "course": m.venue,
                    "venue": m.venue,
                    "venue_code": m.venue_code,
                    "kai": m.kai,
                    "day": m.day,
                }
                for m in meetings
            ],
            "venues": group_races_by_course(races, preferred_order=meeting_order),
            "races": races,
            "count": len(races),
        }

    def resolve_race_ref(self, race_id: str) -> dict[str, Any]:
        """Resolve Win5 or collector race_id to date/course/race_number + numeric id."""
        parsed = parse_race_id_ref(race_id)
        date = parsed["race_date"]
        race_number = int(parsed["race_number"])
        course = parsed.get("course") or ""

        list_html = self.client.fetch_race_list(date)
        listed = parse_list_races_from_race_list(list_html)
        meetings = parse_meetings_from_race_list(list_html)
        venues_present = sorted({m.venue for m in meetings} | {r.venue for r in listed})
        meeting_order = [m.venue for m in meetings]
        venue_labels = assign_venue_label_nos(venues_present, preferred_order=meeting_order)

        if parsed["format"] == "win5":
            label_no = parsed["label_no"]
            inv = {v: k for k, v in venue_labels.items()}
            course = inv.get(label_no, "")
            if not course:
                candidates = [r for r in listed if r.race_no == race_number]
                if len(candidates) == 1:
                    course = candidates[0].venue
                elif not candidates:
                    raise RaceNotFoundError(
                        "race_no_mismatch",
                        f"no published race for race_id={race_id}",
                    )
                else:
                    raise RaceNotFoundError(
                        "race_id_ambiguous",
                        f"cannot map label_no={label_no} for race_id={race_id}; venues={venues_present}",
                    )

        hit = next((r for r in listed if r.venue == course and r.race_no == race_number), None)
        if not hit:
            raise RaceNotFoundError(
                "race_no_mismatch",
                f"race not in published list: date={date} course={course} race_number={race_number}",
            )

        win5_id = make_win5_race_id(date, course, race_number, venue_labels)
        out: dict[str, Any] = {
            "race_id": win5_id,
            "race_date": date,
            "course": course,
            "race_number": race_number,
            "race_label": race_label(course, race_number),
            "race_name": getattr(hit, "race_name", "") or "",
            "numeric_race_id": hit.race_id,
            "collector_race_id": collector_race_id(date, course, race_number),
        }
        post_time = getattr(hit, "post_time", "") or ""
        if post_time:
            out["post_time"] = post_time
        return out

    def get_race(self, race_id: str, *, enrich: bool = True) -> dict[str, Any]:
        """GET /v1/races/{race_id} — display identity + optional shutuba meta."""
        ref = self.resolve_race_ref(race_id)
        summary_extra: dict[str, Any] = {"collector_race_id": ref["collector_race_id"]}
        if ref.get("post_time"):
            summary_extra["post_time"] = ref["post_time"]
        summary = build_race_summary(
            race_id=ref["race_id"],
            race_date=ref["race_date"],
            course=ref["course"],
            race_number=ref["race_number"],
            race_name=ref.get("race_name") or "",
            numeric_race_id=ref["numeric_race_id"],
            status="published",
            extra=summary_extra,
        )
        if not enrich:
            return summary

        try:
            html = self.client.fetch_shutuba(ref["numeric_race_id"])
        except NetkeibaFetchError as exc:
            summary["enrich_error"] = str(exc)
            return summary

        if not shutuba_has_race(html):
            summary["status"] = "unpublished"
            summary["unpublished_reason"] = "shutuba_empty"
            return summary

        meta = parse_race_meta_from_shutuba(
            html,
            date=ref["race_date"],
            venue=ref["course"],
            race_no=ref["race_number"],
            numeric_race_id=ref["numeric_race_id"],
        )
        if meta.get("race_name"):
            summary["race_name"] = meta["race_name"]
        if meta.get("post_time"):
            summary["post_time"] = meta["post_time"]
        summary["distance"] = meta.get("distance")
        summary["surface"] = meta.get("surface") or meta.get("target_surface")
        summary["turn"] = meta.get("turn")
        summary["weather"] = meta.get("weather")
        summary["track_condition"] = meta.get("track_condition")
        summary["field_size"] = meta.get("field_size")
        return summary

    def get_prediction(self, race_id: str) -> dict[str, Any]:
        """
        GET /v1/predictions/{race_id}

        Prediction uses race_id as key; course/race_number/race_label are display-only.
        Ready 応答のみ短 TTL キャッシュ（PE/CE ロジック非変更）。
        """
        from . import cache_metrics

        rid = str(race_id).strip()
        t0 = time.monotonic()
        cached = _prediction_cache.get(rid)
        if cached and time.monotonic() - cached[0] < _PRED_CACHE_TTL_SEC:
            cache_metrics.note_prediction(hit=True, ms=(time.monotonic() - t0) * 1000)
            return dict(cached[1])

        ref = self.resolve_race_ref(race_id)
        display_extra: dict[str, Any] = {"collector_race_id": ref["collector_race_id"]}
        if ref.get("post_time"):
            display_extra["post_time"] = ref["post_time"]
        display = build_race_summary(
            race_id=ref["race_id"],
            race_date=ref["race_date"],
            course=ref["course"],
            race_number=ref["race_number"],
            race_name=ref.get("race_name") or "",
            numeric_race_id=ref["numeric_race_id"],
            extra=display_extra,
        )

        ai_root = _resolve_ai_platform_root()
        if ai_root is None:
            cache_metrics.note_prediction(hit=False, ms=(time.monotonic() - t0) * 1000)
            return {
                **display,
                "prediction_available": False,
                "error": "prediction_runtime_unavailable",
                "message": "AI platform root not found (set PI_AI_PLATFORM_ROOT or AI_PLATFORM_ROOT)",
            }

        try:
            ai_root_str = str(ai_root)
            if ai_root_str not in sys.path:
                sys.path.insert(0, ai_root_str)
            from ai_platform.core.candidate_evaluation import CorePipeline
            from ai_platform.core.features.feature_loader import FeatureLoader, get_last_failure_reason
        except Exception as exc:
            cache_metrics.note_prediction(hit=False, ms=(time.monotonic() - t0) * 1000)
            return {
                **display,
                "prediction_available": False,
                "error": "prediction_runtime_unavailable",
                "message": str(exc),
            }

        data_root = _resolve_prediction_data_root()
        loader = FeatureLoader(data_root=data_root)
        pipeline = CorePipeline(loader=loader)
        result = pipeline.evaluate(ref["race_id"])
        if result is None:
            cache_metrics.note_prediction(hit=False, ms=(time.monotonic() - t0) * 1000)
            return {
                **display,
                "prediction_available": False,
                "error": "features_unavailable",
                "message": get_last_failure_reason() or "FeatureLoader returned None",
            }

        payload = {
            **display,
            "prediction_available": True,
            "prediction": {
                "race_id": result.get("race_id"),
                "candidates": result.get("candidates"),
                "context": result.get("context"),
                "world": result.get("world"),
                "sub_world": result.get("sub_world"),
                "overall_confidence": result.get("overall_confidence"),
                "meta": result.get("meta"),
                "core_version": result.get("core_version"),
                # Version 2 Explainability — additive pass-through only (no transform)
                **(
                    {"explain_payload": result["explain_payload"]}
                    if (
                        result.get("explain_payload") is not None
                        and str(os.environ.get("EXPLAIN_V2_ENABLED", "")).strip().lower()
                        in {"1", "true", "yes", "on"}
                    )
                    else {}
                ),
            },
        }
        # candidates がある Ready のみキャッシュ
        cands = (payload.get("prediction") or {}).get("candidates")
        if isinstance(cands, list) and cands:
            _prediction_cache[rid] = (time.monotonic(), dict(payload))
        cache_metrics.note_prediction(hit=False, ms=(time.monotonic() - t0) * 1000)
        return payload

    def race_meta(self, *, date: str, venue: str, race_no: int) -> dict[str, Any]:
        numeric, html = self.resolve(date=date, venue=venue, race_no=race_no)
        meta = parse_race_meta_from_shutuba(
            html,
            date=date,
            venue=venue,
            race_no=race_no,
            numeric_race_id=numeric,
        )
        return {
            **meta,
            "race_date": date,
            "course": venue,
            "race_number": race_no,
            "race_label": race_label(venue, race_no),
            "race_name": meta.get("race_name") or "",
        }

    def entries_core(self, *, date: str, venue: str, race_no: int) -> dict[str, Any]:
        numeric, html = self.resolve(date=date, venue=venue, race_no=race_no)
        entries = [
            {k: v for k, v in row.items() if not str(k).startswith("_")}
            for row in parse_entries_from_shutuba(html)
        ]
        if not entries:
            raise RaceNotFoundError(
                "parse_entries_empty",
                f"entries parse empty: date={date} venue={venue} race_no={race_no} race_id={numeric}",
            )
        return {
            "race_id": collector_race_id(date, venue, race_no),
            "date": date,
            "race_date": date,
            "venue": venue,
            "course": venue,
            "race_no": race_no,
            "race_number": race_no,
            "race_label": race_label(venue, race_no),
            "entries": entries,
            "numeric_race_id": numeric,
        }

    def odds(self, *, date: str, venue: str, race_no: int) -> dict[str, Any]:
        numeric, html = self.resolve(date=date, venue=venue, race_no=race_no)
        odds_rows, odds_status = self._load_win_odds(numeric_race_id=numeric, shutuba_html=html)
        return {
            "race_id": collector_race_id(date, venue, race_no),
            "date": date,
            "race_date": date,
            "venue": venue,
            "course": venue,
            "race_no": race_no,
            "race_number": race_no,
            "race_label": race_label(venue, race_no),
            "odds": odds_rows,
            "odds_status": odds_status,
            "odds_updated_at": time.strftime("%Y-%m-%dT%H:%M:%S+09:00", time.localtime()),
            "cache_ttl_sec": int(_ODDS_CACHE_TTL_SEC),
        }

    def _load_win_odds(
        self,
        *,
        numeric_race_id: str,
        shutuba_html: str | None = None,
        force: bool = False,
    ) -> tuple[list[dict[str, Any]], str]:
        """
        単勝オッズ取得。優先: JRA odds API → shutuba 埋め込み。
        偽の 99.9 は返さない。キャッシュで netkeiba アクセスを間引く。
        returns (rows, status) status=published|unpublished|error
        """
        rid = str(numeric_race_id)
        now = time.monotonic()
        t0 = now
        if not force and rid in _odds_cache:
            ts, rows, status = _odds_cache[rid]
            if now - ts < _ODDS_CACHE_TTL_SEC:
                from . import cache_metrics

                cache_metrics.note_odds(hit=True, ms=(time.monotonic() - t0) * 1000)
                return rows, status

        rows: list[dict[str, Any]] = []
        status = "unpublished"
        try:
            raw = self.client.fetch_jra_odds_json(rid)
            rows = parse_jra_win_odds_payload(raw)
            if rows:
                status = "published"
        except NetkeibaFetchError as exc:
            print(f"[pi-keibanet] jra odds fetch failed race_id={rid}: {exc}")
            status = "error"

        if not rows and shutuba_html:
            try:
                raw_entries = parse_entries_from_shutuba(shutuba_html)
                rows = parse_odds_from_entries(raw_entries)
                if rows:
                    status = "published"
            except Exception as exc:
                print(f"[pi-keibanet] shutuba odds parse failed race_id={rid}: {exc}")

        _odds_cache[rid] = (now, rows, status)
        if status == "published" and rows:
            self._record_odds_snapshot(rid, rows)
        from . import cache_metrics

        cache_metrics.note_odds(hit=False, ms=(time.monotonic() - t0) * 1000)
        return rows, status

    def _series_path(self, numeric_race_id: str) -> Path:
        return _ODDS_SERIES_DIR / f"{numeric_race_id}.json"

    def _load_odds_series_disk(self, numeric_race_id: str) -> list[dict[str, Any]]:
        rid = str(numeric_race_id)
        if rid in _odds_series:
            return _odds_series[rid]
        path = self._series_path(rid)
        points: list[dict[str, Any]] = []
        if path.is_file():
            try:
                import json

                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and isinstance(raw.get("points"), list):
                    points = raw["points"]
                elif isinstance(raw, list):
                    points = raw
            except Exception as exc:
                print(f"[pi-keibanet] odds series load failed {rid}: {exc}")
        _odds_series[rid] = points
        return points

    def _save_odds_series_disk(self, numeric_race_id: str, points: list[dict[str, Any]]) -> None:
        rid = str(numeric_race_id)
        try:
            _ODDS_SERIES_DIR.mkdir(parents=True, exist_ok=True)
            import json

            payload = {
                "numeric_race_id": rid,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S+09:00", time.localtime()),
                "points": points[-_ODDS_SERIES_MAX_POINTS:],
            }
            self._series_path(rid).write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"[pi-keibanet] odds series save failed {rid}: {exc}")

    def _record_odds_snapshot(
        self,
        numeric_race_id: str,
        rows: list[dict[str, Any]],
    ) -> None:
        """5分以上空けて単勝オッズを時系列に追記（netkeiba 連打はしない）。"""
        rid = str(numeric_race_id)
        if not rid or not rows:
            return
        odds_map: dict[str, float] = {}
        for r in rows:
            hn = r.get("horse_number")
            win = r.get("win")
            if hn is None or win is None:
                continue
            try:
                odds_map[str(int(hn))] = float(win)
            except (TypeError, ValueError):
                continue
        if not odds_map:
            return

        points = self._load_odds_series_disk(rid)
        now_wall = time.time()
        if points:
            try:
                last_ts = float(points[-1].get("ts") or 0)
            except (TypeError, ValueError):
                last_ts = 0.0
            if now_wall - last_ts < _ODDS_SERIES_MIN_GAP_SEC:
                return

        points.append(
            {
                "ts": now_wall,
                "at": time.strftime("%Y-%m-%dT%H:%M:%S+09:00", time.localtime(now_wall)),
                "odds": odds_map,
            }
        )
        points = points[-_ODDS_SERIES_MAX_POINTS:]
        _odds_series[rid] = points
        self._save_odds_series_disk(rid, points)

    def get_odds_series(self, race_id: str, *, refresh: bool = False) -> dict[str, Any]:
        """
        単勝オッズ時系列（折れ線用）。
        refresh=true でもキャッシュ TTL 内なら netkeiba を叩かない（_load_win_odds 側）。
        """
        ref = self.resolve_race_ref(race_id)
        numeric = str(ref.get("numeric_race_id") or "")
        if not numeric:
            raise RaceNotFoundError("no_numeric_id", f"numeric_race_id missing for {race_id}")

        if refresh:
            self._load_win_odds(numeric_race_id=numeric, shutuba_html=None)
        else:
            # キャッシュが空なら一度だけ取得してシリーズ起点を作る
            points0 = self._load_odds_series_disk(numeric)
            if not points0:
                self._load_win_odds(numeric_race_id=numeric, shutuba_html=None)

        points = self._load_odds_series_disk(numeric)
        # 馬名は odds snapshot から推定（get_race_board は重いので呼ばない）
        names: dict[str, str] = {}
        board: dict[str, Any] = {}
        try:
            cached = getattr(self, "_board_cache", None) or {}
            board = cached.get(ref["race_id"]) or {}
            for e in board.get("entries") or []:
                hn = e.get("horse_number")
                if hn is not None:
                    names[str(int(hn))] = str(e.get("horse_name") or "")
        except Exception:
            board = {}
            names = {}

        series: list[dict[str, Any]] = []
        horse_nums = sorted({int(k) for p in points for k in (p.get("odds") or {}) if str(k).isdigit()})
        for hn in horse_nums:
            key = str(hn)
            values = []
            for p in points:
                od = (p.get("odds") or {}).get(key)
                values.append(
                    {
                        "ts": p.get("ts"),
                        "at": p.get("at"),
                        "odds": float(od) if od is not None else None,
                    }
                )
            latest = next((v["odds"] for v in reversed(values) if v["odds"] is not None), None)
            series.append(
                {
                    "horse_number": hn,
                    "horse_name": names.get(key) or f"{hn}番",
                    "latest_odds": latest,
                    "points": values,
                }
            )
        series.sort(
            key=lambda s: (
                s["latest_odds"] is None,
                float(s["latest_odds"]) if s["latest_odds"] is not None else 9999.0,
                s["horse_number"],
            )
        )

        return {
            "schema_version": "expect-odds-series/1.0",
            "race_id": ref["race_id"],
            "race_label": ref.get("race_label") or race_label(ref["course"], int(ref["race_number"])),
            "race_name": (board or {}).get("race_name") or ref.get("race_name") or "",
            "date": ref["race_date"],
            "venue": ref["course"],
            "race_no": int(ref["race_number"]),
            "post_time": ref.get("post_time") or (board or {}).get("post_time"),
            "numeric_race_id": numeric,
            "sample_interval_sec": int(_ODDS_SERIES_MIN_GAP_SEC),
            "point_count": len(points),
            "timestamps": [p.get("at") for p in points],
            "series": series,
        }

    def track(self, *, date: str, venue: str, race_no: int) -> dict[str, Any]:
        _, html = self.resolve(date=date, venue=venue, race_no=race_no)
        return {
            "race_id": collector_race_id(date, venue, race_no),
            "date": date,
            "race_date": date,
            "venue": venue,
            "course": venue,
            "race_no": race_no,
            "race_number": race_no,
            "race_label": race_label(venue, race_no),
            "condition": parse_track_condition(html),
        }

    def entries_full(
        self,
        *,
        date: str,
        venue: str,
        race_no: int,
        numeric_race_id: str,
    ) -> dict[str, Any]:
        """entries_core + sex/age/trainer/horse_url (Win5AI runners.csv compatible).

        numeric_race_id は呼び出し元（resolve_race_ref）から渡すこと。
        内部での find_numeric_race_id / resolve 再実行は禁止。
        """
        numeric = str(numeric_race_id or "").strip()
        if not numeric:
            raise RaceNotFoundError(
                "no_numeric_id",
                f"numeric_race_id required: date={date} venue={venue} race_no={race_no}",
            )
        html = self.client.fetch_shutuba(numeric)
        if not shutuba_has_race(html):
            raise RaceNotFoundError(
                "shutuba_empty",
                f"shutuba has no race content: race_id={numeric} date={date} venue={venue} race_no={race_no}",
            )
        raw_entries = parse_entries_from_shutuba(html)
        if not raw_entries:
            raise RaceNotFoundError(
                "parse_entries_empty",
                f"entries parse empty: date={date} venue={venue} race_no={race_no}",
            )
        meta = parse_race_meta_from_shutuba(
            html, date=date, venue=venue, race_no=race_no, numeric_race_id=numeric,
        )
        entries = []
        for row in raw_entries:
            entries.append({
                "horse_number": row.get("horse_number"),
                "frame_number": row.get("frame", 0),
                "horse_name": row.get("horse_name", ""),
                "jockey": row.get("jockey", ""),
                "trainer": row.get("_trainer", "") or "",
                "weight_carried": row.get("weight", 0.0),
                "horse_id": row.get("horse_id", ""),
                "horse_url": row.get("_horse_url", ""),
                "sex": row.get("_sex", ""),
                "age": row.get("_age"),
                "odds": row.get("_odds"),
                "popularity": row.get("_popularity"),
            })
        return {
            **meta,
            "race_date": date,
            "course": venue,
            "race_number": race_no,
            "race_label": race_label(venue, race_no),
            "race_name": meta.get("race_name") or "",
            "numeric_race_id": numeric,
            "entries": entries,
        }

    def get_race_board(self, race_id: str, *, include_history: bool = False) -> dict[str, Any]:
        """Web GUI: 出馬表 + オッズ（entries_full）。optional 近走。"""
        from . import cache_metrics

        rid = str(race_id).strip()
        t0 = time.monotonic()
        # 近走なし board は 5 分キャッシュ（クライアント 5 分ポーリングと揃えて netkeiba 連打を防ぐ）
        if not include_history and rid in _board_cache:
            ts, cached = _board_cache[rid]
            if time.monotonic() - ts < _BOARD_CACHE_TTL_SEC:
                out = dict(cached)
                out["entries"] = [dict(e) for e in (cached.get("entries") or [])]
                cache_metrics.note_board(hit=True, ms=(time.monotonic() - t0) * 1000)
                return out

        ref = self.resolve_race_ref(rid)
        numeric = str(ref.get("numeric_race_id") or "").strip()
        if not numeric:
            raise RaceNotFoundError(
                "no_numeric_id",
                f"numeric_race_id missing for race_id={rid}",
            )
        full = self.entries_full(
            date=ref["race_date"],
            venue=ref["course"],
            race_no=int(ref["race_number"]),
            numeric_race_id=numeric,
        )
        entries = list(full.get("entries") or [])
        odds_rows, odds_status = self._load_win_odds(
            numeric_race_id=numeric,
            shutuba_html=None,
        )
        if not odds_rows:
            try:
                html = self.client.fetch_shutuba(numeric)
                odds_rows, odds_status = self._load_win_odds(
                    numeric_race_id=numeric,
                    shutuba_html=html,
                    force=True,
                )
            except Exception as exc:
                print(f"[pi-keibanet] board odds shutuba fallback skipped: {exc}")

        by_num = {int(o["horse_number"]): o for o in odds_rows if o.get("horse_number") is not None}
        for e in entries:
            hn = e.get("horse_number")
            hit = by_num.get(int(hn)) if hn is not None else None
            if hit:
                e["odds"] = hit.get("win")
                if hit.get("popularity") is not None:
                    e["popularity"] = hit.get("popularity")
            else:
                if e.get("odds") in (99.9, "99.9"):
                    e["odds"] = None

        with_odds = [e for e in entries if e.get("odds") is not None]
        if with_odds and all(e.get("popularity") is None for e in with_odds):
            ranked = sorted(with_odds, key=lambda x: float(x["odds"]))
            for i, e in enumerate(ranked, start=1):
                e["popularity"] = i

        payload: dict[str, Any] = {
            "schema_version": "expect-race-board/1.0",
            "race_id": ref["race_id"],
            "race_label": ref.get("race_label") or race_label(ref["course"], int(ref["race_number"])),
            "race_name": full.get("race_name") or ref.get("race_name") or "",
            "date": ref["race_date"],
            "venue": ref["course"],
            "race_no": int(ref["race_number"]),
            "post_time": ref.get("post_time") or full.get("post_time"),
            "entries": entries,
            "count": len(entries),
            "numeric_race_id": numeric,
            "odds_status": odds_status,
            "odds_cache_ttl_sec": int(_ODDS_CACHE_TTL_SEC),
        }
        if not include_history:
            _board_cache[rid] = (
                time.monotonic(),
                {**payload, "entries": [dict(e) for e in entries]},
            )
            from . import cache_metrics

            cache_metrics.note_board(hit=False, ms=(time.monotonic() - t0) * 1000)
        if include_history:
            payload["history"] = self._history_grouped(
                entries,
                race_context={
                    "date": ref["race_date"],
                    "venue": ref["course"],
                    "race_no": int(ref["race_number"]),
                    "race_id": ref["race_id"],
                    "numeric_race_id": numeric,
                    "race_name": payload["race_name"],
                },
                limit=3,
            )
        return payload

    def get_race_history(self, race_id: str, *, limit: int = 3) -> dict[str, Any]:
        """Web GUI: 各馬の近走。Version7.4 CSV/DB First → Live fallback。"""
        from . import cache_metrics
        from .history_store import default_history_store

        t0 = time.monotonic()
        board = self.get_race_board(race_id, include_history=False)
        day = str(board.get("date") or "").strip()
        rid = str(board.get("race_id") or race_id).strip()
        entries = list(board.get("entries") or [])
        race_context = {
            "date": board.get("date"),
            "venue": board.get("venue"),
            "race_no": board.get("race_no"),
            "race_id": board.get("race_id"),
            "numeric_race_id": board.get("numeric_race_id"),
            "race_name": board.get("race_name"),
        }

        store = default_history_store()
        static_rows, source = store.resolve_static(rid, date=day)
        if static_rows is not None:
            history = self._history_grouped_from_rows(
                static_rows, entries=entries, limit=limit
            )
            cache_metrics.note_history(hit=True, ms=(time.monotonic() - t0) * 1000)
            cache_metrics.note_history_source(source)
            print(
                f"[pi-keibanet] history source={source} race_id={rid} "
                f"horses={len(history)} rows={len(static_rows)}"
            )
            hist_source = source
        else:
            history = self._history_grouped(
                entries, race_context=race_context, limit=limit
            )
            cache_metrics.note_history_source("live")
            print(
                f"[pi-keibanet] history source=live race_id={rid} "
                f"reason={source} horses={len(history)}"
            )
            hist_source = "live"

        return {
            "schema_version": "expect-race-history/1.0",
            "race_id": board.get("race_id"),
            "race_label": board.get("race_label"),
            "race_name": board.get("race_name"),
            "date": board.get("date"),
            "venue": board.get("venue"),
            "race_no": board.get("race_no"),
            "numeric_race_id": board.get("numeric_race_id"),
            "history": history,
            "count": len(history),
            "history_source": hist_source,
        }

    def _history_grouped_from_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        entries: list[dict[str, Any]] | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """CSV/DB rows → GUI history buckets（契約維持）。"""
        by_key: dict[str, dict[str, Any]] = {}

        def date_key(val: Any) -> int:
            s = str(val or "")
            m = re.search(r"(\d{2,4})[/\-](\d{1,2})[/\-](\d{1,2})", s)
            if not m:
                return 0
            year = int(m.group(1))
            if year < 100:
                year += 2000
            return year * 10000 + int(m.group(2)) * 100 + int(m.group(3))

        def ensure_bucket(
            horse_id: str,
            horse_number: Any,
            horse_name: str,
        ) -> dict[str, Any]:
            key = horse_id or (f"n:{horse_number}" if horse_number is not None else "")
            if not key:
                return {}
            if key not in by_key:
                by_key[key] = {
                    "horse_id": horse_id or None,
                    "horse_number": horse_number,
                    "horse_name": horse_name or "—",
                    "recent": [],
                }
            return by_key[key]

        for entry in entries or []:
            ensure_bucket(
                str(entry.get("horse_id") or "").strip(),
                entry.get("horse_number"),
                str(entry.get("horse_name") or "") or "—",
            )

        for row in rows:
            horse_id = str(row.get("horse_id") or "").strip()
            horse_number = row.get("horse_number")
            try:
                if horse_number is not None and str(horse_number).strip() != "":
                    horse_number = int(float(str(horse_number)))
            except (TypeError, ValueError):
                pass
            bucket = ensure_bucket(
                horse_id,
                horse_number,
                str(row.get("horse_name") or "") or "—",
            )
            if not bucket:
                continue
            if (not bucket.get("horse_name") or bucket["horse_name"] == "—") and row.get(
                "horse_name"
            ):
                bucket["horse_name"] = str(row.get("horse_name"))
            finish = row.get("history_finish")
            try:
                if finish is not None and str(finish).strip() != "":
                    finish = int(float(str(finish)))
            except (TypeError, ValueError):
                pass
            distance = row.get("history_distance")
            try:
                if distance is not None and str(distance).strip() != "":
                    distance = int(float(str(distance)))
            except (TypeError, ValueError):
                pass
            bucket["recent"].append(
                {
                    "date": row.get("history_date"),
                    "place": row.get("history_place"),
                    "race_name": row.get("history_race_name"),
                    "finish": finish,
                    "odds": row.get("history_odds"),
                    "distance": distance,
                    "surface": row.get("history_surface"),
                    "last3f": row.get("history_last3f"),
                    "_sort": date_key(row.get("history_date")),
                }
            )

        out: list[dict[str, Any]] = []
        for bucket in by_key.values():
            recent = sorted(
                bucket["recent"], key=lambda r: int(r.get("_sort") or 0), reverse=True
            )
            bucket["recent"] = [
                {k: v for k, v in r.items() if k != "_sort"} for r in recent[:limit]
            ]
            out.append(bucket)
        out.sort(key=lambda b: int(b.get("horse_number") or 99))
        return out

    def _history_grouped(
        self,
        entries: list[dict[str, Any]],
        *,
        race_context: dict[str, Any] | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        rows = self.horse_history(entries=entries, race_context=race_context)
        return self._history_grouped_from_rows(rows, entries=entries, limit=limit)

    def horse_history(
        self,
        *,
        entries: list[dict[str, Any]],
        race_context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Live netkeiba fetch — History API fallback / pipeline 用。"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        from . import cache_metrics

        targets: list[dict[str, Any]] = []
        for entry in entries:
            horse_id = str(entry.get("horse_id", "")).strip()
            if horse_id:
                targets.append(entry)
        if not targets:
            return []

        def fetch_one(entry: dict[str, Any]) -> list[dict[str, Any]]:
            horse_id = str(entry.get("horse_id", "")).strip()
            now = time.monotonic()
            t0 = now
            cached = _horse_history_cache.get(horse_id)
            if cached and now - cached[0] < _HORSE_HISTORY_TTL_SEC:
                parsed = cached[1]
                cache_metrics.note_history(hit=True, ms=(time.monotonic() - t0) * 1000)
            else:
                worker = NetkeibaClient(
                    timeout=getattr(self.client, "timeout", 25),
                    min_interval_sec=0.15,
                )
                try:
                    parsed = fetch_horse_history(worker, horse_id)
                except NetkeibaFetchError as exc:
                    print(
                        f"[pi-keibanet] horse_history fetch failed: horse_id={horse_id}: {exc}"
                    )
                    cache_metrics.note_history(hit=False, ms=(time.monotonic() - t0) * 1000)
                    cache_metrics.note_history_source("fail")
                    return []
                _horse_history_cache[horse_id] = (time.monotonic(), parsed)
                cache_metrics.note_history(hit=False, ms=(time.monotonic() - t0) * 1000)
            runner = {**entry}
            if race_context:
                runner.update(race_context)
            return build_history_rows(runner, parsed)

        workers = max(1, min(_HORSE_HISTORY_WORKERS, len(targets)))
        all_rows: list[dict[str, Any]] = []
        if workers == 1:
            for entry in targets:
                all_rows.extend(fetch_one(entry))
            return all_rows

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(fetch_one, entry) for entry in targets]
            for fut in as_completed(futures):
                try:
                    all_rows.extend(fut.result() or [])
                except Exception as exc:  # pragma: no cover
                    print(f"[pi-keibanet] horse_history worker failed: {exc}")
        return all_rows

    def get_horse_number_integrity(self, date: str = "") -> dict[str, Any]:
        """Ops Health: Horse Number Integrity from latest report and/or runners.csv."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from .horse_number_integrity import (
            load_integrity_report,
            validate_runners_horse_number_integrity,
            write_integrity_report,
        )
        from .race_refresh import RefreshConfig

        cfg = RefreshConfig.from_env()
        jst = ZoneInfo("Asia/Tokyo")
        day = (date or "").strip() or datetime.now(jst).date().isoformat()
        latest = cfg.state_root / day / "logs" / "horse_number_integrity_latest.json"
        report = load_integrity_report(latest)
        runners_path = cfg.state_root / day / "runners.csv"
        live = None
        if runners_path.is_file():
            import pandas as pd

            runners_df = pd.read_csv(runners_path, encoding="utf-8-sig")
            live_obj = validate_runners_horse_number_integrity(runners_df, date=day)
            live = live_obj.to_dict()
            if report is None:
                write_integrity_report(live_obj, latest)
                report = live

        ok = True
        if live is not None:
            ok = bool(live.get("ok"))
        elif report is not None:
            ok = bool(report.get("ok"))
        else:
            ok = True  # no race day data yet

        return {
            "check": "Horse Number Integrity",
            "ok": ok,
            "date": day,
            "report_path": str(latest) if latest.is_file() else "",
            "latest_report": report,
            "live_runners": live,
        }


__all__ = ["NetkeibaFetchError", "PiKeibaNetService", "RaceNotFoundError"]
