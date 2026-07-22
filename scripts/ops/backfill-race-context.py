#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backfill race_results / race_evaluations with surface, distance, going from predictions."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))

from app.data import db as app_db  # noqa: E402
from app.ops.race_context import apply_context_to_result_row, extract_race_context  # noqa: E402


def backfill(*, dry_run: bool = False) -> dict[str, int]:
    conn = app_db.connect()
    updated_results = 0
    updated_evals = 0
    try:
        rows = conn.execute(
            """
            SELECT race_id, race_date, venue, surface, distance, going, result_json
            FROM race_results
            ORDER BY race_date, race_id
            """
        ).fetchall()
        for row in rows:
            item = dict(row)
            needs = not item.get("surface") or not item.get("distance") or not item.get("going")
            if not needs:
                continue
            pred = conn.execute(
                """
                SELECT bundle_json FROM predictions WHERE race_id=?
                ORDER BY created_at DESC, id DESC LIMIT 1
                """,
                (item["race_id"],),
            ).fetchone()
            if not pred:
                continue
            try:
                bundle = json.loads(pred["bundle_json"])
            except (json.JSONDecodeError, TypeError):
                continue
            ctx = extract_race_context(result=item, bundle=bundle)
            merged = apply_context_to_result_row(item, ctx)
            if (
                merged.get("surface") == item.get("surface")
                and merged.get("distance") == item.get("distance")
                and merged.get("going") == item.get("going")
            ):
                continue
            if not dry_run:
                conn.execute(
                    """
                    UPDATE race_results SET
                      surface=COALESCE(?, surface),
                      distance=COALESCE(?, distance),
                      going=COALESCE(?, going)
                    WHERE race_id=?
                    """,
                    (
                        merged.get("surface"),
                        merged.get("distance"),
                        merged.get("going"),
                        item["race_id"],
                    ),
                )
            updated_results += 1

        eval_rows = conn.execute(
            """
            SELECT id, race_id, meta_json FROM race_evaluations
            ORDER BY id
            """
        ).fetchall()
        for ev in eval_rows:
            meta = {}
            if ev["meta_json"]:
                try:
                    meta = json.loads(ev["meta_json"])
                except json.JSONDecodeError:
                    meta = {}
            if meta.get("going") and meta.get("surface") and meta.get("distance"):
                continue
            result = conn.execute(
                "SELECT surface, distance, going, result_json FROM race_results WHERE race_id=?",
                (ev["race_id"],),
            ).fetchone()
            pred = conn.execute(
                """
                SELECT bundle_json FROM predictions WHERE race_id=?
                ORDER BY created_at DESC, id DESC LIMIT 1
                """,
                (ev["race_id"],),
            ).fetchone()
            bundle = None
            if pred:
                try:
                    bundle = json.loads(pred["bundle_json"])
                except (json.JSONDecodeError, TypeError):
                    bundle = None
            ctx = extract_race_context(
                result=dict(result) if result else None,
                bundle=bundle,
            )
            patch = {
                "surface": ctx.get("surface") or meta.get("surface"),
                "distance": ctx.get("distance") or meta.get("distance"),
                "going": ctx.get("going") or meta.get("going"),
            }
            if not any(patch.values()):
                continue
            meta.update({k: v for k, v in patch.items() if v})
            if not dry_run:
                conn.execute(
                    "UPDATE race_evaluations SET meta_json=? WHERE id=?",
                    (json.dumps(meta, ensure_ascii=False), ev["id"]),
                )
            updated_evals += 1

        if not dry_run:
            conn.commit()
    finally:
        conn.close()
    return {"race_results": updated_results, "race_evaluations": updated_evals}


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill race context for stats heatmap")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    stats = backfill(dry_run=args.dry_run)
    mode = "dry-run" if args.dry_run else "applied"
    print(f"[{mode}] updated race_results={stats['race_results']} race_evaluations={stats['race_evaluations']}")


if __name__ == "__main__":
    main()
