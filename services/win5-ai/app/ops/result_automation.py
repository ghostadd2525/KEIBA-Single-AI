# -*- coding: utf-8 -*-
"""
Result Automation Orchestrator — State Machine pipeline (Production).

改善アルゴリズムは実行しない。Improvement Evidence のみ出力。
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data import db as app_db
from . import state_machine as sm
from .evidence.base import atomic_write_json
from .evidence.registry import build_event
from .miss_evidence import (
    classify_miss,
    hit_flags_from_runners,
    winner_name_from_result,
)
from .race_context import apply_context_to_result_row, extract_race_context
from .result_providers import ResultProvider, RaceResultRow, default_provider

_service: "ResultAutomationService | None" = None
PIPELINE_VERSION = "ops-result-automation/1.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root() -> Path:
    # services/win5-ai
    return Path(__file__).resolve().parents[2]


def improvement_root() -> Path:
    raw = os.environ.get("EXPECT_IMPROVEMENT_EVIDENCE_DIR")
    if raw:
        return Path(raw)
    # prefer repo evidence/improvement when present
    git_path = repo_root().parents[0] / "evidence" / "improvement"
    if (repo_root().parents[0] / "evidence").is_dir():
        return git_path
    return repo_root() / "var" / "improvement-evidence"


def legacy_miss_root() -> Path:
    raw = os.environ.get("EXPECT_MISS_EVIDENCE_DIR")
    if raw:
        return Path(raw)
    git_miss = repo_root().parents[0] / "evidence" / "miss"
    if (repo_root().parents[0] / "evidence").is_dir():
        return git_miss
    return repo_root() / "var" / "miss-evidence"


def miss_evidence_dir() -> Path:
    """Backward-compatible alias."""
    return legacy_miss_root()


class ResultAutomationService:
    def __init__(self, provider: ResultProvider | None = None):
        self.provider = provider or default_provider()

    def run(
        self,
        race_date: str,
        *,
        trigger: str = sm.TRIGGER_MANUAL,
        trigger_source: str | None = None,
        parent_run_id: int | None = None,
        force: bool = False,
        skip_result_sync: bool = False,
        evidence_only: bool = False,
        max_attempts: int = 5,
    ) -> dict[str, Any]:
        trigger_n = sm.normalize_trigger(trigger_source or trigger)
        conn = app_db.connect()
        run_id: int | None = None
        try:
            if force:
                self._supersede_active(conn, race_date)
            elif self._has_active(conn, race_date):
                raise RuntimeError(
                    f"active run exists for {race_date}; use force=True to supersede"
                )

            run_id = self._create_run(
                conn,
                race_date=race_date,
                trigger=trigger_n,
                parent_run_id=parent_run_id,
                max_attempts=max_attempts,
            )
            conn.commit()

            queued_events: list[dict[str, Any]] = []
            warnings: list[str] = []
            hits = misses = evaluated = 0
            sync_rows: list[RaceResultRow] = []

            if evidence_only:
                self._set_status(conn, run_id, sm.PENDING, sm.EVIDENCE_EXPORTING)
                conn.commit()
                # rebuild events from latest evaluations for this date
                queued_events = self._events_from_existing_evals(conn, race_date)
            else:
                # ① PENDING → RESULT_SYNCING
                self._set_status(conn, run_id, sm.PENDING, sm.RESULT_SYNCING)
                conn.commit()

                if skip_result_sync:
                    sync_rows = self._load_existing_results(conn, race_date)
                    if not sync_rows:
                        warnings.append("skip_result_sync but no race_results")
                else:
                    try:
                        sync_rows = self.provider.fetch(race_date)
                        sync_rows = self._enrich_sync_rows(conn, sync_rows)
                        self._upsert_results(conn, sync_rows)
                        conn.commit()
                    except Exception as exc:
                        existing = self._load_existing_results(conn, race_date)
                        if existing:
                            warnings.append(f"result_sync_degraded:{exc}")
                            queued_events.append(
                                {
                                    "event_type": "result_sync_failed",
                                    "ctx": {
                                        "race_date": race_date,
                                        "error": str(exc),
                                        "attempt": self._get_attempt(conn, run_id),
                                        "provider": type(self.provider).__name__,
                                    },
                                }
                            )
                        else:
                            self._set_status(
                                conn,
                                run_id,
                                sm.RESULT_SYNCING,
                                sm.RESULT_SYNC_FAILED,
                                error=str(exc),
                            )
                            conn.commit()
                            attempt = self._get_attempt(conn, run_id)
                            queued_events.append(
                                {
                                    "event_type": "result_sync_failed",
                                    "ctx": {
                                        "race_date": race_date,
                                        "error": str(exc),
                                        "attempt": attempt,
                                        "provider": type(self.provider).__name__,
                                    },
                                }
                            )
                            self._set_status(
                                conn, run_id, sm.RESULT_SYNC_FAILED, sm.EVIDENCE_EXPORTING
                            )
                            conn.commit()
                            written = self._export_evidence(
                                conn, run_id, race_date, queued_events
                            )
                            final = sm.FAILED
                            self._write_manifests(
                                run_id,
                                race_date,
                                status=final,
                                trigger=trigger_n,
                                parent_run_id=parent_run_id,
                                event_counts=written["counts"],
                                hits=0,
                                misses=0,
                                evaluated=0,
                                warnings=[str(exc)],
                            )
                            self._set_status(
                                conn,
                                run_id,
                                sm.EVIDENCE_EXPORTING,
                                final,
                                error=str(exc),
                            )
                            conn.commit()
                            return self._result_payload(
                                run_id,
                                race_date,
                                final,
                                hits=0,
                                misses=0,
                                evaluated=0,
                                event_counts=written["counts"],
                                warnings=[str(exc)],
                            )

                # PREDICTION_MATCHING
                self._set_status(conn, run_id, sm.RESULT_SYNCING, sm.PREDICTION_MATCHING)
                conn.commit()

                results = self._load_existing_results(conn, race_date)
                if not results:
                    warnings.append("no race_results after sync")

                matched: list[dict[str, Any]] = []
                for row in results:
                    race_id = row["race_id"]
                    pred = conn.execute(
                        """
                        SELECT id, engine_source, fallback_reason, model_version, bundle_json
                        FROM predictions WHERE race_id=?
                        ORDER BY created_at DESC, id DESC LIMIT 1
                        """,
                        (race_id,),
                    ).fetchone()
                    if not pred:
                        queued_events.append(
                            {
                                "event_type": "prediction_failed",
                                "ctx": {
                                    "race_id": race_id,
                                    "race_date": race_date,
                                    "reason": "prediction_missing",
                                },
                            }
                        )
                        warnings.append(f"prediction_missing:{race_id}")
                        continue
                    try:
                        bundle = json.loads(pred["bundle_json"])
                    except (json.JSONDecodeError, TypeError):
                        queued_events.append(
                            {
                                "event_type": "prediction_failed",
                                "ctx": {
                                    "race_id": race_id,
                                    "race_date": race_date,
                                    "reason": "bundle_invalid",
                                    "engine_source": pred["engine_source"],
                                },
                            }
                        )
                        warnings.append(f"bundle_invalid:{race_id}")
                        continue

                    fb = pred["fallback_reason"] or ""
                    feat = ((bundle.get("explain") or {}).get("meta") or {}).get(
                        "feature_source"
                    )
                    feature_signals = fb in (
                        "market_feature_missing",
                        "feature_missing",
                        "platform_missing",
                    ) or (
                        isinstance(feat, str)
                        and ("missing" in feat.lower() or feat.lower() == "none")
                    )
                    if feature_signals:
                        queued_events.append(
                            {
                                "event_type": "feature_missing",
                                "ctx": {
                                    "race_id": race_id,
                                    "race_date": race_date,
                                    "fallback_reason": fb,
                                    "feature_source": feat,
                                    "engine_source": pred["engine_source"],
                                    "model_version": pred["model_version"],
                                },
                            }
                        )

                    matched.append(
                        {
                            "result": row,
                            "pred": pred,
                            "bundle": bundle,
                        }
                    )

                # EVALUATING
                self._set_status(conn, run_id, sm.PREDICTION_MATCHING, sm.EVALUATING)
                conn.commit()

                for item in matched:
                    row = item["result"]
                    pred = item["pred"]
                    bundle = item["bundle"]
                    race_id = row["race_id"]
                    ctx = extract_race_context(result=row, bundle=bundle)
                    row = apply_context_to_result_row(row, ctx)
                    if ctx:
                        self._patch_result_context(conn, race_id, ctx)
                    runners = ((bundle.get("evaluation") or {}).get("runners")) or []
                    winner_n = row["winner_horse_number"]
                    hit_at_1, hit_at_3, hit_at_5 = hit_flags_from_runners(
                        runners, winner_n
                    )
                    evaluated += 1
                    miss_cat = classify_miss(
                        hit_at_1=hit_at_1, hit_at_3=hit_at_3, hit_at_5=hit_at_5
                    )
                    if hit_at_1:
                        hits += 1
                    else:
                        misses += 1

                    conn.execute(
                        """
                        INSERT INTO race_evaluations(
                          run_id, race_id, prediction_id, race_date, venue,
                          hit_at_1, hit_at_3, hit_at_5, miss_category,
                          engine_source, model_version, evaluated_at, meta_json
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            run_id,
                            race_id,
                            pred["id"],
                            race_date,
                            row.get("venue"),
                            1 if hit_at_1 else 0,
                            1 if hit_at_3 else 0,
                            1 if hit_at_5 else 0,
                            miss_cat,
                            pred["engine_source"],
                            pred["model_version"],
                            _now(),
                            json.dumps(
                                {
                                    "trigger": trigger_n,
                                    "surface": row.get("surface"),
                                    "distance": row.get("distance"),
                                    "going": row.get("going"),
                                },
                                ensure_ascii=False,
                            ),
                        ),
                    )

                    if miss_cat:
                        queued_events.append(
                            {
                                "event_type": "miss",
                                "ctx": {
                                    "race_id": race_id,
                                    "race_date": race_date,
                                    "bundle": bundle,
                                    "meta": {
                                        "engine_source": pred["engine_source"],
                                        "fallback_reason": pred["fallback_reason"],
                                        "model_version": pred["model_version"],
                                    },
                                    "winner_horse_number": winner_n,
                                    "winner_name": winner_name_from_result(
                                        row.get("result_json")
                                    ),
                                    "hit_at_1": hit_at_1,
                                    "hit_at_3": hit_at_3,
                                    "hit_at_5": hit_at_5,
                                },
                            }
                        )
                conn.commit()

                # STATS_UPDATING
                self._set_status(conn, run_id, sm.EVALUATING, sm.STATS_UPDATING)
                conn.commit()
                stats_meta = {
                    "hits": hits,
                    "misses": misses,
                    "evaluated": evaluated,
                    "hit_at_1_rate": round(hits / evaluated, 4) if evaluated else None,
                }
                # lightweight stats snapshot in run meta (aggregates table optional)
                self._patch_run_meta(conn, run_id, {"stats": stats_meta})
                conn.commit()

                # SELF_EVAL_UPDATING
                self._set_status(conn, run_id, sm.STATS_UPDATING, sm.SELF_EVAL_UPDATING)
                conn.commit()
                self_eval_id = self._write_self_eval(
                    conn,
                    race_date=race_date,
                    trigger=trigger_n,
                    evaluated=evaluated,
                    hits=hits,
                    misses=misses,
                    hit_at_1_rate=stats_meta["hit_at_1_rate"],
                )
                conn.execute(
                    "UPDATE result_automation_runs SET self_eval_run_id=? WHERE id=?",
                    (self_eval_id, run_id),
                )
                conn.commit()

                self._set_status(
                    conn, run_id, sm.SELF_EVAL_UPDATING, sm.EVIDENCE_EXPORTING
                )
                conn.commit()

            written = self._export_evidence(conn, run_id, race_date, queued_events)
            final = sm.COMPLETED
            if warnings or any(
                written["counts"].get(k, 0) > 0
                for k in ("prediction_failed", "feature_missing", "result_sync_failed")
            ):
                final = sm.DEGRADED
            if evaluated == 0 and not evidence_only:
                final = sm.DEGRADED
                warnings.append("zero_evaluated")

            self._write_manifests(
                run_id,
                race_date,
                status=final,
                trigger=trigger_n,
                parent_run_id=parent_run_id,
                event_counts=written["counts"],
                hits=hits,
                misses=misses,
                evaluated=evaluated,
                warnings=warnings,
            )
            self._set_status(conn, run_id, sm.EVIDENCE_EXPORTING, final)
            conn.commit()

            return self._result_payload(
                run_id,
                race_date,
                final,
                hits=hits,
                misses=misses,
                evaluated=evaluated,
                event_counts=written["counts"],
                warnings=warnings,
            )
        except Exception as exc:
            if run_id is not None:
                try:
                    cur = conn.execute(
                        "SELECT status FROM result_automation_runs WHERE id=?",
                        (run_id,),
                    ).fetchone()
                    cur_status = cur["status"] if cur else sm.PENDING
                    if cur_status not in sm.TERMINAL:
                        # best-effort fail transition
                        try:
                            if sm.can_transition(cur_status, sm.FAILED):
                                self._set_status(
                                    conn, run_id, cur_status, sm.FAILED, error=str(exc)
                                )
                            else:
                                conn.execute(
                                    """
                                    UPDATE result_automation_runs
                                    SET status=?, error_json=?, finished_at=?
                                    WHERE id=?
                                    """,
                                    (
                                        sm.FAILED,
                                        json.dumps({"error": str(exc)}),
                                        _now(),
                                        run_id,
                                    ),
                                )
                        except Exception:
                            conn.execute(
                                """
                                UPDATE result_automation_runs
                                SET status=?, error_json=?, finished_at=?
                                WHERE id=?
                                """,
                                (
                                    sm.FAILED,
                                    json.dumps({"error": str(exc)}),
                                    _now(),
                                    run_id,
                                ),
                            )
                        conn.commit()
                except Exception:
                    pass
            raise
        finally:
            conn.close()

    # --- run management ---

    def _create_run(
        self,
        conn: Any,
        *,
        race_date: str,
        trigger: str,
        parent_run_id: int | None,
        max_attempts: int,
    ) -> int:
        attempt = 1
        if parent_run_id:
            prow = conn.execute(
                "SELECT attempt FROM result_automation_runs WHERE id=?",
                (parent_run_id,),
            ).fetchone()
            if prow:
                attempt = int(prow["attempt"] or 1) + 1
        cur = conn.execute(
            """
            INSERT INTO result_automation_runs(
              race_date, status, trigger, parent_run_id, attempt, max_attempts,
              started_at, meta_json
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                race_date,
                sm.PENDING,
                trigger,
                parent_run_id,
                attempt,
                max_attempts,
                _now(),
                json.dumps({"pipeline": PIPELINE_VERSION}, ensure_ascii=False),
            ),
        )
        return int(cur.lastrowid)

    def _has_active(self, conn: Any, race_date: str) -> bool:
        row = conn.execute(
            f"""
            SELECT id FROM result_automation_runs
            WHERE race_date=? AND status IN ({",".join("?" * len(sm.ACTIVE))})
            LIMIT 1
            """,
            (race_date, *sm.ACTIVE),
        ).fetchone()
        return row is not None

    def _supersede_active(self, conn: Any, race_date: str) -> None:
        conn.execute(
            f"""
            UPDATE result_automation_runs
            SET status=?, finished_at=?
            WHERE race_date=? AND status IN ({",".join("?" * len(sm.ACTIVE))})
            """,
            (sm.SUPERSEDED, _now(), race_date, *sm.ACTIVE),
        )

    def _get_attempt(self, conn: Any, run_id: int) -> int:
        row = conn.execute(
            "SELECT attempt FROM result_automation_runs WHERE id=?", (run_id,)
        ).fetchone()
        return int(row["attempt"] or 1) if row else 1

    def _set_status(
        self,
        conn: Any,
        run_id: int,
        current: str,
        nxt: str,
        error: str | None = None,
    ) -> None:
        sm.assert_transition(current, nxt)
        finished = _now() if nxt in sm.TERMINAL else None
        if error:
            conn.execute(
                """
                UPDATE result_automation_runs
                SET status=?, error_json=?, finished_at=COALESCE(?, finished_at)
                WHERE id=?
                """,
                (nxt, json.dumps({"error": error}, ensure_ascii=False), finished, run_id),
            )
        else:
            conn.execute(
                """
                UPDATE result_automation_runs
                SET status=?, finished_at=COALESCE(?, finished_at)
                WHERE id=?
                """,
                (nxt, finished, run_id),
            )

    def _patch_run_meta(self, conn: Any, run_id: int, patch: dict[str, Any]) -> None:
        row = conn.execute(
            "SELECT meta_json FROM result_automation_runs WHERE id=?", (run_id,)
        ).fetchone()
        meta: dict[str, Any] = {}
        if row and row["meta_json"]:
            try:
                meta = json.loads(row["meta_json"])
            except json.JSONDecodeError:
                meta = {}
        meta.update(patch)
        conn.execute(
            "UPDATE result_automation_runs SET meta_json=? WHERE id=?",
            (json.dumps(meta, ensure_ascii=False), run_id),
        )

    # --- results ---

    def _enrich_sync_rows(self, conn: Any, rows: list[RaceResultRow]) -> list[RaceResultRow]:
        enriched: list[RaceResultRow] = []
        for row in rows:
            pred = conn.execute(
                """
                SELECT bundle_json FROM predictions WHERE race_id=?
                ORDER BY created_at DESC, id DESC LIMIT 1
                """,
                (row.race_id,),
            ).fetchone()
            bundle = None
            if pred:
                try:
                    bundle = json.loads(pred["bundle_json"])
                except (json.JSONDecodeError, TypeError):
                    bundle = None
            ctx = extract_race_context(
                result={
                    "surface": row.surface,
                    "distance": row.distance,
                    "going": row.going,
                },
                bundle=bundle,
                extra=row.extra,
            )
            enriched.append(
                RaceResultRow(
                    race_id=row.race_id,
                    race_date=row.race_date,
                    venue=row.venue,
                    winner_horse_number=row.winner_horse_number,
                    field_size=row.field_size,
                    winner_name=row.winner_name,
                    source=row.source,
                    extra=row.extra,
                    surface=ctx.get("surface") or row.surface,
                    distance=ctx.get("distance") or row.distance,
                    going=ctx.get("going") or row.going,
                )
            )
        return enriched

    def _patch_result_context(self, conn: Any, race_id: str, ctx: dict[str, Any]) -> None:
        if not ctx:
            return
        conn.execute(
            """
            UPDATE race_results SET
              surface=COALESCE(?, surface),
              distance=COALESCE(?, distance),
              going=COALESCE(?, going)
            WHERE race_id=?
            """,
            (
                ctx.get("surface"),
                ctx.get("distance"),
                ctx.get("going"),
                race_id,
            ),
        )

    def _upsert_results(self, conn: Any, rows: list[RaceResultRow]) -> None:
        for r in rows:
            conn.execute(
                """
                INSERT INTO race_results(
                  race_id, race_date, venue, surface, distance, going,
                  winner_horse_number, field_size,
                  result_json, source, finalized_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(race_id) DO UPDATE SET
                  race_date=excluded.race_date,
                  venue=excluded.venue,
                  surface=COALESCE(excluded.surface, race_results.surface),
                  distance=COALESCE(excluded.distance, race_results.distance),
                  going=COALESCE(excluded.going, race_results.going),
                  winner_horse_number=excluded.winner_horse_number,
                  field_size=excluded.field_size,
                  result_json=excluded.result_json,
                  source=excluded.source,
                  finalized_at=excluded.finalized_at
                """,
                (
                    r.race_id,
                    r.race_date,
                    r.venue,
                    r.surface,
                    r.distance,
                    r.going,
                    r.winner_horse_number,
                    r.field_size,
                    json.dumps(
                        {
                            "winner_name": r.winner_name,
                            "surface": r.surface,
                            "distance": r.distance,
                            "going": r.going,
                            **(r.extra or {}),
                        },
                        ensure_ascii=False,
                    ),
                    r.source,
                    _now(),
                ),
            )

    def _load_existing_results(self, conn: Any, race_date: str) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT race_id, race_date, venue, surface, distance, going,
                   winner_horse_number, field_size,
                   result_json, source, finalized_at
            FROM race_results WHERE race_date=? ORDER BY race_id
            """,
            (race_date,),
        ).fetchall()
        return [dict(r) for r in rows]

    def _write_self_eval(
        self,
        conn: Any,
        *,
        race_date: str,
        trigger: str,
        evaluated: int,
        hits: int,
        misses: int,
        hit_at_1_rate: float | None,
    ) -> int:
        cur = conn.execute(
            """
            INSERT INTO self_evaluation_runs(
              race_date, trigger_source, status, races_evaluated, hits, misses,
              hit_at_1_rate, created_at, finished_at, meta_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                race_date,
                trigger,
                "success",
                evaluated,
                hits,
                misses,
                hit_at_1_rate,
                _now(),
                _now(),
                json.dumps({"pipeline": PIPELINE_VERSION}, ensure_ascii=False),
            ),
        )
        return int(cur.lastrowid)

    # --- evidence ---

    def _export_evidence(
        self,
        conn: Any,
        run_id: int,
        race_date: str,
        queued: list[dict[str, Any]],
    ) -> dict[str, Any]:
        counts: dict[str, int] = {}
        files: list[dict[str, str]] = []
        imp_root = improvement_root()
        miss_root = legacy_miss_root()

        for item in queued:
            et = item["event_type"]
            ctx = dict(item["ctx"])
            ctx.setdefault("race_date", race_date)
            env = build_event(et, ctx)
            if not env:
                continue
            counts[et] = counts.get(et, 0) + 1
            race_id = env.get("race_id") or race_date
            rel = f"{et}/{race_date}/{race_id}.json"
            dest = imp_root / et / race_date / f"{race_id}.json"
            atomic_write_json(dest, env)

            # dual-write miss → evidence/miss (legacy payload for Cursor transition)
            if et == "miss":
                legacy_path = miss_root / race_date / f"{race_id}.json"
                payload = env.get("payload") or env
                atomic_write_json(legacy_path, payload)

            conn.execute(
                """
                INSERT OR REPLACE INTO improvement_evidence_index(
                  event_id, event_type, race_id, race_date, fingerprint,
                  path, run_id, created_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    env["event_id"],
                    et,
                    env.get("race_id"),
                    race_date,
                    env.get("fingerprint"),
                    str(dest),
                    run_id,
                    _now(),
                ),
            )
            files.append({"event_type": et, "path": rel, "event_id": env["event_id"]})

        # legacy miss day manifest
        miss_day = miss_root / race_date
        miss_day.mkdir(parents=True, exist_ok=True)
        atomic_write_json(
            miss_day / "manifest.json",
            {
                "schema_version": "expect-miss-evidence-manifest/1.0",
                "race_date": race_date,
                "exported_at": _now(),
                "misses": counts.get("miss", 0),
                "files": [f["path"] for f in files if f["event_type"] == "miss"],
                "canonical": "evidence/improvement",
            },
        )
        conn.commit()
        return {"counts": counts, "files": files}

    def _events_from_existing_evals(
        self, conn: Any, race_date: str
    ) -> list[dict[str, Any]]:
        # evidence-only: emit miss events from evaluations lacking hit_at_1
        rows = conn.execute(
            """
            SELECT e.*, p.bundle_json, p.engine_source, p.fallback_reason, p.model_version,
                   r.result_json, r.winner_horse_number
            FROM race_evaluations e
            LEFT JOIN predictions p ON p.id = e.prediction_id
            LEFT JOIN race_results r ON r.race_id = e.race_id
            WHERE e.race_date=? AND e.hit_at_1=0
            """,
            (race_date,),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                bundle = json.loads(row["bundle_json"] or "{}")
            except json.JSONDecodeError:
                continue
            out.append(
                {
                    "event_type": "miss",
                    "ctx": {
                        "race_id": row["race_id"],
                        "race_date": race_date,
                        "bundle": bundle,
                        "meta": {
                            "engine_source": row["engine_source"],
                            "fallback_reason": row["fallback_reason"],
                            "model_version": row["model_version"],
                        },
                        "winner_horse_number": row["winner_horse_number"],
                        "winner_name": winner_name_from_result(row["result_json"]),
                        "hit_at_1": False,
                        "hit_at_3": bool(row["hit_at_3"]),
                        "hit_at_5": bool(row["hit_at_5"]),
                    },
                }
            )
        return out

    def _write_manifests(
        self,
        run_id: int,
        race_date: str,
        *,
        status: str,
        trigger: str,
        parent_run_id: int | None,
        event_counts: dict[str, int],
        hits: int,
        misses: int,
        evaluated: int,
        warnings: list[str],
    ) -> None:
        base = improvement_root() / "manifest" / race_date
        base.mkdir(parents=True, exist_ok=True)
        total_events = sum(event_counts.values())
        run_doc = {
            "schema_version": "expect-result-automation-run/1.0",
            "run_id": run_id,
            "race_date": race_date,
            "status": status,
            "trigger": trigger,
            "parent_run_id": parent_run_id,
            "pipeline_version": PIPELINE_VERSION,
            "finished_at": _now(),
            "warnings": warnings,
        }
        summary = {
            "schema_version": "expect-result-automation-summary/1.0",
            "run_id": run_id,
            "status": status,
            "race_date": race_date,
            "event_counts": event_counts,
            "event_total": total_events,
            "hits": hits,
            "misses": misses,
            "races_evaluated": evaluated,
        }
        index = {
            "schema_version": "expect-result-automation-index/1.0",
            "race_date": race_date,
            "run_id": run_id,
            "paths": {
                et: f"{et}/{race_date}/"
                for et in sorted(event_counts.keys())
            },
            "manifest": {
                "run": f"manifest/{race_date}/run.json",
                "summary": f"manifest/{race_date}/summary.json",
                "index": f"manifest/{race_date}/index.json",
            },
        }
        atomic_write_json(base / "run.json", run_doc)
        atomic_write_json(base / "summary.json", summary)
        atomic_write_json(base / "index.json", index)

    def _result_payload(
        self,
        run_id: int,
        race_date: str,
        status: str,
        *,
        hits: int,
        misses: int,
        evaluated: int,
        event_counts: dict[str, int],
        warnings: list[str],
    ) -> dict[str, Any]:
        # compat aliases for older callers
        ok = status in (sm.COMPLETED, sm.DEGRADED)
        return {
            "status": "success" if status == sm.COMPLETED else status.lower(),
            "run_status": status,
            "run_id": run_id,
            "race_date": race_date,
            "races_evaluated": evaluated,
            "hits": hits,
            "misses_recorded": misses,
            "event_counts": event_counts,
            "warnings": warnings,
            "improvement_root": str(improvement_root()),
            "legacy_miss_root": str(legacy_miss_root()),
            "ok": ok,
        }


def get_result_automation() -> ResultAutomationService:
    global _service
    if _service is None:
        _service = ResultAutomationService()
    return _service
