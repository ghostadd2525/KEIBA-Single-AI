# -*- coding: utf-8 -*-
"""
Version39 — Signal Restoration Simulation

Virtually supply designed WIC signals and re-evaluate World Triggers.
Research / Simulation only. No Production / Trigger / CSV / Signal Service writes.
"""
from __future__ import annotations

import json
import math
import warnings
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ..data.db import connect, migrate
from .config import evidence_root, repo_root
from .difficulty_signal_audit import reconstruct_leg_upset
from .world_activation_research import _proxy_short_field_pressure
from .world_boundary_research import EXISTING_WORLDS, extract_world_label
from .world_trigger_saturation import (
    DESIGN_SHARE,
    TRIGGER_RULES,
    evaluate_all_rules,
    first_match_world,
    normalize_signals,
)
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-signal-restoration-sim/1.0"

SIGNAL_KEYS = (
    "difficulty",
    "chaos",
    "phase",
    "late_stop",
    "sustained",
    "high_pace",
    "short_field_pressure",
)


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


def _frame_num(frame: pd.DataFrame, col: str) -> float | None:
    if frame is None or col not in frame.columns:
        return None
    s = pd.to_numeric(frame[col], errors="coerce").dropna()
    return float(s.iloc[0]) if not s.empty else None


def _frame_mean(frame: pd.DataFrame, col: str) -> float | None:
    if frame is None or col not in frame.columns:
        return None
    s = pd.to_numeric(frame[col], errors="coerce").dropna()
    return float(s.mean()) if not s.empty else None


def _diag_mean(diag: Any, col: str) -> float | None:
    if diag is None or not hasattr(diag, "columns") or col not in diag.columns:
        return None
    s = pd.to_numeric(diag[col], errors="coerce").dropna()
    return float(s.mean()) if not s.empty else None


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
    return math.log(k, 2) if k > 1 else 0.0


def total_variation(p: dict[str, float], q: dict[str, float]) -> float:
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


def share_dict(counts: Counter, keys: tuple[str, ...] = EXISTING_WORLDS) -> dict[str, float]:
    n = sum(counts.values()) or 1
    return {k: counts.get(k, 0) / n for k in keys}


def signal_stats(rows: list[dict[str, float | None]], key: str) -> dict[str, Any]:
    vals = [_f(r.get(key)) for r in rows]
    present = [v for v in vals if v is not None]
    n = len(vals)
    if not present:
        return {
            "n": n,
            "coverage": 0.0,
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
            "nunique_rounded": 0,
            "variance": None,
        }
    mean = sum(present) / len(present)
    var = sum((x - mean) ** 2 for x in present) / len(present)
    uniq = len({round(x, 4) for x in present})
    return {
        "n": n,
        "coverage": len(present) / n,
        "mean": mean,
        "std": math.sqrt(var),
        "min": min(present),
        "max": max(present),
        "nunique_rounded": uniq,
        "variance": var,
    }


class SignalRestorationSimulation:
    def __init__(self) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()

    def _load_meta(self) -> dict[str, dict[str, Any]]:
        con = connect()
        out = {}
        for r in con.execute(
            "SELECT race_id, field_size, distance, surface, venue FROM research_race_meta"
        ):
            out[str(r["race_id"])] = {
                "field_size": _f(r["field_size"]),
                "distance": _f(r["distance"]),
                "surface": r["surface"],
                "venue": r["venue"],
            }
        return out

    def _load_snaps(self) -> dict[str, dict[str, Any]]:
        con = connect()
        out = {}
        for r in con.execute(
            "SELECT race_id, payload_json FROM research_prediction_snapshots"
        ):
            try:
                out[str(r["race_id"])] = json.loads(r["payload_json"] or "{}")
            except Exception:
                pass
        return out

    def _load_pred_labels(self) -> dict[str, tuple[str | None, str | None]]:
        con = connect()
        out: dict[str, tuple[str | None, str | None]] = {}
        for r in con.execute("SELECT race_id, bundle_json FROM predictions"):
            try:
                b = json.loads(r["bundle_json"] or "{}")
            except Exception:
                continue
            out[str(r["race_id"])] = extract_world_label(b)
        return out

    def _find_loadable(self, meta: dict[str, dict[str, Any]]) -> list[str]:
        warnings.filterwarnings("ignore")
        import sys

        sys.path.insert(0, "/opt/expect-ai/platform")
        from ai_platform.core.features import FeatureLoader

        fl = FeatureLoader()
        loadable = []
        for rid in meta:
            try:
                if fl.load(str(rid)) is not None:
                    loadable.append(str(rid))
            except Exception:
                continue
        return loadable

    def _restore_signals(
        self, rid: str, meta_row: dict[str, Any]
    ) -> tuple[dict[str, float | None], dict[str, Any]]:
        """Build restored L1/L2 signals from designed formula + scoring diagnostic."""
        warnings.filterwarnings("ignore")
        import sys

        sys.path.insert(0, "/opt/expect-ai/platform")
        import demo_ticket_optimizer_core as core
        from ai_platform.core.features import FeatureGenerator, FeatureLoader
        from ai_platform.core.scoring import Scorer

        notes: list[str] = []
        loaded = FeatureLoader().load(str(rid))
        if loaded is None:
            return {}, {"ok": False, "notes": ["feature_frame_missing"]}
        frame = loaded.frame
        fm = FeatureGenerator().build_feature_matrix(frame)
        scores = Scorer().score_candidates(fm)
        diag = scores.get("_diagnostic")

        hc = (
            _frame_num(frame, "horse_count")
            or _frame_mean(frame, "horse_count")
            or meta_row.get("field_size")
        )
        recon = reconstruct_leg_upset(
            win5_leg=_frame_num(frame, "win5_leg"),
            horse_count=hc,
            pace_collapse_risk=_frame_mean(frame, "pace_collapse_risk"),
            style_entropy=_frame_mean(frame, "style_entropy"),
            sashi_count=_frame_mean(frame, "sashi_count"),
            oikomi_count=_frame_mean(frame, "oikomi_count"),
            unknown_count=_frame_mean(frame, "unknown_count"),
        )
        difficulty = recon["reconstructed_difficulty"]
        chaos = _diag_mean(diag, "chaos_score")
        high_pace = _diag_mean(diag, "high_pace_score")
        late_stop = _diag_mean(diag, "late_stop_risk_score")
        sustained = _diag_mean(diag, "sustained_run_possible_score")
        phase = _frame_mean(frame, "phase_chain_seed")
        if phase is None:
            notes.append("phase_proxy_missing")
        # short_field: designed calc with injected chaos/pace + meta distance/field
        m = {
            "distance": meta_row.get("distance"),
            "field_size": meta_row.get("field_size") or hc,
            "horse_count": hc,
            "chaos_score": chaos or 0.0,
            "high_pace_score": high_pace or 0.0,
            "pace_collapse_risk": _frame_mean(frame, "pace_collapse_risk") or 0.0,
            "traffic_score": _frame_mean(frame, "inside_traffic_risk") or 0.0,
        }
        try:
            sf_calc = float(core.calc_short_field_pressure(m, None))
        except Exception:
            sf_calc = 0.0
            notes.append("short_field_calc_failed")
        sf_proxy = _proxy_short_field_pressure(meta_row.get("distance"), meta_row.get("field_size"))
        short_field = max(sf_calc, sf_proxy or 0.0)

        # SubWorld via restored meta (read-only classify)
        sub = None
        world_native = None
        try:
            meta_sw = dict(core.detect_race_meta(core.normalize_probabilities(frame.copy())) or {})
            meta_sw["chaos_score"] = chaos
            meta_sw["high_pace_score"] = high_pace
            meta_sw["late_stop_risk_score"] = late_stop
            meta_sw["sustained_run_possible_score"] = sustained
            meta_sw["race_leg_difficulty"] = difficulty
            meta_sw["short_field_pressure"] = short_field
            if phase is not None:
                meta_sw["phase_transition"] = phase
            world_native = core.safe_text(core.classify_world_line_type(meta_sw))
            sub = core.safe_text(core.classify_sub_world_type(meta_sw, None))
        except Exception as e:
            notes.append(f"subworld_classify_skip:{type(e).__name__}")

        raw = {
            "difficulty": difficulty,
            "race_leg_difficulty": difficulty,
            "chaos": chaos,
            "chaos_score": chaos,
            "phase": phase,
            "phase_transition": phase,
            "late_stop": late_stop,
            "late_stop_risk_score": late_stop,
            "sustained": sustained,
            "sustained_run_possible_score": sustained,
            "high_pace": high_pace,
            "high_pace_score": high_pace,
            "short_field_pressure": short_field,
            "pace_collapse": _frame_mean(frame, "pace_collapse_risk"),
            "style_entropy": _frame_mean(frame, "style_entropy"),
        }
        return normalize_signals(raw), {
            "ok": True,
            "feature_source": loaded.feature_source,
            "raw": raw,
            "recon_components": recon.get("components"),
            "sub_world": sub or None,
            "world_native_classify": world_native or None,
            "notes": notes,
        }

    def _current_signals(
        self, rid: str, snap: dict[str, Any] | None
    ) -> tuple[dict[str, float | None], dict[str, Any]]:
        sig_raw: dict[str, Any] = {}
        if snap:
            rws = snap.get("research_world_signals") or {}
            if isinstance(rws, dict):
                sig_raw = rws.get("signals") or {}
        source = "research_world_signals" if sig_raw else "stable_defaults"
        if not sig_raw:
            # Production-like collapse observed in V28–V38
            sig_raw = {
                "difficulty": 0.5,
                "race_leg_difficulty": 0.5,
                "chaos": None,
                "phase": 0.0,
                "late_stop": 0.0,
                "sustained": 0.0,
                "high_pace": 0.0,
                "short_field_pressure": 0.0,
            }
        return normalize_signals(sig_raw), {"source": source, "raw": sig_raw}

    def analyze(self) -> dict[str, Any]:
        meta = self._load_meta()
        snaps = self._load_snaps()
        labels = self._load_pred_labels()
        loadable = self._find_loadable(meta)

        current_rows: list[dict[str, Any]] = []
        restored_rows: list[dict[str, Any]] = []
        cur_sigs: list[dict[str, float | None]] = []
        res_sigs: list[dict[str, float | None]] = []
        rule_pass_cur: Counter = Counter()
        rule_pass_res: Counter = Counter()
        margins_cur: list[float] = []
        margins_res: list[float] = []

        for rid in loadable:
            cur_sig, cur_meta = self._current_signals(rid, snaps.get(rid))
            res_sig, res_meta = self._restore_signals(rid, meta.get(rid) or {})
            if not res_meta.get("ok"):
                continue

            cur_eval = evaluate_all_rules(cur_sig)
            res_eval = evaluate_all_rules(res_sig)
            cur_world = first_match_world(cur_eval)
            res_world = first_match_world(res_eval)

            for ev, counter, margins in (
                (cur_eval, rule_pass_cur, margins_cur),
                (res_eval, rule_pass_res, margins_res),
            ):
                for r in ev:
                    if r.get("pass") and not r.get("is_default"):
                        counter[r["rule_id"]] += 1
                for r in sorted(ev, key=lambda x: int(x["priority"])):
                    if r.get("pass") and not r.get("is_default"):
                        if r.get("margin") is not None:
                            margins.append(float(r["margin"]))
                        break

            assigned, assigned_sub = labels.get(rid, (None, None))
            current_rows.append(
                {
                    "race_id": rid,
                    "world": cur_world,
                    "sub_world": assigned_sub if assigned == cur_world else None,
                    "assigned_label_world": assigned,
                }
            )
            restored_rows.append(
                {
                    "race_id": rid,
                    "world": res_world,
                    "sub_world": res_meta.get("sub_world"),
                    "world_native_classify": res_meta.get("world_native_classify"),
                    "feature_source": res_meta.get("feature_source"),
                    "notes": res_meta.get("notes"),
                }
            )
            cur_sigs.append(cur_sig)
            res_sigs.append(res_sig)

        cur_world_c = Counter(r["world"] for r in current_rows)
        res_world_c = Counter(r["world"] for r in restored_rows)
        cur_sub_c = Counter(r["sub_world"] or "unset" for r in current_rows)
        res_sub_c = Counter(r["sub_world"] or "unset" for r in restored_rows)

        h_cur = shannon_entropy(cur_world_c)
        h_res = shannon_entropy(res_world_c)
        h_max = max_entropy(len(EXISTING_WORLDS))
        share_cur = share_dict(cur_world_c)
        share_res = share_dict(res_world_c)
        tv_cur = total_variation(share_cur, DESIGN_SHARE)
        tv_res = total_variation(share_res, DESIGN_SHARE)

        inactive_cur = [w for w in EXISTING_WORLDS if cur_world_c.get(w, 0) == 0]
        inactive_res = [w for w in EXISTING_WORLDS if res_world_c.get(w, 0) == 0]
        recovered = [w for w in inactive_cur if res_world_c.get(w, 0) > 0]

        # Trigger activation rates (non-default rules)
        n = len(restored_rows) or 1
        trigger_recovery = {
            "rules": [
                {
                    "rule_id": rule["rule_id"],
                    "world": rule["world"],
                    "priority": rule["priority"],
                    "current_pass_n": rule_pass_cur.get(rule["rule_id"], 0),
                    "current_pass_rate": rule_pass_cur.get(rule["rule_id"], 0) / n,
                    "restored_pass_n": rule_pass_res.get(rule["rule_id"], 0),
                    "restored_pass_rate": rule_pass_res.get(rule["rule_id"], 0) / n,
                }
                for rule in TRIGGER_RULES
                if rule["logic"] != "DEFAULT"
            ],
            "mean_winning_margin_current": (sum(margins_cur) / len(margins_cur))
            if margins_cur
            else None,
            "mean_winning_margin_restored": (sum(margins_res) / len(margins_res))
            if margins_res
            else None,
        }

        sig_var = {
            "current": {k: signal_stats(cur_sigs, k) for k in SIGNAL_KEYS},
            "restored": {k: signal_stats(res_sigs, k) for k in SIGNAL_KEYS},
        }

        # Governance A/B/C on entropy
        dh = h_res - h_cur
        active_res = sum(1 for w in EXISTING_WORLDS if res_world_c.get(w, 0) > 0)
        active_cur = sum(1 for w in EXISTING_WORLDS if cur_world_c.get(w, 0) > 0)
        significant = bool(dh >= 0.5 or (h_cur < 0.1 and h_res >= 0.5))
        partial = bool(dh > 0.05 or active_res > active_cur or tv_res < tv_cur - 0.02)
        if significant:
            verdict = "A"
            reason = (
                f"World entropy {h_cur:.3f} → {h_res:.3f} bits (+{dh:.3f}); "
                f"active Worlds {active_cur} → {active_res}; recovered={recovered}"
            )
        elif partial:
            verdict = "B"
            reason = (
                f"Partial: entropy Δ={dh:.3f}, TV_design {tv_cur:.3f}→{tv_res:.3f}, "
                f"active {active_cur}→{active_res}"
            )
        else:
            verdict = "C"
            reason = f"No material entropy recovery (Δ={dh:.3f})"

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "shadow_only": True,
            "product_mutation": False,
            "writes_forbidden": [
                "Production",
                "Prediction",
                "PE",
                "CE",
                "AI",
                "World",
                "Trigger",
                "CSV",
                "FeatureLoader",
                "Signal Service",
            ],
            "method": {
                "current": "research_world_signals when present; else stable defaults (difficulty=0.5, others 0/null)",
                "restored": (
                    "difficulty=designed reconstruct_leg_upset(L0); "
                    "chaos/high_pace/late_stop/sustained=Scorer diagnostic means; "
                    "short_field=calc_short_field_pressure+distance/field proxy; "
                    "phase=phase_chain_seed if present; "
                    "World=first_match Trigger rules (unchanged)"
                ),
                "hit_rate_evaluated": False,
            },
            "corpus": {
                "meta_races": len(meta),
                "featureloader_loadable": len(loadable),
                "simulated_n": len(restored_rows),
                "coverage_note": (
                    "Simulation limited to races FeatureLoader can resolve "
                    "(daily/global pace feature CSV present). Not full 335 corpus."
                ),
            },
            "design_share": DESIGN_SHARE,
            "current": {
                "world_counts": dict(cur_world_c),
                "world_share": share_cur,
                "subworld_counts": dict(cur_sub_c),
                "entropy_bits": h_cur,
                "entropy_ratio": _safe_div(h_cur, h_max),
                "tv_to_design": tv_cur,
                "inactive_worlds": inactive_cur,
                "active_worlds": active_cur,
            },
            "restored": {
                "world_counts": dict(res_world_c),
                "world_share": share_res,
                "subworld_counts": dict(res_sub_c),
                "entropy_bits": h_res,
                "entropy_ratio": _safe_div(h_res, h_max),
                "tv_to_design": tv_res,
                "inactive_worlds": inactive_res,
                "active_worlds": active_res,
                "recovered_worlds": recovered,
            },
            "delta": {
                "entropy_bits": h_res - h_cur,
                "tv_to_design": tv_res - tv_cur,
                "active_worlds": active_res - active_cur,
                "world_count_delta": {
                    w: res_world_c.get(w, 0) - cur_world_c.get(w, 0) for w in EXISTING_WORLDS
                },
            },
            "trigger_recovery": trigger_recovery,
            "signal_variance": sig_var,
            "governance": {
                "verdict": verdict,
                "labels": {
                    "A": "Signal Restoration により World Entropy が有意に改善",
                    "B": "一部改善",
                    "C": "改善なし",
                },
                "reason": reason,
                "design_mix_proximity": {
                    "tv_current": tv_cur,
                    "tv_restored": tv_res,
                    "improved_vs_design": bool(tv_res < tv_cur),
                    "note": (
                        "Entropy gate is primary. Design-mix TV is secondary observation."
                    ),
                },
            },
            "sample_transitions": [
                {
                    "race_id": restored_rows[i]["race_id"],
                    "current_world": current_rows[i]["world"],
                    "restored_world": restored_rows[i]["world"],
                    "restored_subworld": restored_rows[i].get("sub_world"),
                }
                for i in range(min(12, len(restored_rows)))
                if current_rows[i]["world"] != restored_rows[i]["world"]
            ][:12],
        }


def write_docs(report: dict[str, Any], docs_dir: Path) -> dict[str, str]:
    docs_dir.mkdir(parents=True, exist_ok=True)
    cur = report["current"]
    res = report["restored"]
    d = report["delta"]
    gov = report["governance"]
    corp = report["corpus"]
    trig = report["trigger_recovery"]
    sig = report["signal_variance"]

    def world_share_table() -> str:
        lines = [
            "| World | Design | Current n | Current % | Restored n | Restored % | Δn |",
            "|-------|-------:|----------:|----------:|-----------:|-----------:|---:|",
        ]
        for w in EXISTING_WORLDS:
            lines.append(
                f"| {w} | {_pct(DESIGN_SHARE[w])} | {cur['world_counts'].get(w, 0)} | "
                f"{_pct(cur['world_share'].get(w))} | {res['world_counts'].get(w, 0)} | "
                f"{_pct(res['world_share'].get(w))} | {d['world_count_delta'].get(w, 0):+d} |"
            )
        return "\n".join(lines)

    main = f"""# Version39 — Signal Restoration Simulation

**Status:** Research / Simulation only — **no Production / Trigger / CSV / Signal Service writes**  
**Generated:** `{report['generated_at']}`  
**N (FeatureLoader-loadable):** `{corp['simulated_n']}` / meta `{corp['meta_races']}`  
**Verdict:** **{gov['verdict']}** — {gov['labels'][gov['verdict']]}

## Method

```text
Current signals (defaults / research_world_signals)
        ↓ first-match Trigger (unchanged)
Current World mix

Feature frame L0 + Scorer diagnostic (virtual)
        ↓ designed reconstruct_leg_upset + chaos/pace/late/sustained/short_field
Restored signals
        ↓ same Trigger rules
Restored World mix
```

Hit rate is **not** evaluated.

Coverage: {corp['coverage_note']}

## World Distribution

{world_share_table()}

## Entropy

| Arm | H (bits) | H / Hmax | Active Worlds | TV to design |
|-----|---------:|---------:|--------------:|-------------:|
| Current | {cur['entropy_bits']:.3f} | {_pct(cur['entropy_ratio'])} | {cur['active_worlds']} | {cur['tv_to_design']:.3f} |
| Restored | {res['entropy_bits']:.3f} | {_pct(res['entropy_ratio'])} | {res['active_worlds']} | {res['tv_to_design']:.3f} |
| Δ | {d['entropy_bits']:+.3f} | — | {d['active_worlds']:+d} | {d['tv_to_design']:+.3f} |

Recovered Worlds (were inactive → active): `{res['recovered_worlds']}`

## Index

| Doc | Content |
|-----|---------|
| `v39-signal-restoration.md` | 本ファイル |
| `v39-world-entropy.md` | Entropy / design proximity |
| `v39-trigger-recovery.md` | Trigger activation / margins |
| `v39-signal-variance.md` | Signal coverage / variance |
| `v39-governance.md` | A/B/C |

## Guardrails

- Production / Prediction / PE / CE / AI / World / Trigger / CSV / FeatureLoader / Signal Service — unchanged
"""

    entropy = f"""# Version39 — World Entropy

**N:** `{corp['simulated_n']}`  
**Verdict context:** `{gov['verdict']}`

## Current → Restored

| Metric | Current | Restored | Δ |
|--------|--------:|---------:|--:|
| Entropy (bits) | {cur['entropy_bits']:.3f} | {res['entropy_bits']:.3f} | {d['entropy_bits']:+.3f} |
| Entropy ratio | {_pct(cur['entropy_ratio'])} | {_pct(res['entropy_ratio'])} | — |
| Active Worlds | {cur['active_worlds']} | {res['active_worlds']} | {d['active_worlds']:+d} |
| TV distance to design mix | {cur['tv_to_design']:.3f} | {res['tv_to_design']:.3f} | {d['tv_to_design']:+.3f} |

## Design mix proximity (secondary)

Design: core 30 / midupper 35 / rank7 15 / mixed 10 / bug 5 / midhole 5.

{world_share_table()}

- TV improved vs design: `{gov['design_mix_proximity']['improved_vs_design']}`
- Note: {gov['design_mix_proximity']['note']}

## Inactive → Recovered

- Current inactive: `{cur['inactive_worlds']}`
- Restored inactive: `{res['inactive_worlds']}`
- Recovered: `{res['recovered_worlds']}`

## SubWorld distribution

### Current
`{json.dumps(cur['subworld_counts'], ensure_ascii=False)}`

### Restored
`{json.dumps(res['subworld_counts'], ensure_ascii=False)}`
"""

    trig_lines = [
        "# Version39 — Trigger Recovery",
        "",
        f"**N:** `{corp['simulated_n']}`",
        "",
        "## Activation rates (non-default rules)",
        "",
        "| Rule | World | Pri | Current pass | Restored pass |",
        "|------|-------|----:|-------------:|--------------:|",
    ]
    for r in trig["rules"]:
        trig_lines.append(
            f"| {r['rule_id']} | {r['world']} | {r['priority']} | "
            f"{r['current_pass_n']} ({_pct(r['current_pass_rate'])}) | "
            f"{r['restored_pass_n']} ({_pct(r['restored_pass_rate'])}) |"
        )
    trig_lines.extend(
        [
            "",
            "## Winning-rule margins",
            "",
            f"- Current mean margin: `{(trig['mean_winning_margin_current'] if trig['mean_winning_margin_current'] is not None else 'n/a')}`",
            f"- Restored mean margin: `{(trig['mean_winning_margin_restored'] if trig['mean_winning_margin_restored'] is not None else 'n/a')}`",
            "",
            "## Sample transitions (Current → Restored)",
            "",
        ]
    )
    for t in report.get("sample_transitions") or []:
        trig_lines.append(
            f"- `{t['race_id']}`: `{t['current_world']}` → `{t['restored_world']}` "
            f"(sub=`{t.get('restored_subworld')}`)"
        )
    if not report.get("sample_transitions"):
        trig_lines.append("- (no world changes in sample window)")

    sig_lines = [
        "# Version39 — Signal Variance & Coverage",
        "",
        f"**N:** `{corp['simulated_n']}`",
        "",
        "## Current vs Restored",
        "",
        "| Signal | Cur cov | Cur σ | Cur nunique | Res cov | Res σ | Res nunique |",
        "|--------|--------:|------:|------------:|--------:|------:|------------:|",
    ]
    for k in SIGNAL_KEYS:
        c = sig["current"][k]
        r = sig["restored"][k]
        sig_lines.append(
            f"| {k} | {_pct(c['coverage'])} | "
            f"{(c['std'] if c['std'] is not None else 0):.4f} | {c['nunique_rounded']} | "
            f"{_pct(r['coverage'])} | "
            f"{(r['std'] if r['std'] is not None else 0):.4f} | {r['nunique_rounded']} |"
        )
    sig_lines.extend(
        [
            "",
            "## Reading",
            "",
            "- Current arm collapses many L1/L2 signals to constant/null (V28–V38).",
            "- Restored arm reconstructs difficulty from designed pace formula and pulls chaos/pace/late/sustained from Scorer diagnostics (virtual; not written back).",
            "- `phase` may remain weak if `phase_chain_seed` is absent/low-variance.",
            "",
        ]
    )

    gov_md = f"""# Version39 — Governance

**Generated:** `{report['generated_at']}`  
**N:** `{corp['simulated_n']}`

## Verdict options

| Code | Meaning |
|------|---------|
| A | Signal Restoration により World Entropy が有意に改善 |
| B | 一部改善 |
| C | 改善なし |

## Final verdict

# **{gov['verdict']}**

**Label:** {gov['labels'][gov['verdict']]}  
**Reason:** {gov['reason']}

### Gates (observed)

| Gate | Value |
|------|------:|
| Entropy current | {cur['entropy_bits']:.3f} |
| Entropy restored | {res['entropy_bits']:.3f} |
| Δ Entropy | {d['entropy_bits']:+.3f} |
| TV→design current | {cur['tv_to_design']:.3f} |
| TV→design restored | {res['tv_to_design']:.3f} |
| Recovered Worlds | {', '.join(res['recovered_worlds']) or '—'} |

## Guardrails

- Simulation only
- No Production / Trigger / CSV / Signal Service / FeatureLoader mutation
- Hit rate out of scope
"""

    paths = {
        "main": docs_dir / "v39-signal-restoration.md",
        "entropy": docs_dir / "v39-world-entropy.md",
        "trigger": docs_dir / "v39-trigger-recovery.md",
        "signal": docs_dir / "v39-signal-variance.md",
        "gov": docs_dir / "v39-governance.md",
    }
    paths["main"].write_text(main, encoding="utf-8")
    paths["entropy"].write_text(entropy, encoding="utf-8")
    paths["trigger"].write_text("\n".join(trig_lines) + "\n", encoding="utf-8")
    paths["signal"].write_text("\n".join(sig_lines), encoding="utf-8")
    paths["gov"].write_text(gov_md, encoding="utf-8")
    return {k: str(v) for k, v in paths.items()}


def run_and_write() -> dict[str, Any]:
    sim = SignalRestorationSimulation()
    report = sim.analyze()
    reports_dir = evidence_root() / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "v39-signal-restoration-sim.json"
    # trim raw race detail absence — report already aggregate
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
                "n": rep["corpus"]["simulated_n"],
                "current_entropy": rep["current"]["entropy_bits"],
                "restored_entropy": rep["restored"]["entropy_bits"],
                "current_worlds": rep["current"]["world_counts"],
                "restored_worlds": rep["restored"]["world_counts"],
                "outputs": rep.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
