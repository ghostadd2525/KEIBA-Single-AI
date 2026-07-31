# -*- coding: utf-8 -*-
"""
Version24 World Activation Research

Why existing Worlds fire / do not fire.
NOT boundary fitness — activation conditions & gaps.

FORBIDDEN:
  New Worlds
  Prediction / PE / CE / AI / Production mutation
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .analyzer import extract_runners
from .config import evidence_root, repo_root
from .evidence_discovery import EvidenceDiscoveryResearch
from .world_boundary_research import (
    EXISTING_WORLDS,
    extract_world_label,
)
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-world-activation/1.0"

# Research-readable copy of classify_world_line_type thresholds
# (demo_ticket_optimizer_core — READ ONLY documentation, not executed to change product)
SHORT_FIELD_PRESSURE_WORLD_THRESHOLD = 0.58
SHORT_FIELD_DISTANCE_SOFT = 1600
SHORT_FIELD_DISTANCE_HARD = 1400
SHORT_FIELD_SIZE_SOFT = 14
SHORT_FIELD_SIZE_HARD = 16

INACTIVE_RATE_MAX = 0.01  # <1%

# Canonical activation trigger matrix (order matters — first match wins)
WORLD_TRIGGER_RULES: list[dict[str, Any]] = [
    {
        "world": "mixed_world",
        "priority": 1,
        "trigger": (
            "short_field_pressure >= 0.72 AND "
            "(phase_transition >= 0.48 OR chaos_score >= 0.42 OR race_leg_difficulty >= 0.42)"
        ),
        "required": ["short_field_pressure", "phase|chaos|difficulty"],
        "route": "route-forward / multi-survivor",
        "role": "Multiple world-lines coexist; high short-field + phase/chaos/difficulty",
        "gap": "top gaps unstable; rescue diversity needed",
        "spread": "high — avoid single-family collapse",
    },
    {
        "world": "midupper_world",
        "priority": 2,
        "trigger": (
            "short_field_pressure >= 0.58 AND race_leg_difficulty >= 0.38"
        ),
        "required": ["short_field_pressure", "race_leg_difficulty"],
        "route": "midupper_route vs midupper_spread",
        "role": "Short-field × difficulty mid-upper survival world",
        "gap": "moderate; rank deeper than core",
        "spread": "route vs spread split",
    },
    {
        "world": "mixed_world",
        "priority": 3,
        "trigger": "phase_transition >= 0.62",
        "required": ["phase_transition"],
        "route": "phase-chain / transition",
        "role": "Late phase transition dominates",
        "gap": "phase-driven, not ability-lock",
        "spread": "high",
    },
    {
        "world": "midhole_world",
        "priority": 4,
        "trigger": "late_stop >= 0.56 AND sustained >= 0.52",
        "required": ["late_stop", "sustained"],
        "route": "sustained / outside survivor",
        "role": "Late-stop × sustained mid-hole survival",
        "gap": "mid-pack hole between core and deep",
        "spread": "sustained-family preference",
    },
    {
        "world": "rank7_world",
        "priority": 5,
        "trigger": "chaos_score >= 0.58 AND high_pace >= 0.48",
        "required": ["chaos_score", "high_pace"],
        "route": "rank7_transition / rank7_residual",
        "role": "Chaos × high-pace rank7–10 observation world",
        "gap": "compressed top → hidden rank7-10",
        "spread": "transition vs residual",
    },
    {
        "world": "bug_world",
        "priority": 6,
        "trigger": "chaos_score >= 0.66 AND race_leg_difficulty >= 0.62",
        "required": ["chaos_score", "race_leg_difficulty"],
        "route": "deep residual / bug observation",
        "role": "Extreme chaos × difficulty bug residual",
        "gap": "deep ranks (often 12+)",
        "spread": "observation not primary purchase",
    },
    {
        "world": "midupper_world",
        "priority": 7,
        "trigger": "race_leg_difficulty >= 0.50",
        "required": ["race_leg_difficulty"],
        "route": "difficulty-driven midupper",
        "role": "Elevated race difficulty without needing short-field",
        "gap": "ability less decisive",
        "spread": "mid",
    },
    {
        "world": "core_world",
        "priority": 8,
        "trigger": "DEFAULT (no prior trigger matched)",
        "required": [],
        "route": "core_top / core_under (ability lock)",
        "role": "Default ability-settlement world",
        "gap": "small top gaps; model_rank settles",
        "spread": "low",
    },
]

WORLD_ROLES: dict[str, dict[str, str]] = {
    "core_world": {
        "role": "Ability-settlement default",
        "route": "core_top / core_under; may promote to midupper_route under compression",
        "gap": "tight top probability gaps",
        "spread": "low",
        "activation_summary": "Fires when no higher-priority survival world trigger matches",
    },
    "midupper_world": {
        "role": "Short-field / difficulty mid-upper survival",
        "route": "midupper_route | midupper_spread | midupper_corelike",
        "gap": "mid-upper ranks survive via route or spread",
        "spread": "route vs spread",
        "activation_summary": "short_field_pressure≥0.58 & difficulty≥0.38 OR difficulty≥0.50",
    },
    "midhole_world": {
        "role": "Late-stop × sustained mid-hole",
        "route": "sustained / outside (via mixed/midhole sub rules)",
        "gap": "hole between core lock and deep chaos",
        "spread": "sustained-family",
        "activation_summary": "late_stop≥0.56 AND sustained≥0.52",
    },
    "rank7_world": {
        "role": "Chaos × high-pace rank7 observation",
        "route": "rank7_transition | rank7_residual",
        "gap": "hidden rank7–10 under top compression",
        "spread": "transition preference",
        "activation_summary": "chaos≥0.58 AND high_pace≥0.48",
    },
    "bug_world": {
        "role": "Extreme chaos × difficulty residual",
        "route": "bug observation / deep residual",
        "gap": "deep (often ≥12)",
        "spread": "observation",
        "activation_summary": "chaos≥0.66 AND difficulty≥0.62",
    },
    "mixed_world": {
        "role": "Multi world-line coexistence",
        "route": "route-forward + multi-survivor families",
        "gap": "unstable; diversity required",
        "spread": "high",
        "activation_summary": "short_field≥0.72+(phase|chaos|diff) OR phase≥0.62",
    },
}

META_SIGNAL_KEYS = (
    "chaos_score",
    "race_leg_difficulty",
    "late_stop_risk_score",
    "sustained_run_possible_score",
    "high_pace_score",
    "pace_collapse_risk",
    "world_load_score",
    "traffic_score",
    "phase_transition",
    "short_field_pressure",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _proxy_short_field_pressure(distance: float | None, field_size: float | None) -> float | None:
    """Partial short_field_pressure using distance×field only (no chaos/pace)."""
    if distance is None or field_size is None:
        return None
    try:
        distance = float(distance)
        field_size = float(field_size)
    except (TypeError, ValueError):
        return None
    if distance <= 0 or field_size <= 0:
        return None
    if distance <= SHORT_FIELD_DISTANCE_HARD:
        short_score = 1.0
    elif distance <= SHORT_FIELD_DISTANCE_SOFT:
        short_score = (SHORT_FIELD_DISTANCE_SOFT - distance) / max(
            1.0, SHORT_FIELD_DISTANCE_SOFT - SHORT_FIELD_DISTANCE_HARD
        )
    else:
        short_score = 0.0
    if field_size >= SHORT_FIELD_SIZE_HARD:
        field_score = 1.0
    elif field_size >= SHORT_FIELD_SIZE_SOFT:
        field_score = (field_size - SHORT_FIELD_SIZE_SOFT + 1) / max(
            1.0, SHORT_FIELD_SIZE_HARD - SHORT_FIELD_SIZE_SOFT + 1
        )
    else:
        field_score = 0.0
    if short_score <= 0.0 or field_score <= 0.0:
        return 0.0
    # without traffic/chaos/pace: scale of 0.46+0.38 = 0.84 max contribution
    return round(min(1.0, short_score * 0.46 + field_score * 0.38), 4)


def _find_meta_signals(obj: Any, found: dict[str, Any] | None = None, depth: int = 0) -> dict[str, Any]:
    if found is None:
        found = {}
    if depth > 4 or not isinstance(obj, dict):
        return found
    for k, v in obj.items():
        if k in META_SIGNAL_KEYS and k not in found:
            try:
                found[k] = float(v)
            except (TypeError, ValueError):
                pass
        elif isinstance(v, dict):
            _find_meta_signals(v, found, depth + 1)
    return found


class WorldActivationResearch:
    def __init__(self) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()
        self.discovery = EvidenceDiscoveryResearch()

    def _load_labels(self) -> dict[str, dict[str, str]]:
        out: dict[str, dict[str, str]] = {}
        conn = connect()
        try:
            for row in conn.execute("SELECT race_id, bundle_json FROM predictions"):
                try:
                    b = json.loads(row["bundle_json"] or "{}")
                except Exception:
                    continue
                w, s = extract_world_label(b)
                if not w:
                    continue
                out[str(row["race_id"])] = {
                    "world": w,
                    "sub_world": s or "",
                    "source": "predictions",
                    "signals": _find_meta_signals(b),
                }
        finally:
            conn.close()
        pi_dir = self.root / "public" / "data" / "predictions"
        if pi_dir.exists():
            for path in pi_dir.glob("*.pi.json"):
                try:
                    b = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                rid = None
                if isinstance(b.get("race_info"), dict):
                    rid = b["race_info"].get("race_id")
                rid = rid or b.get("race_id") or path.stem.replace(".pi", "")
                w, s = extract_world_label(b)
                if not w or not rid or str(rid) in out:
                    continue
                out[str(rid)] = {
                    "world": w,
                    "sub_world": s or "",
                    "source": "pi_file",
                    "signals": _find_meta_signals(b),
                }
        return out

    def _corpus_condition_scan(self) -> dict[str, Any]:
        """Coverage of activation-relevant conditions across corpus (+proxy)."""
        races = self.discovery.load_corpus()
        n = len(races)
        signal_present = Counter()
        proxy_sf_ge_058 = 0
        proxy_sf_ge_072 = 0
        proxy_sf_known = 0
        field_ge_14 = 0
        dist_le_1600 = 0
        for race in races:
            dist = race.get("distance") or race.get("meta_distance")
            fs = race.get("field_size") or race.get("meta_field_size") or len(
                race.get("runners") or []
            )
            try:
                d_f = float(dist) if dist is not None else None
            except (TypeError, ValueError):
                d_f = None
            try:
                f_f = float(fs) if fs is not None else None
            except (TypeError, ValueError):
                f_f = None
            if d_f is not None and d_f <= SHORT_FIELD_DISTANCE_SOFT:
                dist_le_1600 += 1
            if f_f is not None and f_f >= SHORT_FIELD_SIZE_SOFT:
                field_ge_14 += 1
            proxy = _proxy_short_field_pressure(d_f, f_f)
            if proxy is not None:
                proxy_sf_known += 1
                if proxy >= SHORT_FIELD_PRESSURE_WORLD_THRESHOLD:
                    proxy_sf_ge_058 += 1
                if proxy >= 0.72:
                    proxy_sf_ge_072 += 1

            # bundle signals if present
            try:
                b = json.loads(race.get("bundle_json") or "{}")
            except Exception:
                b = {}
            sigs = _find_meta_signals(b)
            for k in META_SIGNAL_KEYS:
                if k in sigs:
                    signal_present[k] += 1

        return {
            "corpus_n": n,
            "distance_le_1600_n": dist_le_1600,
            "distance_le_1600_rate": _safe_div(dist_le_1600, n),
            "field_ge_14_n": field_ge_14,
            "field_ge_14_rate": _safe_div(field_ge_14, n),
            "proxy_short_field_known_n": proxy_sf_known,
            "proxy_short_field_ge_0_58": {
                "n": proxy_sf_ge_058,
                "rate": _safe_div(proxy_sf_ge_058, proxy_sf_known or n),
            },
            "proxy_short_field_ge_0_72": {
                "n": proxy_sf_ge_072,
                "rate": _safe_div(proxy_sf_ge_072, proxy_sf_known or n),
            },
            "world_line_signal_coverage": {
                k: {
                    "n": signal_present[k],
                    "rate": _safe_div(signal_present[k], n),
                }
                for k in META_SIGNAL_KEYS
            },
            "note": (
                "chaos / difficulty / late_stop / sustained / phase are usually ABSENT "
                "from research PredictionBundles — activation cannot be re-simulated "
                "without those meta signals."
            ),
        }

    def _missing_for_world(
        self,
        world: str,
        *,
        activation_n: int,
        condition_cov: dict[str, Any],
        labeled_n: int,
    ) -> dict[str, Any]:
        """Explain what is missing for inactive / rare Worlds."""
        roles = WORLD_ROLES.get(world) or {}
        triggers = [t for t in WORLD_TRIGGER_RULES if t["world"] == world]
        sig_cov = condition_cov.get("world_line_signal_coverage") or {}

        missing_signals = []
        for t in triggers:
            for req in t.get("required") or []:
                if "|" in str(req):
                    parts = str(req).split("|")
                    if all(
                        _safe_div((sig_cov.get(p) or {}).get("n"), 1) == 0
                        or (sig_cov.get(p) or {}).get("n", 0) == 0
                        for p in parts
                        if p in META_SIGNAL_KEYS
                    ):
                        # check each
                        for p in parts:
                            key = {
                                "phase": "phase_transition",
                                "chaos": "chaos_score",
                                "difficulty": "race_leg_difficulty",
                            }.get(p, p)
                            n = (sig_cov.get(key) or {}).get("n", 0)
                            if n == 0:
                                missing_signals.append(key)
                else:
                    key = str(req)
                    if key == "short_field_pressure":
                        # proxy exists; full score needs chaos/pace too
                        if (sig_cov.get("chaos_score") or {}).get("n", 0) == 0:
                            missing_signals.append("chaos_score(for_full_short_field)")
                        continue
                    if key == "phase_transition":
                        # not stored as key usually
                        if (sig_cov.get("phase_transition") or {}).get("n", 0) == 0:
                            missing_signals.append("phase_transition")
                        continue
                    mapped = {
                        "late_stop": "late_stop_risk_score",
                        "sustained": "sustained_run_possible_score",
                        "high_pace": "high_pace_score",
                        "chaos_score": "chaos_score",
                        "race_leg_difficulty": "race_leg_difficulty",
                    }.get(key, key)
                    if (sig_cov.get(mapped) or {}).get("n", 0) == 0:
                        missing_signals.append(mapped)

        missing_signals = sorted(set(missing_signals))

        why_not_firing = []
        if activation_n == 0:
            why_not_firing.append("Zero labeled activations in current Prediction Bundle sample")
        if world == "core_world" and activation_n == 0:
            why_not_firing.append(
                "Sample is dominated by midupper_world; default core path never observed "
                "in labeled bundles (classifier may still default to core elsewhere)"
            )
        if world in {"midhole_world", "rank7_world", "bug_world", "mixed_world"}:
            why_not_firing.append(
                f"Required trigger signals for `{world}` are not present in research bundles "
                f"(missing: {missing_signals or 'see trigger matrix'})"
            )
        if world == "mixed_world":
            why_not_firing.append(
                "Needs short_field_pressure≥0.72 with phase/chaos/difficulty OR phase≥0.62 — "
                f"proxy short_field≥0.72 corpus rate="
                f"{(condition_cov.get('proxy_short_field_ge_0_72') or {}).get('rate')}"
            )
        if world == "midhole_world":
            why_not_firing.append(
                "Needs late_stop≥0.56 AND sustained≥0.52 — both meta fields absent from Evidence JSON"
            )
        if world == "rank7_world":
            why_not_firing.append(
                "Needs chaos≥0.58 AND high_pace≥0.48 — both meta fields absent from Evidence JSON"
            )
        if world == "bug_world":
            why_not_firing.append(
                "Needs chaos≥0.66 AND difficulty≥0.62 — both meta fields absent from Evidence JSON"
            )

        what_is_needed = [
            "Persist world_line meta on PredictionBundle evaluation "
            "(chaos_score, race_leg_difficulty, late_stop, sustained, high_pace, phase_transition, short_field_pressure)",
            "Accumulate labeled bundles for non-midupper Worlds (not create new Worlds)",
            f"Do NOT change product classifier; research needs observable activation of `{world}`",
        ]
        if world == "midupper_world" and activation_n > 0:
            what_is_needed = [
                "Already activating — deepen sub_world route/spread Evidence coverage"
            ]

        return {
            "world": world,
            "activation_n": activation_n,
            "activation_rate": _safe_div(activation_n, labeled_n),
            "inactive": activation_n == 0
            or (_safe_div(activation_n, labeled_n) or 0) < INACTIVE_RATE_MAX,
            "activation_condition": roles.get("activation_summary"),
            "missing_condition": missing_signals,
            "required": list(
                {r for t in triggers for r in (t.get("required") or [])}
            ),
            "route": roles.get("route"),
            "role": roles.get("role"),
            "gap": roles.get("gap"),
            "spread": roles.get("spread"),
            "world_trigger": [t.get("trigger") for t in triggers],
            "why_not_firing": why_not_firing,
            "what_is_needed": what_is_needed,
        }

    def analyze(self) -> dict[str, Any]:
        labels = self._load_labels()
        canonical = {
            rid: lab
            for rid, lab in labels.items()
            if lab.get("world") in EXISTING_WORLDS
        }
        labeled_n = len(canonical)
        by_world = Counter(lab["world"] for lab in canonical.values())
        by_sub = Counter(
            lab.get("sub_world") or "unspecified"
            for lab in canonical.values()
            if lab.get("world") in EXISTING_WORLDS
        )
        non_canonical = Counter(
            lab["world"]
            for lab in labels.values()
            if lab.get("world") not in EXISTING_WORLDS
        )

        condition_cov = self._corpus_condition_scan()

        activation_map = {}
        for w in EXISTING_WORLDS:
            n = int(by_world.get(w, 0))
            rate = _safe_div(n, labeled_n) if labeled_n else 0.0
            activation_map[w] = {
                **(WORLD_ROLES.get(w) or {}),
                "activation_n": n,
                "activation_rate": rate,
                "inactive": n == 0 or (rate or 0) < INACTIVE_RATE_MAX,
                "sub_world_counts": {
                    s: c
                    for s, c in by_sub.items()
                    if any(
                        lab.get("world") == w and (lab.get("sub_world") or "unspecified") == s
                        for lab in canonical.values()
                    )
                },
            }
            # fix sub counts properly
            sc = Counter(
                (lab.get("sub_world") or "unspecified")
                for lab in canonical.values()
                if lab.get("world") == w
            )
            activation_map[w]["sub_world_counts"] = dict(sc)

        inactive = []
        for w in EXISTING_WORLDS:
            detail = self._missing_for_world(
                w,
                activation_n=int(by_world.get(w, 0)),
                condition_cov=condition_cov,
                labeled_n=labeled_n or 1,
            )
            if detail["inactive"]:
                inactive.append(detail)

        # signal presence on labeled midupper bundles
        labeled_signal_hits = Counter()
        for lab in labels.values():
            for k in (lab.get("signals") or {}):
                labeled_signal_hits[k] += 1

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "new_worlds_forbidden": True,
            "product_mutation": False,
            "sample": {
                "labeled_total": len(labels),
                "labeled_canonical": labeled_n,
                "by_world": dict(by_world),
                "by_sub_world": dict(by_sub),
                "non_canonical": dict(non_canonical),
                "exploratory": labeled_n < 100
                or len([w for w, n in by_world.items() if n > 0]) < 3,
            },
            "activation_map": activation_map,
            "trigger_matrix": WORLD_TRIGGER_RULES,
            "inactive_analysis": inactive,
            "condition_coverage": condition_cov,
            "labeled_bundle_signal_hits": dict(labeled_signal_hits),
            "existing_worlds": list(EXISTING_WORLDS),
        }


def write_activation_map_md(report: dict[str, Any], path: Path) -> None:
    s = report.get("sample") or {}
    lines = [
        "# Version24 — World Activation Map",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Scope:** Existing Worlds only / New Worlds FORBIDDEN  ",
        "",
        "## Sample",
        "",
        f"- Labeled canonical races: `{s.get('labeled_canonical')}`",
        f"- By world: `{json.dumps(s.get('by_world') or {}, ensure_ascii=False)}`",
        f"- By sub_world: `{json.dumps(s.get('by_sub_world') or {}, ensure_ascii=False)}`",
        f"- Exploratory: `{s.get('exploratory')}`",
        "",
        "## Activation Map",
        "",
        "| World | N | Rate | Inactive | Role | Route | Gap | Spread |",
        "|-------|--:|-----:|:--------:|------|-------|-----|--------|",
    ]
    am = report.get("activation_map") or {}
    for w in EXISTING_WORLDS:
        p = am.get(w) or {}
        lines.append(
            f"| `{w}` | {p.get('activation_n')} | {_pct(p.get('activation_rate'))} | "
            f"{'YES' if p.get('inactive') else 'no'} | {p.get('role')} | "
            f"{p.get('route')} | {p.get('gap')} | {p.get('spread')} |"
        )
    lines += [
        "",
        "### Sub-world activations (observed)",
        "",
    ]
    for w in EXISTING_WORLDS:
        p = am.get(w) or {}
        sc = p.get("sub_world_counts") or {}
        if not sc:
            continue
        lines.append(f"- `{w}`: `{json.dumps(sc, ensure_ascii=False)}`")
    lines += [
        "",
        "## Notes",
        "",
        "- Activation Rate = labeled World count / labeled canonical races",
        "- Inactive = N=0 OR rate < 1%",
        "- Hit rate is not used",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_trigger_matrix_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version24 — World Trigger Matrix",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "Source: `classify_world_line_type` (read-only research extract).",
        "First matching rule wins.",
        "",
        "| Pri | World | Trigger | Required | Route | Role | Gap | Spread |",
        "|----:|-------|---------|----------|-------|------|-----|--------|",
    ]
    for t in report.get("trigger_matrix") or []:
        lines.append(
            f"| {t.get('priority')} | `{t.get('world')}` | `{t.get('trigger')}` | "
            f"{t.get('required')} | {t.get('route')} | {t.get('role')} | "
            f"{t.get('gap')} | {t.get('spread')} |"
        )
    lines += [
        "",
        "## World Trigger summary",
        "",
    ]
    for w in EXISTING_WORLDS:
        role = WORLD_ROLES.get(w) or {}
        lines.append(f"### `{w}`")
        lines.append(f"- Activation: {role.get('activation_summary')}")
        lines.append(f"- Role: {role.get('role')}")
        lines.append(f"- Route: {role.get('route')}")
        lines.append(f"- Gap: {role.get('gap')}")
        lines.append(f"- Spread: {role.get('spread')}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_inactive_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version24 — Inactive World Analysis",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "Focus: Worlds with **0 activations** or **activation rate < 1%**.",
        "Question answered: **あと何が足りないか** (what is still missing).",
        "",
    ]
    inactive = report.get("inactive_analysis") or []
    if not inactive:
        lines.append("- (none — all existing Worlds activate ≥1%)")
    for row in inactive:
        lines += [
            f"## `{row.get('world')}`",
            "",
            f"- Activation N / Rate: `{row.get('activation_n')}` / `{_pct(row.get('activation_rate'))}`",
            f"- Activation Condition: {row.get('activation_condition')}",
            f"- Required: `{row.get('required')}`",
            f"- Missing Condition (signals absent in Evidence): `{row.get('missing_condition')}`",
            f"- Route: {row.get('route')}",
            f"- Role: {row.get('role')}",
            f"- Gap: {row.get('gap')}",
            f"- Spread: {row.get('spread')}",
            f"- World Trigger: `{row.get('world_trigger')}`",
            "",
            "### なぜ発火しないのか",
            "",
        ]
        for w in row.get("why_not_firing") or []:
            lines.append(f"- {w}")
        lines += ["", "### あと何が足りないか", ""]
        for w in row.get("what_is_needed") or []:
            lines.append(f"- {w}")
        lines.append("")
    lines += [
        "## Guardrails",
        "",
        "- Do **not** create new Worlds to fill inactive slots",
        "- Do **not** change Prediction / PE / CE / AI",
        "- Mature Evidence so existing triggers become observable",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_condition_coverage_md(report: dict[str, Any], path: Path) -> None:
    c = report.get("condition_coverage") or {}
    lines = [
        "# Version24 — World Condition Coverage",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        f"- Corpus races: `{c.get('corpus_n')}`",
        f"- Distance ≤1600: `{c.get('distance_le_1600_n')}` ({_pct(c.get('distance_le_1600_rate'))})",
        f"- Field ≥14: `{c.get('field_ge_14_n')}` ({_pct(c.get('field_ge_14_rate'))})",
        "",
        "## Proxy short_field_pressure (distance×field only)",
        "",
        f"- Known: `{c.get('proxy_short_field_known_n')}`",
        f"- ≥0.58: `{(c.get('proxy_short_field_ge_0_58') or {}).get('n')}` "
        f"({_pct((c.get('proxy_short_field_ge_0_58') or {}).get('rate'))})",
        f"- ≥0.72: `{(c.get('proxy_short_field_ge_0_72') or {}).get('n')}` "
        f"({_pct((c.get('proxy_short_field_ge_0_72') or {}).get('rate'))})",
        "",
        "## World-line signal coverage in corpus bundles",
        "",
        "| Signal | N | Rate |",
        "|--------|--:|-----:|",
    ]
    for k, v in (c.get("world_line_signal_coverage") or {}).items():
        lines.append(f"| `{k}` | {v.get('n')} | {_pct(v.get('rate'))} |")
    lines += [
        "",
        f"_{c.get('note')}_",
        "",
        "## Labeled-bundle signal hits",
        "",
        f"`{json.dumps(report.get('labeled_bundle_signal_hits') or {}, ensure_ascii=False)}`",
        "",
        "## Coverage interpretation",
        "",
        "- Partial short-field proxy can exist from race distance/field_size",
        "- Full World activation still requires chaos / difficulty / late_stop / "
        "sustained / high_pace / phase — currently near-zero coverage in research store",
        "- This explains why non-midupper Worlds show 0 labeled activations",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write() -> dict[str, Any]:
    report = WorldActivationResearch().analyze()
    docs = repo_root() / "docs" / "research"
    docs.mkdir(parents=True, exist_ok=True)
    map_p = docs / "v24-world-activation-map.md"
    trig_p = docs / "v24-world-trigger-matrix.md"
    ina_p = docs / "v24-inactive-world-analysis.md"
    cov_p = docs / "v24-world-condition-coverage.md"
    write_activation_map_md(report, map_p)
    write_trigger_matrix_md(report, trig_p)
    write_inactive_md(report, ina_p)
    write_condition_coverage_md(report, cov_p)
    json_path = evidence_root() / "reports" / "v24-world-activation.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report["_outputs"] = {
        "activation_map": str(map_p),
        "trigger_matrix": str(trig_p),
        "inactive": str(ina_p),
        "condition_coverage": str(cov_p),
        "json": str(json_path),
    }
    return report
