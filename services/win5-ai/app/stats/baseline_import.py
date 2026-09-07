# -*- coding: utf-8 -*-
"""One-time import of formal research baseline evaluations into race_evaluations.

AI総合実績 = research baseline cumulative + production ResultAutomation cumulative.
Does not change Prediction Engine / Candidate Evaluation.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data import db as app_db

logger = logging.getLogger(__name__)

SETTING_KEY = "baseline_evaluations_imported"
BASELINE_ID = "formal-285r-offline-corpus"
ENGINE_SOURCE = "baseline_import"

# Prefer packaged fixture under services/win5-ai; also repo fixtures/.
_FIXTURE_CANDIDATES = (
    Path(__file__).resolve().parents[2] / "fixtures" / "stats" / "baseline-285r-evaluations.json",
    Path(__file__).resolve().parents[4] / "fixtures" / "stats" / "baseline-285r-evaluations.json",
    Path(__file__).resolve().parents[3] / "fixtures" / "stats" / "baseline-285r-evaluations.json",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_fixture_path(explicit: Path | None = None) -> Path | None:
    if explicit and explicit.is_file():
        return explicit
    for p in _FIXTURE_CANDIDATES:
        if p.is_file():
            return p
    return None


def _get_setting(conn: Any, key: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT value_json FROM app_settings WHERE key=?",
        (key,),
    ).fetchone()
    if not row:
        return None
    raw = row["value_json"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
    try:
        return json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return None


def _set_setting(conn: Any, key: str, value: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO app_settings(key, value_json, updated_at)
        VALUES (?,?,?)
        ON CONFLICT(key) DO UPDATE SET
          value_json=excluded.value_json,
          updated_at=excluded.updated_at
        """,
        (key, json.dumps(value, ensure_ascii=False), _now()),
    )


def is_baseline_imported(conn: Any | None = None) -> bool:
    own = False
    if conn is None:
        conn = app_db.connect()
        own = True
    try:
        flag = _get_setting(conn, SETTING_KEY) or {}
        if flag.get("imported"):
            return True
        row = conn.execute(
            """
            SELECT COUNT(*) AS c FROM race_evaluations
            WHERE engine_source=? OR json_extract(meta_json, '$.source')=?
            """,
            (ENGINE_SOURCE, "baseline_import"),
        ).fetchone()
        return int(row["c"] if row else 0) > 0
    finally:
        if own:
            conn.close()


def import_baseline_evaluations(
    *,
    fixture_path: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Import formal baseline rows once into race_evaluations.

    Skips race_ids that already exist (production ResultAutomation wins).
    """
    app_db.migrate()
    path = resolve_fixture_path(fixture_path)
    if path is None:
        return {
            "ok": False,
            "imported": False,
            "reason": "fixture_not_found",
            "candidates": [str(p) for p in _FIXTURE_CANDIDATES],
        }

    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows") or []
    if not rows:
        return {"ok": False, "imported": False, "reason": "empty_fixture", "path": str(path)}

    conn = app_db.connect()
    try:
        if not force and is_baseline_imported(conn):
            flag = _get_setting(conn, SETTING_KEY) or {}
            return {
                "ok": True,
                "imported": False,
                "already_imported": True,
                "baseline_id": flag.get("baseline_id") or payload.get("baseline_id"),
                "path": str(path),
                "existing_baseline_rows": flag.get("inserted"),
            }

        # Ensure self_evaluation_runs row for FK-less provenance
        cur = conn.execute(
            """
            INSERT INTO self_evaluation_runs(
              race_date, trigger_source, status, races_evaluated, hits, misses,
              hit_at_1_rate, created_at, finished_at, meta_json
            ) VALUES (NULL,?,?,?,?,?,?,?,?,?)
            """,
            (
                "baseline_import",
                "success",
                len(rows),
                int(payload.get("hits") or 0),
                len(rows) - int(payload.get("hits") or 0),
                payload.get("hit_rate"),
                _now(),
                _now(),
                json.dumps(
                    {
                        "baseline_id": payload.get("baseline_id") or BASELINE_ID,
                        "evaluation_version": payload.get("evaluation_version"),
                        "fixture": str(path),
                        "one_time_import": True,
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        run_id = int(cur.lastrowid)

        existing = {
            str(r[0])
            for r in conn.execute("SELECT DISTINCT race_id FROM race_evaluations").fetchall()
        }

        inserted = 0
        skipped = 0
        for row in rows:
            rid = str(row.get("race_id") or "")
            if not rid:
                continue
            if rid in existing:
                skipped += 1
                continue
            meta = {
                "source": "baseline_import",
                "baseline_id": payload.get("baseline_id") or BASELINE_ID,
                "evaluation_version": row.get("evaluation_version")
                or payload.get("evaluation_version"),
                "surface": row.get("surface"),
                "distance": row.get("distance"),
                "going": row.get("going"),
                "field_size": row.get("field_size"),
                "predicted_top1_horse_id": row.get("predicted_top1_horse_id"),
                "winner_id": row.get("winner_id"),
                "pe_v2_hit": row.get("pe_v2_hit"),
                "honmei_top1_hit": row.get("honmei_top1_hit"),
                "metric": payload.get("metric") or "formal_v2_pe_baseline_hit",
            }
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
                    rid,
                    None,
                    row.get("race_date"),
                    row.get("venue"),
                    1 if row.get("hit_at_1") else 0,
                    1 if row.get("hit_at_3") else 0,
                    1 if row.get("hit_at_5") else 0,
                    None if row.get("hit_at_1") else "baseline_miss",
                    ENGINE_SOURCE,
                    row.get("evaluation_version") or payload.get("evaluation_version"),
                    _now(),
                    json.dumps(meta, ensure_ascii=False),
                ),
            )
            existing.add(rid)
            inserted += 1

        result = {
            "imported": True,
            "baseline_id": payload.get("baseline_id") or BASELINE_ID,
            "evaluation_version": payload.get("evaluation_version"),
            "fixture": str(path),
            "run_id": run_id,
            "fixture_rows": len(rows),
            "inserted": inserted,
            "skipped_existing": skipped,
            "hits": int(payload.get("hits") or 0),
            "hit_rate": payload.get("hit_rate"),
            "imported_at": _now(),
        }
        _set_setting(conn, SETTING_KEY, {**result, "imported": True})
        conn.commit()
        logger.info("baseline evaluations imported: %s", result)
        return {"ok": True, **result}
    finally:
        conn.close()


def ensure_baseline_imported() -> dict[str, Any]:
    """Idempotent startup hook — import once if missing."""
    try:
        return import_baseline_evaluations(force=False)
    except Exception as exc:
        logger.exception("baseline import failed")
        return {"ok": False, "imported": False, "reason": str(exc)}
