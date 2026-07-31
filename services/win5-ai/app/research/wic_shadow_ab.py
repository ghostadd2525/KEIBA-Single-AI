# -*- coding: utf-8 -*-
"""
Version34 — World Input Contract Shadow AB

Shadow-only evaluation of WIC-reconstructed signals vs Current Production.
NO Production / Prediction / World Trigger / Signal Service / CSV mutation.

Arms:
  Control — Production snapshot signals + assigned world + frozen PE pick
  Shadow  — WIC difficulty reconstruction (+ optional chaos diagnostic) →
            first-match World simulation; SAME frozen PE pick for Hit/Purchase

Governance (non-inferiority):
  Hit >= Baseline, Purchase >= Baseline, rank710 not worse, other miss not worse

V35 Signal Service design is gated on ROI contribution proof, not only
non-inferiority (see governance doc).
"""
from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from ..data.db import connect, migrate
from .config import evidence_root, repo_root
from .difficulty_signal_audit import reconstruct_leg_upset
from .world_boundary_research import EXISTING_WORLDS, extract_world_label
from .world_fitness_research import trigger_proximity_fitness
from .world_trigger_saturation import (
    DESIGN_SHARE,
    evaluate_all_rules,
    first_match_world,
    normalize_signals,
)
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-wic-shadow-ab/1.0"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _f(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        x = float(v)
        if math.isnan(x):
            return None
        return x
    except (TypeError, ValueError):
        return None


def _i(v: Any) -> int | None:
    try:
        if v is None or v == "":
            return None
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _mean(vals: list[float]) -> float | None:
    return (sum(vals) / len(vals)) if vals else None


def _pick_horse_number(bundle: dict[str, Any]) -> int | None:
    for path in (
        ("selection", "top_pick", "horse_number"),
        ("selection", "primary", "horse_number"),
        ("evaluation", "top_pick", "horse_number"),
        ("picks", "top1", "horse_number"),
    ):
        cur: Any = bundle
        ok = True
        for k in path:
            if not isinstance(cur, dict) or k not in cur:
                ok = False
                break
            cur = cur[k]
        if ok:
            n = _i(cur)
            if n is not None:
                return n
    runners = bundle.get("runners") or bundle.get("candidates") or []
    if isinstance(runners, list) and runners:

        def key(r: dict[str, Any]) -> tuple:
            return (
                _i(r.get("model_rank")) or 999,
                -(_f(r.get("win_prob")) or 0.0),
                _i(r.get("horse_number")) or 999,
            )

        ordered = sorted([r for r in runners if isinstance(r, dict)], key=key)
        if ordered:
            return _i(ordered[0].get("horse_number"))
    return None


def _winner_model_rank(bundle: dict[str, Any], winner: int | None) -> int | None:
    if winner is None:
        return None
    runners = bundle.get("runners") or bundle.get("candidates") or []
    if not isinstance(runners, list):
        return None
    for r in runners:
        if not isinstance(r, dict):
            continue
        if _i(r.get("horse_number")) == winner:
            return _i(r.get("model_rank")) or _i(r.get("rank"))
    return None


def _miss_bucket(hit: bool, winner_rank: int | None) -> str:
    if hit:
        return "hit"
    wr = winner_rank if winner_rank is not None else 999
    if 4 <= wr <= 6:
        return "rank46"
    if 7 <= wr <= 10:
        return "rank710"
    if 2 <= wr <= 3:
        return "other_1_3"
    if 11 <= wr <= 13:
        return "other_10_13"
    return "other"


def _frame_num(frame: Any, col: str) -> float | None:
    if frame is None or col not in getattr(frame, "columns", []):
        return None
    try:
        import pandas as pd

        s = pd.to_numeric(frame[col], errors="coerce").dropna()
        if s.empty:
            return None
        return float(s.iloc[0])
    except Exception:
        return None


def _frame_mean(frame: Any, col: str) -> float | None:
    if frame is None or col not in getattr(frame, "columns", []):
        return None
    try:
        import pandas as pd

        s = pd.to_numeric(frame[col], errors="coerce").dropna()
        if s.empty:
            return None
        return float(s.mean())
    except Exception:
        return None


def reconstruct_wic_difficulty(frame: Any) -> dict[str, Any]:
    notes: list[str] = []
    win5 = _frame_num(frame, "win5_leg")
    horse_count = _frame_num(frame, "horse_count")
    alias_field = False
    if horse_count is None:
        horse_count = _frame_num(frame, "field_size")
        if horse_count is not None:
            alias_field = True
            notes.append("horse_count_aliased_from_field_size_shadow_only")

    pcr = _frame_num(frame, "pace_collapse_risk")
    pcr_bridge = False
    if pcr is None:
        pcr = _frame_num(frame, "pace_collapse_risk_v2")
        if pcr is not None:
            pcr_bridge = True
            notes.append("pace_collapse_risk_bridged_from_v2_shadow_only")

    se = _frame_mean(frame, "style_entropy")
    if se is None:
        notes.append("style_entropy_missing_zero_fill_partial")

    recon = reconstruct_leg_upset(
        win5_leg=win5,
        horse_count=horse_count,
        pace_collapse_risk=pcr,
        style_entropy=se,
        sashi_count=_frame_mean(frame, "sashi_count"),
        oikomi_count=_frame_mean(frame, "oikomi_count"),
        unknown_count=_frame_mean(frame, "unknown_count"),
    )
    full = (
        win5 is not None
        and horse_count is not None
        and not alias_field
        and pcr is not None
        and not pcr_bridge
        and se is not None
    )
    return {
        "difficulty": recon["reconstructed_difficulty"],
        "components": recon["components"],
        "full_wic": full,
        "partial_wic": not full,
        "alias_field_size": alias_field,
        "pcr_v2_bridge": pcr_bridge,
        "notes": notes,
        "inputs": recon["inputs_used"],
    }


def probe_chaos_diagnostic(race_id: str) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False, "chaos_mean": None, "error": None}
    try:
        from app.engine.adapters.single_prediction_mapper import resolve_core_race_id
        from ai_platform.core.candidate_evaluation import CorePipeline

        cid = resolve_core_race_id(race_id)
        if not cid:
            out["error"] = "no_core_id"
            return out
        pipe = CorePipeline()
        ce = pipe.evaluate(str(cid))
        diag = ((ce or {}).get("scores") or {}).get("_diagnostic")
        if diag is None:
            out["error"] = "no_diagnostic"
            return out
        if hasattr(diag, "columns") and "chaos_score" in diag.columns:
            import pandas as pd

            s = pd.to_numeric(diag["chaos_score"], errors="coerce").dropna()
            if not s.empty:
                out["ok"] = True
                out["chaos_mean"] = float(s.mean())
                return out
        out["error"] = "chaos_not_in_diagnostic"
    except Exception as e:
        out["error"] = f"{type(e).__name__}:{e}"
    return out


def load_feature_frame(race_id: str) -> Any:
    try:
        from ai_platform.core.features import FeatureLoader

        loaded = FeatureLoader().load(str(race_id))
        if loaded is None:
            return None
        return loaded.frame
    except Exception:
        return None


class WicShadowAB:
    def __init__(self, *, chaos_probe_limit: int = 40) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()
        self.chaos_probe_limit = chaos_probe_limit

    def _load_races(self) -> list[dict[str, Any]]:
        conn = connect()
        cur = conn.cursor()
        corpus = cur.execute(
            """
            SELECT race_id, prediction_id, winner_horse_number, prediction_pick,
                   snapshot_id, meta_json
            FROM research_prediction_corpus
            WHERE has_race_result = 1
              AND winner_horse_number IS NOT NULL
              AND prediction_pick IS NOT NULL
            """
        ).fetchall()
        by_race: dict[str, dict[str, Any]] = {}
        for row in corpus:
            rid = str(row["race_id"])
            by_race[rid] = {
                "race_id": rid,
                "prediction_id": row["prediction_id"],
                "winner": _i(row["winner_horse_number"]),
                "pick": _i(row["prediction_pick"]),
                "snapshot_id": row["snapshot_id"],
            }

        evals = cur.execute(
            """
            SELECT e.race_id, e.prediction_id, e.hit_at_1, e.miss_category,
                   r.winner_horse_number, p.bundle_json
            FROM race_evaluations e
            JOIN race_results r ON r.race_id = e.race_id
            LEFT JOIN predictions p ON p.id = e.prediction_id
            WHERE r.winner_horse_number IS NOT NULL
            ORDER BY e.id DESC
            """
        ).fetchall()
        for row in evals:
            rid = str(row["race_id"])
            if rid in by_race and by_race[rid].get("pick") is not None:
                by_race[rid]["hit_at_1"] = int(row["hit_at_1"] or 0)
                by_race[rid]["miss_category"] = row["miss_category"]
                if row["bundle_json"] and "bundle" not in by_race[rid]:
                    try:
                        by_race[rid]["bundle"] = json.loads(row["bundle_json"] or "{}")
                    except Exception:
                        pass
                continue
            bundle: dict[str, Any] = {}
            try:
                bundle = json.loads(row["bundle_json"] or "{}")
            except Exception:
                bundle = {}
            pick = _pick_horse_number(bundle)
            winner = _i(row["winner_horse_number"])
            by_race[rid] = {
                "race_id": rid,
                "prediction_id": row["prediction_id"],
                "winner": winner,
                "pick": pick,
                "hit_at_1": int(row["hit_at_1"] or 0),
                "miss_category": row["miss_category"],
                "bundle": bundle,
            }

        snaps = {
            str(r["race_id"]): r
            for r in cur.execute(
                "SELECT race_id, prediction_id, payload_json FROM research_prediction_snapshots"
            ).fetchall()
        }
        preds = {
            int(r["id"]): r
            for r in cur.execute("SELECT id, race_id, bundle_json FROM predictions").fetchall()
        }

        out = []
        for rid, rec in by_race.items():
            if rec.get("winner") is None or rec.get("pick") is None:
                continue
            snap = snaps.get(rid)
            signals_raw: dict[str, Any] = {}
            if snap:
                try:
                    payload = json.loads(snap["payload_json"] or "{}")
                    rws = payload.get("research_world_signals") or {}
                    signals_raw = rws.get("signals") or {}
                except Exception:
                    signals_raw = {}
            if "bundle" not in rec:
                pid = rec.get("prediction_id")
                if pid and int(pid) in preds:
                    try:
                        rec["bundle"] = json.loads(preds[int(pid)]["bundle_json"] or "{}")
                    except Exception:
                        rec["bundle"] = {}
            bundle = rec.get("bundle") or {}
            assigned, sub = extract_world_label(bundle)
            out.append(
                {
                    **rec,
                    "signals_raw": signals_raw,
                    "assigned_world": assigned if assigned in EXISTING_WORLDS else None,
                    "sub_world": sub,
                    "bundle": bundle,
                }
            )
        return out

    def analyze(self) -> dict[str, Any]:
        races = self._load_races()
        rows: list[dict[str, Any]] = []
        chaos_probes = 0

        for rec in races:
            rid = rec["race_id"]
            ctrl_sig = normalize_signals(rec.get("signals_raw"))
            ctrl_rules = evaluate_all_rules(ctrl_sig)
            ctrl_sim = first_match_world(ctrl_rules)
            ctrl_world = rec.get("assigned_world") or ctrl_sim

            frame = load_feature_frame(rid)
            if frame is not None:
                wic = reconstruct_wic_difficulty(frame)
            else:
                wic = {
                    "difficulty": None,
                    "full_wic": False,
                    "partial_wic": True,
                    "notes": ["feature_frame_missing"],
                    "alias_field_size": False,
                    "pcr_v2_bridge": False,
                }

            shadow_sig = dict(ctrl_sig)
            reliability_flags: list[str] = []
            if wic.get("difficulty") is not None:
                shadow_sig["difficulty"] = float(wic["difficulty"])
            else:
                reliability_flags.append("difficulty_unreconstructed")

            if chaos_probes < self.chaos_probe_limit:
                chaos_info = probe_chaos_diagnostic(rid)
                chaos_probes += 1
                if chaos_info.get("ok") and chaos_info.get("chaos_mean") is not None:
                    shadow_sig["chaos"] = float(chaos_info["chaos_mean"])
                else:
                    reliability_flags.append("chaos_unsatisfied")
            else:
                reliability_flags.append("chaos_probe_skipped")

            if wic.get("partial_wic"):
                reliability_flags.append("wic_partial")
            if wic.get("full_wic"):
                reliability_flags.append("wic_full")

            sh_world = first_match_world(evaluate_all_rules(shadow_sig))

            winner = rec["winner"]
            pick = rec["pick"]
            hit = bool(pick == winner)
            purchase = hit
            wr = _winner_model_rank(rec.get("bundle") or {}, winner)
            miss = _miss_bucket(hit, wr)

            ctrl_fit = trigger_proximity_fitness(ctrl_sig)
            sh_fit = trigger_proximity_fitness(shadow_sig)

            rows.append(
                {
                    "race_id": rid,
                    "pick": pick,
                    "winner": winner,
                    "hit": hit,
                    "purchase": purchase,
                    "winner_rank": wr,
                    "miss_bucket": miss,
                    "control_world": ctrl_world,
                    "control_sim_world": ctrl_sim,
                    "shadow_world": sh_world,
                    "world_changed": ctrl_world != sh_world,
                    "control_difficulty": ctrl_sig.get("difficulty"),
                    "shadow_difficulty": shadow_sig.get("difficulty"),
                    "control_chaos": ctrl_sig.get("chaos"),
                    "shadow_chaos": shadow_sig.get("chaos"),
                    "wic": {
                        "full": bool(wic.get("full_wic")),
                        "partial": bool(wic.get("partial_wic")),
                        "alias_field_size": bool(wic.get("alias_field_size")),
                        "pcr_v2_bridge": bool(wic.get("pcr_v2_bridge")),
                        "notes": wic.get("notes") or [],
                    },
                    "reliability_flags": reliability_flags,
                    "control_fitness": ctrl_fit.get("soft"),
                    "shadow_fitness": sh_fit.get("soft"),
                    "frozen_pe_pick": True,
                }
            )

        return self._aggregate(rows)

    def _arm_metrics(self, rows: list[dict[str, Any]], world_key: str) -> dict[str, Any]:
        hits = sum(1 for r in rows if r["hit"])
        purch = sum(1 for r in rows if r["purchase"])
        buckets = Counter(r["miss_bucket"] for r in rows)
        worlds = Counter(r[world_key] for r in rows if r.get(world_key))
        return {
            "n": len(rows),
            "hit": hits,
            "hit_rate": _safe_div(hits, len(rows)),
            "purchase": purch,
            "purchase_rate": _safe_div(purch, len(rows)),
            "rank46": buckets.get("rank46", 0),
            "rank46_rate": _safe_div(buckets.get("rank46", 0), len(rows)),
            "rank710": buckets.get("rank710", 0),
            "rank710_rate": _safe_div(buckets.get("rank710", 0), len(rows)),
            "other_1_3": buckets.get("other_1_3", 0),
            "other_1_3_rate": _safe_div(buckets.get("other_1_3", 0), len(rows)),
            "other_10_13": buckets.get("other_10_13", 0),
            "other_10_13_rate": _safe_div(buckets.get("other_10_13", 0), len(rows)),
            "other": buckets.get("other", 0),
            "other_rate": _safe_div(buckets.get("other", 0), len(rows)),
            "other_miss": buckets.get("other_1_3", 0)
            + buckets.get("other_10_13", 0)
            + buckets.get("other", 0),
            "world_distribution": {
                w: {"n": worlds.get(w, 0), "rate": _safe_div(worlds.get(w, 0), len(rows))}
                for w in EXISTING_WORLDS
            },
            "design_share_ref": DESIGN_SHARE,
        }

    def _aggregate(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        control = self._arm_metrics(rows, "control_world")
        shadow = self._arm_metrics(rows, "shadow_world")

        transitions: Counter[str] = Counter()
        hit_impact = {"improved": 0, "worsened": 0, "unchanged": 0, "n_changed_world": 0}
        changed_rows = []
        for r in rows:
            if r["world_changed"]:
                hit_impact["n_changed_world"] += 1
                transitions[f"{r['control_world']}->{r['shadow_world']}"] += 1
                hit_impact["unchanged"] += 1
                changed_rows.append(
                    {
                        "race_id": r["race_id"],
                        "from": r["control_world"],
                        "to": r["shadow_world"],
                        "hit": r["hit"],
                        "control_difficulty": r["control_difficulty"],
                        "shadow_difficulty": r["shadow_difficulty"],
                        "wic": r["wic"],
                    }
                )

        def activation(world_key: str) -> dict[str, Any]:
            counts = Counter(r[world_key] for r in rows)
            return {
                w: {
                    "n": counts.get(w, 0),
                    "rate": _safe_div(counts.get(w, 0), len(rows)),
                    "design": DESIGN_SHARE.get(w),
                }
                for w in EXISTING_WORLDS
            }

        def mean_self_fit(fit_key: str, world_key: str) -> float | None:
            vals = []
            for r in rows:
                fit = r.get(fit_key) or {}
                w = r.get(world_key)
                if w and isinstance(fit, dict) and fit.get(w) is not None:
                    vals.append(float(fit[w]))
            return _mean(vals)

        cov = {
            "control_difficulty_present_rate": _safe_div(
                sum(1 for r in rows if r["control_difficulty"] is not None), len(rows)
            ),
            "shadow_difficulty_present_rate": _safe_div(
                sum(1 for r in rows if r["shadow_difficulty"] is not None), len(rows)
            ),
            "control_chaos_present_rate": _safe_div(
                sum(1 for r in rows if r["control_chaos"] is not None), len(rows)
            ),
            "shadow_chaos_present_rate": _safe_div(
                sum(1 for r in rows if r["shadow_chaos"] is not None), len(rows)
            ),
            "wic_full_rate": _safe_div(sum(1 for r in rows if r["wic"]["full"]), len(rows)),
            "wic_partial_rate": _safe_div(sum(1 for r in rows if r["wic"]["partial"]), len(rows)),
            "alias_field_size_rate": _safe_div(
                sum(1 for r in rows if r["wic"]["alias_field_size"]), len(rows)
            ),
            "pcr_v2_bridge_rate": _safe_div(
                sum(1 for r in rows if r["wic"]["pcr_v2_bridge"]), len(rows)
            ),
        }

        sh_diffs = [float(r["shadow_difficulty"]) for r in rows if r["shadow_difficulty"] is not None]
        ctrl_diffs = [
            float(r["control_difficulty"]) for r in rows if r["control_difficulty"] is not None
        ]

        delta = {
            "hit": shadow["hit"] - control["hit"],
            "purchase": shadow["purchase"] - control["purchase"],
            "rank710": shadow["rank710"] - control["rank710"],
            "other_miss": shadow["other_miss"] - control["other_miss"],
            "rank46": shadow["rank46"] - control["rank46"],
            "other_1_3": shadow["other_1_3"] - control["other_1_3"],
            "other_10_13": shadow["other_10_13"] - control["other_10_13"],
        }

        gov_checks = {
            "hit_ge_baseline": shadow["hit"] >= control["hit"],
            "purchase_ge_baseline": shadow["purchase"] >= control["purchase"],
            "rank710_not_worse": shadow["rank710"] <= control["rank710"],
            "other_miss_not_worse": shadow["other_miss"] <= control["other_miss"],
        }
        non_inferior = all(gov_checks.values())

        roi_proof = {
            "hit_delta": delta["hit"],
            "purchase_delta": delta["purchase"],
            "frozen_pe_pick": True,
            "world_changed_n": hit_impact["n_changed_world"],
            "hit_improved_on_world_change": hit_impact["improved"],
            "hit_worsened_on_world_change": hit_impact["worsened"],
            "proven_positive_roi_contribution": bool(delta["hit"] > 0),
            "status": (
                "PROVEN_POSITIVE"
                if delta["hit"] > 0
                else "INCONCLUSIVE_FROZEN_PE"
                if delta["hit"] == 0
                else "NEGATIVE"
            ),
        }

        v35_gate = {
            "non_inferiority_pass": non_inferior,
            "roi_contribution_proven": roi_proof["proven_positive_roi_contribution"],
            "allow_signal_service_design_v35": bool(
                non_inferior and roi_proof["proven_positive_roi_contribution"]
            ),
            "reason": (
                "Hit lift observed under Shadow WIC"
                if roi_proof["proven_positive_roi_contribution"]
                else "Hit unchanged: PE pick frozen; World reclassification alone does not alter Prediction top pick in this AB"
            ),
        }

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "product_mutation": False,
            "signal_service_implemented": False,
            "n_races": len(rows),
            "control": control,
            "shadow": shadow,
            "delta": delta,
            "world_transition": {
                "n_changed": hit_impact["n_changed_world"],
                "change_rate": _safe_div(hit_impact["n_changed_world"], len(rows)),
                "matrix_counts": dict(transitions),
                "examples": changed_rows[:25],
            },
            "hit_impact_on_world_change": hit_impact,
            "world_activation": {
                "control": activation("control_world"),
                "shadow": activation("shadow_world"),
            },
            "world_fitness": {
                "control_mean_self_fit": mean_self_fit("control_fitness", "control_world"),
                "shadow_mean_self_fit": mean_self_fit("shadow_fitness", "shadow_world"),
            },
            "signal_coverage": cov,
            "signal_reliability": {
                "control_difficulty_unique_n": len({round(x, 6) for x in ctrl_diffs}),
                "shadow_difficulty_unique_n": len({round(x, 6) for x in sh_diffs}),
                "control_difficulty_mean": _mean(ctrl_diffs),
                "shadow_difficulty_mean": _mean(sh_diffs),
                "control_difficulty_std": (
                    math.sqrt(
                        sum((x - (_mean(ctrl_diffs) or 0.0)) ** 2 for x in ctrl_diffs)
                        / len(ctrl_diffs)
                    )
                    if ctrl_diffs
                    else None
                ),
                "shadow_difficulty_std": (
                    math.sqrt(
                        sum((x - (_mean(sh_diffs) or 0.0)) ** 2 for x in sh_diffs) / len(sh_diffs)
                    )
                    if sh_diffs
                    else None
                ),
                "note": "Shadow difficulty may be partial WIC (alias/v2/missing entropy)",
            },
            "governance_checks": gov_checks,
            "governance_non_inferiority": "PASS" if non_inferior else "FAIL",
            "roi_proof": roi_proof,
            "v35_gate": v35_gate,
            "method": {
                "control": "Production research_world_signals + assigned/sim world; frozen PE pick",
                "shadow": "WIC reconstruct difficulty from FeatureLoader; optional chaos diagnostic; first-match world; frozen PE pick",
                "purchase_proxy": "purchase == hit (no Delete layer on corpus)",
                "miss_taxonomy": "rank46=4-6, rank710=7-10, other_1_3=2-3, other_10_13=11-13",
            },
            "races": rows,
        }


def _md_summary(report: dict[str, Any]) -> str:
    c, s, d = report["control"], report["shadow"], report["delta"]
    v35 = report["v35_gate"]
    lines = [
        "# Version34 — WIC Shadow AB Summary",
        "",
        f"**Date:** {report['generated_at']}  ",
        f"**Schema:** `{report['schema_version']}`  ",
        f"**N races:** `{report['n_races']}`  ",
        "",
        "## Verdict",
        "",
        f"- Non-inferiority governance: **{report['governance_non_inferiority']}**",
        f"- ROI contribution proof: **{report['roi_proof']['status']}**",
        f"- Allow V35 Signal Service design: **{v35['allow_signal_service_design_v35']}**",
        f"- Reason: {v35['reason']}",
        "",
        "## Method",
        "",
        f"- Control: {report['method']['control']}",
        f"- Shadow: {report['method']['shadow']}",
        f"- product_mutation: `{report['product_mutation']}`",
        f"- signal_service_implemented: `{report['signal_service_implemented']}`",
        "",
        "## KPI comparison",
        "",
        "| Metric | Control | Shadow | Delta |",
        "|--------|--------:|-------:|------:|",
        f"| Hit | {c['hit']} ({_pct(c['hit_rate'])}) | {s['hit']} ({_pct(s['hit_rate'])}) | {d['hit']} |",
        f"| Purchase | {c['purchase']} ({_pct(c['purchase_rate'])}) | {s['purchase']} ({_pct(s['purchase_rate'])}) | {d['purchase']} |",
        f"| rank46 | {c['rank46']} | {s['rank46']} | {d['rank46']} |",
        f"| rank710 | {c['rank710']} | {s['rank710']} | {d['rank710']} |",
        f"| other_1_3 | {c['other_1_3']} | {s['other_1_3']} | {d['other_1_3']} |",
        f"| other_10_13 | {c['other_10_13']} | {s['other_10_13']} | {d['other_10_13']} |",
        f"| other_miss (sum) | {c['other_miss']} | {s['other_miss']} | {d['other_miss']} |",
        "",
        "## World distribution",
        "",
        "| World | Control | Shadow | Design ref |",
        "|-------|--------:|-------:|-----------:|",
    ]
    for w in EXISTING_WORLDS:
        cw = c["world_distribution"][w]
        sw = s["world_distribution"][w]
        lines.append(
            f"| `{w}` | {_pct(cw['rate'])} (n={cw['n']}) | {_pct(sw['rate'])} (n={sw['n']}) | "
            f"{_pct(DESIGN_SHARE.get(w))} |"
        )
    cov = report["signal_coverage"]
    rel = report["signal_reliability"]
    lines += [
        "",
        "## Signal coverage / reliability",
        "",
        f"- Control difficulty present: `{_pct(cov['control_difficulty_present_rate'])}`",
        f"- Shadow difficulty present: `{_pct(cov['shadow_difficulty_present_rate'])}`",
        f"- Control chaos present: `{_pct(cov['control_chaos_present_rate'])}`",
        f"- Shadow chaos present: `{_pct(cov['shadow_chaos_present_rate'])}`",
        f"- WIC full rate: `{_pct(cov['wic_full_rate'])}`",
        f"- WIC partial rate: `{_pct(cov['wic_partial_rate'])}`",
        f"- field_size alias rate: `{_pct(cov['alias_field_size_rate'])}`",
        f"- pace_collapse v2 bridge rate: `{_pct(cov['pcr_v2_bridge_rate'])}`",
        f"- Control difficulty unique_n: `{rel['control_difficulty_unique_n']}` mean=`{rel['control_difficulty_mean']}`",
        f"- Shadow difficulty unique_n: `{rel['shadow_difficulty_unique_n']}` mean=`{rel['shadow_difficulty_mean']}` std=`{rel['shadow_difficulty_std']}`",
        "",
        "## World fitness (mean self-fit)",
        "",
        f"- Control: `{report['world_fitness']['control_mean_self_fit']}`",
        f"- Shadow: `{report['world_fitness']['shadow_mean_self_fit']}`",
        "",
        "## Guardrails",
        "",
        "- Production / Trigger / World / CSV / Signal Service unchanged",
        "",
    ]
    return "\n".join(lines)


def _md_transition(report: dict[str, Any]) -> str:
    wt = report["world_transition"]
    lines = [
        "# Version34 — World Transition (Shadow AB)",
        "",
        f"**Date:** {report['generated_at']}  ",
        f"**Changed races:** `{wt['n_changed']}` / `{report['n_races']}` ({_pct(wt['change_rate'])})",
        "",
        "## Transition matrix (counts)",
        "",
        "| From → To | N |",
        "|-----------|--:|",
    ]
    for k, n in sorted(wt["matrix_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"| `{k}` | {n} |")
    lines += [
        "",
        "## Activation (world rates)",
        "",
        "| World | Control rate | Shadow rate |",
        "|-------|-------------:|------------:|",
    ]
    for w in EXISTING_WORLDS:
        lines.append(
            f"| `{w}` | {_pct(report['world_activation']['control'][w]['rate'])} | "
            f"{_pct(report['world_activation']['shadow'][w]['rate'])} |"
        )
    lines += ["", "## Examples (up to 25)", ""]
    for ex in wt["examples"]:
        lines.append(
            f"- `{ex['race_id']}`: `{ex['from']}` → `{ex['to']}` hit={ex['hit']} "
            f"diff {ex['control_difficulty']}→{ex['shadow_difficulty']}"
        )
    lines += ["", "## Guardrails", "", "- Shadow simulation only", ""]
    return "\n".join(lines)


def _md_hit(report: dict[str, Any]) -> str:
    hi = report["hit_impact_on_world_change"]
    lines = [
        "# Version34 — Hit Impact on World Change",
        "",
        f"**Date:** {report['generated_at']}  ",
        "",
        "## World-changed subset",
        "",
        f"- N changed: `{hi['n_changed_world']}`",
        f"- Hit improved: `{hi['improved']}`",
        f"- Hit worsened: `{hi['worsened']}`",
        f"- Hit unchanged: `{hi['unchanged']}`",
        "",
        "## Interpretation",
        "",
        "Shadow AB keeps the **Production PE top pick frozen**.",
        "Therefore, when World label changes under WIC signals, Hit cannot improve or worsen",
        "unless a pick-changing purchase/Role path is also shadowed.",
        "",
        f"ROI proof status: **{report['roi_proof']['status']}**",
        "",
        "## Guardrails",
        "",
        "- No purchase-path mutation in this AB",
        "",
    ]
    return "\n".join(lines)


def _md_governance(report: dict[str, Any]) -> str:
    g = report["governance_checks"]
    lines = [
        "# Version34 — Governance (WIC Shadow AB)",
        "",
        f"**Date:** {report['generated_at']}  ",
        "",
        "## PASS conditions (user)",
        "",
        "| Check | Result |",
        "|-------|:------:|",
        f"| Hit >= Baseline | `{'PASS' if g['hit_ge_baseline'] else 'FAIL'}` |",
        f"| Purchase >= Baseline | `{'PASS' if g['purchase_ge_baseline'] else 'FAIL'}` |",
        f"| rank710 not worse | `{'PASS' if g['rank710_not_worse'] else 'FAIL'}` |",
        f"| other miss not worse | `{'PASS' if g['other_miss_not_worse'] else 'FAIL'}` |",
        "",
        f"**Non-inferiority aggregate:** **{report['governance_non_inferiority']}**",
        "",
        "## V35 gate (Signal Service design)",
        "",
        "User rule: Signal Service detailed design starts in V35 **only if Shadow AB PASS**.",
        "This governance distinguishes:",
        "",
        "1. **Non-inferiority PASS** — does not harm Hit/Purchase/miss layers",
        "2. **ROI contribution PROVEN** — requires Hit lift (or explicit pick-path Shadow improvement)",
        "",
        "| Gate | Value |",
        "|------|-------|",
        f"| non_inferiority_pass | `{report['v35_gate']['non_inferiority_pass']}` |",
        f"| roi_contribution_proven | `{report['v35_gate']['roi_contribution_proven']}` |",
        f"| allow_signal_service_design_v35 | `{report['v35_gate']['allow_signal_service_design_v35']}` |",
        f"| reason | {report['v35_gate']['reason']} |",
        "",
        "## Decision",
        "",
    ]
    if report["v35_gate"]["allow_signal_service_design_v35"]:
        lines.append("**GO V35** — ROI contribution proven under Shadow AB.")
    else:
        lines.append(
            "**NO-GO V35 (Signal Service design)** — "
            "Non-inferiority may PASS, but ROI contribution is not proven "
            f"(`{report['roi_proof']['status']}`)."
        )
        lines.append("")
        lines.append(
            "Next research options (not implemented here): pick-changing World→Purchase Shadow; "
            "or observational cohort Hit (116-era vs 72-era) with governance."
        )
    lines += ["", "## Guardrails", "", "- No Production changes", ""]
    return "\n".join(lines)


def run_and_write() -> dict[str, Any]:
    report = WicShadowAB().analyze()
    evidence = evidence_root()
    reports_dir = evidence / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "v34-wic-shadow-ab.json"
    slim = {k: v for k, v in report.items() if k != "races"}
    slim["races_n"] = report["n_races"]
    slim["races_sample"] = report["races"][:30]
    json_path.write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")

    docs = repo_root() / "docs" / "research"
    docs.mkdir(parents=True, exist_ok=True)
    outputs = {
        "summary": docs / "v34-shadow-ab-summary.md",
        "transition": docs / "v34-world-transition.md",
        "hit": docs / "v34-hit-impact.md",
        "governance": docs / "v34-governance.md",
        "json": json_path,
    }
    outputs["summary"].write_text(_md_summary(report), encoding="utf-8")
    outputs["transition"].write_text(_md_transition(report), encoding="utf-8")
    outputs["hit"].write_text(_md_hit(report), encoding="utf-8")
    outputs["governance"].write_text(_md_governance(report), encoding="utf-8")
    report["_outputs"] = {k: str(v) for k, v in outputs.items()}
    return report


__all__ = ["WicShadowAB", "run_and_write", "SCHEMA_VERSION"]
