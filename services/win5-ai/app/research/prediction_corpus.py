# -*- coding: utf-8 -*-
"""
Version11 Prediction Corpus Expansion

Research-only corpus builder.
Does NOT mutate Prediction Logic / PE / CE / AI / ResultAutomation / Challenge.
Shadow / Governance are linked when available; never written back to Product.
"""
from __future__ import annotations

import json
import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .analyzer import extract_runners, tie_group, unique_top_pick
from .config import evidence_root, repo_root

SCHEMA_VERSION = "expect-prediction-corpus/1.0"
TARGETS = {
    "prediction": 3000,
    "tie": 300,
    "young_horse": 300,
}

VENUE_CODE_TO_JA = {
    "01": "札幌",
    "02": "函館",
    "03": "福島",
    "04": "新潟",
    "05": "東京",
    "06": "中山",
    "07": "中京",
    "08": "京都",
    "09": "阪神",
    "10": "小倉",
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _pct(x: float | None) -> str:
    if x is None:
        return "N/A"
    return f"{x * 100:.1f}%"


def _parse_coded_race_id(race_id: str) -> dict[str, Any] | None:
    """Parse YYYY-MM-DD-VV-RR where VV is venue code."""
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-(\d{2})-(\d{1,2})", str(race_id or ""))
    if not m:
        return None
    return {
        "race_date": m.group(1),
        "venue_code": m.group(2),
        "venue": VENUE_CODE_TO_JA.get(m.group(2)),
        "race_no": int(m.group(3)),
    }


def _parse_catalog_race_id(race_id: str) -> dict[str, Any] | None:
    """Parse YYYY-MM-DD-会場-R."""
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-(.+)-(\d{1,2})", str(race_id or ""))
    if not m:
        return None
    return {
        "race_date": m.group(1),
        "venue": m.group(2),
        "race_no": int(m.group(3)),
    }


def _age_group(class_label: str | None, race_name: str | None = None) -> str:
    text = " ".join([str(class_label or ""), str(race_name or "")]).strip()
    if not text:
        return "unknown"
    if "2歳新馬" in text or (text == "新馬") or ("新馬" in text and "2歳" in text):
        return "2yo_newcomer"
    if "2歳未勝利" in text:
        return "2yo_maiden"
    if "2歳" in text or "ジュニア" in text:
        return "2yo_other"
    if "3歳未勝利" in text:
        return "3yo_maiden"
    if "3歳" in text and "以上" not in text:
        return "3yo_other"
    if any(
        x in text
        for x in (
            "4歳以上",
            "3歳以上",
            "古馬",
            "1勝クラス",
            "2勝クラス",
            "3勝クラス",
            "オープン",
            "G1",
            "G2",
            "G3",
        )
    ):
        return "older"
    return "unknown"


def _is_young_horse(age_group: str) -> bool:
    return age_group in {
        "2yo_newcomer",
        "2yo_maiden",
        "2yo_other",
        "3yo_maiden",
        "3yo_other",
    }


def _surface_key(surface: str | None) -> str:
    s = str(surface or "").strip().lower()
    if "芝" in s or s == "turf":
        return "turf"
    if "ダ" in s or "dirt" in s:
        return "dirt"
    return "unknown"


def _distance_bucket(distance: int | None) -> str:
    d = int(distance or 0)
    if d <= 0:
        return "unknown"
    if d <= 1400:
        return "sprint"
    if d <= 1800:
        return "mile"
    if d <= 2200:
        return "middle"
    return "long"


def _completeness(
    *,
    has_bundle: bool,
    has_result: bool,
    has_snapshot: bool,
    has_shadow: bool,
    has_governance: bool,
) -> float:
    vals = [has_bundle, has_result, has_snapshot, has_shadow, has_governance]
    return round(sum(1 for v in vals if v) / len(vals), 4)


class PredictionCorpusBuilder:
    def __init__(self) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()

    def _load_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _shadow_index(self) -> dict[str, dict[str, Any]]:
        report = self._load_json(self.evidence / "reports" / "v105-shadow-resolver.json")
        out: dict[str, dict[str, Any]] = {}
        for row in report.get("resolver_records") or []:
            rid = str(row.get("race_id") or "")
            if rid:
                out[rid] = row
        return out

    def _governance_status(self) -> dict[str, Any]:
        report = self._load_json(self.evidence / "reports" / "v106-resolver-governance.json")
        return {
            "status": ((report.get("dashboard") or {}).get("current_status")),
            "eligible": bool((report.get("dashboard") or {}).get("eligible")),
            "summary": report.get("cumulative") or {},
        }

    def _race_meta_index(self, conn) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for row in conn.execute(
            """
            SELECT race_id, date, venue, venue_code, race_no, surface, distance,
                   class_label, grade, extra_json
            FROM races
            """
        ).fetchall():
            d = dict(row)
            out[str(d["race_id"])] = d
            # also index by date|venue|race_no
            key = f"{d.get('date')}|{d.get('venue')}|{d.get('race_no')}"
            out.setdefault(key, d)
            if d.get("venue_code"):
                key2 = f"{d.get('date')}|{str(d.get('venue_code')).zfill(2)}|{d.get('race_no')}"
                out.setdefault(key2, d)
        return out

    def _resolve_meta(
        self,
        *,
        race_id: str,
        race_results_row: dict[str, Any] | None,
        race_meta_index: dict[str, dict[str, Any]],
        bundle: dict[str, Any] | None,
        conn=None,
    ) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "race_date": None,
            "venue": None,
            "surface": None,
            "distance": None,
            "class_label": None,
            "grade": None,
            "race_no": None,
        }
        coded = _parse_coded_race_id(race_id)
        catalog = _parse_catalog_race_id(race_id)
        if race_results_row:
            meta.update(
                {
                    "race_date": race_results_row.get("race_date"),
                    "venue": race_results_row.get("venue"),
                    "surface": race_results_row.get("surface"),
                    "distance": race_results_row.get("distance"),
                }
            )
        if coded:
            meta["race_date"] = meta["race_date"] or coded["race_date"]
            # venue_code in prediction IDs is session/track-day code, NOT JRA venue code.
            # Prefer race_results.venue; do not trust VENUE_CODE_TO_JA for class lookup.
            meta["race_no"] = coded.get("race_no")
            if not meta.get("venue"):
                meta["venue"] = coded.get("venue")
        if catalog:
            meta["race_date"] = meta["race_date"] or catalog["race_date"]
            meta["venue"] = meta["venue"] or catalog["venue"]
            meta["race_no"] = meta["race_no"] or catalog["race_no"]
            if race_id in race_meta_index:
                r = race_meta_index[race_id]
                meta["surface"] = meta["surface"] or r.get("surface")
                meta["distance"] = meta["distance"] or r.get("distance")
                meta["class_label"] = meta["class_label"] or r.get("class_label")
                meta["grade"] = meta["grade"] or r.get("grade")

        # Prefer date|venue|race_no join (works across coded vs catalog race_id formats)
        if meta.get("race_date") and meta.get("venue") and meta.get("race_no") is not None:
            key = f"{meta['race_date']}|{meta['venue']}|{meta['race_no']}"
            if key in race_meta_index:
                r = race_meta_index[key]
                meta["surface"] = meta["surface"] or r.get("surface")
                meta["distance"] = meta["distance"] or r.get("distance")
                meta["class_label"] = meta["class_label"] or r.get("class_label")
                meta["grade"] = meta["grade"] or r.get("grade")
            elif conn is not None:
                row = conn.execute(
                    """
                    SELECT surface, distance, class_label, grade
                    FROM races
                    WHERE date=? AND venue=? AND CAST(race_no AS INTEGER)=?
                    LIMIT 1
                    """,
                    (meta["race_date"], meta["venue"], int(meta["race_no"])),
                ).fetchone()
                if row:
                    r = dict(row)
                    meta["surface"] = meta["surface"] or r.get("surface")
                    meta["distance"] = meta["distance"] or r.get("distance")
                    meta["class_label"] = meta["class_label"] or r.get("class_label")
                    meta["grade"] = meta["grade"] or r.get("grade")

        race_name = None
        if isinstance(bundle, dict):
            race_info = bundle.get("race_info") if isinstance(bundle.get("race_info"), dict) else {}
            race_obj = bundle.get("race") if isinstance(bundle.get("race"), dict) else {}
            meta_obj = bundle.get("meta") if isinstance(bundle.get("meta"), dict) else {}
            race_name = (
                race_info.get("race_name")
                or race_obj.get("race_name")
                or bundle.get("race_name")
                or meta_obj.get("race_name")
            )
            if not meta.get("class_label"):
                meta["class_label"] = (
                    race_info.get("class_label")
                    or race_obj.get("class_label")
                    or bundle.get("class_label")
                    or race_name
                )
            if not meta.get("venue"):
                meta["venue"] = race_info.get("venue") or race_obj.get("venue")
            if not meta.get("surface"):
                meta["surface"] = race_info.get("surface") or race_obj.get("surface")
            if meta.get("distance") is None:
                meta["distance"] = race_info.get("distance") or race_obj.get("distance")
            if meta.get("race_date") is None:
                meta["race_date"] = race_info.get("date") or race_obj.get("date")
        # race name often stored in class_label column of races catalog
        age = _age_group(meta.get("class_label"), race_name or meta.get("class_label"))
        meta["age_group"] = age
        meta["is_young_horse"] = int(_is_young_horse(age))
        meta["race_name"] = race_name or meta.get("class_label")
        return meta

    def _iter_live_predictions(self, conn) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT
              p.id AS prediction_id,
              p.race_id,
              p.created_at,
              p.engine_source,
              p.bundle_json,
              s.snapshot_id,
              s.capture_status,
              s.field_coverage,
              rr.race_date AS result_race_date,
              rr.venue AS result_venue,
              rr.surface AS result_surface,
              rr.distance AS result_distance,
              rr.winner_horse_number
            FROM predictions p
            LEFT JOIN research_prediction_snapshots s ON s.prediction_id = p.id
            LEFT JOIN race_results rr
              ON rr.race_id = COALESCE(s.race_id, p.race_id)
            WHERE COALESCE(s.race_id, p.race_id) NOT LIKE '2099%'
            ORDER BY p.created_at ASC, p.id ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def _iter_miss_evidence(self) -> list[dict[str, Any]]:
        roots = [
            self.root / "services" / "win5-ai" / "var" / "miss-evidence",
            Path(__file__).resolve().parents[2] / "var" / "miss-evidence",
            Path(__file__).resolve().parents[2] / "var" / "improvement-evidence" / "miss",
            self.root / "services" / "win5-ai" / "var" / "improvement-evidence" / "miss",
        ]
        out: list[dict[str, Any]] = []
        seen_paths: set[str] = set()
        for root in roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*.json")):
                if path.name == "manifest.json":
                    continue
                key = str(path.resolve())
                if key in seen_paths:
                    continue
                seen_paths.add(key)
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                # unwrap improvement-evidence envelope
                if isinstance(payload.get("payload"), dict) and (
                    payload.get("payload") or {}
                ).get("prediction_bundle"):
                    payload = payload["payload"]
                race_id = str(payload.get("race_id") or "")
                if not race_id or race_id.startswith("2099"):
                    continue
                bundle = payload.get("prediction_bundle")
                if not isinstance(bundle, dict):
                    continue
                winner = payload.get("winner")
                winner_hn = None
                if isinstance(winner, dict):
                    winner_hn = winner.get("horse_number")
                elif winner is not None:
                    winner_hn = winner
                out.append(
                    {
                        "source": "miss_evidence",
                        "prediction_id": None,
                        "race_id": race_id,
                        "created_at": payload.get("timestamp"),
                        "engine_source": payload.get("engine_source"),
                        "bundle": bundle,
                        "winner_horse_number": winner_hn,
                        "path": str(path),
                    }
                )
            return out

    def _iter_historical_bundles(self, conn) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT ingest_id, source, race_id, race_date, venue, surface, distance,
                   class_label, race_name, has_bundle, has_winner, tie_eligible,
                   tie_size, winner_horse_number, winner_horse_id, bundle_json,
                   validation_status, meta_json
            FROM research_historical_bundles
            WHERE has_bundle=1
            ORDER BY race_date ASC, race_id ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def _iter_baseline_eval(self) -> list[dict[str, Any]]:
        fixture = (
            Path(__file__).resolve().parents[2]
            / "fixtures"
            / "stats"
            / "baseline-285r-evaluations.json"
        )
        if not fixture.exists():
            fixture = self.root / "fixtures" / "stats" / "baseline-285r-evaluations.json"
        if not fixture.exists():
            return []
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        out = []
        for row in payload.get("rows") or []:
            race_id = str(row.get("race_id") or "")
            if not race_id:
                continue
            out.append(
                {
                    "source": "baseline_eval",
                    "prediction_id": None,
                    "race_id": race_id,
                    "created_at": row.get("race_date"),
                    "engine_source": "baseline_import",
                    "bundle": None,
                    "winner_horse_number": row.get("winner_horse_number"),
                    "race_date": row.get("race_date"),
                    "venue": row.get("venue"),
                    "surface": row.get("surface"),
                    "distance": row.get("distance"),
                    "field_size": row.get("field_size"),
                    "hit_at_1": row.get("hit_at_1"),
                }
            )
        return out

    def build(self) -> dict[str, Any]:
        run_id = str(uuid.uuid4())
        started = _now()
        conn = connect()
        try:
            race_meta_index = self._race_meta_index(conn)
            shadow_idx = self._shadow_index()
            gov = self._governance_status()
            has_governance = bool(gov.get("status"))

            # clear previous corpus (research rebuild)
            conn.execute("DELETE FROM research_tie_corpus")
            conn.execute("DELETE FROM research_young_horse_corpus")
            conn.execute("DELETE FROM research_prediction_corpus")

            seen_race_ids: set[str] = set()
            prediction_rows: list[dict[str, Any]] = []

            # 1) Live predictions
            for row in self._iter_live_predictions(conn):
                race_id = str(row["race_id"])
                seen_race_ids.add(race_id)
                bundle = {}
                try:
                    bundle = json.loads(row.get("bundle_json") or "{}")
                except Exception:
                    bundle = {}
                runners = extract_runners(bundle)
                g = tie_group(runners) if runners else []
                winner = row.get("winner_horse_number")
                winner_i = int(winner) if winner is not None else None
                pred_pick = unique_top_pick(runners) if runners else None
                shadow = shadow_idx.get(race_id) or {}
                result_row = {
                    "race_date": row.get("result_race_date"),
                    "venue": row.get("result_venue"),
                    "surface": row.get("result_surface"),
                    "distance": row.get("result_distance"),
                }
                meta = self._resolve_meta(
                    race_id=race_id,
                    race_results_row=result_row,
                    race_meta_index=race_meta_index,
                    bundle=bundle,
                    conn=conn,
                )
                has_bundle = bool(runners)
                has_result = winner_i is not None
                has_snapshot = bool(row.get("snapshot_id"))
                has_shadow = bool(shadow)
                corpus_id = f"live:{row['prediction_id']}"
                prediction_rows.append(
                    {
                        "corpus_id": corpus_id,
                        "source": "live_prediction",
                        "prediction_id": int(row["prediction_id"]),
                        "race_id": race_id,
                        "race_date": meta.get("race_date"),
                        "venue": meta.get("venue"),
                        "surface": meta.get("surface"),
                        "distance": meta.get("distance"),
                        "class_label": meta.get("class_label"),
                        "age_group": meta.get("age_group"),
                        "is_young_horse": int(meta.get("is_young_horse") or 0),
                        "is_tie": int(len(g) >= 2),
                        "tie_size": len(g) if g else None,
                        "has_prediction_bundle": int(has_bundle),
                        "has_race_result": int(has_result),
                        "has_evidence_snapshot": int(has_snapshot),
                        "has_shadow_result": int(has_shadow),
                        "has_governance": int(has_governance and has_shadow),
                        "winner_horse_number": winner_i,
                        "prediction_pick": pred_pick,
                        "shadow_pick": shadow.get("shadow_pick"),
                        "shadow_outcome": shadow.get("outcome"),
                        "snapshot_id": row.get("snapshot_id"),
                        "engine_source": row.get("engine_source"),
                        "completeness": _completeness(
                            has_bundle=has_bundle,
                            has_result=has_result,
                            has_snapshot=has_snapshot,
                            has_shadow=has_shadow,
                            has_governance=has_governance and has_shadow,
                        ),
                        "meta": {
                            "race_name": meta.get("race_name"),
                            "grade": meta.get("grade"),
                            "used_feature": shadow.get("used_feature"),
                            "used_tier": shadow.get("used_tier"),
                            "confidence": shadow.get("confidence"),
                            "created_at": row.get("created_at"),
                        },
                    }
                )

            # 2) Miss evidence bundles not already present
            for row in self._iter_miss_evidence():
                race_id = str(row["race_id"])
                if race_id in seen_race_ids:
                    continue
                bundle = row.get("bundle") or {}
                runners = extract_runners(bundle)
                # Bundle無しは Tie 対象外。seen に入れず historical に委ねる
                if not runners:
                    continue
                seen_race_ids.add(race_id)
                g = tie_group(runners) if runners else []
                winner_i = (
                    int(row["winner_horse_number"])
                    if row.get("winner_horse_number") is not None
                    else None
                )
                pred_pick = unique_top_pick(runners) if runners else None
                shadow = shadow_idx.get(race_id) or {}
                # try race_results lookup
                rr = conn.execute(
                    "SELECT race_date, venue, surface, distance, winner_horse_number FROM race_results WHERE race_id=?",
                    (race_id,),
                ).fetchone()
                result_row = dict(rr) if rr else None
                if result_row and winner_i is None and result_row.get("winner_horse_number") is not None:
                    winner_i = int(result_row["winner_horse_number"])
                snap = conn.execute(
                    "SELECT snapshot_id FROM research_prediction_snapshots WHERE race_id=? LIMIT 1",
                    (race_id,),
                ).fetchone()
                meta = self._resolve_meta(
                    race_id=race_id,
                    race_results_row=result_row,
                    race_meta_index=race_meta_index,
                    bundle=bundle,
                    conn=conn,
                )
                has_bundle = bool(runners)
                has_result = winner_i is not None
                has_snapshot = bool(snap)
                has_shadow = bool(shadow)
                corpus_id = f"miss:{race_id}"
                prediction_rows.append(
                    {
                        "corpus_id": corpus_id,
                        "source": "miss_evidence",
                        "prediction_id": None,
                        "race_id": race_id,
                        "race_date": meta.get("race_date"),
                        "venue": meta.get("venue"),
                        "surface": meta.get("surface"),
                        "distance": meta.get("distance"),
                        "class_label": meta.get("class_label"),
                        "age_group": meta.get("age_group"),
                        "is_young_horse": int(meta.get("is_young_horse") or 0),
                        "is_tie": int(len(g) >= 2),
                        "tie_size": len(g) if g else None,
                        "has_prediction_bundle": int(has_bundle),
                        "has_race_result": int(has_result),
                        "has_evidence_snapshot": int(has_snapshot),
                        "has_shadow_result": int(has_shadow),
                        "has_governance": int(has_governance and has_shadow),
                        "winner_horse_number": winner_i,
                        "prediction_pick": pred_pick,
                        "shadow_pick": shadow.get("shadow_pick"),
                        "shadow_outcome": shadow.get("outcome"),
                        "snapshot_id": snap["snapshot_id"] if snap else None,
                        "engine_source": row.get("engine_source"),
                        "completeness": _completeness(
                            has_bundle=has_bundle,
                            has_result=has_result,
                            has_snapshot=has_snapshot,
                            has_shadow=has_shadow,
                            has_governance=has_governance and has_shadow,
                        ),
                        "meta": {
                            "race_name": meta.get("race_name"),
                            "path": row.get("path"),
                            "used_feature": shadow.get("used_feature"),
                            "used_tier": shadow.get("used_tier"),
                            "confidence": shadow.get("confidence"),
                            "created_at": row.get("created_at"),
                        },
                    }
                )

            # 3) Historical ingested bundles (Research-only; Tie-eligible when model_rank present)
            for row in self._iter_historical_bundles(conn):
                race_id = str(row["race_id"])
                if race_id in seen_race_ids:
                    continue
                seen_race_ids.add(race_id)
                bundle = {}
                try:
                    bundle = json.loads(row.get("bundle_json") or "{}")
                except Exception:
                    bundle = {}
                runners = extract_runners(bundle)
                g = tie_group(runners) if runners else []
                # Only Tie-analyze when bundle+model_rank present (already filtered has_bundle=1)
                is_tie = int(len(g) >= 2)
                winner_i = (
                    int(row["winner_horse_number"])
                    if row.get("winner_horse_number") is not None
                    else None
                )
                pred_pick = unique_top_pick(runners) if runners else None
                shadow = shadow_idx.get(race_id) or {}
                meta = self._resolve_meta(
                    race_id=race_id,
                    race_results_row={
                        "race_date": row.get("race_date"),
                        "venue": row.get("venue"),
                        "surface": row.get("surface"),
                        "distance": row.get("distance"),
                    },
                    race_meta_index=race_meta_index,
                    bundle=bundle,
                    conn=conn,
                )
                if row.get("class_label") and not meta.get("class_label"):
                    meta["class_label"] = row.get("class_label")
                    meta["age_group"] = _age_group(meta.get("class_label"), row.get("race_name"))
                    meta["is_young_horse"] = int(_is_young_horse(meta["age_group"]))
                if row.get("race_name") and meta.get("age_group") == "unknown":
                    meta["age_group"] = _age_group(meta.get("class_label"), row.get("race_name"))
                    meta["is_young_horse"] = int(_is_young_horse(meta["age_group"]))
                corpus_id = f"hist:{row['ingest_id']}"
                prediction_rows.append(
                    {
                        "corpus_id": corpus_id,
                        "source": f"historical:{row.get('source')}",
                        "prediction_id": None,
                        "race_id": race_id,
                        "race_date": meta.get("race_date") or row.get("race_date"),
                        "venue": meta.get("venue") or row.get("venue"),
                        "surface": meta.get("surface") or row.get("surface"),
                        "distance": meta.get("distance") or row.get("distance"),
                        "class_label": meta.get("class_label") or row.get("class_label"),
                        "age_group": meta.get("age_group"),
                        "is_young_horse": int(meta.get("is_young_horse") or 0),
                        "is_tie": is_tie,
                        "tie_size": len(g) if g else None,
                        "has_prediction_bundle": 1,
                        "has_race_result": int(winner_i is not None or row.get("has_winner")),
                        "has_evidence_snapshot": 0,
                        "has_shadow_result": int(bool(shadow)),
                        "has_governance": int(has_governance and bool(shadow)),
                        "winner_horse_number": winner_i,
                        "prediction_pick": pred_pick,
                        "shadow_pick": shadow.get("shadow_pick"),
                        "shadow_outcome": shadow.get("outcome"),
                        "snapshot_id": None,
                        "engine_source": f"historical_ingest:{row.get('source')}",
                        "completeness": _completeness(
                            has_bundle=True,
                            has_result=winner_i is not None,
                            has_snapshot=False,
                            has_shadow=bool(shadow),
                            has_governance=has_governance and bool(shadow),
                        ),
                        "meta": {
                            "race_name": row.get("race_name") or meta.get("race_name"),
                            "validation_status": row.get("validation_status"),
                            "winner_horse_id": row.get("winner_horse_id"),
                            "ingest_source": row.get("source"),
                        },
                    }
                )

            # 4) Baseline evaluation seed (no full Prediction Bundle / no Tie)
            for row in self._iter_baseline_eval():
                race_id = str(row["race_id"])
                if race_id in seen_race_ids:
                    continue
                # If historical unrecoverable only, still allow metadata seed
                seen_race_ids.add(race_id)
                meta = self._resolve_meta(
                    race_id=race_id,
                    race_results_row={
                        "race_date": row.get("race_date"),
                        "venue": row.get("venue"),
                        "surface": row.get("surface"),
                        "distance": row.get("distance"),
                    },
                    race_meta_index=race_meta_index,
                    bundle=None,
                    conn=conn,
                )
                # baseline class often missing; keep unknown young horse
                corpus_id = f"baseline:{race_id}"
                prediction_rows.append(
                    {
                        "corpus_id": corpus_id,
                        "source": "baseline_eval",
                        "prediction_id": None,
                        "race_id": race_id,
                        "race_date": meta.get("race_date") or row.get("race_date"),
                        "venue": meta.get("venue") or row.get("venue"),
                        "surface": meta.get("surface") or row.get("surface"),
                        "distance": meta.get("distance") or row.get("distance"),
                        "class_label": meta.get("class_label"),
                        "age_group": meta.get("age_group"),
                        "is_young_horse": int(meta.get("is_young_horse") or 0),
                        "is_tie": 0,
                        "tie_size": None,
                        "has_prediction_bundle": 0,
                        "has_race_result": 1,
                        "has_evidence_snapshot": 0,
                        "has_shadow_result": 0,
                        "has_governance": 0,
                        "winner_horse_number": row.get("winner_horse_number"),
                        "prediction_pick": None,
                        "shadow_pick": None,
                        "shadow_outcome": None,
                        "snapshot_id": None,
                        "engine_source": row.get("engine_source"),
                        "completeness": _completeness(
                            has_bundle=False,
                            has_result=True,
                            has_snapshot=False,
                            has_shadow=False,
                            has_governance=False,
                        ),
                        "meta": {
                            "hit_at_1": row.get("hit_at_1"),
                            "field_size": row.get("field_size"),
                            "note": "evaluation-only seed; no Prediction Bundle / Tie",
                        },
                    }
                )

            now = _now()
            for rec in prediction_rows:
                conn.execute(
                    """
                    INSERT INTO research_prediction_corpus(
                      corpus_id, source, prediction_id, race_id, race_date, venue,
                      surface, distance, class_label, age_group, is_young_horse,
                      is_tie, tie_size, has_prediction_bundle, has_race_result,
                      has_evidence_snapshot, has_shadow_result, has_governance,
                      winner_horse_number, prediction_pick, shadow_pick, shadow_outcome,
                      snapshot_id, engine_source, completeness, meta_json,
                      created_at, updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        rec["corpus_id"],
                        rec["source"],
                        rec["prediction_id"],
                        rec["race_id"],
                        rec["race_date"],
                        rec["venue"],
                        rec["surface"],
                        rec["distance"],
                        rec["class_label"],
                        rec["age_group"],
                        rec["is_young_horse"],
                        rec["is_tie"],
                        rec["tie_size"],
                        rec["has_prediction_bundle"],
                        rec["has_race_result"],
                        rec["has_evidence_snapshot"],
                        rec["has_shadow_result"],
                        rec["has_governance"],
                        rec["winner_horse_number"],
                        rec["prediction_pick"],
                        rec["shadow_pick"],
                        rec["shadow_outcome"],
                        rec["snapshot_id"],
                        rec["engine_source"],
                        rec["completeness"],
                        json.dumps(rec.get("meta") or {}, ensure_ascii=False),
                        now,
                        now,
                    ),
                )
                if rec["is_tie"]:
                    conn.execute(
                        """
                        INSERT INTO research_tie_corpus(
                          corpus_id, race_id, race_date, venue, surface, distance,
                          class_label, age_group, tie_size, winner_horse_number,
                          prediction_pick, shadow_pick, shadow_outcome, used_feature,
                          used_tier, confidence, meta_json, created_at
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            rec["corpus_id"],
                            rec["race_id"],
                            rec["race_date"],
                            rec["venue"],
                            rec["surface"],
                            rec["distance"],
                            rec["class_label"],
                            rec["age_group"],
                            rec["tie_size"],
                            rec["winner_horse_number"],
                            rec["prediction_pick"],
                            rec["shadow_pick"],
                            rec["shadow_outcome"],
                            (rec.get("meta") or {}).get("used_feature"),
                            (rec.get("meta") or {}).get("used_tier"),
                            (rec.get("meta") or {}).get("confidence"),
                            json.dumps(rec.get("meta") or {}, ensure_ascii=False),
                            now,
                        ),
                    )
                if rec["is_young_horse"]:
                    conn.execute(
                        """
                        INSERT INTO research_young_horse_corpus(
                          corpus_id, race_id, race_date, venue, surface, distance,
                          class_label, age_group, is_tie, tie_size, winner_horse_number,
                          prediction_pick, meta_json, created_at
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            rec["corpus_id"],
                            rec["race_id"],
                            rec["race_date"],
                            rec["venue"],
                            rec["surface"],
                            rec["distance"],
                            rec["class_label"],
                            rec["age_group"],
                            rec["is_tie"],
                            rec["tie_size"],
                            rec["winner_horse_number"],
                            rec["prediction_pick"],
                            json.dumps(rec.get("meta") or {}, ensure_ascii=False),
                            now,
                        ),
                    )

            summary = self._summarize(prediction_rows, gov)
            conn.execute(
                """
                INSERT INTO research_corpus_runs(
                  run_id, schema_version, started_at, finished_at, status,
                  prediction_count, tie_count, young_horse_count,
                  target_prediction, target_tie, target_young_horse,
                  summary_json, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    run_id,
                    SCHEMA_VERSION,
                    started,
                    _now(),
                    "success",
                    summary["prediction_count"],
                    summary["tie_count"],
                    summary["young_horse_count"],
                    TARGETS["prediction"],
                    TARGETS["tie"],
                    TARGETS["young_horse"],
                    json.dumps(summary, ensure_ascii=False),
                    _now(),
                ),
            )
            conn.commit()
            summary["run_id"] = run_id
            summary["records"] = prediction_rows
            return summary
        finally:
            conn.close()

    def _summarize(
        self, rows: list[dict[str, Any]], gov: dict[str, Any]
    ) -> dict[str, Any]:
        n = len(rows)
        tie_n = sum(1 for r in rows if r.get("is_tie"))
        young_n = sum(1 for r in rows if r.get("is_young_horse"))
        by_age = Counter(str(r.get("age_group") or "unknown") for r in rows)
        by_class = Counter(str(r.get("class_label") or "unknown") for r in rows)
        by_surface = Counter(_surface_key(r.get("surface")) for r in rows)
        by_distance = Counter(_distance_bucket(r.get("distance")) for r in rows)
        by_venue = Counter(str(r.get("venue") or "unknown") for r in rows)
        by_source = Counter(str(r.get("source") or "unknown") for r in rows)
        with_bundle = sum(1 for r in rows if r.get("has_prediction_bundle"))
        with_result = sum(1 for r in rows if r.get("has_race_result"))
        with_snapshot = sum(1 for r in rows if r.get("has_evidence_snapshot"))
        with_shadow = sum(1 for r in rows if r.get("has_shadow_result"))

        gap = {
            "prediction": max(TARGETS["prediction"] - n, 0),
            "tie": max(TARGETS["tie"] - tie_n, 0),
            "young_horse": max(TARGETS["young_horse"] - young_n, 0),
            "targets_met": {
                "prediction": n >= TARGETS["prediction"],
                "tie": tie_n >= TARGETS["tie"],
                "young_horse": young_n >= TARGETS["young_horse"],
            },
        }
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "shadow_only": True,
            "production_prediction": "unchanged",
            "prediction_count": n,
            "tie_count": tie_n,
            "young_horse_count": young_n,
            "targets": TARGETS,
            "gap": gap,
            "coverage": {
                "with_prediction_bundle": with_bundle,
                "with_race_result": with_result,
                "with_evidence_snapshot": with_snapshot,
                "with_shadow_result": with_shadow,
            },
            "by_age": dict(by_age),
            "by_class": dict(by_class.most_common(40)),
            "by_surface": dict(by_surface),
            "by_distance": dict(by_distance),
            "by_venue": dict(by_venue),
            "by_source": dict(by_source),
            "governance": gov,
        }


def write_prediction_corpus_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gap = report.get("gap") or {}
    lines = [
        "# Version11 Research — Prediction Corpus",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Scope:** Research only / Prediction 変更禁止 / Shadow only  ",
        "",
        "## Summary",
        "",
        f"- Prediction count: `{report.get('prediction_count')}` / target `{TARGETS['prediction']}`",
        f"- Gap: `{gap.get('prediction')}`",
        f"- Bundle付き: `{report['coverage']['with_prediction_bundle']}`",
        f"- RaceResult付き: `{report['coverage']['with_race_result']}`",
        f"- Evidence Snapshot付き: `{report['coverage']['with_evidence_snapshot']}`",
        f"- Shadow Result付き: `{report['coverage']['with_shadow_result']}`",
        "",
        "## Source Breakdown",
        "",
        "| Source | Count |",
        "|--------|------:|",
    ]
    for k, v in (report.get("by_source") or {}).items():
        lines.append(f"| `{k}` | {v} |")
    lines.extend(
        [
            "",
            "## Breakdown",
            "",
            "### 年齢別",
            "",
            "| Age | Count |",
            "|-----|------:|",
        ]
    )
    for k, v in (report.get("by_age") or {}).items():
        lines.append(f"| `{k}` | {v} |")
    lines.extend(
        [
            "",
            "### クラス別",
            "",
            "| Class | Count |",
            "|-------|------:|",
        ]
    )
    for k, v in (report.get("by_class") or {}).items():
        lines.append(f"| `{k}` | {v} |")
    lines.extend(["", "### 芝ダート別", "", "| Surface | Count |", "|---------|------:|"])
    for k, v in (report.get("by_surface") or {}).items():
        lines.append(f"| `{k}` | {v} |")
    lines.extend(["", "### 距離別", "", "| Distance | Count |", "|----------|------:|"])
    for k, v in (report.get("by_distance") or {}).items():
        lines.append(f"| `{k}` | {v} |")
    lines.extend(["", "### 開催別", "", "| Venue | Count |", "|-------|------:|"])
    for k, v in sorted((report.get("by_venue") or {}).items(), key=lambda x: -x[1])[:30]:
        lines.append(f"| `{k}` | {v} |")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "```",
            "Action Type: Prediction Corpus Expansion (Research)",
            "Prediction Mutation: FORBIDDEN",
            "Shadow Only: YES",
            "Next: continue ingesting historical Prediction Bundles + RaceResults",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_tie_corpus_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [r for r in (report.get("records") or []) if r.get("is_tie")]
    by_age = Counter(str(r.get("age_group") or "unknown") for r in rows)
    by_surface = Counter(_surface_key(r.get("surface")) for r in rows)
    by_venue = Counter(str(r.get("venue") or "unknown") for r in rows)
    lines = [
        "# Version11 Research — Tie Corpus",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"- Tie count: `{report.get('tie_count')}` / target `{TARGETS['tie']}`",
        f"- Gap: `{(report.get('gap') or {}).get('tie')}`",
        "",
        "## Breakdown",
        "",
        "| Age | Count |",
        "|-----|------:|",
    ]
    for k, v in by_age.items():
        lines.append(f"| `{k}` | {v} |")
    lines.extend(["", "| Surface | Count |", "|---------|------:|"])
    for k, v in by_surface.items():
        lines.append(f"| `{k}` | {v} |")
    lines.extend(["", "| Venue | Count |", "|-------|------:|"])
    for k, v in sorted(by_venue.items(), key=lambda x: -x[1]):
        lines.append(f"| `{k}` | {v} |")
    lines.extend(
        [
            "",
            "## Sample",
            "",
            "| Race | TieSize | Winner | PredPick | ShadowPick | Outcome |",
            "|------|--------:|-------:|---------:|-----------:|---------|",
        ]
    )
    for r in rows[:30]:
        lines.append(
            f"| `{r.get('race_id')}` | {r.get('tie_size')} | {r.get('winner_horse_number')} | "
            f"{r.get('prediction_pick')} | {r.get('shadow_pick')} | {r.get('shadow_outcome')} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_young_horse_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [r for r in (report.get("records") or []) if r.get("is_young_horse")]
    by_age = Counter(str(r.get("age_group") or "unknown") for r in rows)
    by_class = Counter(str(r.get("class_label") or "unknown") for r in rows)
    lines = [
        "# Version11 Research — Young Horse Corpus",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"- Young Horse count: `{report.get('young_horse_count')}` / target `{TARGETS['young_horse']}`",
        f"- Gap: `{(report.get('gap') or {}).get('young_horse')}`",
        "",
        "## Age Group",
        "",
        "| Age | Count |",
        "|-----|------:|",
    ]
    for k, v in by_age.items():
        lines.append(f"| `{k}` | {v} |")
    lines.extend(["", "## Class", "", "| Class | Count |", "|-------|------:|"])
    for k, v in by_class.most_common(40):
        lines.append(f"| `{k}` | {v} |")
    lines.extend(
        [
            "",
            "## Note",
            "",
            "Young Horse 判定は `class_label` / race_name のヒューリスティック。",
            "現状は class_label 欠損が多く、`young_horse_count` が過小になる。",
            "次フェーズで race meta の補完と過去 Prediction Bundle の取り込みが必要。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write(
    *,
    prediction_md: Path | None = None,
    tie_md: Path | None = None,
    young_md: Path | None = None,
    json_path: Path | None = None,
) -> dict[str, Any]:
    report = PredictionCorpusBuilder().build()
    root = repo_root()
    prediction_md = prediction_md or (root / "docs/research/v11-prediction-corpus.md")
    tie_md = tie_md or (root / "docs/research/v11-tie-corpus.md")
    young_md = young_md or (root / "docs/research/v11-young-horse-corpus.md")
    json_path = json_path or (evidence_root() / "corpus" / "v11-prediction-corpus.json")

    # strip bulky records for markdown writers already use records; keep in JSON
    write_prediction_corpus_md(report, prediction_md)
    write_tie_corpus_md(report, tie_md)
    write_young_horse_md(report, young_md)

    export = dict(report)
    # keep records but ensure serializable
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "prediction_md": str(prediction_md),
        "tie_md": str(tie_md),
        "young_md": str(young_md),
        "json": str(json_path),
    }
    return report
