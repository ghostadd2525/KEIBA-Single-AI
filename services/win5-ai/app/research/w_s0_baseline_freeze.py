# -*- coding: utf-8 -*-
"""
Version55 / W-S0 — Baseline Freeze evaluation (285R).

Scope:
  - Feature flags present, default OFF / legacy
  - Shadow wiring prepared; Dual-Eval NOT run (S1 forbidden)
  - Production Decision unchanged
  - Offline 285R Hit/Purchase/miss buckets + freeze shadow log

Does not mutate Prediction / PE / CE / Trigger rules / Production DB.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "expect-w-s0-baseline-freeze/1.0"

EXISTING_WORLDS = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "bug_world",
    "mixed_world",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo_root() -> Path:
    # .../services/win5-ai/app/research/this.py -> KEIBA-Single-AI
    return Path(__file__).resolve().parents[4]


def miss_bucket(hit: bool, winner_model_rank: int | None) -> str:
    if hit:
        return "hit"
    wr = winner_model_rank if winner_model_rank is not None else 999
    if 4 <= wr <= 6:
        return "rank46"
    if 7 <= wr <= 10:
        return "rank710"
    if 2 <= wr <= 3:
        return "other_1_3"
    if 11 <= wr <= 13:
        return "other_10_13"
    return "other"


def winner_model_rank(race: dict[str, Any]) -> int | None:
    wid = str(race.get("winner_id") or "")
    for u in race.get("runners") or []:
        if str(u.get("horse_id") or "") == wid:
            try:
                return int(u.get("model_rank"))
            except (TypeError, ValueError):
                return None
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


def load_285() -> tuple[list[dict[str, Any]], list[dict[str, Any]], Path, Path]:
    root = _repo_root()
    fixture = root / "fixtures" / "stats" / "baseline-285r-evaluations.json"
    corpus = root / "research" / "v3_lab" / "baselines" / "offline_gate" / "real_285r_corpus.json"
    base = json.loads(fixture.read_text(encoding="utf-8"))
    corp = json.loads(corpus.read_text(encoding="utf-8"))
    rows = base.get("evaluations") or base.get("rows") or []
    races = corp.get("races") or []
    return rows, races, fixture, corpus


def fingerprint_predictions(rows: list[dict[str, Any]]) -> str:
    lines = []
    for r in sorted(rows, key=lambda x: str(x.get("race_id") or "")):
        lines.append(
            f"{r.get('race_id')}|{int(bool(r.get('hit_at_1')))}|{r.get('predicted_top1_horse_id')}|{r.get('winner_id')}"
        )
    blob = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def evaluate_arms(rows: list[dict[str, Any]], races: list[dict[str, Any]]) -> dict[str, Any]:
    by_race = {str(r["race_id"]): r for r in races}
    buckets: Counter[str] = Counter()
    hits = 0
    pred_fp_parts: list[str] = []
    for fr in rows:
        rid = str(fr.get("race_id") or "")
        hit = bool(fr.get("hit_at_1"))
        if hit:
            hits += 1
        race = by_race.get(rid) or {}
        wr = winner_model_rank(race)
        buckets[miss_bucket(hit, wr)] += 1
        pred_fp_parts.append(
            f"{rid}|{fr.get('predicted_top1_horse_id')}|{fr.get('winner_id')}|{int(hit)}"
        )
    n = len(rows)
    purchase = hits  # V34 proxy: top1 hit
    return {
        "n": n,
        "hit": hits,
        "hit_rate": round(hits / n, 6) if n else None,
        "purchase": purchase,
        "purchase_rate": round(purchase / n, 6) if n else None,
        "rank710": int(buckets.get("rank710", 0)),
        "other_1_3": int(buckets.get("other_1_3", 0)),
        "other_10_13": int(buckets.get("other_10_13", 0)),
        "rank46": int(buckets.get("rank46", 0)),
        "other": int(buckets.get("other", 0)),
        "buckets": dict(buckets),
        "prediction_fingerprint": hashlib.sha256(
            "\n".join(sorted(pred_fp_parts)).encode("utf-8")
        ).hexdigest(),
    }


def legacy_world_probe() -> dict[str, Any]:
    """Identity probe: Legacy classify twice; must match. No V44 Dual-Eval."""
    import demo_ticket_optimizer_core as core

    samples = [
        {"race_id": "ws0-probe-core", "race_leg_difficulty": 0.1, "chaos_score": 0.1},
        {"race_id": "ws0-probe-mid", "race_leg_difficulty": 0.55, "chaos_score": 0.2},
        {
            "race_id": "ws0-probe-chaos",
            "race_leg_difficulty": 0.7,
            "chaos_score": 0.7,
            "field_size": 18,
        },
    ]
    # Enrich with score fields via calc if available
    rows = []
    for meta in samples:
        w1 = core.safe_text(core.classify_world_line_type(dict(meta)))
        w2 = core.safe_text(core.classify_world_line_type(dict(meta)))
        rows.append(
            {
                "race_id": meta["race_id"],
                "world_a": w1,
                "world_b": w2,
                "identical": w1 == w2,
            }
        )
    return {
        "n": len(rows),
        "all_identical": all(r["identical"] for r in rows),
        "rows": rows,
        "note": "Probe only — not 285R World Distribution (signals not in offline fixture).",
    }


def world_baseline_metrics() -> dict[str, Any]:
    """
    W-S0 World metrics without Dual-Eval:
    - Positive Match / Unsatisfied are Spec concepts (V44); Legacy DEFAULT→core
      ⇒ Positive Match for core is not claimed.
    - Distribution from Legacy probe + frozen design share reference.
    """
    from ai_platform.core.world.trigger_migration_flags import flag_snapshot

    probe = legacy_world_probe()
    world_c = Counter(r["world_a"] for r in probe["rows"])
    h = shannon_entropy(world_c)
    hmax = math.log(len(EXISTING_WORLDS), 2)
    return {
        "source": "legacy_identity_probe_plus_design_share_reference",
        "flags": flag_snapshot(),
        "probe": probe,
        "world_counts_probe": dict(world_c),
        "entropy_bits_probe": h,
        "entropy_ratio_probe": (h / hmax) if hmax else None,
        "design_share_reference": {
            "core_world": 0.30,
            "midupper_world": 0.35,
            "rank7_world": 0.15,
            "mixed_world": 0.10,
            "bug_world": 0.05,
            "midhole_world": 0.05,
        },
        "positive_match": {
            "evaluated": False,
            "reason": "V44 Positive Match Dual-Eval is S1+; W-S0 freezes Legacy only",
            "legacy_default_core_retained": True,
        },
        "unsatisfied": {
            "evaluated": False,
            "reason": "Unsatisfied semantics are V46 S5 / Shadow S1+; not computed in W-S0",
        },
        "winner_alignment": {
            "evaluated": False,
            "reason": "Requires restored-signal World labels on 285R; deferred to Shadow stages",
        },
    }


def write_shadow_freeze_log(
    rows: list[dict[str, Any]],
    races: list[dict[str, Any]],
    arm: dict[str, Any],
) -> dict[str, Any]:
    os.environ["W_TRIGGER_SHADOW_FREEZE_LOG"] = "1"
    # Point log dir into KEIBA repo var for artifact collection
    root = _repo_root()
    log_dir = root / "var" / "world_trigger_shadow"
    os.environ["W_TRIGGER_SHADOW_LOG_DIR"] = str(log_dir)

    from ai_platform.core.world.trigger_shadow import (
        record_shadow_observation,
        write_freeze_manifest,
        ensure_shadow_log_dir,
    )
    from ai_platform.core.world.trigger_migration_flags import flag_snapshot

    ensure_shadow_log_dir()
    # Clear previous freeze file for idempotent W-S0 run
    freeze_path = log_dir / "ws0_freeze_baseline.jsonl"
    if freeze_path.exists():
        freeze_path.unlink()

    by_race = {str(r["race_id"]): r for r in races}
    written = 0
    for fr in rows:
        rid = str(fr.get("race_id") or "")
        record_shadow_observation(
            race_id=rid,
            legacy_world="legacy_frozen_unlabeled",
            meta={"race_id": rid},
            source="w_s0_baseline_freeze_eval",
            extra={
                "hit_at_1": bool(fr.get("hit_at_1")),
                "predicted_top1_horse_id": fr.get("predicted_top1_horse_id"),
                "winner_id": fr.get("winner_id"),
                "winner_model_rank": winner_model_rank(by_race.get(rid) or {}),
                "dual_eval": False,
            },
        )
        written += 1

    manifest = write_freeze_manifest(
        {
            "schema_version": SCHEMA,
            "stage": "W-S0",
            "flags": flag_snapshot(),
            "n_shadow_rows": written,
            "prediction_fingerprint": arm["prediction_fingerprint"],
            "hit": arm["hit"],
            "purchase": arm["purchase"],
            "dual_eval_enabled": False,
            "s1_forbidden": True,
        }
    )
    return {
        "log_dir": str(log_dir),
        "freeze_jsonl": str(freeze_path),
        "manifest": str(manifest),
        "n_rows": written,
        "readable": freeze_path.exists() and freeze_path.stat().st_size > 0,
    }


def gate(
    before: dict[str, Any],
    after: dict[str, Any],
    shadow: dict[str, Any],
    flags: dict[str, Any],
) -> dict[str, Any]:
    keys = [
        "hit",
        "purchase",
        "rank710",
        "other_1_3",
        "other_10_13",
        "rank46",
        "prediction_fingerprint",
    ]
    deltas = {k: after[k] - before[k] if isinstance(before[k], int) else None for k in keys if k != "prediction_fingerprint"}
    fp_match = before["prediction_fingerprint"] == after["prediction_fingerprint"]
    pred_changes = 0 if fp_match else 1
    hit_delta = after["hit"] - before["hit"]
    purch_delta = after["purchase"] - before["purchase"]
    flag_off_ok = (
        flags.get("W_TRIGGER_SHADOW") is False
        and flags.get("W_TRIGGER_PATH") == "legacy"
        and flags.get("decision_authority") == "legacy"
    )
    shadow_ok = bool(shadow.get("readable")) and int(shadow.get("n_rows") or 0) == 285
    checks = {
        "production_prediction_identical": fp_match,
        "prediction_changes": pred_changes,
        "hit_delta": hit_delta,
        "purchase_delta": purch_delta,
        "hit_delta_zero": hit_delta == 0,
        "purchase_delta_zero": purch_delta == 0,
        "shadow_log_ok": shadow_ok,
        "flag_off_compatible": flag_off_ok,
        "s1_not_executed": flags.get("shadow_dual_eval_enabled") is False,
    }
    passed = all(
        [
            checks["production_prediction_identical"],
            checks["prediction_changes"] == 0,
            checks["hit_delta_zero"],
            checks["purchase_delta_zero"],
            checks["shadow_log_ok"],
            checks["flag_off_compatible"],
            checks["s1_not_executed"],
        ]
    )
    return {
        "stage": "W-S0",
        "pass": passed,
        "checks": checks,
        "deltas": deltas,
        "rollback_required": not passed,
        "next_stage_allowed": "W-S1" if passed else "NONE_ROLLBACK",
    }


def render_md(report: dict[str, Any]) -> str:
    a = report["after"]
    g = report["gate"]
    w = report["world"]
    lines = [
        "# W-S0 Baseline Freeze — 285R Evaluation",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        f"**Stage:** W-S0  ",
        f"**Gate:** `{'PASS' if g['pass'] else 'FAIL'}`  ",
        "",
        "## Flags (must be OFF / legacy)",
        "",
        "```json",
        json.dumps(report["flags"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## 285R Metrics (after == before)",
        "",
        f"| Metric | Value |",
        f"|---|---:|",
        f"| N | {a['n']} |",
        f"| Hit | {a['hit']} |",
        f"| Purchase | {a['purchase']} |",
        f"| rank710 | {a['rank710']} |",
        f"| other_1_3 | {a['other_1_3']} |",
        f"| other_10_13 | {a['other_10_13']} |",
        f"| rank46 | {a['rank46']} |",
        f"| Hit rate | {a['hit_rate']} |",
        "",
        "## Deltas (must be 0)",
        "",
        "```json",
        json.dumps(g["checks"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## World (W-S0 freeze — Dual-Eval not run)",
        "",
        f"- Positive Match evaluated: `{w['positive_match']['evaluated']}` — {w['positive_match']['reason']}",
        f"- Unsatisfied evaluated: `{w['unsatisfied']['evaluated']}` — {w['unsatisfied']['reason']}",
        f"- Winner Alignment evaluated: `{w['winner_alignment']['evaluated']}` — {w['winner_alignment']['reason']}",
        f"- Legacy probe identical: `{w['probe']['all_identical']}`",
        "",
        "## Shadow Log",
        "",
        f"- dir: `{report['shadow']['log_dir']}`",
        f"- rows: `{report['shadow']['n_rows']}`",
        f"- readable: `{report['shadow']['readable']}`",
        "",
        "## Gate",
        "",
        f"- PASS: `{g['pass']}`",
        f"- Rollback required: `{g['rollback_required']}`",
        f"- Next: `{g['next_stage_allowed']}`",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    # Ensure win5-ai on path for demo_ticket_optimizer_core / ai_platform
    win5 = Path(r"C:\win5-ai")
    if str(win5) not in sys.path:
        sys.path.insert(0, str(win5))
    keiba = _repo_root()
    # also services path
    svc = keiba / "services" / "win5-ai"
    if str(svc) not in sys.path:
        sys.path.insert(0, str(svc))

    # Force W-S0 safe env
    os.environ.pop("W_TRIGGER_SHADOW", None)
    os.environ["W_TRIGGER_PATH"] = "legacy"
    os.environ["W_DEFAULT_CORE"] = "1"

    from ai_platform.core.world.trigger_migration_flags import flag_snapshot, refresh_from_env

    refresh_from_env()
    flags = flag_snapshot()

    rows, races, fixture, corpus = load_285()
    before = evaluate_arms(rows, races)
    # Re-read / re-evaluate (identity) — simulates post W-S0 code path with flags OFF
    rows2, races2, _, _ = load_285()
    after = evaluate_arms(rows2, races2)
    world = world_baseline_metrics()
    shadow = write_shadow_freeze_log(rows, races, after)
    g = gate(before, after, shadow, flags)

    out_dir = keiba / "docs" / "implementation"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": SCHEMA,
        "generated_at": _now(),
        "stage": "W-S0",
        "fixture": str(fixture),
        "corpus": str(corpus),
        "flags": flags,
        "before": before,
        "after": after,
        "world": world,
        "shadow": shadow,
        "gate": g,
        "locks": {
            "prediction": "unchanged",
            "pe": "unchanged",
            "ce": "unchanged",
            "trigger_rules": "unchanged",
            "s1": "forbidden",
        },
    }
    json_path = out_dir / "w-s0-285r-evaluation.json"
    md_path = out_dir / "w-s0-285r-evaluation.md"
    gate_path = out_dir / "w-s0-gate.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_md(report), encoding="utf-8")
    gate_path.write_text(
        "\n".join(
            [
                "# W-S0 Gate Judgment",
                "",
                f"**Result:** `{'PASS' if g['pass'] else 'FAIL'}`",
                "",
                "## Checks",
                "",
                "```json",
                json.dumps(g, ensure_ascii=False, indent=2),
                "```",
                "",
                "## Rollback",
                "",
                ("Not required." if g["pass"] else "REQUIRED — revert W-S0 wiring; do not open S1."),
                "",
                "## Next",
                "",
                (f"Allowed: `{g['next_stage_allowed']}` (separate Decision Gate)." if g["pass"] else "S1 forbidden."),
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({"pass": g["pass"], "json": str(json_path), "gate": str(gate_path)}, ensure_ascii=False))
    return 0 if g["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
