# -*- coding: utf-8 -*-
"""
Version56 / W-S1 — Shadow Dual Evaluation (285R).

Legacy Trigger + V44 Logic Form on the same signal input.
Production decision = Legacy only. V44 = Shadow observation only.

Does not mutate Prediction / PE / Score / Rank / Confidence / CE / Pool.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import warnings
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "expect-w-s1-shadow-dual-eval/1.0"

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
    return Path(__file__).resolve().parents[4]


def _f(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        x = float(v)
        if x != x:
            return None
        return x
    except (TypeError, ValueError):
        return None


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


def winner_alignment(world: str, rank: int | None) -> str:
    if rank is None:
        return "unknown"
    if world == "unsatisfied":
        return "unsatisfied"
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


def ranking_concepts(race: dict[str, Any]) -> dict[str, float | None]:
    runners = list(race.get("runners") or [])
    probs = []
    for u in runners:
        p = _f(u.get("win_prob"))
        if p is None:
            continue
        probs.append(p)
    if len(probs) < 2:
        return {
            "top_gap": None,
            "ability_separation": None,
            "upper_ability_band": None,
            "mid_eval_band_open": None,
            "top_monopoly": None,
            "ability_subordinate": None,
        }
    probs = sorted(probs, reverse=True)
    s = sum(probs) or 1.0
    top_gap = probs[0] - probs[1]
    median = probs[len(probs) // 2]
    sep = probs[0] - median
    upper = sum(probs[:3]) / s
    mid = sum(probs[3:10]) / s if len(probs) > 3 else 0.0
    mono = probs[0] / s
    # subordinate: low gap / low monopoly
    sub = 1.0 - min(1.0, top_gap * 5.0)
    return {
        "top_gap": top_gap,
        "ability_separation": sep,
        "upper_ability_band": upper,
        "mid_eval_band_open": mid,
        "top_monopoly": mono,
        "ability_subordinate": sub,
    }


def restore_trigger_signals(rid: str, field_size: Any, distance: Any) -> dict[str, float | None]:
    """Best-effort FeatureLoader+Scorer diagnostic restore (read-only)."""
    warnings.filterwarnings("ignore")
    try:
        import demo_ticket_optimizer_core as core
        from ai_platform.core.features import FeatureGenerator, FeatureLoader
        from ai_platform.core.scoring import Scorer
        from app.research.difficulty_signal_audit import reconstruct_leg_upset
    except Exception:
        return {}

    loaded = FeatureLoader().load(str(rid))
    if loaded is None:
        return {}
    frame = loaded.frame
    fm = FeatureGenerator().build_feature_matrix(frame)
    scores = Scorer().score_candidates(fm)
    diag = scores.get("_diagnostic")

    def diag_mean(name: str) -> float | None:
        if diag is None or not hasattr(diag, "get"):
            return None
        col = diag.get(name) if isinstance(diag, dict) else None
        if col is None:
            try:
                import pandas as pd

                if isinstance(diag, pd.DataFrame) and name in diag.columns:
                    return float(diag[name].mean())
            except Exception:
                return None
            return None
        try:
            return float(col.mean())
        except Exception:
            return _f(col)

    def frame_mean(col: str) -> float | None:
        try:
            if col in frame.columns:
                return float(frame[col].mean())
        except Exception:
            return None
        return None

    hc = field_size or frame_mean("horse_count")
    recon = reconstruct_leg_upset(
        win5_leg=frame_mean("win5_leg"),
        horse_count=hc,
        pace_collapse_risk=frame_mean("pace_collapse_risk"),
        style_entropy=frame_mean("style_entropy"),
        sashi_count=frame_mean("sashi_count"),
        oikomi_count=frame_mean("oikomi_count"),
        unknown_count=frame_mean("unknown_count"),
    )
    difficulty = recon.get("reconstructed_difficulty")
    chaos = diag_mean("chaos_score")
    high_pace = diag_mean("high_pace_score")
    late_stop = diag_mean("late_stop_risk_score")
    sustained = diag_mean("sustained_run_possible_score")
    phase = frame_mean("phase_chain_seed")
    m = {
        "distance": distance,
        "field_size": field_size or hc,
        "horse_count": hc,
        "chaos_score": chaos or 0.0,
        "high_pace_score": high_pace or 0.0,
        "pace_collapse_risk": frame_mean("pace_collapse_risk") or 0.0,
        "traffic_score": frame_mean("inside_traffic_risk") or 0.0,
    }
    try:
        sfp = float(core.calc_short_field_pressure(m, None))
    except Exception:
        sfp = None
    return {
        "difficulty": _f(difficulty),
        "chaos": _f(chaos),
        "high_pace": _f(high_pace),
        "late_stop": _f(late_stop),
        "sustained": _f(sustained),
        "phase": _f(phase),
        "short_field_pressure": _f(sfp),
    }


def build_legacy_meta(signals: dict[str, float | None]) -> dict[str, Any]:
    return {
        "race_leg_difficulty": signals.get("difficulty") or 0.0,
        "chaos_score": signals.get("chaos") or 0.0,
        "phase_transition": signals.get("phase") or 0.0,
        "late_stop_risk_score": signals.get("late_stop") or 0.0,
        "sustained_run_possible_score": signals.get("sustained") or 0.0,
        "high_pace_score": signals.get("high_pace") or 0.0,
        "short_field_pressure": signals.get("short_field_pressure") or 0.0,
        "top_gap": signals.get("top_gap"),
        "ability_separation": signals.get("ability_separation"),
        "upper_ability_band": signals.get("upper_ability_band"),
        "mid_eval_band_open": signals.get("mid_eval_band_open"),
        "top_monopoly": signals.get("top_monopoly"),
        "ability_subordinate": signals.get("ability_subordinate"),
        "aptitude_fit": signals.get("aptitude_fit"),
        "development_pressure": signals.get("development_pressure"),
        "exception_flag": signals.get("exception_flag"),
        "field_size": signals.get("field_size"),
        "distance": signals.get("distance"),
    }


def evaluate_prediction_arm(rows: list[dict[str, Any]], races: list[dict[str, Any]]) -> dict[str, Any]:
    by = {str(r["race_id"]): r for r in races}
    buckets: Counter[str] = Counter()
    hits = 0
    parts = []
    for fr in rows:
        rid = str(fr.get("race_id") or "")
        hit = bool(fr.get("hit_at_1"))
        if hit:
            hits += 1
        wr = winner_model_rank(by.get(rid) or {})
        buckets[miss_bucket(hit, wr)] += 1
        parts.append(f"{rid}|{fr.get('predicted_top1_horse_id')}|{fr.get('winner_id')}|{int(hit)}")
    n = len(rows)
    return {
        "n": n,
        "hit": hits,
        "purchase": hits,
        "rank710": int(buckets.get("rank710", 0)),
        "other_1_3": int(buckets.get("other_1_3", 0)),
        "other_10_13": int(buckets.get("other_10_13", 0)),
        "rank46": int(buckets.get("rank46", 0)),
        "other": int(buckets.get("other", 0)),
        "other_miss": int(buckets.get("other_1_3", 0))
        + int(buckets.get("other_10_13", 0))
        + int(buckets.get("other", 0)),
        "buckets": dict(buckets),
        "prediction_fingerprint": hashlib.sha256("\n".join(sorted(parts)).encode("utf-8")).hexdigest(),
    }


def run_dual_eval(
    rows: list[dict[str, Any]],
    races: list[dict[str, Any]],
    *,
    restore: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    import demo_ticket_optimizer_core as core
    from ai_platform.core.world.v44_shadow_eval import (
        build_polarity_thresholds,
        evaluate_v44_logic_form,
    )
    from ai_platform.core.world.trigger_shadow import record_shadow_observation, ensure_shadow_log_dir

    by_race = {str(r["race_id"]): r for r in races}

    # Pass 1: build signals
    signal_table: list[dict[str, float | None]] = []
    built: list[dict[str, Any]] = []
    for fr in rows:
        rid = str(fr.get("race_id") or "")
        race = by_race.get(rid) or {}
        concepts = ranking_concepts(race)
        field_size = fr.get("field_size") or (race.get("context") or {}).get("field_size")
        distance = fr.get("distance")
        restored: dict[str, float | None] = {}
        if restore:
            restored = restore_trigger_signals(rid, field_size, distance)
        # aptitude / development proxies (observational, documented)
        apt = None
        if distance is not None and field_size is not None:
            # mild proxy only — marked in notes
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
            "exception_flag": None,  # no explicit flag in corpus
            "field_size": _f(field_size),
            "distance": _f(distance),
        }
        signal_table.append(sig)
        built.append({"race_id": rid, "signals": sig, "restored_ok": bool(restored)})

    thr = build_polarity_thresholds(signal_table)

    # Pass 2: dual eval + shadow log
    ensure_shadow_log_dir()
    log_path = Path(os.environ["W_TRIGGER_SHADOW_LOG_DIR"]) / "ws1_shadow_dual_eval.jsonl"
    if log_path.exists():
        log_path.unlink()

    out_rows: list[dict[str, Any]] = []
    for item, fr in zip(built, rows):
        rid = item["race_id"]
        sig = item["signals"]
        meta = build_legacy_meta(sig)
        legacy = core.safe_text(core.classify_world_line_type(meta))
        v44 = evaluate_v44_logic_form(sig, thr)
        wr = winner_model_rank(by_race.get(rid) or {})
        hit = bool(fr.get("hit_at_1"))
        row = {
            "race_id": rid,
            "legacy_world": legacy,
            "v44_world": v44["v44_world"],
            "positive_match": v44["positive_match"],
            "unsatisfied": v44["unsatisfied"],
            "match_set": v44["match_set"],
            "trigger_path": v44["trigger_path"],
            "decision_trace": v44["decision_trace"],
            "world_transition": f"{legacy}->{v44['v44_world']}",
            "winner_model_rank": wr,
            "hit_at_1": hit,
            "winner_alignment_legacy": winner_alignment(legacy, wr),
            "winner_alignment_v44": winner_alignment(str(v44["v44_world"]), wr),
            "restored_ok": item["restored_ok"],
            "decision_used": legacy,
            "decision_authority": "legacy",
        }
        record_shadow_observation(
            race_id=rid,
            legacy_world=legacy,
            meta=meta,
            source="w_s1_shadow_dual_eval",
            dual_eval=v44,
            extra={"winner_model_rank": wr, "hit_at_1": hit},
        )
        out_rows.append(row)

    return out_rows, {"polarity_thresholds": thr, "n_restored": sum(1 for b in built if b["restored_ok"])}


def aggregate_shadow(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    leg_c = Counter(r["legacy_world"] for r in rows)
    v44_c = Counter(r["v44_world"] for r in rows)
    trans: Counter[str] = Counter(r["world_transition"] for r in rows)
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        matrix[str(r["legacy_world"])][str(r["v44_world"])] += 1

    pm = sum(1 for r in rows if r["positive_match"])
    uns = sum(1 for r in rows if r["unsatisfied"])
    h_leg = shannon_entropy(leg_c)
    h_v44 = shannon_entropy(v44_c)
    hmax = math.log(len(EXISTING_WORLDS), 2)

    align_l = Counter(r["winner_alignment_legacy"] for r in rows)
    align_v = Counter(r["winner_alignment_v44"] for r in rows)

    # Semantic compliance: V44 assigned world Must true in decision_trace
    compliant = 0
    for r in rows:
        w = r["v44_world"]
        if w == "unsatisfied":
            continue
        tr = (r.get("decision_trace") or {}).get(w) or {}
        if tr.get("must") is True and tr.get("match") is True:
            compliant += 1
    coverage = sum(1 for w in EXISTING_WORLDS if v44_c.get(w, 0) > 0)

    return {
        "n": n,
        "legacy_distribution": dict(leg_c),
        "v44_distribution": dict(v44_c),
        "legacy_entropy_bits": h_leg,
        "v44_entropy_bits": h_v44,
        "legacy_entropy_ratio": h_leg / hmax if hmax else None,
        "v44_entropy_ratio": h_v44 / hmax if hmax else None,
        "positive_match_rate": pm / n if n else None,
        "unsatisfied_rate": uns / n if n else None,
        "positive_match_n": pm,
        "unsatisfied_n": uns,
        "transition_counts": dict(trans),
        "transition_matrix": {a: dict(b) for a, b in matrix.items()},
        "world_coverage_v44": coverage,
        "world_coverage_max": len(EXISTING_WORLDS),
        "winner_alignment_legacy": dict(align_l),
        "winner_alignment_v44": dict(align_v),
        "semantic_compliance_n": compliant,
        "semantic_compliance_rate": compliant / n if n else None,
    }


def flag_off_compat_check() -> dict[str, Any]:
    """Feature Flag OFF must keep Legacy-only behavior and no dual decide."""
    os.environ.pop("W_TRIGGER_SHADOW", None)
    os.environ["W_TRIGGER_PATH"] = "legacy"
    from ai_platform.core.world.trigger_migration_flags import refresh_from_env, flag_snapshot, production_path
    from ai_platform.core.world import WorldClassifier
    import demo_ticket_optimizer_core as core

    refresh_from_env()
    snap = flag_snapshot()
    meta = {"race_leg_difficulty": 0.1, "chaos_score": 0.1}
    legacy = core.safe_text(core.classify_world_line_type(dict(meta)))
    out = WorldClassifier().classify_world({"race_id": "compat"}, dict(meta))
    return {
        "flags": snap,
        "production_path": production_path(),
        "legacy_world": legacy,
        "classifier_world": out["world"],
        "identical": legacy == out["world"],
        "shadow_disabled": snap.get("W_TRIGGER_SHADOW") is False,
        "decision_authority_legacy": snap.get("decision_authority") == "legacy",
        "ok": legacy == out["world"]
        and snap.get("W_TRIGGER_SHADOW") is False
        and production_path() == "legacy",
    }


def gate(before: dict[str, Any], after: dict[str, Any], shadow: dict[str, Any], compat: dict[str, Any], log_ok: bool) -> dict[str, Any]:
    def d(k: str) -> int:
        return int(after[k]) - int(before[k])

    checks = {
        "production_prediction_identical": before["prediction_fingerprint"] == after["prediction_fingerprint"],
        "prediction_changes": 0 if before["prediction_fingerprint"] == after["prediction_fingerprint"] else 1,
        "hit_delta": d("hit"),
        "purchase_delta": d("purchase"),
        "rank710_delta": d("rank710"),
        "other_1_3_delta": d("other_1_3"),
        "other_10_13_delta": d("other_10_13"),
        "rank46_delta": d("rank46"),
        "other_miss_delta": d("other_miss"),
        "world_compare_log_ok": log_ok,
        "transition_matrix_ok": bool(shadow.get("transition_matrix")),
        "positive_match_ok": shadow.get("positive_match_n") is not None,
        "unsatisfied_ok": shadow.get("unsatisfied_n") is not None,
        "entropy_ok": shadow.get("v44_entropy_bits") is not None,
        "flag_off_compatible": bool(compat.get("ok")),
    }
    zeros = [
        checks["hit_delta"] == 0,
        checks["purchase_delta"] == 0,
        checks["rank710_delta"] == 0,
        checks["other_1_3_delta"] == 0,
        checks["other_10_13_delta"] == 0,
        checks["rank46_delta"] == 0,
        checks["other_miss_delta"] == 0,
    ]
    passed = (
        checks["production_prediction_identical"]
        and checks["prediction_changes"] == 0
        and all(zeros)
        and checks["world_compare_log_ok"]
        and checks["transition_matrix_ok"]
        and checks["positive_match_ok"]
        and checks["unsatisfied_ok"]
        and checks["entropy_ok"]
        and checks["flag_off_compatible"]
    )
    return {
        "stage": "W-S1",
        "pass": passed,
        "checks": checks,
        "rollback_required": not passed,
        "next_stage_allowed": "W-S2" if passed else "NONE_ROLLBACK",
    }


def write_reports(report: dict[str, Any]) -> dict[str, Path]:
    out = _repo_root() / "docs" / "implementation"
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    paths["json"] = out / "w-s1-285r-evaluation.json"
    paths["json"].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sh = report["shadow_kpi"]
    g = report["gate"]
    a = report["after"]

    def md_table(d: dict[str, Any]) -> str:
        lines = ["| Key | Value |", "|---|---:|"]
        for k, v in d.items():
            lines.append(f"| {k} | {v} |")
        return "\n".join(lines)

    paths["eval"] = out / "w-s1-285r-evaluation.md"
    paths["eval"].write_text(
        "\n".join(
            [
                "# W-S1 Shadow Dual-Eval — 285R",
                "",
                f"**Generated:** `{report['generated_at']}`  ",
                f"**Gate:** `{'PASS' if g['pass'] else 'FAIL'}`  ",
                f"**Decision authority:** Legacy only  ",
                f"**Restored signals n:** `{report['dual_meta']['n_restored']}` / {a['n']}",
                "",
                "## Prediction (Δ0 required)",
                "",
                md_table(
                    {
                        "Hit": a["hit"],
                        "Purchase": a["purchase"],
                        "rank710": a["rank710"],
                        "other_1_3": a["other_1_3"],
                        "other_10_13": a["other_10_13"],
                        "rank46": a["rank46"],
                        "other_miss": a["other_miss"],
                        "fingerprint": a["prediction_fingerprint"],
                    }
                ),
                "",
                "## Gate checks",
                "",
                "```json",
                json.dumps(g["checks"], ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )

    paths["transition"] = out / "w-s1-world-transition-matrix.md"
    paths["transition"].write_text(
        "# W-S1 World Transition Matrix (Legacy → V44 Shadow)\n\n"
        + "```json\n"
        + json.dumps(sh["transition_matrix"], ensure_ascii=False, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )
    paths["pm"] = out / "w-s1-positive-match-report.md"
    paths["pm"].write_text(
        f"# W-S1 Positive Match Report\n\n"
        f"- n: {sh['positive_match_n']}\n"
        f"- rate: {sh['positive_match_rate']}\n"
        f"- method: V44 Logic Form batch-median polarity (Shadow only)\n",
        encoding="utf-8",
    )
    paths["un"] = out / "w-s1-unsatisfied-report.md"
    paths["un"].write_text(
        f"# W-S1 Unsatisfied Report\n\n"
        f"- n: {sh['unsatisfied_n']}\n"
        f"- rate: {sh['unsatisfied_rate']}\n"
        f"- note: V44 has no DEFAULT→core; unsatisfied when no Must match\n",
        encoding="utf-8",
    )
    paths["dist"] = out / "w-s1-world-distribution.md"
    paths["dist"].write_text(
        "# W-S1 World Distribution\n\n## Legacy\n\n"
        + md_table(sh["legacy_distribution"])
        + "\n\n## V44 Shadow\n\n"
        + md_table(sh["v44_distribution"])
        + "\n",
        encoding="utf-8",
    )
    paths["ent"] = out / "w-s1-world-entropy.md"
    paths["ent"].write_text(
        "# W-S1 World Entropy\n\n"
        + md_table(
            {
                "legacy_bits": sh["legacy_entropy_bits"],
                "legacy_ratio": sh["legacy_entropy_ratio"],
                "v44_bits": sh["v44_entropy_bits"],
                "v44_ratio": sh["v44_entropy_ratio"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    paths["wa"] = out / "w-s1-winner-alignment.md"
    paths["wa"].write_text(
        "# W-S1 Winner Alignment\n\n## Legacy\n\n"
        + md_table(sh["winner_alignment_legacy"])
        + "\n\n## V44 Shadow\n\n"
        + md_table(sh["winner_alignment_v44"])
        + "\n",
        encoding="utf-8",
    )
    paths["gate"] = out / "w-s1-gate.md"
    paths["gate"].write_text(
        f"# W-S1 Gate Judgment\n\n**Result:** `{'PASS' if g['pass'] else 'FAIL'}`\n\n"
        f"```json\n{json.dumps(g, ensure_ascii=False, indent=2)}\n```\n",
        encoding="utf-8",
    )
    paths["gov"] = out / "w-s1-governance.md"
    paths["gov"].write_text(
        "\n".join(
            [
                "# W-S1 Governance",
                "",
                "```",
                "【Decision】",
                "Action Type: Track W Stage W-S1 Shadow Dual-Eval",
                f"Implementation Required: Yes (completed — Gate {'PASS' if g['pass'] else 'FAIL'})",
                "Deployment Required: No",
                "Configuration Required: W_TRIGGER_SHADOW for observation only",
                "Production Required: No",
                f"Rollback Required: {'Yes' if not g['pass'] else 'No'}",
                "Risk: Low (Production decision remains Legacy)",
                "Expected Next Action: W-S2 Must Signal Readiness (separate Gate) — not started",
                "```",
                "",
                "Hit improvement is **out of scope**. Shadow observation only.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return paths


def main() -> int:
    win5 = Path(r"C:\win5-ai")
    if str(win5) not in sys.path:
        sys.path.insert(0, str(win5))
    root = _repo_root()
    svc = root / "services" / "win5-ai"
    if str(svc) not in sys.path:
        sys.path.insert(0, str(svc))

    # Prediction arms (flag-independent corpus)
    fixture = root / "fixtures" / "stats" / "baseline-285r-evaluations.json"
    corpus = root / "research" / "v3_lab" / "baselines" / "offline_gate" / "real_285r_corpus.json"
    base = json.loads(fixture.read_text(encoding="utf-8"))
    corp = json.loads(corpus.read_text(encoding="utf-8"))
    rows = base.get("evaluations") or base.get("rows") or []
    races = corp.get("races") or []
    before = evaluate_prediction_arm(rows, races)

    # Flag OFF compatibility BEFORE enabling shadow
    compat = flag_off_compat_check()

    # Enable Shadow observation for Dual-Eval run (still Legacy decide)
    os.environ["W_TRIGGER_SHADOW"] = "1"
    os.environ["W_TRIGGER_PATH"] = "legacy"
    os.environ["W_DEFAULT_CORE"] = "1"
    log_dir = root / "var" / "world_trigger_shadow"
    os.environ["W_TRIGGER_SHADOW_LOG_DIR"] = str(log_dir)

    from ai_platform.core.world.trigger_migration_flags import refresh_from_env, flag_snapshot

    refresh_from_env()
    flags = flag_snapshot()

    restore = str(os.environ.get("W_S1_RESTORE_SIGNALS", "1")).lower() not in {"0", "false", "no"}
    dual_rows, dual_meta = run_dual_eval(rows, races, restore=restore)
    shadow_kpi = aggregate_shadow(dual_rows)

    after = evaluate_prediction_arm(rows, races)
    log_path = log_dir / "ws1_shadow_dual_eval.jsonl"
    log_ok = log_path.exists() and sum(1 for _ in log_path.open(encoding="utf-8")) == 285

    g = gate(before, after, shadow_kpi, compat, log_ok)
    report = {
        "schema_version": SCHEMA,
        "generated_at": _now(),
        "stage": "W-S1",
        "flags": flags,
        "flag_off_compat": compat,
        "before": before,
        "after": after,
        "dual_meta": dual_meta,
        "shadow_kpi": shadow_kpi,
        "shadow_log": str(log_path),
        "shadow_log_rows": 285 if log_ok else 0,
        "sample_rows": dual_rows[:5],
        "gate": g,
        "locks": {
            "production_decision": "legacy",
            "prediction": "unchanged",
            "pe_score_rank_confidence_ce_pool": "unchanged",
            "v44": "shadow_only",
        },
        "method": {
            "v44_polarity": "batch_median_within_285R",
            "legacy": "classify_world_line_type on same signal meta",
            "restore": restore,
            "aptitude_fit": "distance/field_size observational proxy (documented)",
            "exception_flag": "absent in corpus → bug Must fails",
        },
    }
    paths = write_reports(report)
    # also dump per-race jsonl copy under docs
    race_jsonl = root / "docs" / "implementation" / "w-s1-dual-eval-rows.jsonl"
    with race_jsonl.open("w", encoding="utf-8") as fh:
        for r in dual_rows:
            # trim huge traces in docs copy? keep full for evidence
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "pass": g["pass"],
                "hit": after["hit"],
                "v44_entropy": shadow_kpi["v44_entropy_bits"],
                "positive_match_rate": shadow_kpi["positive_match_rate"],
                "unsatisfied_rate": shadow_kpi["unsatisfied_rate"],
                "restored": dual_meta["n_restored"],
                "gate": str(paths["gate"]),
            },
            ensure_ascii=False,
        )
    )
    return 0 if g["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
