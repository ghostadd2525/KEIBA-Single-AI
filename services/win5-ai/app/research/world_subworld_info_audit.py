# -*- coding: utf-8 -*-
"""
Version38 — World × SubWorld Information Audit

Research / Audit only. No product mutation. No new Worlds.
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
from .world_activation_research import WORLD_ROLES
from .world_boundary_research import (
    EXISTING_SUBWORLDS,
    EXISTING_WORLDS,
    extract_world_label,
)
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-world-subworld-info-audit/1.0"

# Design SubWorld inventory per World (from V24 roles + EXISTING_SUBWORLDS).
# Names must already exist — do not invent new Worlds or new SubWorld labels here.
DESIGN_SUBWORLDS: dict[str, tuple[str, ...]] = {
    "core_world": ("core_top", "core_under"),
    "midupper_world": ("midupper_route", "midupper_spread", "midupper_corelike"),
    "midhole_world": ("fallback_standard",),  # named inventory thin vs role text
    "rank7_world": ("rank7_transition", "rank7_residual"),
    "bug_world": ("fallback_standard",),  # no dedicated bug_* in EXISTING_SUBWORLDS
    "mixed_world": ("fallback_standard",),  # role implies multi-route; named inventory thin
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _i(v: Any) -> int | None:
    try:
        if v is None or v == "":
            return None
        return int(float(v))
    except (TypeError, ValueError):
        return None


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


def max_entropy(k: int) -> float:
    if k <= 1:
        return 0.0
    return math.log(k, 2)


def runners_of(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    for path in (
        ("runners",),
        ("candidates",),
        ("evaluation", "runners"),
        ("evaluation", "candidates"),
    ):
        cur: Any = bundle
        ok = True
        for k in path:
            if not isinstance(cur, dict) or k not in cur:
                ok = False
                break
            cur = cur[k]
        if ok and isinstance(cur, list) and cur:
            return [r for r in cur if isinstance(r, dict)]
    return []


def bin_signal(x: float | None, edges: tuple[float, ...]) -> str:
    if x is None:
        return "missing"
    for e in edges:
        if x < e:
            return f"<{e}"
    return f">={edges[-1]}"


class WorldSubworldInfoAudit:
    def __init__(self) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()

    def _load_races(self) -> list[dict[str, Any]]:
        con = connect()
        cur = con.cursor()
        corpus = cur.execute(
            """
            SELECT race_id, prediction_id, winner_horse_number, prediction_pick, snapshot_id
            FROM research_prediction_corpus
            WHERE has_race_result = 1
              AND winner_horse_number IS NOT NULL
              AND prediction_pick IS NOT NULL
            """
        ).fetchall()
        preds = {
            int(r["id"]): json.loads(r["bundle_json"] or "{}")
            for r in cur.execute("SELECT id, bundle_json FROM predictions").fetchall()
            if r["bundle_json"]
        }
        snaps = {}
        for r in cur.execute(
            "SELECT race_id, payload_json FROM research_prediction_snapshots"
        ).fetchall():
            try:
                snaps[str(r["race_id"])] = json.loads(r["payload_json"] or "{}")
            except Exception:
                pass
        meta_rows = {
            str(r["race_id"]): r
            for r in cur.execute(
                "SELECT race_id, field_size, distance, surface, venue FROM research_race_meta"
            ).fetchall()
        }

        out: list[dict[str, Any]] = []
        for row in corpus:
            rid = str(row["race_id"])
            winner = _i(row["winner_horse_number"])
            pick = _i(row["prediction_pick"])
            if winner is None or pick is None:
                continue
            bundle: dict[str, Any] = {}
            pid = row["prediction_id"]
            if pid is not None and int(pid) in preds:
                bundle = preds[int(pid)]
            world, sub = extract_world_label(bundle) if bundle else (None, None)
            signals: dict[str, Any] = {}
            snap = snaps.get(rid) or {}
            rws = snap.get("research_world_signals") or {}
            if isinstance(rws, dict):
                signals = rws.get("signals") or {}
                if not world:
                    w2 = signals.get("world")
                    if w2 and str(w2) in EXISTING_WORLDS:
                        world = str(w2)
                if not sub:
                    s2 = signals.get("sub_world")
                    if s2:
                        sub = str(s2)
            if world not in EXISTING_WORLDS:
                # unlabeled / dummy — keep as None for saturation accounting
                world = None
            if sub in ("", "None", "null", "dummy_sub"):
                sub = None
            runners = runners_of(bundle) if bundle else []
            if any(str(r.get("horse_name") or "").startswith("サンプル") for r in runners):
                runners = []
            meta = meta_rows.get(rid) or {}
            n_horses = len(runners) if runners else _i(meta["field_size"] if "field_size" in meta.keys() else None)
            out.append(
                {
                    "race_id": rid,
                    "world": world,
                    "sub_world": sub,
                    "hit": bool(pick == winner),
                    "n_horses": int(n_horses or 0),
                    "has_runners": bool(runners),
                    "signals": {
                        "difficulty": _f(signals.get("race_leg_difficulty") or signals.get("difficulty")),
                        "chaos": _f(signals.get("chaos_score") or signals.get("chaos")),
                        "short_field": _f(signals.get("short_field_pressure")),
                        "phase": _f(signals.get("phase_transition") or signals.get("phase")),
                        "late_stop": _f(signals.get("late_stop") or signals.get("late_stop_risk_score")),
                        "sustained": _f(signals.get("sustained") or signals.get("sustained_run_possible_score")),
                        "high_pace": _f(signals.get("high_pace") or signals.get("high_pace_score")),
                    },
                    "field_size": _i(meta["field_size"]) if meta else None,
                    "distance": _f(meta["distance"]) if meta else None,
                }
            )
        return out

    def analyze(self) -> dict[str, Any]:
        races = self._load_races()
        labeled = [r for r in races if r["world"] in EXISTING_WORLDS]
        unlabeled_n = len(races) - len(labeled)

        by_world: dict[str, list[dict[str, Any]]] = {w: [] for w in EXISTING_WORLDS}
        for r in labeled:
            by_world[r["world"]].append(r)

        world_info: dict[str, Any] = {}
        for w in EXISTING_WORLDS:
            rows = by_world[w]
            sub_c = Counter(r["sub_world"] or "unset" for r in rows)
            design = DESIGN_SUBWORLDS[w]
            present_design = [s for s in design if sub_c.get(s, 0) > 0]
            present_any = [s for s, n in sub_c.items() if s != "unset" and n > 0]
            n = len(rows)
            hits = sum(1 for r in rows if r["hit"])
            horses = sum(int(r["n_horses"] or 0) for r in rows)
            h_sub = shannon_entropy(Counter({k: v for k, v in sub_c.items() if k != "unset"}))
            h_max_design = max_entropy(len(design))
            h_max_obs = max_entropy(len(present_any)) if present_any else 0.0
            util = _safe_div(len(present_design), len(design)) if design else None
            missing = [s for s in design if sub_c.get(s, 0) == 0]
            # information gain vs single-bucket: H_max_design - H_obs (how much unused capacity)
            unused_bits = (h_max_design - h_sub) if design else None
            world_info[w] = {
                "n_races": n,
                "n_horses": horses,
                "mean_field": _safe_div(horses, n),
                "n_subworlds_observed": len(present_any),
                "n_subworlds_design": len(design),
                "subworld_utilization": util,
                "subworld_counts": dict(sub_c),
                "design_subworlds": list(design),
                "present_design_subworlds": present_design,
                "missing_design_subworlds": missing,
                "missing_rate": _safe_div(len(missing), len(design)) if design else None,
                "hit": hits,
                "hit_rate": _safe_div(hits, n),
                "entropy_subworld_bits": h_sub,
                "entropy_max_design_bits": h_max_design,
                "entropy_max_observed_bits": h_max_obs,
                "entropy_ratio_vs_design": _safe_div(h_sub, h_max_design) if h_max_design else None,
                "unused_design_bits": unused_bits,
                "role": (WORLD_ROLES.get(w) or {}).get("role"),
                "design_route_text": (WORLD_ROLES.get(w) or {}).get("route"),
            }

        # Global labeled entropy
        world_c = Counter(r["world"] for r in labeled)
        h_world = shannon_entropy(world_c)
        h_world_max = max_entropy(len(EXISTING_WORLDS))

        # Coverage table
        coverage = {
            w: {
                "design": list(DESIGN_SUBWORLDS[w]),
                "observed": world_info[w]["present_design_subworlds"],
                "observed_all_labels": [
                    s
                    for s, n in world_info[w]["subworld_counts"].items()
                    if s != "unset" and n > 0
                ],
                "missing": world_info[w]["missing_design_subworlds"],
                "missing_rate": world_info[w]["missing_rate"],
                "utilization": world_info[w]["subworld_utilization"],
            }
            for w in EXISTING_WORLDS
        }

        # Missing classification: within dominant SubWorld, signal heterogeneity
        missing_class = self._missing_classification(labeled)

        # Refinement potential
        refinement = self._refinement_potential(world_info, missing_class)

        # Governance
        governance = self._governance(world_info, world_c, h_world, h_world_max, refinement)

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "shadow_only": True,
            "product_mutation": False,
            "new_worlds_forbidden": True,
            "corpus": {
                "n_evaluable": len(races),
                "n_labeled_canonical": len(labeled),
                "n_unlabeled_or_noncanonical": unlabeled_n,
                "world_counts": dict(world_c),
                "subworld_counts_global": dict(
                    Counter(r["sub_world"] or "unset" for r in labeled)
                ),
            },
            "design_subworld_inventory": {w: list(v) for w, v in DESIGN_SUBWORLDS.items()},
            "existing_subworlds_catalog": list(EXISTING_SUBWORLDS),
            "world_information": world_info,
            "coverage": coverage,
            "information_density": {
                "world_prior_entropy_bits": h_world,
                "world_prior_max_bits": h_world_max,
                "world_prior_entropy_ratio": _safe_div(h_world, h_world_max),
                "per_world": {
                    w: {
                        "subworld_entropy_bits": world_info[w]["entropy_subworld_bits"],
                        "design_capacity_bits": world_info[w]["entropy_max_design_bits"],
                        "entropy_ratio_vs_design": world_info[w]["entropy_ratio_vs_design"],
                        "unused_design_bits": world_info[w]["unused_design_bits"],
                        "information_gain_vs_flat_world": world_info[w]["entropy_subworld_bits"],
                        "n_races": world_info[w]["n_races"],
                    }
                    for w in EXISTING_WORLDS
                },
            },
            "missing_classification": missing_class,
            "refinement_potential": refinement,
            "governance": governance,
        }

    def _missing_classification(self, labeled: list[dict[str, Any]]) -> dict[str, Any]:
        """Detect heterogeneous win-path signals collapsed into the same SubWorld."""
        by_ws: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for r in labeled:
            if not r["sub_world"]:
                continue
            by_ws[(r["world"], r["sub_world"])].append(r)

        collapsed = []
        for (world, sub), rows in sorted(by_ws.items(), key=lambda kv: -len(kv[1])):
            if len(rows) < 8:
                continue
            # Build joint bins of difficulty × short_field × field
            joint = Counter()
            for r in rows:
                sig = r["signals"]
                d = bin_signal(sig.get("difficulty"), (0.4, 0.5, 0.6))
                sf = bin_signal(sig.get("short_field"), (0.5, 0.58, 0.72))
                fs = bin_signal(
                    float(r["field_size"]) if r.get("field_size") is not None else None,
                    (12, 14, 16),
                )
                joint[f"d{d}|sf{sf}|fs{fs}"] += 1
            h = shannon_entropy(joint)
            hmax = max_entropy(min(12, len(joint))) if joint else 0.0
            # Also chaos/phase for absorption into midupper
            chaos_bins = Counter(
                bin_signal(r["signals"].get("chaos"), (0.42, 0.58, 0.66)) for r in rows
            )
            phase_bins = Counter(
                bin_signal(r["signals"].get("phase"), (0.48, 0.62)) for r in rows
            )
            # Heuristic: high joint entropy inside one SubWorld ⇒ under-split
            under_split = bool(h >= 1.5 and len(rows) >= 15)
            collapsed.append(
                {
                    "world": world,
                    "sub_world": sub,
                    "n": len(rows),
                    "joint_signal_entropy_bits": h,
                    "joint_unique_bins": len(joint),
                    "top_bins": joint.most_common(5),
                    "chaos_bin_counts": dict(chaos_bins),
                    "phase_bin_counts": dict(phase_bins),
                    "under_split_suspected": under_split,
                    "note": (
                        "Heterogeneous signal bins share one SubWorld label"
                        if under_split
                        else "Limited heterogeneity or small n"
                    ),
                }
            )

        # Cross-world absorption: races that would match other world triggers by signals
        # but are labeled midupper (read-only heuristic using V24 thresholds)
        absorbed = {"n_checked": 0, "would_match_other_world": Counter(), "examples": []}
        for r in labeled:
            if r["world"] != "midupper_world":
                continue
            sig = r["signals"]
            absorbed["n_checked"] += 1
            cands = []
            chaos = sig.get("chaos")
            diff = sig.get("difficulty")
            sf = sig.get("short_field")
            phase = sig.get("phase")
            late = sig.get("late_stop")
            sust = sig.get("sustained")
            hp = sig.get("high_pace")
            if sf is not None and sf >= 0.72 and (
                (phase is not None and phase >= 0.48)
                or (chaos is not None and chaos >= 0.42)
                or (diff is not None and diff >= 0.42)
            ):
                cands.append("mixed_world")
            if late is not None and sust is not None and late >= 0.56 and sust >= 0.52:
                cands.append("midhole_world")
            if chaos is not None and hp is not None and chaos >= 0.58 and hp >= 0.48:
                cands.append("rank7_world")
            if chaos is not None and diff is not None and chaos >= 0.66 and diff >= 0.62:
                cands.append("bug_world")
            # core: only if no midupper-like signals — skip; we're checking absorption INTO midupper
            for c in cands:
                absorbed["would_match_other_world"][c] += 1
            if cands and len(absorbed["examples"]) < 8:
                absorbed["examples"].append(
                    {
                        "race_id": r["race_id"],
                        "sub_world": r["sub_world"],
                        "alt_worlds": cands,
                        "signals": {k: sig.get(k) for k in ("difficulty", "chaos", "short_field", "phase")},
                    }
                )

        return {
            "within_subworld_heterogeneity": collapsed,
            "midupper_absorption_of_other_triggers": {
                "n_checked": absorbed["n_checked"],
                "would_match_other_world": dict(absorbed["would_match_other_world"]),
                "examples": absorbed["examples"],
                "note": (
                    "Read-only V24 threshold probe on stored signals; "
                    "missing signals reduce detection (esp. chaos)."
                ),
            },
        }

    def _refinement_potential(
        self, world_info: dict[str, Any], missing_class: dict[str, Any]
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        under = {
            (x["world"], x["sub_world"]): x
            for x in missing_class.get("within_subworld_heterogeneity") or []
            if x.get("under_split_suspected")
        }
        for w in EXISTING_WORLDS:
            info = world_info[w]
            n = info["n_races"]
            miss_rate = info["missing_rate"] if info["missing_rate"] is not None else 1.0
            unused = info["unused_design_bits"] if info["unused_design_bits"] is not None else 0.0
            under_hits = [u for (ww, _s), u in under.items() if ww == w]
            if n == 0:
                level = "blocked_inactive"
                rationale = "World never activated in labeled corpus; SubWorld refinement not observable"
            elif miss_rate >= 0.34 or unused >= 0.5:
                level = "high"
                rationale = "Design SubWorlds unused or entropy far below design capacity"
            elif under_hits:
                level = "high"
                rationale = "Observed SubWorld collapses heterogeneous signal bins"
            elif info["n_subworlds_observed"] <= 1 and n >= 10:
                level = "medium"
                rationale = "Single SubWorld dominates a populated World"
            elif info["n_subworlds_observed"] >= 2 and (info["entropy_ratio_vs_design"] or 0) >= 0.5:
                level = "low"
                rationale = "Multiple SubWorlds in use with moderate entropy"
            else:
                level = "medium"
                rationale = "Partial SubWorld use"
            out[w] = {
                "level": level,
                "n_races": n,
                "observed_subworlds": info["n_subworlds_observed"],
                "design_subworlds": info["n_subworlds_design"],
                "missing_rate": info["missing_rate"],
                "unused_design_bits": info["unused_design_bits"],
                "under_split_subworlds": [u["sub_world"] for u in under_hits],
                "rationale": rationale,
            }
        return out

    def _governance(
        self,
        world_info: dict[str, Any],
        world_c: Counter,
        h_world: float,
        h_world_max: float,
        refinement: dict[str, Any],
    ) -> dict[str, Any]:
        n_lab = sum(world_c.values())
        mid_share = _safe_div(world_c.get("midupper_world", 0), n_lab) or 0.0
        active_worlds = sum(1 for w in EXISTING_WORLDS if world_info[w]["n_races"] > 0)
        high_refine = [w for w, r in refinement.items() if r["level"] == "high"]
        inactive = [w for w, r in refinement.items() if r["level"] == "blocked_inactive"]

        # A: SubWorld sufficient
        # B: SubWorld insufficient within existing Worlds
        # C: World-level information insufficient (prior collapse)
        world_info_starved = bool(mid_share >= 0.80 or (h_world / h_world_max if h_world_max else 0) < 0.25)
        subworld_insufficient = bool(
            any(
                (world_info[w]["missing_rate"] or 0) >= 0.34
                or (world_info[w]["n_races"] > 0 and world_info[w]["n_subworlds_observed"] < world_info[w]["n_subworlds_design"])
                for w in EXISTING_WORLDS
                if world_info[w]["n_races"] > 0
            )
            or high_refine
        )

        if world_info_starved and subworld_insufficient:
            # Both true — primary is World prior collapse (C), with SubWorld gap as secondary
            verdict = "C"
            primary = "World-level information collapse (midupper saturation); SubWorld inventory also underused"
        elif world_info_starved:
            verdict = "C"
            primary = "World prior entropy too low"
        elif subworld_insufficient:
            verdict = "B"
            primary = "Active Worlds under-utilize design SubWorlds / under-split"
        else:
            verdict = "A"
            primary = "SubWorld coverage adequate on observed Worlds"

        return {
            "verdict": verdict,
            "labels": {
                "A": "現在の SubWorld で十分",
                "B": "既存 World の SubWorld が不足",
                "C": "World 自体の情報量不足",
            },
            "primary_reason": primary,
            "metrics": {
                "midupper_share": mid_share,
                "world_prior_entropy_ratio": _safe_div(h_world, h_world_max),
                "active_worlds": active_worlds,
                "inactive_worlds": inactive,
                "high_refinement_worlds": high_refine,
            },
            "secondary_findings": {
                "subworld_insufficient_on_active": subworld_insufficient,
                "world_prior_starved": world_info_starved,
            },
        }


def write_docs(report: dict[str, Any], docs_dir: Path) -> dict[str, str]:
    docs_dir.mkdir(parents=True, exist_ok=True)
    corp = report["corpus"]
    wi = report["world_information"]
    cov = report["coverage"]
    dens = report["information_density"]
    ref = report["refinement_potential"]
    gov = report["governance"]
    miss = report["missing_classification"]

    def world_table() -> str:
        lines = [
            "| World | Races | Horses | SubWorlds obs/design | Util | Hit | H_sub (bits) | H_ratio |",
            "|-------|------:|-------:|---------------------:|-----:|----:|-------------:|--------:|",
        ]
        for w in EXISTING_WORLDS:
            r = wi[w]
            lines.append(
                f"| {w} | {r['n_races']} | {r['n_horses']} | "
                f"{r['n_subworlds_observed']}/{r['n_subworlds_design']} | "
                f"{_pct(r['subworld_utilization'])} | {_pct(r['hit_rate'])} | "
                f"{r['entropy_subworld_bits']:.3f} | {_pct(r['entropy_ratio_vs_design'])} |"
            )
        return "\n".join(lines)

    info_md = f"""# Version38 — World Information Audit

**Status:** Research / Audit only — no product mutation, no new Worlds  
**Generated:** `{report['generated_at']}`  
**Evaluable races:** `{corp['n_evaluable']}`  
**Canonical-labeled:** `{corp['n_labeled_canonical']}` (unlabeled/non-canonical: `{corp['n_unlabeled_or_noncanonical']}`)  
**Governance:** **{gov['verdict']}** — {gov['labels'][gov['verdict']]}

## ① World Information

{world_table()}

### Global World prior

- Counts: `{json.dumps(corp['world_counts'], ensure_ascii=False)}`
- Entropy: `{dens['world_prior_entropy_bits']:.3f}` / max `{dens['world_prior_max_bits']:.3f}` bits  
- Ratio: `{_pct(dens['world_prior_entropy_ratio'])}`

### SubWorld counts (labeled)

`{json.dumps(corp['subworld_counts_global'], ensure_ascii=False)}`

## Index

| Doc | Content |
|-----|---------|
| `v38-world-information.md` | 本ファイル |
| `v38-subworld-coverage.md` | 設計 vs 実在 |
| `v38-information-density.md` | Entropy / IG |
| `v38-refinement-potential.md` | 細分化余地 |
| `v38-governance.md` | A/B/C |

## Guardrails

- Prediction / PE / CE / AI / World / SubWorld / Role / Required / Pool / Production — unchanged
- New World proposals — forbidden
"""

    cov_lines = [
        "# Version38 — SubWorld Coverage",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "## ② Design vs Observed",
        "",
        "| World | Design SubWorlds | Observed (design) | Missing | Missing rate | Util |",
        "|-------|------------------|-------------------|---------|-------------:|-----:|",
    ]
    for w in EXISTING_WORLDS:
        c = cov[w]
        cov_lines.append(
            f"| {w} | {', '.join(c['design']) or '—'} | "
            f"{', '.join(c['observed']) or '—'} | "
            f"{', '.join(c['missing']) or '—'} | "
            f"{_pct(c['missing_rate'])} | {_pct(c['utilization'])} |"
        )
    cov_lines.extend(
        [
            "",
            "### Catalog (`EXISTING_SUBWORLDS`)",
            "",
            ", ".join(f"`{s}`" for s in report["existing_subworlds_catalog"]),
            "",
            "### Notes",
            "",
            "- Design inventory is taken from V24 `WORLD_ROLES` routes ∩ `EXISTING_SUBWORLDS` (no new labels).",
            "- `bug_world` / `mixed_world` / `midhole_world` have **thin named** SubWorld inventory (`fallback_standard` only) relative to role text.",
            "- Observed corpus activates almost only `midupper_world` with `midupper_route` / `midupper_spread`.",
            "",
        ]
    )

    dens_lines = [
        "# Version38 — Information Density",
        "",
        "## ③ Density chain",
        "",
        "```text",
        "World prior entropy",
        "  → SubWorld count / utilization",
        "  → SubWorld entropy",
        "  → Information gain vs flat World bucket",
        "```",
        "",
        f"- World prior H: `{dens['world_prior_entropy_bits']:.3f}` bits (ratio `{_pct(dens['world_prior_entropy_ratio'])}`)",
        "",
        "| World | n | H_sub | design capacity | ratio | unused bits | IG (=H_sub) |",
        "|-------|--:|------:|----------------:|------:|------------:|------------:|",
    ]
    for w in EXISTING_WORLDS:
        p = dens["per_world"][w]
        dens_lines.append(
            f"| {w} | {p['n_races']} | {p['subworld_entropy_bits']:.3f} | "
            f"{p['design_capacity_bits']:.3f} | {_pct(p['entropy_ratio_vs_design'])} | "
            f"{(p['unused_design_bits'] if p['unused_design_bits'] is not None else 0):.3f} | "
            f"{p['information_gain_vs_flat_world']:.3f} |"
        )
    dens_lines.extend(
        [
            "",
            "## Reading",
            "",
            "- **IG ≈ SubWorld entropy** within a World: how much SubWorld splits the World bucket.",
            "- **unused_design_bits**: design capacity not realized (missing / unused SubWorlds).",
            "- Near-zero World prior entropy means almost all races share one World — SubWorld cannot restore World-level diversity.",
            "",
        ]
    )

    # refinement + missing classification
    ref_lines = [
        "# Version38 — Refinement Potential & Existing SubWorld Review",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "## ④ Existing SubWorld review",
        "",
        "Does SubWorld adequately refine each World?",
        "",
    ]
    for w in EXISTING_WORLDS:
        info = wi[w]
        r = ref[w]
        ref_lines.append(f"### {w}")
        ref_lines.append("")
        ref_lines.append(f"- Design route: `{info['design_route_text']}`")
        ref_lines.append(f"- Observed counts: `{json.dumps(info['subworld_counts'], ensure_ascii=False)}`")
        ref_lines.append(
            f"- Adequate? **{'No' if r['level'] in ('high', 'blocked_inactive', 'medium') and not (r['level']=='low') else 'Mostly'}** "
            f"(refinement level: `{r['level']}`)"
        )
        ref_lines.append(f"- Rationale: {r['rationale']}")
        ref_lines.append("")

    ref_lines.extend(
        [
            "## ⑤ Missing classification (absorption / under-split)",
            "",
            "### Within-SubWorld heterogeneity",
            "",
            "| World | SubWorld | n | joint H (bits) | bins | under_split? |",
            "|-------|----------|--:|---------------:|-----:|:------------:|",
        ]
    )
    for x in miss.get("within_subworld_heterogeneity") or []:
        ref_lines.append(
            f"| {x['world']} | {x['sub_world']} | {x['n']} | "
            f"{x['joint_signal_entropy_bits']:.3f} | {x['joint_unique_bins']} | "
            f"{'`yes`' if x['under_split_suspected'] else 'no'} |"
        )
    absb = miss.get("midupper_absorption_of_other_triggers") or {}
    ref_lines.extend(
        [
            "",
            "### Midupper absorption of other World triggers (signal probe)",
            "",
            f"- Checked midupper races with signals: `{absb.get('n_checked')}`",
            f"- Would also match (count): `{json.dumps(absb.get('would_match_other_world') or {}, ensure_ascii=False)}`",
            f"- Note: {absb.get('note')}",
            "",
            "Examples:",
            "",
        ]
    )
    for ex in absb.get("examples") or []:
        ref_lines.append(
            f"- `{ex['race_id']}` sub=`{ex['sub_world']}` alt=`{ex['alt_worlds']}` signals=`{ex['signals']}`"
        )
    if not (absb.get("examples") or []):
        ref_lines.append("- (none detected or signals mostly null)")

    ref_lines.extend(
        [
            "",
            "## ⑥ Refinement potential summary",
            "",
            "| World | Level | obs/design SubWorlds | missing_rate | unused bits |",
            "|-------|-------|---------------------:|-------------:|------------:|",
        ]
    )
    for w in EXISTING_WORLDS:
        r = ref[w]
        ref_lines.append(
            f"| {w} | `{r['level']}` | {r['observed_subworlds']}/{r['design_subworlds']} | "
            f"{_pct(r['missing_rate'])} | {(r['unused_design_bits'] if r['unused_design_bits'] is not None else 0):.3f} |"
        )
    ref_lines.extend(
        [
            "",
            "No new World proposals. Levels describe **existing** World/SubWorld inventory only.",
            "",
        ]
    )

    gov_md = f"""# Version38 — Governance

**Generated:** `{report['generated_at']}`  
**Canonical-labeled N:** `{corp['n_labeled_canonical']}`

## ⑦ Verdict options

| Code | Meaning |
|------|---------|
| A | 現在の SubWorld で十分 |
| B | 既存 World の SubWorld が不足 |
| C | World 自体の情報量不足 |

## Final verdict

# **{gov['verdict']}**

**Label:** {gov['labels'][gov['verdict']]}  
**Primary reason:** {gov['primary_reason']}

### Supporting metrics

| Metric | Value |
|--------|------:|
| midupper_share | {_pct(gov['metrics']['midupper_share'])} |
| world_prior_entropy_ratio | {_pct(gov['metrics']['world_prior_entropy_ratio'])} |
| active_worlds | {gov['metrics']['active_worlds']} / 6 |
| inactive_worlds | {', '.join(gov['metrics']['inactive_worlds']) or '—'} |
| high_refinement_worlds | {', '.join(gov['metrics']['high_refinement_worlds']) or '—'} |

### Secondary

- `world_prior_starved`: `{gov['secondary_findings']['world_prior_starved']}`
- `subworld_insufficient_on_active`: `{gov['secondary_findings']['subworld_insufficient_on_active']}`

## Guardrails

- Research / Audit only
- No improvements, no implementation, no new Worlds
"""

    paths = {
        "info": docs_dir / "v38-world-information.md",
        "cov": docs_dir / "v38-subworld-coverage.md",
        "dens": docs_dir / "v38-information-density.md",
        "ref": docs_dir / "v38-refinement-potential.md",
        "gov": docs_dir / "v38-governance.md",
    }
    paths["info"].write_text(info_md, encoding="utf-8")
    paths["cov"].write_text("\n".join(cov_lines) + "\n", encoding="utf-8")
    paths["dens"].write_text("\n".join(dens_lines), encoding="utf-8")
    paths["ref"].write_text("\n".join(ref_lines), encoding="utf-8")
    paths["gov"].write_text(gov_md, encoding="utf-8")
    return {k: str(v) for k, v in paths.items()}


def run_and_write() -> dict[str, Any]:
    audit = WorldSubworldInfoAudit()
    report = audit.analyze()
    reports_dir = evidence_root() / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "v38-world-subworld-info.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    docs_dir = repo_root() / "docs" / "research"
    docs = write_docs(report, docs_dir)
    report["_outputs"] = {"json": str(json_path), **docs}
    return report


if __name__ == "__main__":
    rep = run_and_write()
    print(
        json.dumps(
            {
                "ok": True,
                "verdict": rep["governance"]["verdict"],
                "reason": rep["governance"]["primary_reason"],
                "n_labeled": rep["corpus"]["n_labeled_canonical"],
                "world_counts": rep["corpus"]["world_counts"],
                "outputs": rep.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
