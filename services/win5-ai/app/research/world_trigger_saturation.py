# -*- coding: utf-8 -*-
"""
Version27 World Trigger Saturation Research

Why observed World assignment is midupper-saturated vs design mix.
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

SCHEMA_VERSION = "expect-world-trigger-saturation/1.0"

# Design intent (research reference only — not product config)
DESIGN_SHARE: dict[str, float] = {
    "core_world": 0.30,
    "midupper_world": 0.35,
    "rank7_world": 0.15,
    "mixed_world": 0.10,
    "bug_world": 0.05,
    "midhole_world": 0.05,
}

NEAR_ACTIVATION_EPS = 0.05  # within 5pp of threshold → near
SIGNAL_KEYS = (
    "chaos",
    "chaos_score",
    "difficulty",
    "race_leg_difficulty",
    "phase",
    "phase_transition",
    "late_stop",
    "late_stop_risk_score",
    "sustained",
    "sustained_run_possible_score",
    "high_pace",
    "high_pace_score",
    "short_field_pressure",
)

# Atomic conditions used by classify_world_line_type (read-only mirror)
# Each rule: world, priority, conditions with AND/OR structure
TRIGGER_RULES: list[dict[str, Any]] = [
    {
        "rule_id": "R1_mixed_short_field",
        "world": "mixed_world",
        "priority": 1,
        "logic": "AND",
        "parts": [
            {"signal": "short_field_pressure", "op": "ge", "threshold": 0.72},
            {
                "logic": "OR",
                "parts": [
                    {"signal": "phase", "op": "ge", "threshold": 0.48},
                    {"signal": "chaos", "op": "ge", "threshold": 0.42},
                    {"signal": "difficulty", "op": "ge", "threshold": 0.42},
                ],
            },
        ],
    },
    {
        "rule_id": "R2_midupper_sf_diff",
        "world": "midupper_world",
        "priority": 2,
        "logic": "AND",
        "parts": [
            {"signal": "short_field_pressure", "op": "ge", "threshold": 0.58},
            {"signal": "difficulty", "op": "ge", "threshold": 0.38},
        ],
    },
    {
        "rule_id": "R3_mixed_phase",
        "world": "mixed_world",
        "priority": 3,
        "logic": "AND",
        "parts": [{"signal": "phase", "op": "ge", "threshold": 0.62}],
    },
    {
        "rule_id": "R4_midhole",
        "world": "midhole_world",
        "priority": 4,
        "logic": "AND",
        "parts": [
            {"signal": "late_stop", "op": "ge", "threshold": 0.56},
            {"signal": "sustained", "op": "ge", "threshold": 0.52},
        ],
    },
    {
        "rule_id": "R5_rank7",
        "world": "rank7_world",
        "priority": 5,
        "logic": "AND",
        "parts": [
            {"signal": "chaos", "op": "ge", "threshold": 0.58},
            {"signal": "high_pace", "op": "ge", "threshold": 0.48},
        ],
    },
    {
        "rule_id": "R6_bug",
        "world": "bug_world",
        "priority": 6,
        "logic": "AND",
        "parts": [
            {"signal": "chaos", "op": "ge", "threshold": 0.66},
            {"signal": "difficulty", "op": "ge", "threshold": 0.62},
        ],
    },
    {
        "rule_id": "R7_midupper_diff",
        "world": "midupper_world",
        "priority": 7,
        "logic": "AND",
        "parts": [{"signal": "difficulty", "op": "ge", "threshold": 0.50}],
    },
    {
        "rule_id": "R8_core_default",
        "world": "core_world",
        "priority": 8,
        "logic": "DEFAULT",
        "parts": [],
    },
]


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


def _median(vals: list[float]) -> float | None:
    return _pctile(sorted(vals), 0.5)


def _mean(vals: list[float]) -> float | None:
    if not vals:
        return None
    return sum(vals) / len(vals)


def normalize_signals(raw: dict[str, Any] | None) -> dict[str, float | None]:
    """Canonical signal view from V25 research_world_signals."""
    s = raw or {}

    def pick(*keys: str) -> float | None:
        for k in keys:
            if s.get(k) is not None:
                return _f(s.get(k))
        return None

    return {
        "chaos": pick("chaos", "chaos_score"),
        "difficulty": pick("difficulty", "race_leg_difficulty"),
        "phase": pick("phase", "phase_transition"),
        "late_stop": pick("late_stop", "late_stop_risk_score"),
        "sustained": pick("sustained", "sustained_run_possible_score"),
        "high_pace": pick("high_pace", "high_pace_score"),
        "short_field_pressure": pick("short_field_pressure"),
    }


def atomic_margin(
    signals: dict[str, float | None], signal: str, threshold: float
) -> dict[str, Any]:
    """margin = value - threshold; negative ⇒ failed by |margin|."""
    val = signals.get(signal)
    if val is None:
        return {
            "signal": signal,
            "value": None,
            "threshold": threshold,
            "margin": None,
            "pass": False,
            "missing": True,
        }
    m = round(float(val) - float(threshold), 6)
    return {
        "signal": signal,
        "value": float(val),
        "threshold": threshold,
        "margin": m,
        "pass": m >= 0.0,
        "missing": False,
    }


def eval_node(node: dict[str, Any], signals: dict[str, float | None]) -> dict[str, Any]:
    """Evaluate AND/OR/atomic tree → pass + rule_margin + bottleneck atoms."""
    if "signal" in node:
        atom = atomic_margin(signals, str(node["signal"]), float(node["threshold"]))
        return {
            "pass": atom["pass"],
            "margin": atom["margin"],
            "atoms": [atom],
            "bottleneck": atom if not atom["pass"] else None,
        }

    logic = str(node.get("logic") or "AND").upper()
    parts = node.get("parts") or []
    if logic == "DEFAULT":
        return {"pass": True, "margin": 0.0, "atoms": [], "bottleneck": None}

    child_results = [eval_node(p, signals) for p in parts]
    all_atoms: list[dict[str, Any]] = []
    for c in child_results:
        all_atoms.extend(c.get("atoms") or [])

    if logic == "OR":
        # OR margin = best (max) among children; missing treated as -inf for ranking
        margins = []
        for c in child_results:
            if c.get("margin") is None:
                margins.append(float("-inf"))
            else:
                margins.append(float(c["margin"]))
        best_i = max(range(len(margins)), key=lambda i: margins[i]) if margins else 0
        passed = any(bool(c.get("pass")) for c in child_results)
        rule_m = None if margins and margins[best_i] == float("-inf") else (
            margins[best_i] if margins else None
        )
        bot = None
        if not passed:
            # only atoms from failing children (not siblings that also failed inside a mix)
            failed_child_atoms: list[dict[str, Any]] = []
            for c in child_results:
                if not c.get("pass"):
                    failed_child_atoms.extend(c.get("atoms") or [])
            bot = _worst_atom(failed_child_atoms)
        return {
            "pass": passed,
            "margin": rule_m if rule_m != float("-inf") else None,
            "atoms": all_atoms,
            "bottleneck": bot,
            "children": child_results,
        }

    # AND: margin = min of children; missing ⇒ fail with margin None contribution as -inf
    margins = []
    for c in child_results:
        if c.get("margin") is None:
            margins.append(float("-inf"))
        else:
            margins.append(float(c["margin"]))
    passed = all(bool(c.get("pass")) for c in child_results) if child_results else False
    rule_m = min(margins) if margins else None
    if rule_m == float("-inf"):
        rule_m = None
    bot = None
    if not passed:
        # Binding constraint = bottleneck of the worst failing child only
        failing = [c for c in child_results if not c.get("pass")]
        if failing:
            # prefer child with lowest margin (most binding); missing margin → -inf
            def child_key(c: dict[str, Any]) -> float:
                m = c.get("margin")
                return float(m) if m is not None else float("-inf")

            worst_child = min(failing, key=child_key)
            bot = worst_child.get("bottleneck")
            if bot is None:
                bot = _worst_atom(worst_child.get("atoms") or [])
    return {
        "pass": passed,
        "margin": rule_m,
        "atoms": all_atoms,
        "bottleneck": bot,
        "children": child_results,
    }


def _worst_atom(atoms: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not atoms:
        return None
    # missing first, then most negative margin
    missing = [a for a in atoms if a.get("missing")]
    if missing:
        return missing[0]
    return min(atoms, key=lambda a: float(a.get("margin") if a.get("margin") is not None else -999))


def evaluate_all_rules(signals: dict[str, float | None]) -> list[dict[str, Any]]:
    out = []
    for rule in TRIGGER_RULES:
        if rule["logic"] == "DEFAULT":
            out.append(
                {
                    "rule_id": rule["rule_id"],
                    "world": rule["world"],
                    "priority": rule["priority"],
                    "pass": True,
                    "margin": 0.0,
                    "atoms": [],
                    "bottleneck": None,
                    "is_default": True,
                }
            )
            continue
        ev = eval_node(rule, signals)
        out.append(
            {
                "rule_id": rule["rule_id"],
                "world": rule["world"],
                "priority": rule["priority"],
                "pass": bool(ev.get("pass")),
                "margin": ev.get("margin"),
                "atoms": ev.get("atoms") or [],
                "bottleneck": ev.get("bottleneck"),
                "is_default": False,
            }
        )
    return out


def first_match_world(rule_evals: list[dict[str, Any]]) -> str:
    for r in sorted(rule_evals, key=lambda x: int(x["priority"])):
        if r.get("is_default"):
            return str(r["world"])
        if r.get("pass"):
            return str(r["world"])
    return "core_world"


def histogram(vals: list[float], edges: list[float] | None = None) -> list[dict[str, Any]]:
    if edges is None:
        edges = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.01]
    bins = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        n = sum(1 for v in vals if lo <= v < hi)
        bins.append(
            {
                "bin": f"[{lo:.1f},{hi:.1f})" if hi < 1.01 else f"[{lo:.1f},1.0]",
                "n": n,
                "rate": _safe_div(n, len(vals)),
            }
        )
    return bins


class WorldTriggerSaturationResearch:
    def __init__(self) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()

    def _load_labeled_races(self) -> list[dict[str, Any]]:
        snaps: dict[str, dict[str, Any]] = {}
        conn = connect()
        try:
            for row in conn.execute(
                "SELECT race_id, prediction_id, payload_json FROM research_prediction_snapshots"
            ).fetchall():
                try:
                    payload = json.loads(row["payload_json"] or "{}")
                except Exception:
                    continue
                block = payload.get("research_world_signals")
                signals = (block or {}).get("signals") if isinstance(block, dict) else {}
                snaps[str(row["race_id"])] = {
                    "prediction_id": row["prediction_id"],
                    "signals_raw": signals if isinstance(signals, dict) else {},
                    "instrumented": isinstance(block, dict),
                }
            pred_rows = conn.execute(
                "SELECT id, race_id, bundle_json FROM predictions ORDER BY id ASC"
            ).fetchall()
        finally:
            conn.close()

        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in pred_rows:
            try:
                bundle = json.loads(row["bundle_json"] or "{}")
            except Exception:
                continue
            w, sub = extract_world_label(bundle)
            if not w or w not in EXISTING_WORLDS:
                continue
            rid = str(row["race_id"])
            if rid in seen:
                continue
            seen.add(rid)
            snap = snaps.get(rid) or {}
            sig = normalize_signals(snap.get("signals_raw"))
            out.append(
                {
                    "race_id": rid,
                    "prediction_id": int(row["id"]),
                    "assigned_world": w,
                    "sub_world": sub,
                    "signals": sig,
                    "instrumented": bool(snap.get("instrumented")),
                }
            )
        return out

    def analyze(self) -> dict[str, Any]:
        races = self._load_labeled_races()
        assigned_counts = Counter(r["assigned_world"] for r in races)
        n = len(races) or 1

        # Per-race rule margins
        race_details: list[dict[str, Any]] = []
        # Collect margins per rule_id / signal
        margins_by_rule: dict[str, list[float]] = defaultdict(list)
        margins_by_atom: dict[str, list[float]] = defaultdict(list)  # "rule.signal"
        bottleneck_by_world: dict[str, Counter[str]] = {
            w: Counter() for w in EXISTING_WORLDS
        }
        bottleneck_by_rule: dict[str, Counter[str]] = defaultdict(Counter)
        pass_by_rule: dict[str, int] = defaultdict(int)
        fail_by_rule: dict[str, int] = defaultdict(int)
        near_by_world: dict[str, list[dict[str, Any]]] = defaultdict(list)
        simulated_first_match: Counter[str] = Counter()
        signal_series: dict[str, list[float]] = defaultdict(list)
        missing_counts: Counter[str] = Counter()

        for r in races:
            sig = r["signals"]
            for k, v in sig.items():
                if v is None:
                    missing_counts[k] += 1
                else:
                    signal_series[k].append(float(v))

            rule_evals = evaluate_all_rules(sig)
            sim_world = first_match_world(rule_evals)
            simulated_first_match[sim_world] += 1

            per_rules = []
            for ev in rule_evals:
                rid = ev["rule_id"]
                if ev.get("is_default"):
                    per_rules.append(ev)
                    continue
                if ev.get("pass"):
                    pass_by_rule[rid] += 1
                else:
                    fail_by_rule[rid] += 1
                if ev.get("margin") is not None:
                    margins_by_rule[rid].append(float(ev["margin"]))
                for atom in ev.get("atoms") or []:
                    key = f"{rid}.{atom['signal']}"
                    if atom.get("margin") is not None:
                        margins_by_atom[key].append(float(atom["margin"]))
                    elif atom.get("missing"):
                        missing_counts[f"atom:{key}"] += 1
                bot = ev.get("bottleneck")
                if bot and not ev.get("pass"):
                    sig_name = str(bot.get("signal") or "unknown")
                    if bot.get("missing"):
                        sig_name = f"{sig_name}(MISSING)"
                    bottleneck_by_rule[rid][sig_name] += 1
                    bottleneck_by_world[str(ev["world"])][sig_name] += 1

                # Near activation: failed but margin within -eps, or all atoms near
                near = False
                if not ev.get("pass"):
                    m = ev.get("margin")
                    if m is not None and -NEAR_ACTIVATION_EPS <= m < 0:
                        near = True
                    else:
                        # any atom within eps of pass while others pass or near
                        atoms = ev.get("atoms") or []
                        if atoms and all(
                            (a.get("pass") or (
                                a.get("margin") is not None
                                and -NEAR_ACTIVATION_EPS <= float(a["margin"]) < 0
                            ))
                            and not a.get("missing")
                            for a in atoms
                        ):
                            near = True
                if near:
                    near_by_world[str(ev["world"])].append(
                        {
                            "race_id": r["race_id"],
                            "rule_id": rid,
                            "assigned_world": r["assigned_world"],
                            "margin": ev.get("margin"),
                            "atoms": [
                                {
                                    "signal": a["signal"],
                                    "value": a.get("value"),
                                    "threshold": a.get("threshold"),
                                    "margin": a.get("margin"),
                                    "missing": a.get("missing"),
                                }
                                for a in (ev.get("atoms") or [])
                            ],
                        }
                    )

                per_rules.append(
                    {
                        "rule_id": rid,
                        "world": ev["world"],
                        "priority": ev["priority"],
                        "pass": ev.get("pass"),
                        "margin": ev.get("margin"),
                        "bottleneck": bot,
                        "atoms": ev.get("atoms"),
                    }
                )

            race_details.append(
                {
                    "race_id": r["race_id"],
                    "assigned_world": r["assigned_world"],
                    "simulated_first_match": sim_world,
                    "signals": sig,
                    "rules": per_rules,
                }
            )

        # Saturation stats per rule / atom
        def margin_stats(vals: list[float]) -> dict[str, Any]:
            sv = sorted(vals)
            return {
                "n": len(vals),
                "mean": round(_mean(vals), 6) if vals else None,
                "median": round(_median(vals), 6) if vals else None,
                "p05": round(_pctile(sv, 0.05), 6) if vals else None,
                "p95": round(_pctile(sv, 0.95), 6) if vals else None,
                "pass_rate_approx": _safe_div(sum(1 for v in vals if v >= 0), len(vals)),
            }

        saturation_rules = {}
        for rule in TRIGGER_RULES:
            if rule["logic"] == "DEFAULT":
                continue
            rid = rule["rule_id"]
            bot_rank = [
                {"signal": s, "n": n_, "share": _safe_div(n_, fail_by_rule[rid] or 1)}
                for s, n_ in bottleneck_by_rule[rid].most_common()
            ]
            saturation_rules[rid] = {
                "world": rule["world"],
                "priority": rule["priority"],
                "pass_n": pass_by_rule[rid],
                "fail_n": fail_by_rule[rid],
                "pass_rate": _safe_div(pass_by_rule[rid], pass_by_rule[rid] + fail_by_rule[rid]),
                "margin": margin_stats(margins_by_rule[rid]),
                "top_dropout_condition": bot_rank[0] if bot_rank else None,
                "bottleneck_rank": bot_rank,
            }

        # Atom-level saturation across all rules
        atom_sat = {}
        for key, vals in sorted(margins_by_atom.items()):
            atom_sat[key] = margin_stats(vals)

        # World bottleneck ranking (aggregate across its rules)
        world_bottlenecks = {}
        for w in EXISTING_WORLDS:
            rank = [
                {"signal": s, "n": n_, "share": _safe_div(n_, sum(bottleneck_by_world[w].values()) or 1)}
                for s, n_ in bottleneck_by_world[w].most_common()
            ]
            world_bottlenecks[w] = rank

        # Distributions
        distributions = {}
        for k in ("chaos", "difficulty", "phase", "late_stop", "high_pace", "short_field_pressure", "sustained"):
            vals = signal_series.get(k) or []
            sv = sorted(vals)
            distributions[k] = {
                "n": len(vals),
                "missing_n": missing_counts.get(k, 0),
                "missing_rate": _safe_div(missing_counts.get(k, 0), len(races)),
                "mean": round(_mean(vals), 6) if vals else None,
                "median": round(_median(vals), 6) if vals else None,
                "p05": round(_pctile(sv, 0.05), 6) if vals else None,
                "p50": round(_pctile(sv, 0.50), 6) if vals else None,
                "p95": round(_pctile(sv, 0.95), 6) if vals else None,
                "histogram": histogram(vals),
            }

        # Observed vs design
        observed_share = {
            w: _safe_div(assigned_counts.get(w, 0), len(races)) or 0.0
            for w in EXISTING_WORLDS
        }
        sim_share = {
            w: _safe_div(simulated_first_match.get(w, 0), len(races)) or 0.0
            for w in EXISTING_WORLDS
        }
        design_gap = {}
        abs_gap_sum = 0.0
        for w in EXISTING_WORLDS:
            d = DESIGN_SHARE.get(w, 0.0)
            o = observed_share.get(w, 0.0)
            gap = o - d
            abs_gap_sum += abs(gap)
            design_gap[w] = {
                "design": d,
                "observed": round(o, 6),
                "simulated_first_match": round(sim_share.get(w, 0.0), 6),
                "gap_pp": round(gap * 100, 3),
                "abs_gap_pp": round(abs(gap) * 100, 3),
                "ratio_obs_design": round(o / d, 4) if d > 0 else None,
            }

        # TV distance / 2 = half L1
        tv = abs_gap_sum / 2.0

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "product_mutation": False,
            "world_trigger_changed": False,
            "improvement_forbidden": True,
            "sample": {
                "n_labeled_canonical": len(races),
                "assigned_counts": dict(assigned_counts),
                "near_activation_eps": NEAR_ACTIVATION_EPS,
            },
            "design_share": DESIGN_SHARE,
            "observed_share": observed_share,
            "simulated_first_match_share": sim_share,
            "design_gap": design_gap,
            "design_gap_summary": {
                "total_variation_distance": round(tv, 6),
                "l1_abs_gap": round(abs_gap_sum, 6),
                "max_abs_gap_world": max(
                    design_gap.items(), key=lambda x: x[1]["abs_gap_pp"]
                )[0]
                if design_gap
                else None,
            },
            "saturation_by_rule": saturation_rules,
            "saturation_by_atom": atom_sat,
            "bottleneck_by_world": world_bottlenecks,
            "distributions": distributions,
            "near_activation": {
                w: items[:40] for w, items in near_by_world.items()
            },
            "near_activation_counts": {w: len(v) for w, v in near_by_world.items()},
            "race_sample": race_details[:40],
            "races_n": len(race_details),
            "notes": [
                "Margins are observational vs frozen Trigger thresholds — thresholds not changed",
                "chaos MISSING counted as dropout bottleneck when required",
                "first-match simulation uses same priority order as classify_world_line_type",
                "No improvement proposals in this research version",
            ],
        }


def _fmt_hist(bins: list[dict[str, Any]]) -> list[str]:
    lines = []
    for b in bins:
        bar = "#" * int(round((b.get("rate") or 0) * 40))
        lines.append(f"| `{b.get('bin')}` | {b.get('n')} | {_pct(b.get('rate'))} | `{bar}` |")
    return lines


def write_margin_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version27 — Trigger Margin Analysis",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Scope:** Research only / Trigger unchanged / No improvements  ",
        "",
        "## Definition",
        "",
        "`margin = signal_value - threshold`",
        "",
        "- `margin >= 0` → condition passes",
        "- `margin < 0` → dropped by |margin|",
        "- `margin = NULL` → signal missing (dropout)",
        "",
        f"- Near-activation epsilon: `{NEAR_ACTIVATION_EPS}`",
        f"- Sample N: `{(report.get('sample') or {}).get('n_labeled_canonical')}`",
        "",
        "## Rule-level margin summary",
        "",
        "| Rule | World | Pass rate | Mean margin | Median | P95 | Top dropout |",
        "|------|-------|----------:|------------:|-------:|----:|-------------|",
    ]
    for rid, block in (report.get("saturation_by_rule") or {}).items():
        m = block.get("margin") or {}
        top = block.get("top_dropout_condition") or {}
        lines.append(
            f"| `{rid}` | `{block.get('world')}` | {_pct(block.get('pass_rate'))} | "
            f"{m.get('mean')} | {m.get('median')} | {m.get('p95')} | "
            f"`{top.get('signal')}` |"
        )
    lines += [
        "",
        "## Atom-level margins (rule.signal)",
        "",
        "| Atom | N | Mean | Median | P05 | P95 | ≈Pass rate |",
        "|------|--:|-----:|-------:|----:|----:|-----------:|",
    ]
    for key, m in (report.get("saturation_by_atom") or {}).items():
        lines.append(
            f"| `{key}` | {m.get('n')} | {m.get('mean')} | {m.get('median')} | "
            f"{m.get('p05')} | {m.get('p95')} | {_pct(m.get('pass_rate_approx'))} |"
        )
    lines += [
        "",
        "## Example interpretation",
        "",
        "If `R5_rank7.chaos` mean margin is largely negative or NULL, rank7 drops on chaos before high_pace is decisive.",
        "",
        "## Guardrails",
        "",
        f"- product_mutation: `{report.get('product_mutation')}`",
        f"- world_trigger_changed: `{report.get('world_trigger_changed')}`",
        f"- improvement_forbidden: `{report.get('improvement_forbidden')}`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_bottleneck_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version27 — Trigger Bottleneck",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Question:** Which condition most often stops each World from firing?  ",
        "",
        "## By World",
        "",
    ]
    for w in EXISTING_WORLDS:
        rank = (report.get("bottleneck_by_world") or {}).get(w) or []
        lines.append(f"### `{w}`")
        lines.append("")
        if not rank:
            lines.append("_No failed-rule bottleneck counted (rule rarely evaluated as fail, or world only default)._")
            lines.append("")
            continue
        lines.append("| Rank | Condition | N | Share among dropouts |")
        lines.append("|-----:|-----------|--:|---------------------:|")
        for i, row in enumerate(rank, 1):
            lines.append(
                f"| {i} | `{row.get('signal')}` | {row.get('n')} | {_pct(row.get('share'))} |"
            )
        lines.append("")
    lines += [
        "## By Rule",
        "",
        "| Rule | World | #1 bottleneck | #2 | #3 |",
        "|------|-------|---------------|----|----|",
    ]
    for rid, block in (report.get("saturation_by_rule") or {}).items():
        br = block.get("bottleneck_rank") or []
        a = br[0]["signal"] if len(br) > 0 else "-"
        b = br[1]["signal"] if len(br) > 1 else "-"
        c = br[2]["signal"] if len(br) > 2 else "-"
        lines.append(f"| `{rid}` | `{block.get('world')}` | `{a}` | `{b}` | `{c}` |")
    lines += [
        "",
        "## Near Activation counts",
        "",
        "| World | Near-N |",
        "|-------|-------:|",
    ]
    for w in EXISTING_WORLDS:
        lines.append(
            f"| `{w}` | {(report.get('near_activation_counts') or {}).get(w, 0)} |"
        )
    lines += [
        "",
        "### Near Activation examples",
        "",
    ]
    for w, items in (report.get("near_activation") or {}).items():
        if not items:
            continue
        lines.append(f"#### `{w}`")
        for it in items[:12]:
            lines.append(
                f"- `{it.get('race_id')}` rule=`{it.get('rule_id')}` "
                f"margin=`{it.get('margin')}` assigned=`{it.get('assigned_world')}`"
            )
        lines.append("")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_distribution_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version27 — Trigger Signal Distribution",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Source:** V25 `research_world_signals` on labeled canonical Predictions  ",
        "",
    ]
    for k, block in (report.get("distributions") or {}).items():
        lines += [
            f"## `{k}`",
            "",
            f"- N present: `{block.get('n')}`",
            f"- Missing: `{block.get('missing_n')}` ({_pct(block.get('missing_rate'))})",
            f"- Mean / Median: `{block.get('mean')}` / `{block.get('median')}`",
            f"- P05 / P95: `{block.get('p05')}` / `{block.get('p95')}`",
            "",
            "| Bin | N | Rate | Bar |",
            "|-----|--:|-----:|-----|",
        ]
        lines.extend(_fmt_hist(block.get("histogram") or []))
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_saturation_md(report: dict[str, Any], path: Path) -> None:
    s = report.get("sample") or {}
    lines = [
        "# Version27 — Trigger Saturation",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "## Observed assignment",
        "",
        f"- N: `{s.get('n_labeled_canonical')}`",
        "",
        "| World | Assigned N | Observed share |",
        "|-------|-----------:|---------------:|",
    ]
    counts = s.get("assigned_counts") or {}
    obs = report.get("observed_share") or {}
    for w in EXISTING_WORLDS:
        lines.append(
            f"| `{w}` | {counts.get(w, 0)} | {_pct(obs.get(w))} |"
        )
    lines += [
        "",
        "## First-match simulation (same priority order, frozen thresholds)",
        "",
        "| World | Simulated share |",
        "|-------|----------------:|",
    ]
    for w in EXISTING_WORLDS:
        lines.append(
            f"| `{w}` | {_pct((report.get('simulated_first_match_share') or {}).get(w))} |"
        )
    lines += [
        "",
        "## Why midupper saturates (observational)",
        "",
        "Priority order (unchanged):",
        "",
        "1. mixed (short_field≥0.72 ∧ …)",
        "2. **midupper** (short_field≥0.58 ∧ difficulty≥0.38)",
        "3. mixed (phase≥0.62)",
        "4. midhole",
        "5. rank7",
        "6. bug",
        "7. midupper (difficulty≥0.50)",
        "8. core default",
        "",
        "Saturation reading uses rule pass rates + bottleneck ranks below — no threshold changes.",
        "",
        "## Rule pass / fail",
        "",
        "| Rule | World | Pass | Fail | Pass rate | Mean margin | Top dropout |",
        "|------|-------|-----:|-----:|----------:|------------:|-------------|",
    ]
    for rid, block in (report.get("saturation_by_rule") or {}).items():
        top = (block.get("top_dropout_condition") or {}).get("signal")
        m = (block.get("margin") or {}).get("mean")
        lines.append(
            f"| `{rid}` | `{block.get('world')}` | {block.get('pass_n')} | "
            f"{block.get('fail_n')} | {_pct(block.get('pass_rate'))} | {m} | `{top}` |"
        )
    lines += [
        "",
        "## Guardrails",
        "",
        "- Trigger / thresholds / Worlds not modified",
        "- Improvement proposals forbidden in V27",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_design_gap_md(report: dict[str, Any], path: Path) -> None:
    gsum = report.get("design_gap_summary") or {}
    lines = [
        "# Version27 — Design Gap (Observational)",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Design reference mix (research intent, not a product knob):** "
        "core 30% / midupper 35% / rank7 15% / mixed 10% / bug 5% / midhole 5%  ",
        "",
        "## Quantitative gap",
        "",
        f"- Total variation distance: `{gsum.get('total_variation_distance')}`",
        f"- L1 absolute gap: `{gsum.get('l1_abs_gap')}`",
        f"- Max |gap| world: `{gsum.get('max_abs_gap_world')}`",
        "",
        "| World | Design | Observed | Sim first-match | Gap (pp) | Obs/Design |",
        "|-------|-------:|---------:|----------------:|---------:|-----------:|",
    ]
    for w in EXISTING_WORLDS:
        d = (report.get("design_gap") or {}).get(w) or {}
        lines.append(
            f"| `{w}` | {_pct(d.get('design'))} | {_pct(d.get('observed'))} | "
            f"{_pct(d.get('simulated_first_match'))} | {d.get('gap_pp')} | "
            f"{d.get('ratio_obs_design')} |"
        )
    lines += [
        "",
        "## Reading (facts only)",
        "",
        "- Positive gap_pp ⇒ over-represented vs design intent",
        "- Negative gap_pp ⇒ under-represented vs design intent",
        "- This document does **not** propose Trigger changes",
        "",
        "## Guardrails",
        "",
        f"- improvement_forbidden: `{report.get('improvement_forbidden')}`",
        f"- world_trigger_changed: `{report.get('world_trigger_changed')}`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write() -> dict[str, Any]:
    ops = WorldTriggerSaturationResearch()
    report = ops.analyze()
    docs = repo_root() / "docs" / "research"
    docs.mkdir(parents=True, exist_ok=True)
    paths = {
        "margin": docs / "v27-trigger-margin.md",
        "bottleneck": docs / "v27-trigger-bottleneck.md",
        "distribution": docs / "v27-trigger-distribution.md",
        "saturation": docs / "v27-trigger-saturation.md",
        "design_gap": docs / "v27-design-gap.md",
    }
    write_margin_md(report, paths["margin"])
    write_bottleneck_md(report, paths["bottleneck"])
    write_distribution_md(report, paths["distribution"])
    write_saturation_md(report, paths["saturation"])
    write_design_gap_md(report, paths["design_gap"])
    json_path = evidence_root() / "reports" / "v27-trigger-saturation.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    slim = {k: v for k, v in report.items() if k not in {"race_sample"}}
    slim["race_sample"] = report.get("race_sample")
    json_path.write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {**{k: str(p) for k, p in paths.items()}, "json": str(json_path)}
    return report
