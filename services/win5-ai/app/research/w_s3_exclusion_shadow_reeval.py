# -*- coding: utf-8 -*-
"""
Version61 — W-S3 Exclusion Shadow Re-evaluation (read-only).

Re-scores Exclusion clauses under W-S3 Polarity ADR meanings.
Does NOT change Trigger / Polarity / Production / Prediction.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORLDS = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "mixed_world",
    "bug_world",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo() -> Path:
    return Path(__file__).resolve().parents[4]


def _f(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        x = float(v)
        return None if x != x else x
    except (TypeError, ValueError):
        return None


def _hi(sig: dict[str, float | None], key: str, thr: dict[str, float]) -> bool | None:
    v = _f(sig.get(key))
    if v is None or key not in thr:
        return None
    return v >= thr[key]


def _lo(sig: dict[str, float | None], key: str, thr: dict[str, float]) -> bool | None:
    v = _f(sig.get(key))
    if v is None or key not in thr:
        return None
    return v <= thr[key]


def winner_alignment(world: str, rank: int | None) -> str:
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


def evaluate_exclusion_clauses(
    sig: dict[str, float | None], thr: dict[str, float]
) -> dict[str, Any]:
    """Return must/exclude/clauses per world. Clause IDs map to V44 EXCLUDE + W-S3 F+."""
    from ai_platform.core.world.v44_shadow_eval import evaluate_v44_logic_form

    top_gap_hi = _hi(sig, "top_gap", thr)
    sep_hi = _hi(sig, "ability_separation", thr)
    upper_hi = _hi(sig, "upper_ability_band", thr)
    mid_open = _hi(sig, "mid_eval_band_open", thr)
    top_mono_lo = _lo(sig, "top_monopoly", thr)
    chaos_hi = _hi(sig, "chaos", thr)
    high_pace_hi = _hi(sig, "high_pace", thr)
    difficulty_hi = _hi(sig, "difficulty", thr)
    sfp_hi = _hi(sig, "short_field_pressure", thr)
    late_hi = _hi(sig, "late_stop", thr)
    sust_hi = _hi(sig, "sustained", thr)
    phase_hi = _hi(sig, "phase", thr)
    apt_hi = _hi(sig, "aptitude_fit", thr)
    ability_sub = _hi(sig, "ability_subordinate", thr)
    top_gap_lo = _lo(sig, "top_gap", thr)
    if ability_sub is None:
        ability_sub = top_gap_lo

    if late_hi is None or sust_hi is None:
        late_and_sust = None
    else:
        late_and_sust = bool(late_hi and sust_hi)

    # development axis (same as v44_shadow_eval)
    dev_vals = [
        _hi(sig, "development_pressure", thr),
        phase_hi,
        sfp_hi,
        high_pace_hi,
    ]
    if all(v is None for v in dev_vals):
        dev_axis = None
    else:
        dev_axis = any(v is True for v in dev_vals)

    # --- clause fires (design-aligned IDs from V44 + W-S3 ADR) ---
    core_clauses = []
    if chaos_hi is True:
        core_clauses.append("CORE_EXCL:chaos↑_F+")
    if sfp_hi is True:
        core_clauses.append("CORE_EXCL:sfp↑_F+")
    if late_and_sust is True:
        core_clauses.append("CORE_EXCL:late∧sust_F+")
    if mid_open is True:
        core_clauses.append("CORE_EXCL:mid_band_open_ForbidDef")

    midupper_clauses = []
    if chaos_hi is True and high_pace_hi is True:
        midupper_clauses.append("MIDUPPER_EXCL:chaos∧high_pace_rank7_region")
    if mid_open is True:
        midupper_clauses.append("MIDUPPER_EXCL:mid_band_open_ForbidDef")
    if top_gap_hi is True and dev_axis is not True and apt_hi is not True:
        midupper_clauses.append("MIDUPPER_EXCL:top_gap↑_without_dev_apt_core_lean")

    midhole_clauses = []
    if top_gap_hi is True:
        midhole_clauses.append("MIDHOLE_EXCL:top_gap↑_monopoly_F+")
    if chaos_hi is True and difficulty_hi is True:
        midhole_clauses.append("MIDHOLE_EXCL:chaos∧difficulty_extreme")

    rank7_clauses = []
    if top_gap_hi is True:
        rank7_clauses.append("RANK7_EXCL:top_gap↑_ability_resolution")
    if difficulty_hi is True and chaos_hi is not True:
        rank7_clauses.append("RANK7_EXCL:difficulty↑_without_chaos")

    bug_clauses = []
    if chaos_hi is True and sig.get("exception_flag") is not True:
        bug_clauses.append("BUG_EXCL:chaos↑_without_exception_flag")

    v44 = evaluate_v44_logic_form(sig, thr)

    def pack(world: str, must: bool | None, clauses: list[str]) -> dict[str, Any]:
        excl = len(clauses) > 0
        # align with evaluator exclude when must computed same way
        tr = (v44.get("decision_trace") or {}).get(world) or {}
        return {
            "must": bool(tr.get("must")),
            "exclude": bool(tr.get("exclude")),
            "match": bool(tr.get("match")),
            "clauses_fired": clauses,
            "exclude_via_clauses": excl,
        }

    # Use evaluator must/exclude as authority; clauses explain exclude
    out = {
        "core_world": {
            **{k: ((v44.get("decision_trace") or {}).get("core_world") or {}).get(k) for k in ("must", "exclude", "match")},
            "clauses_fired": core_clauses if ((v44.get("decision_trace") or {}).get("core_world") or {}).get("exclude") else [],
        },
        "midupper_world": {
            **{k: ((v44.get("decision_trace") or {}).get("midupper_world") or {}).get(k) for k in ("must", "exclude", "match")},
            "clauses_fired": midupper_clauses
            if ((v44.get("decision_trace") or {}).get("midupper_world") or {}).get("exclude")
            else [],
        },
        "midhole_world": {
            **{k: ((v44.get("decision_trace") or {}).get("midhole_world") or {}).get(k) for k in ("must", "exclude", "match")},
            "clauses_fired": midhole_clauses
            if ((v44.get("decision_trace") or {}).get("midhole_world") or {}).get("exclude")
            else [],
        },
        "rank7_world": {
            **{k: ((v44.get("decision_trace") or {}).get("rank7_world") or {}).get(k) for k in ("must", "exclude", "match")},
            "clauses_fired": rank7_clauses
            if ((v44.get("decision_trace") or {}).get("rank7_world") or {}).get("exclude")
            else [],
        },
        "bug_world": {
            **{k: ((v44.get("decision_trace") or {}).get("bug_world") or {}).get(k) for k in ("must", "exclude", "match")},
            "clauses_fired": bug_clauses
            if ((v44.get("decision_trace") or {}).get("bug_world") or {}).get("exclude")
            else [],
        },
        "mixed_world": {
            **{k: ((v44.get("decision_trace") or {}).get("mixed_world") or {}).get(k) for k in ("must", "exclude", "match")},
            "clauses_fired": [],
        },
        "v44_world": v44.get("v44_world"),
        "unsatisfied": v44.get("unsatisfied"),
    }
    # If evaluator says exclude but our clause list empty, mark unknown
    for w in WORLDS:
        if w == "mixed_world":
            continue
        block = out[w]
        if block.get("exclude") and not block.get("clauses_fired"):
            block["clauses_fired"] = [f"{w}:EXCLUDE_UNEXPLAINED"]
    return out


def main() -> int:
    win5 = Path(r"C:\win5-ai")
    root = _repo()
    sys.path.insert(0, str(win5))
    sys.path.insert(0, str(root / "services" / "win5-ai"))

    os.environ["W_TRIGGER_PATH"] = "legacy"
    os.environ.pop("W_TRIGGER_SHADOW", None)

    from app.research.w_s1_shadow_dual_eval import (
        build_legacy_meta,
        evaluate_prediction_arm,
        ranking_concepts,
        restore_trigger_signals,
        winner_model_rank,
    )
    from ai_platform.core.world.v44_shadow_eval import build_polarity_thresholds
    import demo_ticket_optimizer_core as core

    fixture = root / "fixtures" / "stats" / "baseline-285r-evaluations.json"
    corpus = root / "research" / "v3_lab" / "baselines" / "offline_gate" / "real_285r_corpus.json"
    base = json.loads(fixture.read_text(encoding="utf-8"))
    corp = json.loads(corpus.read_text(encoding="utf-8"))
    rows = base.get("evaluations") or base.get("rows") or []
    races = corp.get("races") or []
    by_race = {str(r["race_id"]): r for r in races}

    before = evaluate_prediction_arm(rows, races)

    restore = str(os.environ.get("W_S1_RESTORE_SIGNALS", "1")).lower() not in {"0", "false", "no"}
    signal_table: list[dict[str, float | None]] = []
    built: list[dict[str, Any]] = []
    for fr in rows:
        rid = str(fr.get("race_id") or "")
        race = by_race.get(rid) or {}
        concepts = ranking_concepts(race)
        field_size = fr.get("field_size") or (race.get("context") or {}).get("field_size")
        distance = fr.get("distance")
        restored = restore_trigger_signals(rid, field_size, distance) if restore else {}
        apt = None
        if distance is not None and field_size is not None:
            apt = min(1.0, float(distance) / 2500.0) * (1.0 if int(field_size) >= 12 else 0.4)
        dev = restored.get("phase") or restored.get("short_field_pressure") or restored.get("high_pace")
        sig = {
            **concepts,
            "difficulty": restored.get("difficulty"),
            "chaos": restored.get("chaos"),
            "high_pace": restored.get("high_pace"),
            "late_stop": restored.get("late_stop"),
            "sustained": restored.get("sustained"),
            "phase": restored.get("phase"),
            "short_field_pressure": restored.get("short_field_pressure"),
            "aptitude_fit": apt,
            "development_pressure": _f(dev),
            "exception_flag": None,
            "field_size": _f(field_size),
            "distance": _f(distance),
        }
        signal_table.append(sig)
        built.append({"race_id": rid, "signals": sig, "hit": bool(fr.get("hit_at_1"))})

    thr = build_polarity_thresholds(signal_table)

    near_match_rows: list[dict[str, Any]] = []
    clause_rank: Counter[str] = Counter()
    world_excl: Counter[str] = Counter()
    wa_legacy = Counter()
    wa_near = Counter()
    true_n = 0
    false_n = 0
    design_ok_n = 0
    unexplained_excl = 0

    for item, fr in zip(built, rows):
        rid = item["race_id"]
        sig = item["signals"]
        meta = build_legacy_meta(sig)
        legacy = core.safe_text(core.classify_world_line_type(meta))
        detail = evaluate_exclusion_clauses(sig, thr)
        wr = winner_model_rank(by_race.get(rid) or {})
        wa_legacy[winner_alignment(legacy, wr)] += 1

        near_worlds = []
        for w in WORLDS:
            block = detail.get(w) or {}
            if block.get("must") is True and block.get("exclude") is True:
                near_worlds.append(w)
                world_excl[w] += 1
                for c in block.get("clauses_fired") or []:
                    clause_rank[c] += 1
                    if "UNEXPLAINED" in c:
                        unexplained_excl += 1

        if not near_worlds:
            continue

        # primary near world: prefer core, then midupper, midhole, rank7, mixed, bug
        order = ["core_world", "midupper_world", "midhole_world", "rank7_world", "mixed_world", "bug_world"]
        primary = next(w for w in order if w in near_worlds)
        wa = winner_alignment(primary, wr)
        wa_near[wa] += 1
        clauses = (detail.get(primary) or {}).get("clauses_fired") or []
        design_aligned = bool(clauses) and not any("UNEXPLAINED" in c for c in clauses)
        if design_aligned:
            design_ok_n += 1

        # True vs False by outcome alignment of the excluded Positive-Match candidate
        # False Exclusion = WA aligned (outcome supports the excluded world)
        # True Exclusion = WA misaligned/soft/unknown (exclusion agrees with outcome band)
        is_false = wa == "aligned"
        if is_false:
            false_n += 1
            kind = "false_exclusion"
        else:
            true_n += 1
            kind = "true_exclusion"

        near_match_rows.append(
            {
                "race_id": rid,
                "legacy_world": legacy,
                "primary_near_world": primary,
                "near_worlds": near_worlds,
                "winner_model_rank": wr,
                "winner_alignment_primary": wa,
                "kind": kind,
                "design_aligned_clauses": design_aligned,
                "clauses_fired_primary": clauses,
                "clauses_all": {
                    w: (detail.get(w) or {}).get("clauses_fired") or []
                    for w in near_worlds
                },
                "v44_world": detail.get("v44_world"),
                "hit_at_1": item["hit"],
            }
        )

    after = evaluate_prediction_arm(rows, races)
    n_near = len(near_match_rows)

    # Prediction gate
    pred_ok = before["prediction_fingerprint"] == after["prediction_fingerprint"]
    deltas = {
        k: after[k] - before[k]
        for k in ("hit", "purchase", "rank710", "other_1_3", "other_10_13", "rank46", "other_miss")
    }

    # Governance heuristic
    false_rate = false_n / n_near if n_near else 0.0
    unexplained_rate = unexplained_excl / max(1, sum(clause_rank.values()))
    if not pred_ok or any(deltas[k] != 0 for k in deltas):
        verdict = "FAIL_PRED"
        grade = "C"
        reason = "Production/Prediction delta detected"
    elif false_rate >= 0.45 or unexplained_rate >= 0.10:
        verdict = "C"
        grade = "C"
        reason = f"Exclusion過剰候補: false_rate={false_rate:.3f} unexplained_clause_share={unexplained_rate:.3f}"
    elif false_rate >= 0.20 or design_ok_n < n_near:
        verdict = "B"
        grade = "B"
        reason = f"一部再設計候補: false_rate={false_rate:.3f} design_aligned_primary={design_ok_n}/{n_near}"
    else:
        verdict = "A"
        grade = "A"
        reason = f"Exclusion概ね設計どおり: false_rate={false_rate:.3f} design_aligned_primary={design_ok_n}/{n_near}"

    report = {
        "schema_version": "expect-w-s3-exclusion-shadow/1.0",
        "generated_at": _now(),
        "stage": "W-S3-Exclusion-Shadow",
        "polarity_adr": "Accepted (W-S3) — thresholds not changed; batch-median observational",
        "n_285": len(rows),
        "n_near_match": n_near,
        "true_exclusion_n": true_n,
        "false_exclusion_n": false_n,
        "false_exclusion_rate": false_rate,
        "design_aligned_primary_n": design_ok_n,
        "world_breakdown_near_match": dict(world_excl),
        "clause_ranking": clause_rank.most_common(40),
        "winner_alignment_legacy": dict(wa_legacy),
        "winner_alignment_near_primary": dict(wa_near),
        "prediction": {"before": before, "after": after, "deltas": deltas, "identical": pred_ok},
        "governance": {"grade": grade, "verdict": verdict, "reason": reason},
        "method": {
            "near_match": "must=True AND exclude=True (V44 shadow evaluator)",
            "true_exclusion": "Near Match AND winner_alignment(primary) != aligned",
            "false_exclusion": "Near Match AND winner_alignment(primary) == aligned",
            "clause_ids": "V44 EXCLUDE × W-S3 F+ labels; observational median polarity unchanged",
            "production_decision": "legacy classify_world_line_type only",
        },
        "sample_false": [r for r in near_match_rows if r["kind"] == "false_exclusion"][:15],
        "sample_true": [r for r in near_match_rows if r["kind"] == "true_exclusion"][:15],
    }

    out = root / "docs" / "implementation"
    out.mkdir(parents=True, exist_ok=True)
    (out / "w-s3-exclusion-shadow-data.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out / "w-s3-near-match-rows.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in near_match_rows) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "n_near_match": n_near,
                "true": true_n,
                "false": false_n,
                "grade": grade,
                "world": dict(world_excl),
                "top_clauses": clause_rank.most_common(8),
                "pred_identical": pred_ok,
                "deltas": deltas,
            },
            ensure_ascii=False,
        )
    )
    return 0 if pred_ok and all(v == 0 for v in deltas.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
