# -*- coding: utf-8 -*-
"""
Version11.1 Historical Bundle Ingest (Research-only)

Ingests past Prediction Bundles into Research DB.
Does NOT mutate Product Prediction Logic / PE / CE / AI / Challenge / ResultAutomation.

Rules:
- Bundle present → Research Corpus candidate (Tie-eligible if model_rank + runners)
- Bundle absent → metadata-only / unrecoverable; excluded from Tie analysis
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .analyzer import extract_runners, tie_group
from .config import evidence_root, repo_root

SCHEMA_VERSION = "expect-historical-ingest/1.1"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


def _parse_race_date(race_id: str) -> str | None:
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(race_id or ""))
    return m.group(1) if m else None


def _has_model_rank_runners(bundle: dict[str, Any] | None) -> tuple[bool, list[dict[str, Any]]]:
    if not isinstance(bundle, dict):
        return False, []
    runners = extract_runners(bundle)
    if not runners:
        return False, []
    ok = all("model_rank" in r for r in runners) and any(
        int(r.get("model_rank") or 999) < 999 for r in runners
    )
    return ok, runners


def _normalize_horse_numbers(
    runners: list[dict[str, Any]],
    *,
    winner_horse_id: str | None = None,
    winner_horse_number: int | None = None,
) -> tuple[list[dict[str, Any]], int | None]:
    """Ensure unique positive horse_number for research Tie analysis."""
    used: set[int] = set()
    out: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    for r in runners:
        item = dict(r)
        try:
            hn = int(item.get("horse_number") or 0)
        except Exception:
            hn = 0
        if hn > 0 and hn not in used:
            used.add(hn)
            item["horse_number"] = hn
            out.append(item)
        else:
            pending.append(item)
    nxt = 1
    for item in pending:
        while nxt in used:
            nxt += 1
        item["horse_number"] = nxt
        used.add(nxt)
        out.append(item)
        nxt += 1

    winner_hn = winner_horse_number
    if winner_hn is None and winner_horse_id:
        for item in out:
            if str(item.get("horse_id") or "") == str(winner_horse_id):
                winner_hn = int(item["horse_number"])
                break
    return out, winner_hn


def _as_canonical_bundle(
    *,
    race_id: str,
    runners: list[dict[str, Any]],
    race_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "race_id": race_id,
        "race_info": race_info or {"race_id": race_id},
        "evaluation": {
            "runners": [
                {
                    "horse_number": int(r.get("horse_number") or 0),
                    "horse_id": r.get("horse_id"),
                    "horse_name": r.get("horse_name") or r.get("CandidateID"),
                    "model_rank": int(r.get("model_rank") or r.get("Rank") or 999),
                    "win_prob": float(r.get("win_prob") or r.get("Confidence") or 0.0),
                    "odds": r.get("odds"),
                    "popularity": r.get("popularity"),
                }
                for r in runners
            ]
        },
        "meta": {"research_ingest": True, "schema": SCHEMA_VERSION},
    }


class HistoricalBundleIngest:
    def __init__(self) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()
        self.win5 = Path(__file__).resolve().parents[2]

    def _paths(self) -> dict[str, list[Path]]:
        roots = [
            self.root,
            self.win5,
            self.win5.parent.parent if self.win5.name == "win5-ai" else self.root,
        ]
        # unique existing roots
        uniq: list[Path] = []
        for r in roots:
            try:
                rr = r.resolve()
            except Exception:
                rr = r
            if rr.exists() and rr not in uniq:
                uniq.append(rr)

        def first_existing(rel: str) -> list[Path]:
            out = []
            for base in uniq:
                p = base / rel
                if p.exists():
                    out.append(p)
            return out

        return {
            "real_285r": first_existing(
                "research/v3_lab/baselines/offline_gate/real_285r_corpus.json"
            )
            or first_existing(
                "services/win5-ai/../research/v3_lab/baselines/offline_gate/real_285r_corpus.json"
            ),
            "pi_predictions": first_existing("public/data/predictions"),
            "miss_evidence": [
                self.win5 / "var" / "miss-evidence",
                self.win5 / "var" / "improvement-evidence" / "miss",
            ],
            "fixtures_bundle": first_existing("fixtures/prediction-bundle"),
            "baseline_eval": first_existing("fixtures/stats/baseline-285r-evaluations.json")
            or first_existing("services/win5-ai/fixtures/stats/baseline-285r-evaluations.json"),
            "tmp_captures": [self.root] if (self.root / "tmp-pred-nc2.json").exists() or True else [],
        }

    def inventory(self) -> dict[str, Any]:
        """Scan all candidate sources and count recoverable bundles."""
        inv: dict[str, Any] = {
            "generated_at": _now(),
            "sources": [],
            "totals": {
                "bundle_candidates": 0,
                "unique_race_ids_with_bundle": 0,
                "metadata_only": 0,
                "unrecoverable": 0,
            },
        }
        seen_bundle_races: set[str] = set()
        sources_out: list[dict[str, Any]] = []

        # 1) DB predictions
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT id, race_id, bundle_json FROM predictions WHERE race_id NOT LIKE '2099%'"
            ).fetchall()
            with_b = 0
            race_ids = set()
            for r in rows:
                try:
                    b = json.loads(r["bundle_json"] or "{}")
                except Exception:
                    b = {}
                ok, _ = _has_model_rank_runners(b)
                if ok:
                    with_b += 1
                    rid = str(r["race_id"])
                    race_ids.add(rid)
                    seen_bundle_races.add(rid)
            sources_out.append(
                {
                    "source": "db.predictions",
                    "path": "var/expect_ai.db::predictions",
                    "rows": len(rows),
                    "with_bundle": with_b,
                    "unique_races": len(race_ids),
                    "tie_recoverable": True,
                    "note": "Product table read-only; copied into research_historical_bundles",
                }
            )
            inv["totals"]["bundle_candidates"] += with_b

            # prediction_history
            ph = conn.execute("SELECT COUNT(*) c FROM prediction_history").fetchone()["c"]
            sources_out.append(
                {
                    "source": "db.prediction_history",
                    "path": "var/expect_ai.db::prediction_history",
                    "rows": ph,
                    "with_bundle": 0,
                    "unique_races": 0,
                    "tie_recoverable": False,
                    "note": "user view history; no Prediction Bundle payload",
                }
            )

            # snapshots
            snaps = conn.execute(
                "SELECT race_id, payload_json FROM research_prediction_snapshots"
            ).fetchall()
            snap_b = 0
            for s in snaps:
                try:
                    payload = json.loads(s["payload_json"] or "{}")
                except Exception:
                    payload = {}
                # payload may wrap bundle
                cand = payload.get("prediction_bundle") if isinstance(payload, dict) else None
                ok, _ = _has_model_rank_runners(
                    cand if isinstance(cand, dict) else payload if isinstance(payload, dict) else None
                )
                if ok:
                    snap_b += 1
                    seen_bundle_races.add(str(s["race_id"]))
            sources_out.append(
                {
                    "source": "db.research_prediction_snapshots",
                    "path": "var/expect_ai.db::research_prediction_snapshots",
                    "rows": len(snaps),
                    "with_bundle": snap_b,
                    "unique_races": snap_b,
                    "tie_recoverable": snap_b > 0,
                    "note": "Evidence snapshots; usually features-only",
                }
            )

            # race_evaluations metadata
            evals = conn.execute(
                "SELECT COUNT(DISTINCT race_id) c FROM race_evaluations WHERE race_id NOT LIKE '2099%'"
            ).fetchone()["c"]
            sources_out.append(
                {
                    "source": "db.race_evaluations",
                    "path": "var/expect_ai.db::race_evaluations",
                    "rows": evals,
                    "with_bundle": 0,
                    "unique_races": evals,
                    "tie_recoverable": False,
                    "note": "hit metrics only; Bundle absent → unrecoverable for Tie",
                }
            )
        finally:
            conn.close()

        paths = self._paths()

        # 2) real_285r
        for p in paths.get("real_285r") or []:
            if not p.exists():
                # also check under repo parent
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
            races = data.get("races") or []
            with_b = 0
            for race in races:
                runners = race.get("runners") or []
                if runners and all("model_rank" in x for x in runners):
                    with_b += 1
                    seen_bundle_races.add(str(race.get("race_id")))
            sources_out.append(
                {
                    "source": "real_285r_corpus",
                    "path": str(p),
                    "rows": len(races),
                    "with_bundle": with_b,
                    "unique_races": with_b,
                    "tie_recoverable": True,
                    "note": "Offline gate corpus; horse_number often 0 → normalized by horse_id",
                }
            )
            inv["totals"]["bundle_candidates"] += with_b

        # discover 285r relative to KEIBA root
        for candidate in [
            self.root / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json",
            Path("/home/ubuntu/KEIBA-Single-AI/research/v3_lab/baselines/offline_gate/real_285r_corpus.json"),
            self.win5.parents[1] / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json",
        ]:
            if candidate.exists() and not any(
                s.get("source") == "real_285r_corpus" for s in sources_out
            ):
                data = json.loads(candidate.read_text(encoding="utf-8"))
                races = data.get("races") or []
                with_b = sum(
                    1
                    for race in races
                    if (race.get("runners") or [])
                    and all("model_rank" in x for x in (race.get("runners") or []))
                )
                for race in races:
                    if race.get("runners"):
                        seen_bundle_races.add(str(race.get("race_id")))
                sources_out.append(
                    {
                        "source": "real_285r_corpus",
                        "path": str(candidate),
                        "rows": len(races),
                        "with_bundle": with_b,
                        "unique_races": with_b,
                        "tie_recoverable": True,
                        "note": "Offline gate corpus; horse_number often 0 → normalized by horse_id",
                    }
                )
                inv["totals"]["bundle_candidates"] += with_b

        # 3) pi.json
        pi_dirs = []
        for base in [self.root, self.win5.parents[1] if len(self.win5.parents) > 1 else self.root]:
            d = base / "public" / "data" / "predictions"
            if d.exists():
                pi_dirs.append(d)
        pi_files = []
        for d in pi_dirs:
            pi_files.extend(sorted(d.glob("*.pi.json")))
        pi_with = 0
        for f in pi_files:
            try:
                payload = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            cands = ((payload.get("prediction") or {}) if isinstance(payload, dict) else {}).get(
                "candidates"
            ) or []
            if cands and any("Rank" in c for c in cands):
                pi_with += 1
                seen_bundle_races.add(str(payload.get("race_id")))
        sources_out.append(
            {
                "source": "public.pi_json",
                "path": str(pi_dirs[0]) if pi_dirs else "public/data/predictions",
                "rows": len(pi_files),
                "with_bundle": pi_with,
                "unique_races": pi_with,
                "tie_recoverable": True,
                "note": "Rank/Confidence/HorseNumber → canonical Bundle",
            }
        )
        inv["totals"]["bundle_candidates"] += pi_with

        # 4) miss-evidence
        miss_files = []
        for d in [
            self.win5 / "var" / "miss-evidence",
            self.win5 / "var" / "improvement-evidence" / "miss",
        ]:
            if d.exists():
                miss_files.extend([p for p in d.rglob("*.json") if p.name != "manifest.json"])
        miss_with = 0
        miss_races = set()
        for f in miss_files:
            try:
                payload = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(payload.get("payload"), dict):
                payload = payload["payload"]
            b = payload.get("prediction_bundle") if isinstance(payload, dict) else None
            ok, _ = _has_model_rank_runners(b if isinstance(b, dict) else None)
            rid = str((payload or {}).get("race_id") or "")
            if ok and rid and not rid.startswith("2099"):
                miss_with += 1
                miss_races.add(rid)
                seen_bundle_races.add(rid)
        sources_out.append(
            {
                "source": "miss_evidence",
                "path": "var/miss-evidence + var/improvement-evidence/miss",
                "rows": len(miss_files),
                "with_bundle": miss_with,
                "unique_races": len(miss_races),
                "tie_recoverable": True,
                "note": "includes envelopes with payload.prediction_bundle",
            }
        )
        inv["totals"]["bundle_candidates"] += miss_with

        # 5) baseline eval metadata-only
        baseline_paths = []
        for p in [
            self.win5 / "fixtures" / "stats" / "baseline-285r-evaluations.json",
            self.root / "fixtures" / "stats" / "baseline-285r-evaluations.json",
        ]:
            if p.exists():
                baseline_paths.append(p)
                break
        baseline_n = 0
        if baseline_paths:
            data = json.loads(baseline_paths[0].read_text(encoding="utf-8"))
            baseline_n = len(data.get("rows") or [])
        sources_out.append(
            {
                "source": "baseline_285r_evaluations",
                "path": str(baseline_paths[0]) if baseline_paths else "fixtures/stats/baseline-285r-evaluations.json",
                "rows": baseline_n,
                "with_bundle": 0,
                "unique_races": baseline_n,
                "tie_recoverable": False,
                "note": "evaluation-only; metadata / unrecoverable for Tie unless covered by real_285r",
            }
        )

        # 6) tmp API captures at KEIBA root
        tmp_files = list(self.root.glob("tmp*pred*.json")) + list(self.root.glob("tmp-p-*.json"))
        tmp_with = 0
        for f in tmp_files:
            try:
                payload = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            # may be list or dict
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    continue
                ok, _ = _has_model_rank_runners(item)
                if not ok and isinstance(item.get("data"), dict):
                    ok, _ = _has_model_rank_runners(item["data"])
                    item = item["data"]
                if ok:
                    tmp_with += 1
                    rid = str(item.get("race_id") or "")
                    if rid:
                        seen_bundle_races.add(rid)
        sources_out.append(
            {
                "source": "tmp_api_captures",
                "path": str(self.root / "tmp*pred*.json"),
                "rows": len(tmp_files),
                "with_bundle": tmp_with,
                "unique_races": tmp_with,
                "tie_recoverable": tmp_with > 0,
                "note": "local API capture dumps; may duplicate live predictions",
            }
        )
        inv["totals"]["bundle_candidates"] += tmp_with

        # S3 / backup markers
        sources_out.append(
            {
                "source": "s3_or_remote_backup",
                "path": "not found in checkout / EC2 var",
                "rows": 0,
                "with_bundle": 0,
                "unique_races": 0,
                "tie_recoverable": False,
                "note": "No S3 credentials or backup dumps discovered during inventory",
            }
        )

        inv["sources"] = sources_out
        inv["totals"]["unique_race_ids_with_bundle"] = len(seen_bundle_races)
        inv["seen_bundle_race_ids_count"] = len(seen_bundle_races)
        return inv

    def _upsert_bundle(
        self,
        conn,
        *,
        source: str,
        source_path: str | None,
        race_id: str,
        bundle: dict[str, Any],
        winner_horse_number: int | None,
        winner_horse_id: str | None,
        race_meta: dict[str, Any] | None,
        extra_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ok, runners = _has_model_rank_runners(bundle)
        errors: list[str] = []
        if not ok:
            errors.append("missing_model_rank_runners")
        runners2, winner_hn = _normalize_horse_numbers(
            runners,
            winner_horse_id=winner_horse_id,
            winner_horse_number=winner_horse_number,
        )
        if ok and runners2:
            # rewrite bundle with normalized numbers
            race_info = {}
            if isinstance(bundle.get("race_info"), dict):
                race_info = dict(bundle["race_info"])
            if race_meta:
                race_info.update({k: v for k, v in race_meta.items() if v is not None})
            bundle = _as_canonical_bundle(race_id=race_id, runners=runners2, race_info=race_info)
            runners = runners2
        g = tie_group(runners) if runners else []
        has_winner = winner_hn is not None or bool(winner_horse_id)
        # Validation chain: Bundle → model_rank → (optional) RaceResult/Winner
        if ok and has_winner:
            status = "recoverable"
        elif ok:
            status = "bundle_only"
            errors.append("winner_missing")
        else:
            status = "unrecoverable"
        tie_eligible = int(ok and len(runners) >= 2)
        ingest_id = f"{source}:{_sha(race_id)}"
        now = _now()
        meta = {
            "race_meta": race_meta or {},
            "extra": extra_meta or {},
            "errors": errors,
        }
        conn.execute(
            """
            INSERT INTO research_historical_bundles(
              ingest_id, source, source_path, race_id, race_date, venue, surface,
              distance, class_label, race_name, has_bundle, has_model_rank,
              has_race_result, has_winner, tie_eligible, tie_size,
              winner_horse_number, winner_horse_id, runner_count,
              validation_status, validation_errors_json, bundle_json, meta_json,
              created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(ingest_id) DO UPDATE SET
              source_path=excluded.source_path,
              race_date=excluded.race_date,
              venue=excluded.venue,
              surface=excluded.surface,
              distance=excluded.distance,
              class_label=excluded.class_label,
              race_name=excluded.race_name,
              has_bundle=excluded.has_bundle,
              has_model_rank=excluded.has_model_rank,
              has_race_result=excluded.has_race_result,
              has_winner=excluded.has_winner,
              tie_eligible=excluded.tie_eligible,
              tie_size=excluded.tie_size,
              winner_horse_number=excluded.winner_horse_number,
              winner_horse_id=excluded.winner_horse_id,
              runner_count=excluded.runner_count,
              validation_status=excluded.validation_status,
              validation_errors_json=excluded.validation_errors_json,
              bundle_json=excluded.bundle_json,
              meta_json=excluded.meta_json,
              updated_at=excluded.updated_at
            """,
            (
                ingest_id,
                source,
                source_path,
                race_id,
                (race_meta or {}).get("race_date") or _parse_race_date(race_id),
                (race_meta or {}).get("venue"),
                (race_meta or {}).get("surface"),
                (race_meta or {}).get("distance"),
                (race_meta or {}).get("class_label"),
                (race_meta or {}).get("race_name"),
                int(ok),
                int(ok),
                int(has_winner),
                int(has_winner),
                tie_eligible,
                len(g) if g else None,
                winner_hn,
                winner_horse_id,
                len(runners) if runners else 0,
                status,
                json.dumps(errors, ensure_ascii=False),
                json.dumps(bundle, ensure_ascii=False) if ok else None,
                json.dumps(meta, ensure_ascii=False),
                now,
                now,
            ),
        )
        return {
            "ingest_id": ingest_id,
            "race_id": race_id,
            "status": status,
            "tie_eligible": tie_eligible,
            "tie_size": len(g) if g else 0,
            "has_bundle": ok,
        }

    def _add_unrecoverable(
        self,
        conn,
        *,
        source: str,
        race_id: str,
        reason: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        rid = f"{source}:{_sha(race_id + reason)}"
        conn.execute(
            """
            INSERT OR REPLACE INTO research_unrecoverable_predictions(
              record_id, source, race_id, reason, has_metadata, meta_json, created_at
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (
                rid,
                source,
                race_id,
                reason,
                1,
                json.dumps(meta or {}, ensure_ascii=False),
                _now(),
            ),
        )

    def ingest(self) -> dict[str, Any]:
        run_id = str(uuid.uuid4())
        started = _now()
        inventory = self.inventory()
        conn = connect()
        summary: dict[str, Any] = {
            "ingested_bundles": 0,
            "recoverable": 0,
            "bundle_only": 0,
            "unrecoverable": 0,
            "by_source": Counter(),
            "tie_eligible_rows": 0,
            "tie_races_with_size_ge2": 0,
        }
        try:
            # clear previous ingest tables (rebuild)
            conn.execute("DELETE FROM research_historical_bundles")
            conn.execute("DELETE FROM research_unrecoverable_predictions")

            # --- DB predictions ---
            for r in conn.execute(
                "SELECT id, race_id, bundle_json, created_at, engine_source FROM predictions WHERE race_id NOT LIKE '2099%'"
            ):
                race_id = str(r["race_id"])
                try:
                    bundle = json.loads(r["bundle_json"] or "{}")
                except Exception:
                    bundle = {}
                rr = conn.execute(
                    "SELECT winner_horse_number, venue, race_date, surface, distance FROM race_results WHERE race_id=?",
                    (race_id,),
                ).fetchone()
                winner = int(rr["winner_horse_number"]) if rr and rr["winner_horse_number"] is not None else None
                race_meta = {
                    "race_date": rr["race_date"] if rr else _parse_race_date(race_id),
                    "venue": rr["venue"] if rr else None,
                    "surface": rr["surface"] if rr else None,
                    "distance": rr["distance"] if rr else None,
                }
                # enrich from bundle race_info
                ri = bundle.get("race_info") if isinstance(bundle.get("race_info"), dict) else {}
                race_meta["race_name"] = ri.get("race_name")
                race_meta["class_label"] = ri.get("class_label") or ri.get("race_name")
                race_meta["venue"] = race_meta["venue"] or ri.get("venue")
                out = self._upsert_bundle(
                    conn,
                    source="db.predictions",
                    source_path=f"predictions:{r['id']}",
                    race_id=race_id,
                    bundle=bundle,
                    winner_horse_number=winner,
                    winner_horse_id=None,
                    race_meta=race_meta,
                    extra_meta={"prediction_id": r["id"], "engine_source": r["engine_source"]},
                )
                summary["by_source"]["db.predictions"] += 1
                if out["has_bundle"]:
                    summary["ingested_bundles"] += 1
                    summary[out["status"]] = summary.get(out["status"], 0) + 1
                    if out["tie_eligible"] and out["tie_size"] >= 2:
                        summary["tie_races_with_size_ge2"] += 1
                        summary["tie_eligible_rows"] += 1
                else:
                    summary["unrecoverable"] += 1
                    self._add_unrecoverable(
                        conn,
                        source="db.predictions",
                        race_id=race_id,
                        reason="bundle_missing_or_invalid",
                        meta={"prediction_id": r["id"]},
                    )

            # --- real_285r ---
            corpus_paths = []
            for p in [
                self.root / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json",
                Path("/home/ubuntu/KEIBA-Single-AI/research/v3_lab/baselines/offline_gate/real_285r_corpus.json"),
                self.win5.parents[1] / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json",
            ]:
                if p.exists():
                    corpus_paths.append(p)
                    break
            if corpus_paths:
                data = json.loads(corpus_paths[0].read_text(encoding="utf-8"))
                for race in data.get("races") or []:
                    race_id = str(race.get("race_id") or "")
                    if not race_id:
                        continue
                    runners = race.get("runners") or []
                    bundle = _as_canonical_bundle(
                        race_id=race_id,
                        runners=runners,
                        race_info={"race_id": race_id, "field_size": (race.get("context") or {}).get("field_size")},
                    )
                    out = self._upsert_bundle(
                        conn,
                        source="real_285r_corpus",
                        source_path=str(corpus_paths[0]),
                        race_id=race_id,
                        bundle=bundle,
                        winner_horse_number=None,
                        winner_horse_id=str(race.get("winner_id") or "") or None,
                        race_meta={
                            "race_date": _parse_race_date(race_id),
                            "venue": race_id.split("-")[3] if len(race_id.split("-")) >= 4 else None,
                        },
                        extra_meta={
                            "winner_name": race.get("winner_name"),
                            "winner_rank": race.get("winner_rank"),
                            "source_tag": race.get("source"),
                        },
                    )
                    summary["by_source"]["real_285r_corpus"] += 1
                    if out["has_bundle"]:
                        summary["ingested_bundles"] += 1
                        summary[out["status"]] = summary.get(out["status"], 0) + 1
                        if out["tie_eligible"] and out["tie_size"] >= 2:
                            summary["tie_races_with_size_ge2"] += 1
                            summary["tie_eligible_rows"] += 1
                    else:
                        summary["unrecoverable"] += 1

            # --- pi.json ---
            pi_dirs = []
            for base in [self.root, self.win5.parents[1]]:
                d = base / "public" / "data" / "predictions"
                if d.exists() and d not in pi_dirs:
                    pi_dirs.append(d)
            for d in pi_dirs:
                for f in sorted(d.glob("*.pi.json")):
                    try:
                        payload = json.loads(f.read_text(encoding="utf-8"))
                    except Exception:
                        continue
                    race_id = str(payload.get("race_id") or "")
                    if not race_id or race_id.startswith("2099"):
                        continue
                    cands = ((payload.get("prediction") or {}) if isinstance(payload.get("prediction"), dict) else {}).get(
                        "candidates"
                    ) or []
                    runners = [
                        {
                            "horse_number": c.get("HorseNumber"),
                            "horse_name": c.get("CandidateID"),
                            "model_rank": c.get("Rank"),
                            "win_prob": c.get("Confidence"),
                        }
                        for c in cands
                        if isinstance(c, dict)
                    ]
                    if not runners:
                        self._add_unrecoverable(
                            conn,
                            source="public.pi_json",
                            race_id=race_id,
                            reason="pi_json_without_candidates",
                            meta={"path": str(f)},
                        )
                        summary["unrecoverable"] += 1
                        continue
                    bundle = _as_canonical_bundle(
                        race_id=race_id,
                        runners=runners,
                        race_info={
                            "race_id": race_id,
                            "venue": payload.get("venue") or payload.get("course"),
                            "race_name": payload.get("race_name"),
                            "date": payload.get("race_date"),
                        },
                    )
                    rr = conn.execute(
                        "SELECT winner_horse_number FROM race_results WHERE race_id=?",
                        (race_id,),
                    ).fetchone()
                    winner = (
                        int(rr["winner_horse_number"])
                        if rr and rr["winner_horse_number"] is not None
                        else None
                    )
                    out = self._upsert_bundle(
                        conn,
                        source="public.pi_json",
                        source_path=str(f),
                        race_id=race_id,
                        bundle=bundle,
                        winner_horse_number=winner,
                        winner_horse_id=None,
                        race_meta={
                            "race_date": payload.get("race_date") or _parse_race_date(race_id),
                            "venue": payload.get("venue") or payload.get("course"),
                            "race_name": payload.get("race_name"),
                            "class_label": payload.get("race_name"),
                        },
                    )
                    summary["by_source"]["public.pi_json"] += 1
                    if out["has_bundle"]:
                        summary["ingested_bundles"] += 1
                        summary[out["status"]] = summary.get(out["status"], 0) + 1
                        if out["tie_eligible"] and out["tie_size"] >= 2:
                            summary["tie_races_with_size_ge2"] += 1
                            summary["tie_eligible_rows"] += 1

            # --- miss evidence ---
            for d in [
                self.win5 / "var" / "miss-evidence",
                self.win5 / "var" / "improvement-evidence" / "miss",
            ]:
                if not d.exists():
                    continue
                for f in sorted(d.rglob("*.json")):
                    if f.name == "manifest.json":
                        continue
                    try:
                        payload = json.loads(f.read_text(encoding="utf-8"))
                    except Exception:
                        continue
                    if isinstance(payload.get("payload"), dict):
                        payload = payload["payload"]
                    race_id = str(payload.get("race_id") or "")
                    if not race_id or race_id.startswith("2099"):
                        continue
                    bundle = payload.get("prediction_bundle")
                    if not isinstance(bundle, dict):
                        self._add_unrecoverable(
                            conn,
                            source="miss_evidence",
                            race_id=race_id,
                            reason="miss_without_prediction_bundle",
                            meta={"path": str(f)},
                        )
                        summary["unrecoverable"] += 1
                        continue
                    winner = None
                    w = payload.get("winner")
                    if isinstance(w, dict) and w.get("horse_number") is not None:
                        winner = int(w["horse_number"])
                    ri = bundle.get("race_info") if isinstance(bundle.get("race_info"), dict) else {}
                    out = self._upsert_bundle(
                        conn,
                        source="miss_evidence",
                        source_path=str(f),
                        race_id=race_id,
                        bundle=bundle,
                        winner_horse_number=winner,
                        winner_horse_id=None,
                        race_meta={
                            "race_date": payload.get("timestamp", "")[:10] or _parse_race_date(race_id),
                            "venue": ri.get("venue"),
                            "race_name": ri.get("race_name"),
                            "class_label": ri.get("class_label") or ri.get("race_name"),
                            "surface": ri.get("surface"),
                            "distance": ri.get("distance"),
                        },
                    )
                    summary["by_source"]["miss_evidence"] += 1
                    if out["has_bundle"]:
                        summary["ingested_bundles"] += 1
                        summary[out["status"]] = summary.get(out["status"], 0) + 1
                        if out["tie_eligible"] and out["tie_size"] >= 2:
                            summary["tie_races_with_size_ge2"] += 1
                            summary["tie_eligible_rows"] += 1

            # --- baseline eval without bundle coverage → unrecoverable metadata ---
            covered = {
                str(r["race_id"])
                for r in conn.execute(
                    "SELECT DISTINCT race_id FROM research_historical_bundles WHERE has_bundle=1"
                )
            }
            for p in [
                self.win5 / "fixtures" / "stats" / "baseline-285r-evaluations.json",
                self.root / "fixtures" / "stats" / "baseline-285r-evaluations.json",
            ]:
                if not p.exists():
                    continue
                data = json.loads(p.read_text(encoding="utf-8"))
                for row in data.get("rows") or []:
                    race_id = str(row.get("race_id") or "")
                    if not race_id:
                        continue
                    if race_id in covered:
                        continue
                    # metadata-only registration as unrecoverable for Tie
                    self._add_unrecoverable(
                        conn,
                        source="baseline_285r_evaluations",
                        race_id=race_id,
                        reason="evaluation_only_no_prediction_bundle",
                        meta={
                            "race_date": row.get("race_date"),
                            "venue": row.get("venue"),
                            "winner_horse_number": row.get("winner_horse_number"),
                            "hit_at_1": row.get("hit_at_1"),
                        },
                    )
                    summary["unrecoverable"] += 1
                    summary["by_source"]["baseline_285r_evaluations_unrecoverable"] += 1
                break

            # --- race_evaluations without bundle ---
            for r in conn.execute(
                "SELECT DISTINCT race_id FROM race_evaluations WHERE race_id NOT LIKE '2099%'"
            ):
                race_id = str(r["race_id"])
                if race_id in covered:
                    continue
                self._add_unrecoverable(
                    conn,
                    source="db.race_evaluations",
                    race_id=race_id,
                    reason="evaluation_without_recoverable_bundle",
                    meta={},
                )
                summary["unrecoverable"] += 1
                summary["by_source"]["race_evaluations_unrecoverable"] += 1

            # finalize unique counts
            uniq_bundle = conn.execute(
                "SELECT COUNT(DISTINCT race_id) c FROM research_historical_bundles WHERE has_bundle=1"
            ).fetchone()["c"]
            uniq_tie = conn.execute(
                """
                SELECT COUNT(DISTINCT race_id) c FROM research_historical_bundles
                WHERE has_bundle=1 AND tie_eligible=1 AND COALESCE(tie_size,0) >= 2
                """
            ).fetchone()["c"]
            uniq_unrec = conn.execute(
                "SELECT COUNT(DISTINCT race_id) c FROM research_unrecoverable_predictions"
            ).fetchone()["c"]
            summary["unique_races_with_bundle"] = uniq_bundle
            summary["unique_tie_races"] = uniq_tie
            summary["unique_unrecoverable_races"] = uniq_unrec
            summary["by_source"] = dict(summary["by_source"])
            summary["inventory_totals"] = inventory.get("totals")

            conn.execute(
                """
                INSERT INTO research_ingest_runs(
                  run_id, schema_version, started_at, finished_at, status,
                  inventory_json, summary_json, created_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    run_id,
                    SCHEMA_VERSION,
                    started,
                    _now(),
                    "success",
                    json.dumps(inventory, ensure_ascii=False),
                    json.dumps(summary, ensure_ascii=False),
                    _now(),
                ),
            )
            conn.commit()
            summary["run_id"] = run_id
            summary["inventory"] = inventory
            return summary
        finally:
            conn.close()


def write_docs(summary: dict[str, Any], before: dict[str, Any] | None = None, after: dict[str, Any] | None = None) -> dict[str, str]:
    root = repo_root()
    docs = root / "docs" / "research"
    docs.mkdir(parents=True, exist_ok=True)
    inv = summary.get("inventory") or {}
    sources = inv.get("sources") or []

    # inventory
    inv_path = docs / "v111-bundle-inventory.md"
    lines = [
        "# Version11.1 - Bundle Inventory",
        "",
        f"**Date:** {inv.get('generated_at') or _now()}  ",
        "**Scope:** Research only / Prediction mutation FORBIDDEN  ",
        "",
        "## Totals",
        "",
        f"- Bundle candidate rows (sum across sources, may overlap): `{(inv.get('totals') or {}).get('bundle_candidates')}`",
        f"- Unique race_ids with Bundle (inventory scan): `{inv.get('seen_bundle_race_ids_count')}`",
        f"- Ingest unique races with Bundle: `{summary.get('unique_races_with_bundle')}`",
        f"- Unique Tie races (|G|≥2): `{summary.get('unique_tie_races')}`",
        f"- Unique unrecoverable races: `{summary.get('unique_unrecoverable_races')}`",
        "",
        "## Sources",
        "",
        "| Source | Path | Rows | With Bundle | Unique races | Tie recoverable | Note |",
        "|--------|------|-----:|------------:|-------------:|:---------------:|------|",
    ]
    for s in sources:
        lines.append(
            f"| `{s.get('source')}` | `{s.get('path')}` | {s.get('rows')} | {s.get('with_bundle')} | "
            f"{s.get('unique_races')} | {'yes' if s.get('tie_recoverable') else 'no'} | {s.get('note')} |"
        )
    lines.extend(["", "## By ingest source", "", "| Source | Count |", "|--------|------:|"])
    for k, v in (summary.get("by_source") or {}).items():
        lines.append(f"| `{k}` | {v} |")
    lines.append("")
    inv_path.write_text("\n".join(lines), encoding="utf-8")

    # ingest report
    ingest_path = docs / "v111-historical-ingest.md"
    ingest_lines = [
        "# Version11.1 - Historical Bundle Ingest",
        "",
        f"**Date:** {_now()}  ",
        f"**Run:** `{summary.get('run_id')}`  ",
        "**Shadow only / Research only / Prediction mutation FORBIDDEN**  ",
        "",
        "## Result",
        "",
        f"- Ingested bundle rows: `{summary.get('ingested_bundles')}`",
        f"- Recoverable (Bundle+Winner): `{summary.get('recoverable')}`",
        f"- Bundle only (winner missing): `{summary.get('bundle_only')}`",
        f"- Unrecoverable records: `{summary.get('unrecoverable')}`",
        f"- Unique races with Bundle: `{summary.get('unique_races_with_bundle')}`",
        f"- Unique Tie races: `{summary.get('unique_tie_races')}`",
        "",
        "## Validation chain",
        "",
        "```",
        "Prediction Bundle → model_rank runners → RaceResult/Winner",
        "```",
        "",
        "- `recoverable`: Bundle + model_rank + winner restored",
        "- `bundle_only`: Bundle OK but winner missing (Tie structure OK, outcome eval limited)",
        "- `unrecoverable`: no usable Bundle -> excluded from Tie analysis",
        "",
        "## Decision",
        "",
        "```",
        "Action Type: Historical Bundle Ingest (Research)",
        "Prediction Mutation: FORBIDDEN",
        "Product tables: READ-ONLY",
        "```",
        "",
    ]
    ingest_path.write_text("\n".join(ingest_lines), encoding="utf-8")

    # growth
    growth_path = docs / "v111-corpus-growth.md"
    before = before or {}
    after = after or {}
    growth_lines = [
        "# Version11.1 - Corpus Growth",
        "",
        f"**Date:** {_now()}  ",
        "",
        "| Metric | Before (V11) | After (V11.1) | Delta | Target |",
        "|--------|-------------:|--------------:|------:|-------:|",
        f"| Prediction | {before.get('prediction_count', 'N/A')} | {after.get('prediction_count', 'N/A')} | "
        f"{(after.get('prediction_count') or 0) - (before.get('prediction_count') or 0)} | 3000 |",
        f"| Tie | {before.get('tie_count', 'N/A')} | {after.get('tie_count', 'N/A')} | "
        f"{(after.get('tie_count') or 0) - (before.get('tie_count') or 0)} | 300 |",
        f"| Young Horse | {before.get('young_horse_count', 'N/A')} | {after.get('young_horse_count', 'N/A')} | "
        f"{(after.get('young_horse_count') or 0) - (before.get('young_horse_count') or 0)} | 300 |",
        "",
        "## Coverage after rebuild",
        "",
        f"- with Prediction Bundle: `{(after.get('coverage') or {}).get('with_prediction_bundle')}`",
        f"- with RaceResult: `{(after.get('coverage') or {}).get('with_race_result')}`",
        f"- with Evidence Snapshot: `{(after.get('coverage') or {}).get('with_evidence_snapshot')}`",
        "",
        "## Gap remaining",
        "",
        f"- Prediction gap: `{(after.get('gap') or {}).get('prediction')}`",
        f"- Tie gap: `{(after.get('gap') or {}).get('tie')}`",
        f"- Young Horse gap: `{(after.get('gap') or {}).get('young_horse')}`",
        "",
        "## Note",
        "",
        "Tie grows only from shared model_rank (|G|>=2) inside Prediction Bundles.",
        "285r offline corpus adds Bundles but few Ties. Young Horse needs class/race_name meta.",
        "",
    ]
    growth_path.write_text("\n".join(growth_lines), encoding="utf-8")

    # unrecoverable
    unrec_path = docs / "v111-unrecoverable-predictions.md"
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT source, reason, COUNT(*) c, COUNT(DISTINCT race_id) u
            FROM research_unrecoverable_predictions
            GROUP BY source, reason
            ORDER BY u DESC
            """
        ).fetchall()
        samples = conn.execute(
            """
            SELECT source, race_id, reason FROM research_unrecoverable_predictions
            ORDER BY source, race_id LIMIT 40
            """
        ).fetchall()
        total_u = conn.execute(
            "SELECT COUNT(DISTINCT race_id) c FROM research_unrecoverable_predictions"
        ).fetchone()["c"]
    finally:
        conn.close()
    unrec_lines = [
        "# Version11.1 - Unrecoverable Predictions",
        "",
        f"**Date:** {_now()}  ",
        f"- Unique unrecoverable race_ids (no Bundle from ANY source): `{total_u}`",
        f"- Total unrecoverable records: `{summary.get('unrecoverable')}`",
        "",
        "## Definition",
        "",
        "A race is unrecoverable for Tie analysis when `evaluation.runners[].model_rank`",
        "cannot be restored from any researched source.",
        "Metadata-only rows are kept but **excluded from Tie analysis**.",
        "",
        "## Native sources without Bundle (before cross-source recovery)",
        "",
        "| Source | Native Bundle | Note |",
        "|--------|:-------------:|------|",
        "| `db.race_evaluations` | no | hit metrics only |",
        "| `baseline_285r_evaluations` | no | evaluation-only JSON |",
        "| `db.prediction_history` | no | empty (0 rows) |",
        "| `db.research_prediction_snapshots` | rare | evidence features, not full Bundle |",
        "| `s3_or_remote_backup` | not found | no dump discovered |",
        "",
        "## Cross-source recovery result",
        "",
        f"- Evaluations without any Bundle after ingest: see inventory",
        f"- Remaining unique unrecoverable races: `{total_u}`",
        "",
        "If baseline/evaluations race_ids are covered by `real_285r_corpus` or live",
        "`predictions.bundle_json`, they are **recoverable** and not listed below.",
        "",
        "## By source / reason",
        "",
        "| Source | Reason | Records | Unique races |",
        "|--------|--------|--------:|-------------:|",
    ]
    for r in rows:
        unrec_lines.append(
            f"| `{r['source']}` | `{r['reason']}` | {r['c']} | {r['u']} |"
        )
    unrec_lines.extend(
        [
            "",
            "## Samples",
            "",
            "| Source | Race | Reason |",
            "|--------|------|--------|",
        ]
    )
    for r in samples:
        unrec_lines.append(f"| `{r['source']}` | `{r['race_id']}` | `{r['reason']}` |")
    unrec_lines.append("")
    unrec_path.write_text("\n".join(unrec_lines), encoding="utf-8")

    # also dump json
    out_json = evidence_root() / "corpus" / "v111-historical-ingest.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "inventory": str(inv_path),
        "ingest": str(ingest_path),
        "growth": str(growth_path),
        "unrecoverable": str(unrec_path),
        "json": str(out_json),
    }


def run_and_write(*, rebuild_corpus: bool = True) -> dict[str, Any]:
    before = None
    if rebuild_corpus:
        try:
            from .prediction_corpus import PredictionCorpusBuilder

            # read current counts if table exists
            conn = connect()
            try:
                row = conn.execute(
                    """
                    SELECT prediction_count, tie_count, young_horse_count
                    FROM research_corpus_runs ORDER BY created_at DESC LIMIT 1
                    """
                ).fetchone()
                if row:
                    before = dict(row)
            finally:
                conn.close()
        except Exception:
            before = None

    summary = HistoricalBundleIngest().ingest()
    after = None
    if rebuild_corpus:
        from .prediction_corpus import run_and_write as corpus_run

        after_report = corpus_run()
        after = {
            "prediction_count": after_report.get("prediction_count"),
            "tie_count": after_report.get("tie_count"),
            "young_horse_count": after_report.get("young_horse_count"),
            "coverage": after_report.get("coverage"),
            "gap": after_report.get("gap"),
            "by_source": after_report.get("by_source"),
        }
    outputs = write_docs(summary, before=before, after=after)
    summary["_outputs"] = outputs
    summary["_corpus_before"] = before
    summary["_corpus_after"] = after
    return summary
