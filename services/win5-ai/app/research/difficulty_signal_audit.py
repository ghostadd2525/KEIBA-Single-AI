# -*- coding: utf-8 -*-
"""
Version28 Difficulty Signal Audit

Quantitative audit of race_leg_difficulty / difficulty signal.
Research ONLY — no Trigger / World / Prediction / PE / CE / AI changes.
No improvement proposals.
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .config import evidence_root, repo_root
from .world_boundary_research import EXISTING_WORLDS, extract_world_label
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-difficulty-signal-audit/1.0"

# Canonical formula (demo_pace_model_v2.add_win5_leg_difficulty_features) — READ ONLY
DIFFICULTY_COMPONENTS: tuple[dict[str, Any], ...] = (
    {
        "name": "leg_base_chaos",
        "weight": 0.35,
        "source": "win5_leg map {1:0.46,2:0.50,3:0.56,4:0.60,5:0.64}; missing→0.50",
        "inputs": ["win5_leg"],
    },
    {
        "name": "leg_field_pressure",
        "weight": 0.20,
        "source": "clip((horse_count - 8) / 10, 0, 1); horse_count fallback 12",
        "inputs": ["horse_count", "field_size", "race_id count"],
    },
    {
        "name": "pace_collapse_risk",
        "weight": 0.20,
        "source": "pace model front-pressure share",
        "inputs": ["nige_count", "front_count", "horse_count"],
    },
    {
        "name": "style_entropy",
        "weight": 0.15,
        "source": "running-style entropy within race",
        "inputs": ["running_style counts"],
    },
    {
        "name": "upset_share",
        "weight": 0.10,
        "source": "(sashi_count + oikomi_count + unknown_count) / horse_count",
        "inputs": ["sashi_count", "oikomi_count", "unknown_count", "horse_count"],
    },
)

# Stable default when column absent (demo_probability_feature_utils.STABLE_FEATURE_DEFAULTS)
STABLE_DEFAULT_DIFFICULTY = 0.5

SATURATION_THRESHOLDS = (0.50, 0.60, 0.70, 0.80, 0.90)

WIN5_LEG_BASE = {1: 0.46, 2: 0.50, 3: 0.56, 4: 0.60, 5: 0.64}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _f(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pctile(sorted_vals: list[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def _mean(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def _std(vals: list[float]) -> float | None:
    if len(vals) < 2:
        return 0.0 if vals else None
    m = _mean(vals) or 0.0
    return math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))


def _entropy(vals: list[float], *, bins: int = 20) -> float | None:
    if not vals:
        return None
    # discrete entropy over rounded values (signal uniqueness) + binned
    rounded = [round(v, 6) for v in vals]
    c = Counter(rounded)
    n = len(rounded)
    h = 0.0
    for cnt in c.values():
        p = cnt / n
        h -= p * math.log(p + 1e-15)
    return h


def _max_entropy(n_unique: int) -> float:
    if n_unique <= 1:
        return 0.0
    return math.log(n_unique)


def histogram(vals: list[float], edges: list[float] | None = None) -> list[dict[str, Any]]:
    if edges is None:
        edges = [i / 10 for i in range(11)] + [1.01]
    bins = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        n = sum(1 for v in vals if (lo <= v < hi) or (hi >= 1.01 and v >= lo and v <= 1.0))
        # fix double-count on last: use < hi except last bin inclusive
        if hi < 1.01:
            n = sum(1 for v in vals if lo <= v < hi)
        else:
            n = sum(1 for v in vals if lo <= v <= 1.0)
        bins.append(
            {
                "bin": f"[{lo:.1f},{hi:.1f})" if hi < 1.01 else f"[{lo:.1f},1.0]",
                "n": n,
                "rate": _safe_div(n, len(vals)),
            }
        )
    return bins


def reconstruct_leg_upset(
    *,
    win5_leg: float | None,
    horse_count: float | None,
    pace_collapse_risk: float | None,
    style_entropy: float | None,
    sashi_count: float | None,
    oikomi_count: float | None,
    unknown_count: float | None,
) -> dict[str, Any]:
    """Read-only reconstruction of designed formula (does not mutate product)."""
    leg = int(win5_leg) if win5_leg is not None else None
    leg_base = WIN5_LEG_BASE.get(leg, 0.50) if leg is not None else 0.50
    hc = float(horse_count) if horse_count is not None else 12.0
    if hc <= 0:
        hc = 12.0
    field_p = max(0.0, min(1.0, (hc - 8.0) / 10.0))
    pcr = float(pace_collapse_risk or 0.0)
    se = float(style_entropy or 0.0)
    upset = (
        (float(sashi_count or 0.0) + float(oikomi_count or 0.0) + float(unknown_count or 0.0))
        / hc
    )
    components = {
        "leg_base_chaos": leg_base,
        "leg_field_pressure": field_p,
        "pace_collapse_risk": pcr,
        "style_entropy": se,
        "upset_share": upset,
    }
    weighted = {
        "leg_base_chaos": leg_base * 0.35,
        "leg_field_pressure": field_p * 0.20,
        "pace_collapse_risk": pcr * 0.20,
        "style_entropy": se * 0.15,
        "upset_share": upset * 0.10,
    }
    total = sum(weighted.values())
    total = max(0.0, min(1.0, total))
    contrib = {
        k: round(v / total, 6) if total > 1e-12 else None for k, v in weighted.items()
    }
    return {
        "components": {k: round(v, 6) for k, v in components.items()},
        "weighted": {k: round(v, 6) for k, v in weighted.items()},
        "contribution_share": contrib,
        "reconstructed_difficulty": round(total, 6),
        "inputs_used": {
            "win5_leg": win5_leg,
            "horse_count": hc,
            "pace_collapse_risk": pace_collapse_risk,
            "style_entropy": style_entropy,
            "sashi_count": sashi_count,
            "oikomi_count": oikomi_count,
            "unknown_count": unknown_count,
        },
    }


def sensitivity_grid() -> dict[str, Any]:
    """
    Observational sensitivity: vary one input in designed formula,
    hold others at neutral defaults (not a product change).
    """
    base = {
        "win5_leg": 2.0,
        "horse_count": 12.0,
        "pace_collapse_risk": 0.0,
        "style_entropy": 0.0,
        "sashi_count": 0.0,
        "oikomi_count": 0.0,
        "unknown_count": 0.0,
    }
    sweeps: dict[str, list[dict[str, Any]]] = {}

    # field / horse_count
    rows = []
    for hc in range(8, 19):
        kw = dict(base)
        kw["horse_count"] = float(hc)
        r = reconstruct_leg_upset(**kw)
        rows.append(
            {
                "horse_count": hc,
                "difficulty": r["reconstructed_difficulty"],
                "leg_field_pressure": r["components"]["leg_field_pressure"],
            }
        )
    sweeps["horse_count"] = rows
    d_vals = [r["difficulty"] for r in rows]
    sweeps["horse_count_range"] = {
        "min": min(d_vals),
        "max": max(d_vals),
        "delta": round(max(d_vals) - min(d_vals), 6),
    }

    # win5_leg
    rows = []
    for leg in (1, 2, 3, 4, 5, None):
        kw = dict(base)
        kw["win5_leg"] = float(leg) if leg is not None else None
        r = reconstruct_leg_upset(**kw)
        rows.append(
            {
                "win5_leg": leg if leg is not None else "missing→0.50",
                "difficulty": r["reconstructed_difficulty"],
                "leg_base_chaos": r["components"]["leg_base_chaos"],
            }
        )
    sweeps["win5_leg"] = rows
    d_vals = [r["difficulty"] for r in rows]
    sweeps["win5_leg_range"] = {
        "min": min(d_vals),
        "max": max(d_vals),
        "delta": round(max(d_vals) - min(d_vals), 6),
    }

    # pace_collapse_risk
    rows = []
    for p in [i / 10 for i in range(11)]:
        kw = dict(base)
        kw["pace_collapse_risk"] = p
        r = reconstruct_leg_upset(**kw)
        rows.append({"pace_collapse_risk": p, "difficulty": r["reconstructed_difficulty"]})
    sweeps["pace_collapse_risk"] = rows
    d_vals = [r["difficulty"] for r in rows]
    sweeps["pace_collapse_risk_range"] = {
        "min": min(d_vals),
        "max": max(d_vals),
        "delta": round(max(d_vals) - min(d_vals), 6),
    }

    # style_entropy
    rows = []
    for p in [i / 10 for i in range(11)]:
        kw = dict(base)
        kw["style_entropy"] = p
        r = reconstruct_leg_upset(**kw)
        rows.append({"style_entropy": p, "difficulty": r["reconstructed_difficulty"]})
    sweeps["style_entropy"] = rows
    d_vals = [r["difficulty"] for r in rows]
    sweeps["style_entropy_range"] = {
        "min": min(d_vals),
        "max": max(d_vals),
        "delta": round(max(d_vals) - min(d_vals), 6),
    }

    # distance is NOT in the designed formula — record explicitly
    sweeps["distance_in_formula"] = False
    sweeps["field_size_alias"] = "horse_count drives leg_field_pressure; distance not a direct input"

    ranking = sorted(
        [
            ("horse_count / field pressure", sweeps["horse_count_range"]["delta"]),
            ("win5_leg / leg_base_chaos", sweeps["win5_leg_range"]["delta"]),
            ("pace_collapse_risk", sweeps["pace_collapse_risk_range"]["delta"]),
            ("style_entropy", sweeps["style_entropy_range"]["delta"]),
            ("upset_share (weight 0.10)", 0.10),  # theoretical max contribution span
        ],
        key=lambda x: -x[1],
    )
    sweeps["sensitivity_rank"] = [
        {"factor": name, "difficulty_delta_span": delta} for name, delta in ranking
    ]
    return sweeps


class DifficultySignalAudit:
    def __init__(self) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()

    def _load_difficulty_series(self) -> list[dict[str, Any]]:
        conn = connect()
        try:
            snap_rows = conn.execute(
                "SELECT race_id, prediction_id, payload_json FROM research_prediction_snapshots"
            ).fetchall()
            pred_rows = conn.execute(
                "SELECT id, race_id, bundle_json FROM predictions ORDER BY id ASC"
            ).fetchall()
        finally:
            conn.close()

        labels: dict[str, str] = {}
        for row in pred_rows:
            try:
                bundle = json.loads(row["bundle_json"] or "{}")
            except Exception:
                continue
            w, _ = extract_world_label(bundle)
            if w in EXISTING_WORLDS:
                labels[str(row["race_id"])] = w

        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in snap_rows:
            rid = str(row["race_id"])
            if rid in seen:
                continue
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except Exception:
                continue
            sig = ((payload.get("research_world_signals") or {}).get("signals")) or {}
            d = _f(sig.get("difficulty") if sig.get("difficulty") is not None else sig.get("race_leg_difficulty"))
            out.append(
                {
                    "race_id": rid,
                    "prediction_id": row["prediction_id"],
                    "assigned_world": labels.get(rid),
                    "difficulty": d,
                    "instrumented": isinstance(payload.get("research_world_signals"), dict),
                }
            )
            seen.add(rid)
        return out

    def _live_component_probe(self, limit: int = 12) -> dict[str, Any]:
        """Read-only Core frame probe for difficulty provenance."""
        try:
            from app.engine.adapters.single_prediction_mapper import resolve_core_race_id
            from app.research.world_signal_instrumentation import _ensure_research_core_path

            _ensure_research_core_path()
            from ai_platform.core.candidate_evaluation import CorePipeline
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"import:{type(exc).__name__}:{exc}"}

        conn = connect()
        try:
            rows = conn.execute(
                "SELECT race_id FROM research_prediction_snapshots "
                "WHERE race_id LIKE '2026-07-%' ORDER BY captured_at DESC"
            ).fetchall()
        finally:
            conn.close()

        pipe = CorePipeline()
        probes = []
        constants = Counter()
        has_col = 0
        missing_col = 0
        for row in rows[:limit]:
            rid = str(row["race_id"])
            try:
                cid = resolve_core_race_id(rid)
                if not cid:
                    continue
                loaded = pipe.load_race_input(cid)
                if loaded is None:
                    continue
                frame = loaded.frame
                has = "race_leg_difficulty" in frame.columns
                if has:
                    has_col += 1
                    vals = [
                        float(x)
                        for x in frame["race_leg_difficulty"].tolist()
                        if x is not None and str(x) != "nan"
                    ]
                    uniq = sorted(set(round(v, 6) for v in vals))
                    d0 = vals[0] if vals else None
                    if d0 is not None and abs(d0 - STABLE_DEFAULT_DIFFICULTY) < 1e-9:
                        constants["exactly_0.5"] += 1
                    constants[f"unique_n={len(uniq)}"] += 1
                else:
                    missing_col += 1
                    d0 = None
                    uniq = []

                # component columns availability
                comp_avail = {
                    c: c in frame.columns
                    for c in (
                        "win5_leg",
                        "horse_count",
                        "field_size",
                        "pace_collapse_risk",
                        "style_entropy",
                        "sashi_count",
                        "oikomi_count",
                        "unknown_count",
                        "leg_upset_risk",
                        "leg_base_chaos",
                        "leg_field_pressure",
                        "distance",
                    )
                }

                def col0(name: str) -> float | None:
                    if name not in frame.columns:
                        return None
                    try:
                        return float(frame[name].iloc[0])
                    except Exception:
                        return None

                hc = col0("horse_count")
                if hc is None:
                    hc = col0("field_size")
                recon = reconstruct_leg_upset(
                    win5_leg=col0("win5_leg"),
                    horse_count=hc if hc is not None else float(len(frame)),
                    pace_collapse_risk=col0("pace_collapse_risk"),
                    style_entropy=col0("style_entropy"),
                    sashi_count=col0("sashi_count"),
                    oikomi_count=col0("oikomi_count"),
                    unknown_count=col0("unknown_count"),
                )
                probes.append(
                    {
                        "race_id": rid,
                        "core_race_id": cid,
                        "frame_has_race_leg_difficulty": has,
                        "frame_difficulty_first": d0,
                        "frame_difficulty_uniques": uniq[:8],
                        "component_columns_present": comp_avail,
                        "reconstruction": recon,
                        "match_default_0_5": bool(
                            d0 is not None and abs(d0 - STABLE_DEFAULT_DIFFICULTY) < 1e-9
                        ),
                        "gap_frame_vs_reconstructed": (
                            round(float(d0) - recon["reconstructed_difficulty"], 6)
                            if d0 is not None
                            else None
                        ),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                probes.append({"race_id": rid, "error": f"{type(exc).__name__}:{exc}"})

        return {
            "ok": True,
            "probed_n": len(probes),
            "frame_has_col_n": has_col,
            "frame_missing_col_n": missing_col,
            "constant_flags": dict(constants),
            "samples": probes,
            "note": (
                "Core FeatureLoader path does not call add_win5_leg_difficulty_features; "
                "STABLE_FEATURE_DEFAULTS.race_leg_difficulty=0.5 fills missing columns."
            ),
        }

    def analyze(self) -> dict[str, Any]:
        rows = self._load_difficulty_series()
        vals = [float(r["difficulty"]) for r in rows if r.get("difficulty") is not None]
        missing_n = sum(1 for r in rows if r.get("difficulty") is None)
        sv = sorted(vals)

        # distribution
        dist = {
            "n_present": len(vals),
            "n_missing": missing_n,
            "missing_rate": _safe_div(missing_n, len(rows)),
            "mean": round(_mean(vals), 6) if vals else None,
            "median": round(_pctile(sv, 0.5), 6) if vals else None,
            "std": round(_std(vals), 6) if vals else None,
            "min": min(vals) if vals else None,
            "max": max(vals) if vals else None,
            "percentiles": {
                "p05": round(_pctile(sv, 0.05), 6) if vals else None,
                "p25": round(_pctile(sv, 0.25), 6) if vals else None,
                "p50": round(_pctile(sv, 0.50), 6) if vals else None,
                "p75": round(_pctile(sv, 0.75), 6) if vals else None,
                "p95": round(_pctile(sv, 0.95), 6) if vals else None,
            },
            "histogram": histogram(vals),
            "value_counts": dict(Counter(round(v, 6) for v in vals).most_common(20)),
        }

        # variance
        uniq = set(round(v, 6) for v in vals)
        n = len(vals) or 1
        unique_n = len(uniq)
        unique_rate = _safe_div(unique_n, len(vals))
        # duplicate rate = 1 - unique/n
        duplicate_rate = 1.0 - (unique_rate or 0.0) if vals else None
        var = (_std(vals) or 0.0) ** 2 if vals else None
        ent = _entropy(vals)
        mean_v = _mean(vals)
        cv = (
            (_std(vals) / abs(mean_v))
            if mean_v not in (None, 0.0) and _std(vals) is not None
            else None
        )
        variance_block = {
            "unique_n": unique_n,
            "unique_rate": unique_rate,
            "duplicate_rate": duplicate_rate,
            "variance": round(var, 8) if var is not None else None,
            "std": dist["std"],
            "entropy_bits_nat": round(ent, 6) if ent is not None else None,
            "entropy_normalized": (
                round(ent / _max_entropy(unique_n), 6)
                if ent is not None and unique_n > 1
                else (0.0 if unique_n <= 1 else None)
            ),
            "coefficient_of_variation": round(cv, 6) if cv is not None else None,
            "all_equal": unique_n <= 1,
            "dominated_by_default_0_5": (
                _safe_div(sum(1 for v in vals if abs(v - 0.5) < 1e-9), len(vals))
                if vals
                else None
            ),
        }

        # saturation
        sat = {}
        for thr in SATURATION_THRESHOLDS:
            n_pass = sum(1 for v in vals if v >= thr)
            sat[f">={thr:.2f}"] = {
                "threshold": thr,
                "pass_n": n_pass,
                "pass_rate": _safe_div(n_pass, len(vals)),
            }

        # components (designed weights = contribution rates when all inputs=1)
        weight_sum = sum(float(c["weight"]) for c in DIFFICULTY_COMPONENTS)
        components = {
            "formula_source": "demo_pace_model_v2.add_win5_leg_difficulty_features",
            "aggregation": "race_leg_difficulty = mean(leg_upset_risk) by race_id",
            "stable_default_when_column_missing": STABLE_DEFAULT_DIFFICULTY,
            "stable_default_source": "demo_probability_feature_utils.STABLE_FEATURE_DEFAULTS",
            "items": [
                {
                    **c,
                    "designed_weight": c["weight"],
                    "designed_weight_share": round(float(c["weight"]) / weight_sum, 4),
                }
                for c in DIFFICULTY_COMPONENTS
            ],
            "note": (
                "Designed weights are the only fixed contribution rates. "
                "Empirical contribution depends on realized component magnitudes."
            ),
        }

        probe = self._live_component_probe(limit=15)
        sensitivity = sensitivity_grid()

        # Empirical contribution from probe reconstructions (mean weighted shares)
        emp_shares: dict[str, list[float]] = defaultdict(list)
        for s in probe.get("samples") or []:
            recon = s.get("reconstruction") or {}
            for k, v in (recon.get("contribution_share") or {}).items():
                if v is not None:
                    emp_shares[k].append(float(v))
        components["empirical_contribution_share_mean"] = {
            k: round(_mean(vs), 6) if vs else None for k, vs in emp_shares.items()
        }

        # Design consistency (observational flags — not recommendations)
        disc = variance_block.get("unique_n") or 0
        sat50 = (sat.get(">=0.50") or {}).get("pass_rate")
        design_review = {
            "design_claim": "difficulty should disperse Worlds (informative World-line signal)",
            "sufficient_discriminability": bool(disc >= 5 and (variance_block.get("std") or 0) > 0.05),
            "sufficient_information": bool(
                (variance_block.get("entropy_normalized") or 0) >= 0.5
            ),
            "saturated_at_0_50": bool(sat50 is not None and sat50 >= 0.90),
            "collapsed_to_constant": bool(variance_block.get("all_equal")),
            "dominated_by_stable_default": bool(
                (variance_block.get("dominated_by_default_0_5") or 0) >= 0.90
            ),
            "observed_facts": [
                f"unique_n={variance_block.get('unique_n')}",
                f"std={variance_block.get('std')}",
                f"pass_rate(>=0.50)={sat50}",
                f"share_exactly_0.5={variance_block.get('dominated_by_default_0_5')}",
            ],
            "improvement_forbidden": True,
        }

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "product_mutation": False,
            "world_trigger_changed": False,
            "improvement_forbidden": True,
            "sample": {
                "snapshots_n": len(rows),
                "difficulty_present_n": len(vals),
                "labeled_world_counts": dict(
                    Counter(r["assigned_world"] for r in rows if r.get("assigned_world"))
                ),
            },
            "distribution": dist,
            "components": components,
            "variance": variance_block,
            "saturation": sat,
            "sensitivity": sensitivity,
            "live_probe": probe,
            "design_review": design_review,
            "races": rows,
            "notes": [
                "V27 midupper saturation via R7 difficulty>=0.50 is consistent with constant 0.5",
                "Designed formula exists in pace_model_v2 but Core FeatureLoader may not invoke it",
                "No threshold / Trigger / World changes in this audit",
            ],
        }


def _bar(rate: float | None, width: int = 40) -> str:
    if rate is None:
        return ""
    return "#" * int(round(rate * width))


def write_distribution_md(report: dict[str, Any], path: Path) -> None:
    d = report.get("distribution") or {}
    p = d.get("percentiles") or {}
    lines = [
        "# Version28 — Difficulty Distribution",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Signal:** `difficulty` / `race_leg_difficulty` from V25 research_world_signals  ",
        "",
        "## Summary",
        "",
        f"- N present: `{d.get('n_present')}`",
        f"- Missing: `{d.get('n_missing')}` ({_pct(d.get('missing_rate'))})",
        f"- Mean / Median / Std: `{d.get('mean')}` / `{d.get('median')}` / `{d.get('std')}`",
        f"- Min / Max: `{d.get('min')}` / `{d.get('max')}`",
        "",
        "## Percentiles",
        "",
        f"- P5: `{p.get('p05')}`",
        f"- P25: `{p.get('p25')}`",
        f"- P50: `{p.get('p50')}`",
        f"- P75: `{p.get('p75')}`",
        f"- P95: `{p.get('p95')}`",
        "",
        "## Histogram",
        "",
        "| Bin | N | Rate | Bar |",
        "|-----|--:|-----:|-----|",
    ]
    for b in d.get("histogram") or []:
        lines.append(
            f"| `{b.get('bin')}` | {b.get('n')} | {_pct(b.get('rate'))} | `{_bar(b.get('rate'))}` |"
        )
    lines += [
        "",
        "## Top value counts",
        "",
        "| Value | N |",
        "|------:|--:|",
    ]
    for v, n in (d.get("value_counts") or {}).items():
        lines.append(f"| {v} | {n} |")
    lines += [
        "",
        "## Guardrails",
        "",
        f"- product_mutation: `{report.get('product_mutation')}`",
        f"- improvement_forbidden: `{report.get('improvement_forbidden')}`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_components_md(report: dict[str, Any], path: Path) -> None:
    c = report.get("components") or {}
    probe = report.get("live_probe") or {}
    lines = [
        "# Version28 — Difficulty Components",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "## Designed formula (read-only)",
        "",
        f"- Source: `{c.get('formula_source')}`",
        f"- Aggregation: `{c.get('aggregation')}`",
        "",
        "```",
        "leg_upset_risk =",
        "    leg_base_chaos      * 0.35",
        "  + leg_field_pressure  * 0.20",
        "  + pace_collapse_risk  * 0.20",
        "  + style_entropy       * 0.15",
        "  + upset_share         * 0.10",
        "race_leg_difficulty = mean(leg_upset_risk) by race_id",
        "```",
        "",
        f"- Stable default when column missing: `{c.get('stable_default_when_column_missing')}`",
        f"- Default source: `{c.get('stable_default_source')}`",
        "",
        "## Designed weight / contribution share",
        "",
        "| Component | Weight | Share | Inputs |",
        "|-----------|-------:|------:|--------|",
    ]
    for it in c.get("items") or []:
        lines.append(
            f"| `{it.get('name')}` | {it.get('designed_weight')} | "
            f"{_pct(it.get('designed_weight_share'))} | {', '.join(it.get('inputs') or [])} |"
        )
    lines += [
        "",
        "## Empirical contribution share (live reconstruction mean)",
        "",
        "| Component | Mean share of reconstructed total |",
        "|-----------|----------------------------------:|",
    ]
    for k, v in (c.get("empirical_contribution_share_mean") or {}).items():
        lines.append(f"| `{k}` | {v} |")
    lines += [
        "",
        "## Live frame probe",
        "",
        f"- ok: `{probe.get('ok')}`",
        f"- probed_n: `{probe.get('probed_n')}`",
        f"- frame has race_leg_difficulty: `{probe.get('frame_has_col_n')}`",
        f"- frame missing col: `{probe.get('frame_missing_col_n')}`",
        f"- flags: `{probe.get('constant_flags')}`",
        f"- note: {probe.get('note')}",
        "",
        "### Samples",
        "",
    ]
    for s in (probe.get("samples") or [])[:10]:
        if s.get("error"):
            lines.append(f"- `{s.get('race_id')}` error=`{s.get('error')}`")
            continue
        lines.append(
            f"- `{s.get('race_id')}` frame_diff=`{s.get('frame_difficulty_first')}` "
            f"default0.5=`{s.get('match_default_0_5')}` "
            f"recon=`{(s.get('reconstruction') or {}).get('reconstructed_difficulty')}` "
            f"gap=`{s.get('gap_frame_vs_reconstructed')}`"
        )
        avail = s.get("component_columns_present") or {}
        present = [k for k, v in avail.items() if v]
        lines.append(f"  - component cols present: {present}")
    lines += [
        "",
        "## Guardrails",
        "",
        "- Reconstruction is observational; product formula/path unchanged",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_variance_md(report: dict[str, Any], path: Path) -> None:
    v = report.get("variance") or {}
    lines = [
        "# Version28 — Difficulty Variance",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "## Metrics",
        "",
        f"- Unique N: `{v.get('unique_n')}`",
        f"- Unique rate: `{_pct(v.get('unique_rate'))}`",
        f"- Duplicate rate: `{_pct(v.get('duplicate_rate'))}`",
        f"- Variance: `{v.get('variance')}`",
        f"- Std: `{v.get('std')}`",
        f"- Entropy (nats): `{v.get('entropy_bits_nat')}`",
        f"- Entropy normalized (by unique support): `{v.get('entropy_normalized')}`",
        f"- Coefficient of Variation: `{v.get('coefficient_of_variation')}`",
        f"- All equal: `{v.get('all_equal')}`",
        f"- Share exactly 0.5: `{_pct(v.get('dominated_by_default_0_5'))}`",
        "",
        "## Reading (facts)",
        "",
        "- Unique rate near 0 ⇒ almost no dispersion across races",
        "- CV near 0 ⇒ mean-stable with negligible relative spread",
        "- This section does not propose changes",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_saturation_md(report: dict[str, Any], path: Path) -> None:
    sat = report.get("saturation") or {}
    lines = [
        "# Version28 — Difficulty Saturation",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Context:** V27 observed R7 `difficulty >= 0.50` pass ≈ 98%  ",
        "",
        "## Pass rates",
        "",
        "| Threshold | Pass N | Pass rate | Bar |",
        "|----------:|-------:|----------:|-----|",
    ]
    for key in [f">={t:.2f}" for t in SATURATION_THRESHOLDS]:
        block = sat.get(key) or {}
        lines.append(
            f"| `{key}` | {block.get('pass_n')} | {_pct(block.get('pass_rate'))} | "
            f"`{_bar(block.get('pass_rate'))}` |"
        )
    lines += [
        "",
        "## Link to World assignment (observational)",
        "",
        "- R7 midupper trigger uses `difficulty >= 0.50` only",
        "- If pass_rate(>=0.50) is near 100% and unique values collapse to 0.5, "
        "first-match simulation yields midupper saturation after earlier rules fail",
        "- Thresholds are not modified in this audit",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_design_review_md(report: dict[str, Any], path: Path) -> None:
    dr = report.get("design_review") or {}
    sens = report.get("sensitivity") or {}
    lines = [
        "# Version28 — Difficulty Design Consistency Review",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"**Design claim:** {dr.get('design_claim')}  ",
        "",
        "## Evaluation flags (observational)",
        "",
        f"- Sufficient discriminability: `{dr.get('sufficient_discriminability')}`",
        f"- Sufficient information: `{dr.get('sufficient_information')}`",
        f"- Saturated at 0.50: `{dr.get('saturated_at_0_50')}`",
        f"- Collapsed to constant: `{dr.get('collapsed_to_constant')}`",
        f"- Dominated by stable default 0.5: `{dr.get('dominated_by_stable_default')}`",
        "",
        "### Observed facts",
        "",
    ]
    for f in dr.get("observed_facts") or []:
        lines.append(f"- {f}")
    lines += [
        "",
        "## Sensitivity (designed formula, held-other-constant sweeps)",
        "",
        "| Factor | Difficulty delta span |",
        "|--------|----------------------:|",
    ]
    for row in sens.get("sensitivity_rank") or []:
        lines.append(f"| {row.get('factor')} | {row.get('difficulty_delta_span')} |")
    lines += [
        "",
        f"- distance in designed formula: `{sens.get('distance_in_formula')}`",
        f"- field note: {sens.get('field_size_alias')}",
        "",
        "### horse_count sweep (excerpt)",
        "",
        "| horse_count | field_pressure | difficulty |",
        "|------------:|---------------:|-----------:|",
    ]
    for row in (sens.get("horse_count") or [])[::2]:
        lines.append(
            f"| {row.get('horse_count')} | {row.get('leg_field_pressure')} | {row.get('difficulty')} |"
        )
    lines += [
        "",
        "## Consistency statement (no improvements)",
        "",
        "Under the design claim that difficulty should disperse Worlds, the measured "
        "research signal is evaluated only by the flags above. "
        "This document does **not** propose Trigger, threshold, World, or AI changes.",
        "",
        f"- improvement_forbidden: `{dr.get('improvement_forbidden')}`",
        f"- world_trigger_changed: `{report.get('world_trigger_changed')}`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write() -> dict[str, Any]:
    ops = DifficultySignalAudit()
    report = ops.analyze()
    docs = repo_root() / "docs" / "research"
    docs.mkdir(parents=True, exist_ok=True)
    paths = {
        "distribution": docs / "v28-difficulty-distribution.md",
        "components": docs / "v28-difficulty-components.md",
        "variance": docs / "v28-difficulty-variance.md",
        "saturation": docs / "v28-difficulty-saturation.md",
        "design_review": docs / "v28-difficulty-design-review.md",
    }
    write_distribution_md(report, paths["distribution"])
    write_components_md(report, paths["components"])
    write_variance_md(report, paths["variance"])
    write_saturation_md(report, paths["saturation"])
    write_design_review_md(report, paths["design_review"])
    json_path = evidence_root() / "reports" / "v28-difficulty-audit.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    slim = {k: v for k, v in report.items() if k != "races"}
    slim["races_n"] = len(report.get("races") or [])
    json_path.write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {**{k: str(p) for k, p in paths.items()}, "json": str(json_path)}
    return report
