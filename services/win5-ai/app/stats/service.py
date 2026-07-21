# -*- coding: utf-8 -*-
"""STATS-1 — import, recompute, query."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.core_benchmark import load_labeled_races
from ..data.repository import RaceRepository
from .evaluator import distance_bucket, evaluate_bundle_against_result
from .repository import StatsRepository


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pct(num: float, den: int) -> float:
    if den <= 0:
        return 0.0
    return round(num / den, 4)


class StatsService:
    SCHEMA = "expect-stats/1.0"

    def __init__(self) -> None:
        self.repo = StatsRepository()
        self.races = RaceRepository()

    def import_results(
        self,
        *,
        race_date: str | None = None,
        result_paths: list[Path] | None = None,
    ) -> int:
        labels = load_labeled_races(result_paths=result_paths)
        imported = 0
        for rid, label in labels.items():
            if race_date:
                race_row = self.races.get(rid)
                rd = (race_row or {}).get("date")
                if rd and rd != race_date:
                    continue
            meta = self.races.get(rid) or {}
            rd = meta.get("date") or (race_date or "")
            if race_date and rd and rd != race_date:
                continue
            self.repo.upsert_race_result(
                {
                    "race_id": rid,
                    "race_date": rd or race_date or "unknown",
                    "venue": meta.get("venue"),
                    "meeting_id": meta.get("meeting_id"),
                    "surface": meta.get("surface"),
                    "distance": meta.get("distance"),
                    "going": (meta.get("extra_json") and json.loads(meta.get("extra_json") or "{}").get("going"))
                    if isinstance(meta.get("extra_json"), str)
                    else None,
                    "winner_horse_number": label.winner_number,
                    "field_size": label.field_size,
                    "result_json": {
                        "by_number": label.by_number,
                        "winner_name": label.winner_name,
                    },
                    "source": "csv_import",
                }
            )
            imported += 1
        return imported

    def recompute(self, *, trigger_source: str = "manual", race_date: str | None = None) -> dict[str, Any]:
        run_id = self.repo.start_run(trigger_source)
        imported = 0
        evaluated = 0
        try:
            imported = self.import_results(race_date=race_date)
            results = self.repo.list_race_results(race_date=race_date)
            eval_rows: list[dict[str, Any]] = []

            for result in results:
                rid = result["race_id"]
                pred_row = self.repo.latest_prediction_for_race(rid)
                if not pred_row:
                    continue
                try:
                    bundle = json.loads(pred_row["bundle_json"])
                except json.JSONDecodeError:
                    continue

                ev = evaluate_bundle_against_result(
                    bundle,
                    winner_horse_number=result.get("winner_horse_number"),
                )
                info = bundle.get("race_info") or {}
                row = {
                    "race_id": rid,
                    "prediction_id": pred_row.get("id"),
                    "race_date": result.get("race_date") or info.get("date"),
                    "venue": result.get("venue") or info.get("venue"),
                    "meeting_id": result.get("meeting_id") or info.get("meeting_id"),
                    "surface": result.get("surface") or info.get("surface"),
                    "distance": result.get("distance") or info.get("distance"),
                    "going": result.get("going"),
                    "field_size": result.get("field_size") or info.get("field_size"),
                    "winner_horse_number": result.get("winner_horse_number"),
                    "engine_source": pred_row.get("engine_source"),
                    "fallback_reason": pred_row.get("fallback_reason"),
                    "model_version": pred_row.get("model_version"),
                    "feature_source": (bundle.get("explain") or {}).get("meta", {}).get("feature_source"),
                    "evaluated_at": _now(),
                    **ev,
                }
                self.repo.save_race_evaluation(run_id, row)
                eval_rows.append(row)
                evaluated += 1

            aggregates = self._build_aggregates(eval_rows)
            self.repo.replace_aggregates(run_id, aggregates)
            self._update_timeseries(run_id, eval_rows)

            self.repo.finish_run(
                run_id,
                status="success",
                races_imported=imported,
                races_evaluated=evaluated,
                meta={"race_date": race_date},
            )
            return {
                "schema_version": self.SCHEMA,
                "run_id": run_id,
                "status": "success",
                "races_imported": imported,
                "races_evaluated": evaluated,
            }
        except Exception as exc:
            self.repo.finish_run(
                run_id,
                status="failed",
                races_imported=imported,
                races_evaluated=evaluated,
                meta={"error": str(exc)},
            )
            raise

    def _build_aggregates(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

        for row in rows:
            buckets[("overall", "all")].append(row)
            venue = row.get("venue") or "unknown"
            buckets[("venue", venue)].append(row)
            dist = distance_bucket(row.get("distance"))
            buckets[("distance", dist)].append(row)
            going = row.get("going") or "unknown"
            buckets[("going", going)].append(row)
            meeting = row.get("meeting_id") or "unknown"
            buckets[("meeting", meeting)].append(row)
            rd = str(row.get("race_date") or "")[:7] or "unknown"
            buckets[("month", rd)].append(row)

        out: list[dict[str, Any]] = []
        for (dimension, key), group in buckets.items():
            n = len(group)
            h1 = sum(1 for g in group if g.get("hit_at_1"))
            h3 = sum(1 for g in group if g.get("hit_at_3"))
            h5 = sum(1 for g in group if g.get("hit_at_5"))
            roi_vals = [g["roi"] for g in group if g.get("roi") is not None]
            roi = round(sum(roi_vals) / len(roi_vals), 2) if roi_vals else None
            dates = sorted({str(g.get("race_date") or "") for g in group if g.get("race_date")})
            out.append(
                {
                    "dimension": dimension,
                    "dimension_key": key,
                    "period_start": dates[0] if dates else None,
                    "period_end": dates[-1] if dates else None,
                    "races_evaluated": n,
                    "prediction_count": n,
                    "hit_at_1": _pct(h1, n),
                    "hit_at_3": _pct(h3, n),
                    "hit_at_5": _pct(h5, n),
                    "roi": roi,
                }
            )
        return out

    def _update_timeseries(self, run_id: int, rows: list[dict[str, Any]]) -> None:
        by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            key = str(row.get("race_date") or "")[:7]
            if key:
                by_month[key].append(row)
        for period_key, group in by_month.items():
            n = len(group)
            h1 = sum(1 for g in group if g.get("hit_at_1"))
            h3 = sum(1 for g in group if g.get("hit_at_3"))
            h5 = sum(1 for g in group if g.get("hit_at_5"))
            roi_vals = [g["roi"] for g in group if g.get("roi") is not None]
            self.repo.upsert_timeseries(
                {
                    "period_type": "month",
                    "period_key": period_key,
                    "races_evaluated": n,
                    "prediction_count": n,
                    "hit_rate": _pct(h1, n),
                    "top3_rate": _pct(h3, n),
                    "hit_at_5_rate": _pct(h5, n),
                    "roi": round(sum(roi_vals) / len(roi_vals), 2) if roi_vals else None,
                    "run_id": run_id,
                }
            )

    def get_summary(self, *, period: str = "overall") -> dict[str, Any]:
        run = self.repo.latest_run()
        if not run:
            return self._empty_summary()
        overall = self.repo.get_overall_aggregate(int(run["id"]))
        if not overall:
            return self._empty_summary(run_id=int(run["id"]))

        if period == "month":
            month_key = datetime.now().strftime("%Y-%m")
            month_rows = self.repo.get_aggregates(int(run["id"]), "month")
            row = next((r for r in month_rows if r["dimension_key"] == month_key), overall)
        else:
            row = overall

        return self._format_summary(row, run_id=int(run["id"]))

    def get_breakdown(self, dimension: str) -> dict[str, Any]:
        run = self.repo.latest_run()
        if not run:
            return {"schema_version": self.SCHEMA, "dimension": dimension, "items": []}
        items = self.repo.get_aggregates(int(run["id"]), dimension)
        return {
            "schema_version": self.SCHEMA,
            "run_id": int(run["id"]),
            "dimension": dimension,
            "items": [self._format_breakdown_item(i) for i in items],
        }

    def get_timeseries(self, *, period_type: str = "month", limit: int = 12) -> dict[str, Any]:
        rows = self.repo.list_timeseries(period_type, limit=limit)
        return {
            "schema_version": self.SCHEMA,
            "period_type": period_type,
            "points": [
                {
                    "period_key": r["period_key"],
                    "hit_rate": r["hit_rate"],
                    "top3_rate": r["top3_rate"],
                    "hit_at_5_rate": r["hit_at_5_rate"],
                    "roi": r.get("roi"),
                    "races_evaluated": r["races_evaluated"],
                    "prediction_count": r["prediction_count"],
                    "snapshot_at": r["snapshot_at"],
                }
                for r in rows
            ],
        }

    def get_trust_display(self, *, venue: str | None = None) -> dict[str, Any]:
        """Home 信頼度ゲージ用 — stats DB の hit_rate から生成。"""
        summary = self.get_summary(period="month")
        venue_rate = None
        venue_n = 0
        if venue:
            breakdown = self.get_breakdown("venue")
            for item in breakdown.get("items") or []:
                if item.get("key") == venue:
                    venue_rate = float(item.get("hit_rate") or 0)
                    venue_n = int(item.get("races_evaluated") or 0)
                    break

        if venue_rate is not None and venue_n >= 3:
            trust_rate = venue_rate
            scope = "venue"
        else:
            trust_rate = float(summary.get("hit_rate") or 0)
            scope = "overall"

        return {
            "schema_version": "expect-stats-trust/1.0",
            "trust_score": round(trust_rate * 100, 1),
            "hit_rate": summary.get("hit_rate"),
            "top3_rate": summary.get("top3_rate"),
            "hit_at_5_rate": summary.get("hit_at_5_rate"),
            "roi": summary.get("roi"),
            "scope": scope,
            "venue": venue,
            "venue_hit_rate": venue_rate,
            "venue_races_evaluated": venue_n,
            "races_evaluated": summary.get("races_evaluated") or 0,
            "source": "stats_db",
            "label": "実績ベース信頼度",
            "updated_at": summary.get("updated_at"),
        }

    def _empty_summary(self, run_id: int | None = None) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA,
            "run_id": run_id,
            "period": "overall",
            "races_evaluated": 0,
            "prediction_count": 0,
            "hit_rate": 0.0,
            "top3_rate": 0.0,
            "hit_at_5_rate": 0.0,
            "roi": None,
            "updated_at": None,
        }

    def _format_summary(self, row: dict[str, Any], *, run_id: int) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA,
            "run_id": run_id,
            "period": row.get("dimension_key") or "overall",
            "races_evaluated": row["races_evaluated"],
            "prediction_count": row["prediction_count"],
            "hit_rate": row["hit_at_1"],
            "top3_rate": row["hit_at_3"],
            "hit_at_5_rate": row["hit_at_5"],
            "roi": row.get("roi"),
            "updated_at": row.get("updated_at"),
        }

    def _format_breakdown_item(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "key": row["dimension_key"],
            "races_evaluated": row["races_evaluated"],
            "prediction_count": row["prediction_count"],
            "hit_rate": row["hit_at_1"],
            "top3_rate": row["hit_at_3"],
            "hit_at_5_rate": row["hit_at_5"],
            "roi": row.get("roi"),
        }


_stats_service: StatsService | None = None


def get_stats_service() -> StatsService:
    global _stats_service
    if _stats_service is None:
        _stats_service = StatsService()
    return _stats_service
