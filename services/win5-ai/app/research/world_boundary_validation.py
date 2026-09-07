# -*- coding: utf-8 -*-
"""
Version40 — World Boundary Validation

Validate Trigger boundaries under V39-restored signals (read-only).
No Trigger / Threshold / World / SubWorld / Production changes.
"""
from __future__ import annotations

import json
import math
import warnings
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .config import evidence_root, repo_root
from .signal_restoration_sim import SignalRestorationSimulation
from .world_boundary_research import AMBIGUITY_MARGIN, EXISTING_WORLDS
from .world_fitness_research import trigger_proximity_fitness
from .world_trigger_saturation import (
    DESIGN_SHARE,
    TRIGGER_RULES,
    evaluate_all_rules,
    first_match_world,
)
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-world-boundary-validation/1.0"
NEAR_MISS_EPS = AMBIGUITY_MARGIN  # 0.15 soft fitness margin
PERTURB_DELTAS = (0.02, 0.05)


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


def shannon_entropy(counts: Counter | dict[str, int]) -> float:
    vals = [int(v) for v in counts.values() if int(v) > 0]
    n = sum(vals)
    if n <= 0:
        return 0.0
    h = 0.0
    for v in vals:
        p = v / n
        h -= p * math.log(p, 2)
    return h


def total_variation(p: dict[str, float], q: dict[str, float]) -> float:
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


def winner_rank_bucket(world: str, rank: int | None) -> str:
    if rank is None:
        return "unknown"
    if world == "core_world":
        return "aligned" if rank <= 3 else ("soft" if rank <= 5 else "misaligned")
    if world == "midupper_world":
        return "aligned" if 2 <= rank <= 6 else ("soft" if rank <= 8 else "misaligned")
    if world == "midhole_world":
        return "aligned" if 5 <= rank <= 10 else ("soft" if 4 <= rank <= 11 else "misaligned")
    if world == "rank7_world":
        return "aligned" if 7 <= rank <= 10 else ("soft" if 6 <= rank <= 11 else "misaligned")
    if world == "bug_world":
        return "aligned" if rank >= 11 else ("soft" if rank >= 9 else "misaligned")
    if world == "mixed_world":
        return "aligned" if rank <= 10 else "soft"
    return "unknown"


def perturb_signals(sig: dict[str, float | None], delta: float, direction: int) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for k, v in sig.items():
        if v is None:
            out[k] = None
        else:
            out[k] = max(0.0, min(1.0, float(v) + direction * delta))
    return out


class WorldBoundaryValidation:
    def __init__(self) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()
        self.restorer = SignalRestorationSimulation()

    def _winners(self) -> dict[str, dict[str, Any]]:
        con = connect()
        out: dict[str, dict[str, Any]] = {}
        for r in con.execute(
            """
            SELECT race_id, winner_horse_number, prediction_pick
            FROM research_prediction_corpus
            WHERE winner_horse_number IS NOT NULL
            """
        ):
            out[str(r["race_id"])] = {
                "winner": _i(r["winner_horse_number"]),
                "pick": _i(r["prediction_pick"]),
            }
        # also race_results
        for r in con.execute(
            "SELECT race_id, winner_horse_number FROM race_results WHERE winner_horse_number IS NOT NULL"
        ):
            rid = str(r["race_id"])
            if rid not in out:
                out[rid] = {"winner": _i(r["winner_horse_number"]), "pick": None}
        return out

    def _winner_model_rank(self, rid: str, winner: int | None) -> int | None:
        if winner is None:
            return None
        warnings.filterwarnings("ignore")
        import sys

        sys.path.insert(0, "/opt/expect-ai/platform")
        from ai_platform.core.features import FeatureGenerator, FeatureLoader
        from ai_platform.core.scoring import Scorer

        loaded = FeatureLoader().load(str(rid))
        if loaded is None:
            return None
        frame = loaded.frame
        fm = FeatureGenerator().build_feature_matrix(frame)
        scores = Scorer().score_candidates(fm)
        # map horse_number -> rank by win_prob
        if "horse_number" not in frame.columns:
            return None
        work = frame.copy()
        work["_wp"] = list(scores["win_prob"]) if hasattr(scores["win_prob"], "__iter__") else scores["win_prob"]
        # scores may align by index
        try:
            import pandas as pd

            wp = scores["win_prob"]
            if isinstance(wp, pd.Series):
                work["_wp"] = wp.reindex(work.index).fillna(0.0)
            else:
                work["_wp"] = list(wp)
        except Exception:
            return None
        work = work.sort_values("_wp", ascending=False).reset_index(drop=True)
        for i, row in work.iterrows():
            if _i(row.get("horse_number")) == winner:
                return int(i) + 1
        return None

    def analyze(self) -> dict[str, Any]:
        meta = self.restorer._load_meta()
        loadable = self.restorer._find_loadable(meta)
        winners = self._winners()

        rows: list[dict[str, Any]] = []
        for rid in loadable:
            sig, info = self.restorer._restore_signals(rid, meta.get(rid) or {})
            if not info.get("ok"):
                continue
            ev = evaluate_all_rules(sig)
            assigned = first_match_world(ev)
            prox = trigger_proximity_fitness(
                {
                    "short_field_pressure": sig.get("short_field_pressure"),
                    "phase": sig.get("phase"),
                    "chaos": sig.get("chaos"),
                    "difficulty": sig.get("difficulty"),
                    "late_stop": sig.get("late_stop"),
                    "sustained": sig.get("sustained"),
                    "high_pace": sig.get("high_pace"),
                }
            )
            soft = prox["soft"]
            fit_assigned = float(soft.get(assigned, 0.0))
            # rule margins for assigned / competitors
            rule_margins = {}
            for r in ev:
                if r.get("is_default"):
                    rule_margins[r["world"]] = {
                        "rule_id": r["rule_id"],
                        "pass": True,
                        "margin": 0.0,
                        "is_default": True,
                    }
                else:
                    rule_margins[r["world"]] = {
                        "rule_id": r["rule_id"],
                        "pass": bool(r.get("pass")),
                        "margin": r.get("margin"),
                        "is_default": False,
                    }
            # best non-assigned soft fitness
            others = [(w, s) for w, s in soft.items() if w != assigned]
            others.sort(key=lambda x: -x[1])
            second_w, second_s = others[0] if others else (None, 0.0)
            sep = fit_assigned - float(second_s)
            # silhouette-like on similarity
            denom = max(fit_assigned, float(second_s), 1e-9)
            silhouette = sep / denom

            winfo = winners.get(rid) or {}
            winner = winfo.get("winner")
            # avoid double full score when possible: use info frame path once more only if needed
            wrank = self._winner_model_rank(rid, winner)
            align = winner_rank_bucket(assigned, wrank)
            hit = bool(winner is not None and winfo.get("pick") is not None and winner == winfo.get("pick"))

            # stability under perturbation
            flips = 0
            trials = 0
            for delta in PERTURB_DELTAS:
                for direction in (-1, 1):
                    trials += 1
                    psig = perturb_signals(sig, delta, direction)
                    pw = first_match_world(evaluate_all_rules(psig))
                    if pw != assigned:
                        flips += 1

            # near-miss: assigned core (or any) with small soft margin to another world
            near_targets = []
            for w, s in soft.items():
                if w == assigned:
                    continue
                gap = fit_assigned - float(s)
                if abs(gap) <= NEAR_MISS_EPS:
                    near_targets.append({"world": w, "fitness": s, "gap": round(gap, 4)})

            rows.append(
                {
                    "race_id": rid,
                    "assigned_world": assigned,
                    "fitness": soft,
                    "fit_assigned": fit_assigned,
                    "best_fit_world": prox["best_fit_world"],
                    "best_fit": prox["best_fit"],
                    "second_fit_world": second_w,
                    "second_fit": second_s,
                    "soft_margin": round(sep, 4),
                    "silhouette": round(silhouette, 4),
                    "agree_best_fit": bool(assigned == prox["best_fit_world"]),
                    "rule_margins": rule_margins,
                    "winner": winner,
                    "winner_model_rank": wrank,
                    "winner_alignment": align,
                    "hit_pick": hit,
                    "stability_flip_rate": flips / trials if trials else None,
                    "stability_flips": flips,
                    "stability_trials": trials,
                    "near_miss_targets": near_targets,
                    "signals": sig,
                }
            )

        n = len(rows) or 1
        world_c = Counter(r["assigned_world"] for r in rows)
        share = {w: world_c.get(w, 0) / n for w in EXISTING_WORLDS}

        # ① aggregate fitness
        mean_fit = {
            w: _safe_div(sum(float(r["fitness"].get(w, 0.0)) for r in rows), len(rows))
            for w in EXISTING_WORLDS
        }
        mean_fit_given_assigned = {}
        for w in EXISTING_WORLDS:
            subset = [r for r in rows if r["assigned_world"] == w]
            mean_fit_given_assigned[w] = {
                "n": len(subset),
                "mean_own_fitness": _safe_div(
                    sum(r["fit_assigned"] for r in subset), len(subset)
                ),
                "mean_soft_margin": _safe_div(
                    sum(r["soft_margin"] for r in subset), len(subset)
                ),
                "mean_silhouette": _safe_div(
                    sum(r["silhouette"] for r in subset), len(subset)
                ),
                "agree_best_fit_rate": _safe_div(
                    sum(1 for r in subset if r["agree_best_fit"]), len(subset)
                ),
            }

        # ② winner alignment
        align_c = Counter(r["winner_alignment"] for r in rows)
        align_by_world = {}
        for w in EXISTING_WORLDS:
            subset = [r for r in rows if r["assigned_world"] == w]
            ac = Counter(r["winner_alignment"] for r in subset)
            align_by_world[w] = {
                "n": len(subset),
                "aligned": ac.get("aligned", 0),
                "soft": ac.get("soft", 0),
                "misaligned": ac.get("misaligned", 0),
                "unknown": ac.get("unknown", 0),
                "aligned_rate": _safe_div(ac.get("aligned", 0), len(subset)),
                "mean_winner_rank": _safe_div(
                    sum(r["winner_model_rank"] for r in subset if r["winner_model_rank"]),
                    sum(1 for r in subset if r["winner_model_rank"]),
                ),
            }

        # ③ boundary margins (mean rule margin for each world's primary non-default rules)
        margin_stats = {}
        for w in EXISTING_WORLDS:
            margins = []
            for r in rows:
                rm = (r["rule_margins"] or {}).get(w) or {}
                if rm.get("is_default"):
                    continue
                if rm.get("margin") is not None:
                    margins.append(float(rm["margin"]))
            pos = [m for m in margins if m >= 0]
            neg = [m for m in margins if m < 0]
            margin_stats[w] = {
                "n_obs": len(margins),
                "mean_margin": _safe_div(sum(margins), len(margins)),
                "pass_rate": _safe_div(len(pos), len(margins)),
                "near_zero_rate": _safe_div(
                    sum(1 for m in margins if abs(m) <= 0.05), len(margins)
                ),
                "negative_rate": _safe_div(len(neg), len(margins)),
            }

        # ambiguous races: soft_margin small
        ambiguous = [r for r in rows if abs(r["soft_margin"]) <= NEAR_MISS_EPS]
        ambiguous_rate = len(ambiguous) / n

        # ④ near miss among core-assigned
        core_rows = [r for r in rows if r["assigned_world"] == "core_world"]
        near_miss_core = []
        for r in core_rows:
            if not r["near_miss_targets"]:
                continue
            near_miss_core.append(
                {
                    "race_id": r["race_id"],
                    "fit_core": r["fit_assigned"],
                    "targets": r["near_miss_targets"],
                    "best_alt": r["second_fit_world"],
                    "best_alt_fit": r["second_fit"],
                    "soft_margin": r["soft_margin"],
                    "winner_model_rank": r["winner_model_rank"],
                }
            )
        near_miss_core.sort(key=lambda x: x["soft_margin"])

        # ⑤ stability
        mean_flip = _safe_div(sum(r["stability_flip_rate"] or 0 for r in rows), len(rows))
        unstable = [r for r in rows if (r["stability_flip_rate"] or 0) >= 0.25]
        stability = {
            "mean_flip_rate": mean_flip,
            "unstable_race_n": len(unstable),
            "unstable_rate": len(unstable) / n,
            "by_world": {
                w: {
                    "n": sum(1 for r in rows if r["assigned_world"] == w),
                    "mean_flip_rate": _safe_div(
                        sum(
                            (r["stability_flip_rate"] or 0)
                            for r in rows
                            if r["assigned_world"] == w
                        ),
                        sum(1 for r in rows if r["assigned_world"] == w),
                    ),
                }
                for w in EXISTING_WORLDS
                if world_c.get(w, 0)
            },
        }

        # ⑥ distribution quality
        h = shannon_entropy(world_c)
        hmax = math.log(len(EXISTING_WORLDS), 2)
        # information gain vs flat prior over 6 worlds
        ig = h  # vs single-bucket 0; vs uniform: hmax - KL later
        mean_sil = _safe_div(sum(r["silhouette"] for r in rows), len(rows))
        mean_sep = _safe_div(sum(r["soft_margin"] for r in rows), len(rows))
        agree_rate = _safe_div(sum(1 for r in rows if r["agree_best_fit"]), len(rows))
        tv = total_variation(share, DESIGN_SHARE)
        quality = {
            "entropy_bits": h,
            "entropy_ratio": _safe_div(h, hmax),
            "information_gain_vs_collapse": h,
            "mean_soft_margin": mean_sep,
            "mean_silhouette": mean_sil,
            "agree_best_fit_rate": agree_rate,
            "ambiguous_rate": ambiguous_rate,
            "tv_to_design": tv,
            "world_share": share,
            "world_counts": dict(world_c),
        }

        # ⑦ trigger diagnosis (no threshold changes)
        diagnosis = {}
        for w in EXISTING_WORLDS:
            obs = share.get(w, 0.0)
            des = DESIGN_SHARE.get(w, 0.0)
            ms = mean_fit_given_assigned[w]
            # near-miss INTO this world from others
            inbound = 0
            for r in rows:
                if r["assigned_world"] == w:
                    continue
                for t in r["near_miss_targets"]:
                    if t["world"] == w:
                        inbound += 1
                        break
            # near-miss OUT from this world
            outbound = sum(
                1
                for r in rows
                if r["assigned_world"] == w and r["near_miss_targets"]
            )
            ratio = _safe_div(obs, des) if des else None
            if obs == 0 and inbound == 0:
                label = "不足"
                why = "never assigned under restored signals; no inbound near-miss"
            elif obs == 0 and inbound > 0:
                label = "不足"
                why = f"never assigned but {inbound} inbound near-miss races"
            elif ratio is not None and ratio >= 1.8 and (
                (ms.get("mean_soft_margin") or 0) < 0.15 or outbound / max(ms["n"], 1) >= 0.35
            ):
                label = "過剰"
                why = (
                    f"share {obs:.1%} vs design {des:.1%}; "
                    f"weak separation or high outbound near-miss"
                )
            elif ratio is not None and ratio >= 1.8:
                label = "過剰"
                why = f"share {obs:.1%} vs design {des:.1%} (volume over-firing as default/other)"
            elif ratio is not None and ratio <= 0.4:
                label = "不足"
                why = f"share {obs:.1%} vs design {des:.1%}"
            else:
                label = "適正"
                why = f"share near design ({obs:.1%} vs {des:.1%}) with observable assignment"
            # refine: core default sink
            if w == "core_world" and obs >= 0.55:
                label = "過剰"
                why = (
                    f"default sink {obs:.1%} (design {des:.1%}); "
                    f"agree_best_fit={_pct(ms.get('agree_best_fit_rate'))}"
                )
            diagnosis[w] = {
                "label": label,
                "observed_share": obs,
                "design_share": des,
                "share_ratio_vs_design": ratio,
                "inbound_near_miss_n": inbound,
                "outbound_near_miss_n": outbound,
                "mean_own_fitness": ms.get("mean_own_fitness"),
                "mean_soft_margin": ms.get("mean_soft_margin"),
                "reason": why,
            }

        # ⑧ governance
        over_n = sum(1 for w, x in diagnosis.items() if x["label"] == "過剰")
        under_n = sum(1 for w, x in diagnosis.items() if x["label"] == "不足")
        core_share = share.get("core_world", 0.0)
        if core_share >= 0.55 or over_n >= 1 and tv >= 0.35:
            verdict = "C"
            reason = (
                f"Boundary over-concentrates (core_share={core_share:.1%}, "
                f"TV_design={tv:.3f}, over_worlds={over_n})"
            )
        elif ambiguous_rate >= 0.35 or (mean_sil is not None and mean_sil < 0.15) or mean_flip >= 0.20:
            verdict = "B"
            reason = (
                f"Ambiguous boundaries (ambiguous_rate={ambiguous_rate:.1%}, "
                f"mean_silhouette={mean_sil}, mean_flip_rate={mean_flip})"
            )
        else:
            verdict = "A"
            reason = (
                f"Separation adequate (mean_silhouette={mean_sil}, "
                f"ambiguous_rate={ambiguous_rate:.1%}, TV={tv:.3f})"
            )

        # demote A if C conditions also mild — already handled
        # if both ambiguous and biased, prefer C when core dominance strong
        if verdict == "B" and core_share >= 0.60:
            verdict = "C"
            reason = (
                f"Ambiguity present but primary issue is bias "
                f"(core_share={core_share:.1%}, ambiguous_rate={ambiguous_rate:.1%})"
            )

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "shadow_only": True,
            "product_mutation": False,
            "trigger_unchanged": True,
            "threshold_unchanged": True,
            "method": {
                "signals": "V39 restored signal pack (virtual)",
                "assignment": "first_match Trigger rules (unchanged)",
                "fitness": "trigger_proximity_fitness (V26)",
                "perturbation": list(PERTURB_DELTAS),
                "near_miss_eps": NEAR_MISS_EPS,
            },
            "corpus": {
                "n": len(rows),
                "featureloader_loadable": len(loadable),
            },
            "world_fitness": {
                "mean_fitness_all_races": mean_fit,
                "by_assigned_world": mean_fit_given_assigned,
            },
            "winner_alignment": {
                "overall": dict(align_c),
                "aligned_rate": _safe_div(align_c.get("aligned", 0), len(rows)),
                "by_world": align_by_world,
            },
            "boundary_margin": {
                "by_world_rule_margin": margin_stats,
                "ambiguous_race_n": len(ambiguous),
                "ambiguous_rate": ambiguous_rate,
                "mean_soft_margin": mean_sep,
            },
            "near_miss": {
                "core_assigned_n": len(core_rows),
                "core_near_miss_n": len(near_miss_core),
                "core_near_miss_rate": _safe_div(len(near_miss_core), len(core_rows)),
                "examples": near_miss_core[:20],
                "alt_world_counts": dict(
                    Counter(
                        t["world"]
                        for r in near_miss_core
                        for t in r["targets"]
                    )
                ),
            },
            "boundary_stability": stability,
            "distribution_quality": quality,
            "trigger_diagnosis": diagnosis,
            "governance": {
                "verdict": verdict,
                "labels": {
                    "A": "現在の Boundary は妥当",
                    "B": "Boundary が曖昧",
                    "C": "Boundary が過度に偏っている",
                },
                "reason": reason,
                "metrics": {
                    "core_share": core_share,
                    "tv_to_design": tv,
                    "ambiguous_rate": ambiguous_rate,
                    "mean_silhouette": mean_sil,
                    "mean_flip_rate": mean_flip,
                    "over_worlds": over_n,
                    "under_worlds": under_n,
                },
            },
        }


def write_docs(report: dict[str, Any], docs_dir: Path) -> dict[str, str]:
    docs_dir.mkdir(parents=True, exist_ok=True)
    wf = report["world_fitness"]
    wa = report["winner_alignment"]
    bm = report["boundary_margin"]
    nm = report["near_miss"]
    st = report["boundary_stability"]
    dq = report["distribution_quality"]
    td = report["trigger_diagnosis"]
    gov = report["governance"]
    n = report["corpus"]["n"]

    fit_lines = [
        "# Version40 — World Fitness",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        f"**N:** `{n}` (V39 restored signals + unchanged Triggers)  ",
        f"**Governance:** **{gov['verdict']}**",
        "",
        "## ① Mean fitness (all races → each World)",
        "",
        "| World | Mean trigger-proximity fitness |",
        "|-------|-------------------------------:|",
    ]
    for w in EXISTING_WORLDS:
        fit_lines.append(f"| {w} | {(wf['mean_fitness_all_races'].get(w) or 0):.4f} |")
    fit_lines.extend(
        [
            "",
            "## Fitness given assigned World",
            "",
            "| Assigned | n | mean own fit | mean margin | mean silhouette | agree best-fit |",
            "|----------|--:|-------------:|------------:|----------------:|---------------:|",
        ]
    )
    for w in EXISTING_WORLDS:
        r = wf["by_assigned_world"][w]
        if r["n"] == 0:
            fit_lines.append(f"| {w} | 0 | — | — | — | — |")
            continue
        fit_lines.append(
            f"| {w} | {r['n']} | {(r['mean_own_fitness'] or 0):.4f} | "
            f"{(r['mean_soft_margin'] or 0):.4f} | {(r['mean_silhouette'] or 0):.4f} | "
            f"{_pct(r['agree_best_fit_rate'])} |"
        )
    fit_lines.extend(
        [
            "",
            "## ② Winner alignment",
            "",
            f"- Overall aligned rate: `{_pct(wa['aligned_rate'])}`",
            f"- Counts: `{json.dumps(wa['overall'], ensure_ascii=False)}`",
            "",
            "| World | n | aligned | soft | misaligned | aligned rate | mean winner rank |",
            "|-------|--:|--------:|-----:|-----------:|-------------:|-----------------:|",
        ]
    )
    for w in EXISTING_WORLDS:
        r = wa["by_world"][w]
        fit_lines.append(
            f"| {w} | {r['n']} | {r['aligned']} | {r['soft']} | {r['misaligned']} | "
            f"{_pct(r['aligned_rate'])} | "
            f"{(r['mean_winner_rank'] if r['mean_winner_rank'] is not None else float('nan')):.2f} |"
        )
    fit_lines.extend(
        [
            "",
            "## Index",
            "",
            "| Doc | Content |",
            "|-----|---------|",
            "| `v40-world-fitness.md` | this file |",
            "| `v40-boundary-margin.md` | margins / ambiguity |",
            "| `v40-near-miss.md` | core near-miss |",
            "| `v40-boundary-quality.md` | quality + trigger diagnosis |",
            "| `v40-governance.md` | A/B/C |",
            "",
            "## Guardrails",
            "",
            "- Trigger / Threshold / World / SubWorld / Production — unchanged",
            "",
        ]
    )

    margin_lines = [
        "# Version40 — Boundary Margin",
        "",
        f"**N:** `{n}`  ",
        f"**Ambiguous rate (|soft_margin| ≤ {NEAR_MISS_EPS}):** `{_pct(bm['ambiguous_rate'])}` "
        f"({bm['ambiguous_race_n']} races)",
        "",
        "## ③ Rule margins by World",
        "",
        "| World | n_obs | mean margin | pass rate | near-zero (|m|≤0.05) | negative rate |",
        "|-------|------:|------------:|----------:|---------------------:|--------------:|",
    ]
    for w in EXISTING_WORLDS:
        r = bm["by_world_rule_margin"][w]
        margin_lines.append(
            f"| {w} | {r['n_obs']} | "
            f"{(r['mean_margin'] if r['mean_margin'] is not None else float('nan')):.4f} | "
            f"{_pct(r['pass_rate'])} | {_pct(r['near_zero_rate'])} | {_pct(r['negative_rate'])} |"
        )
    margin_lines.extend(
        [
            "",
            f"- Mean soft margin (assigned vs 2nd): `{(bm['mean_soft_margin'] or 0):.4f}`",
            "",
            "Positive margin ⇒ rule condition exceeded. Near-zero ⇒ ambiguous boundary.",
            "",
        ]
    )

    near_lines = [
        "# Version40 — Near Miss (core-assigned)",
        "",
        f"**Core assigned:** `{nm['core_assigned_n']}`  ",
        f"**Near-miss among core:** `{nm['core_near_miss_n']}` "
        f"(`{_pct(nm['core_near_miss_rate'])}`)",
        "",
        "## ④ Alt-world attraction from core",
        "",
        f"Counts: `{json.dumps(nm['alt_world_counts'], ensure_ascii=False)}`",
        "",
        "| Race | fit_core | best_alt | alt_fit | soft_margin | winner_rank |",
        "|------|---------:|----------|--------:|------------:|------------:|",
    ]
    for ex in nm["examples"]:
        near_lines.append(
            f"| `{ex['race_id']}` | {ex['fit_core']:.3f} | `{ex['best_alt']}` | "
            f"{ex['best_alt_fit']:.3f} | {ex['soft_margin']:.3f} | "
            f"{ex['winner_model_rank']} |"
        )
    if not nm["examples"]:
        near_lines.append("| — | — | — | — | — | — |")
    near_lines.append("")

    qual_lines = [
        "# Version40 — Boundary Quality & Trigger Diagnosis",
        "",
        f"**N:** `{n}`",
        "",
        "## ⑤ Stability (signal ±0.02 / ±0.05)",
        "",
        f"- Mean flip rate: `{_pct(st['mean_flip_rate'])}`",
        f"- Unstable races (≥25% flips): `{st['unstable_race_n']}` (`{_pct(st['unstable_rate'])}`)",
        "",
        "| World | n | mean flip rate |",
        "|-------|--:|---------------:|",
    ]
    for w, r in (st.get("by_world") or {}).items():
        qual_lines.append(f"| {w} | {r['n']} | {_pct(r['mean_flip_rate'])} |")
    qual_lines.extend(
        [
            "",
            "## ⑥ Distribution quality",
            "",
            "| Metric | Value |",
            "|--------|------:|",
            f"| Entropy (bits) | {dq['entropy_bits']:.3f} |",
            f"| Entropy ratio | {_pct(dq['entropy_ratio'])} |",
            f"| IG vs collapse | {dq['information_gain_vs_collapse']:.3f} |",
            f"| Mean soft margin | {(dq['mean_soft_margin'] or 0):.4f} |",
            f"| Mean silhouette | {(dq['mean_silhouette'] or 0):.4f} |",
            f"| Agree best-fit rate | {_pct(dq['agree_best_fit_rate'])} |",
            f"| Ambiguous rate | {_pct(dq['ambiguous_rate'])} |",
            f"| TV to design | {dq['tv_to_design']:.3f} |",
            "",
            f"Shares: `{json.dumps(dq['world_share'], ensure_ascii=False)}`",
            "",
            "## ⑦ Trigger diagnosis (no threshold changes)",
            "",
            "| World | Diagnosis | obs share | design | ratio | inbound NM | outbound NM | reason |",
            "|-------|-----------|----------:|-------:|------:|-----------:|------------:|--------|",
        ]
    )
    for w in EXISTING_WORLDS:
        r = td[w]
        qual_lines.append(
            f"| {w} | **{r['label']}** | {_pct(r['observed_share'])} | {_pct(r['design_share'])} | "
            f"{(r['share_ratio_vs_design'] if r['share_ratio_vs_design'] is not None else float('nan')):.2f} | "
            f"{r['inbound_near_miss_n']} | {r['outbound_near_miss_n']} | {r['reason']} |"
        )
    qual_lines.append("")

    gov_md = f"""# Version40 — Governance

**Generated:** `{report['generated_at']}`  
**N:** `{n}`

## ⑧ Verdict options

| Code | Meaning |
|------|---------|
| A | 現在の Boundary は妥当 |
| B | Boundary が曖昧 |
| C | Boundary が過度に偏っている |

## Final verdict

# **{gov['verdict']}**

**Label:** {gov['labels'][gov['verdict']]}  
**Reason:** {gov['reason']}

### Supporting metrics

| Metric | Value |
|--------|------:|
| core_share | {_pct(gov['metrics']['core_share'])} |
| TV to design | {gov['metrics']['tv_to_design']:.3f} |
| ambiguous_rate | {_pct(gov['metrics']['ambiguous_rate'])} |
| mean_silhouette | {(gov['metrics']['mean_silhouette'] or 0):.4f} |
| mean_flip_rate | {_pct(gov['metrics']['mean_flip_rate'])} |
| over_worlds | {gov['metrics']['over_worlds']} |
| under_worlds | {gov['metrics']['under_worlds']} |

## Guardrails

- Research / Audit / Simulation only
- No Trigger / Threshold / World / SubWorld changes
- No improvement proposals
"""

    paths = {
        "fit": docs_dir / "v40-world-fitness.md",
        "margin": docs_dir / "v40-boundary-margin.md",
        "near": docs_dir / "v40-near-miss.md",
        "qual": docs_dir / "v40-boundary-quality.md",
        "gov": docs_dir / "v40-governance.md",
    }
    paths["fit"].write_text("\n".join(fit_lines), encoding="utf-8")
    paths["margin"].write_text("\n".join(margin_lines), encoding="utf-8")
    paths["near"].write_text("\n".join(near_lines), encoding="utf-8")
    paths["qual"].write_text("\n".join(qual_lines), encoding="utf-8")
    paths["gov"].write_text(gov_md, encoding="utf-8")
    return {k: str(v) for k, v in paths.items()}


def run_and_write() -> dict[str, Any]:
    warnings.filterwarnings("ignore")
    report = WorldBoundaryValidation().analyze()
    reports = evidence_root() / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    json_path = reports / "v40-world-boundary-validation.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    docs = write_docs(report, repo_root() / "docs" / "research")
    report["_outputs"] = {"json": str(json_path), **docs}
    return report


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    rep = run_and_write()
    print(
        json.dumps(
            {
                "ok": True,
                "verdict": rep["governance"]["verdict"],
                "reason": rep["governance"]["reason"],
                "n": rep["corpus"]["n"],
                "core_share": rep["governance"]["metrics"]["core_share"],
                "ambiguous_rate": rep["boundary_margin"]["ambiguous_rate"],
                "diagnosis": {
                    w: v["label"] for w, v in rep["trigger_diagnosis"].items()
                },
                "outputs": rep.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
