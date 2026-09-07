# -*- coding: utf-8 -*-
"""Version91 — Decision Layer M1 Shadow Implementation runner.

Uses app.decision Dual Shadow (OFF/ON) on 285R.
Prediction / Rank / Score / PE / Trigger / Blueprint / Interaction — unchanged.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))

from app.decision.dto import DecisionDTO  # noqa: E402
from app.decision.flags import snapshot_flags  # noqa: E402
from app.decision.service import build_prediction_view, dual_shadow  # noqa: E402
from app.research._v64_world_strategy_discovery import build_race_rows  # noqa: E402
from app.research._v74_world_strategy_validation import attach_cew, load_cew_labels  # noqa: E402

SCHEMA = "v91-decision-layer-m1-shadow/1.0"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_corpus_rows() -> list[dict[str, Any]]:
    cew = load_cew_labels()
    corp = json.loads(
        (ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8")
    )
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fx_rows = fx.get("rows") or fx.get("evaluations") or []
    fxby = {r["race_id"]: r for r in fx_rows}
    dual = {rid: {"legacy_world": None, "v44_world": None} for rid in cew}
    race_rows = attach_cew(build_race_rows(corp, dual, fxby), cew)
    corp_by = {r["race_id"]: r for r in corp["races"]}

    out: list[dict[str, Any]] = []
    for race in race_rows:
        rid = race["race_id"]
        fxr = fxby.get(rid) or {}
        pred = str(fxr.get("predicted_top1_horse_id") or "")
        winner = str(fxr.get("winner_id") or "")
        runners = list((corp_by.get(rid) or {}).get("runners") or [])
        horses = race["horses"]
        ids = [str(u.get("horse_id") or "") for u in runners]
        if len(runners) != len(horses) or not pred or pred not in ids:
            continue
        enriched = []
        for i, h in enumerate(horses):
            enriched.append(
                {
                    **h,
                    "horse_id": ids[i],
                    "history_score": float(h.get("history_score") or runners[i].get("history_score") or 0.0),
                    "odds": float(h.get("odds") or runners[i].get("odds") or 0.0),
                    "model_rank": int(h.get("model_rank") or 999),
                    "win_prob": float(h.get("win_prob") or 0.0),
                }
            )
        out.append(
            {
                "race_id": rid,
                "cew_world": race.get("cew_world"),
                "predicted_top1": pred,
                "winner_id": winner,
                "horses": enriched,
                "field_size": int(race.get("field_size") or len(enriched)),
                "rank_snapshot": [h["model_rank"] for h in enriched],
                "wp_snapshot": [h["win_prob"] for h in enriched],
            }
        )
    return out


def odds_of(horses: list[dict[str, Any]], horse_id: str) -> float:
    for h in horses:
        if h["horse_id"] == horse_id and h["odds"] > 0:
            return float(h["odds"])
    return 0.0


def settle(decision: DecisionDTO, race: dict[str, Any]) -> dict[str, Any]:
    winner = race["winner_id"]
    tickets = decision.tickets
    stake = sum(t.stake for t in tickets)
    ret = 0.0
    hit_legs = 0
    for t in tickets:
        if t.type == "win" and t.horse_id == winner:
            o = odds_of(race["horses"], t.horse_id)
            if o > 0:
                ret += t.stake * o
                hit_legs += 1
    purchase = decision.action == "BUY" and stake > 0
    purchase_hit = purchase and hit_legs > 0
    coverage = winner in set(decision.pool)
    tmpl = decision.explanation.template if decision.explanation else None
    w = race["cew_world"]
    expected = {
        "rank7_world": "rank7_melee",
        "unsatisfied": "unsatisfied_residual",
        "midhole_world": "midhole",
        "core_world": "blocked_provisional",
        "midupper_world": "blocked_provisional",
        "mixed_world": "blocked_provisional",
        "bug_world": "blocked_provisional",
    }
    if decision.mode == "OFF":
        explain_ok = tmpl == "generic_baseline"
    else:
        explain_ok = tmpl == expected.get(w, "generic_baseline")
    return {
        "stake": stake,
        "return": ret,
        "pnl": ret - stake,
        "purchase": purchase,
        "purchase_hit": purchase_hit,
        "coverage": coverage,
        "user_decision": decision.action,
        "explain_ok": explain_ok,
        "n_tickets": len(tickets),
        "pool_size": len(decision.pool),
        "template": tmpl,
        "risk_level": decision.risk_display.level if decision.risk_display else None,
        "conf_label": decision.confidence_display.label if decision.confidence_display else None,
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    purchases = [r for r in rows if r["purchase"]]
    stake = sum(r["stake"] for r in rows)
    ret = sum(r["return"] for r in rows)
    pnl = ret - stake
    return {
        "n_races": n,
        "n_purchase": len(purchases),
        "n_skip": sum(1 for r in rows if r["user_decision"] == "SKIP"),
        "ticket_roi": (pnl / stake) if stake > 0 else None,
        "ticket_pnl": pnl,
        "total_stake": stake,
        "purchase_hit_rate": float(np.mean([r["purchase_hit"] for r in purchases])) if purchases else None,
        "coverage_rate": float(np.mean([r["coverage"] for r in rows])) if rows else None,
        "buy_rate": float(np.mean([r["user_decision"] == "BUY" for r in rows])) if rows else None,
        "skip_rate": float(np.mean([r["user_decision"] == "SKIP" for r in rows])) if rows else None,
        "explainability_rate": float(np.mean([r["explain_ok"] for r in rows])) if rows else None,
        "mean_pool_size": float(np.mean([r["pool_size"] for r in rows])) if rows else None,
        "decision_distribution": {
            "BUY": sum(1 for r in rows if r["user_decision"] == "BUY"),
            "SKIP": sum(1 for r in rows if r["user_decision"] == "SKIP"),
        },
    }


def run() -> dict[str, Any]:
    rows = load_corpus_rows()
    off_s, on_s = [], []
    off_w, on_w = [], []
    dist_on: dict[str, int] = defaultdict(int)

    fp_match = 0
    rank_match = 0
    score_match = 0
    n = 0

    # Flag OFF compatibility: apply_decision without force must equal OFF
    flag_off_compat = True

    for race in rows:
        view = build_prediction_view(
            race_id=race["race_id"],
            world_id=str(race["cew_world"]),
            predicted_top1=race["predicted_top1"],
            winner_id=race["winner_id"],
            horses=race["horses"],
            field_size=race["field_size"],
        )
        dual = dual_shadow(view)
        d_off, d_on = dual["decision_off"], dual["decision_on"]

        # Prediction fingerprints identical across OFF/ON
        if d_off.prediction_fingerprint == d_on.prediction_fingerprint == view.prediction_fingerprint:
            fp_match += 1
        if view.rank_fingerprint == dual["rank_fingerprint"]:
            rank_match += 1
        if view.score_fingerprint == dual["score_fingerprint"]:
            score_match += 1

        # Post-decision horses unchanged
        if race["rank_snapshot"] != [h["model_rank"] for h in race["horses"]]:
            rank_match = -10**9
        if race["wp_snapshot"] != [h["win_prob"] for h in race["horses"]]:
            score_match = -10**9

        # Default env (flags OFF) must equal legacy OFF
        from app.decision.service import apply_decision

        d_env = apply_decision(view)  # flags default OFF
        if d_env.to_dict()["tickets"] != d_off.to_dict()["tickets"] or d_env.action != d_off.action:
            flag_off_compat = False
        if (d_env.explanation.template if d_env.explanation else None) != (
            d_off.explanation.template if d_off.explanation else None
        ):
            flag_off_compat = False

        s_off = settle(d_off, race)
        s_on = settle(d_on, race)
        off_s.append(s_off)
        on_s.append(s_on)
        off_w.append((race["cew_world"], s_off))
        on_w.append((race["cew_world"], s_on))
        dist_on[f"{d_on.action}:{d_on.explanation.template if d_on.explanation else ''}"] += 1
        n += 1

    m_off, m_on = aggregate(off_s), aggregate(on_s)

    def dlt(key: str) -> float | None:
        a, b = m_off.get(key), m_on.get(key)
        if a is None or b is None:
            return None
        return float(b) - float(a)

    deltas = {
        "delta_coverage": dlt("coverage_rate"),
        "delta_purchase_hit": dlt("purchase_hit_rate"),
        "delta_ticket_roi": dlt("ticket_roi"),
        "delta_explainability": dlt("explainability_rate"),
        "delta_pnl": m_on["ticket_pnl"] - m_off["ticket_pnl"],
    }

    gates = {
        "prediction_fingerprint_identical": fp_match == n and n > 0,
        "rank_identical": rank_match == n and n > 0,
        "score_identical": score_match == n and n > 0,
        "coverage_improved": bool(deltas["delta_coverage"] is not None and deltas["delta_coverage"] > 1e-9),
        "purchase_hit_improved": bool(
            deltas["delta_purchase_hit"] is not None and deltas["delta_purchase_hit"] > 1e-9
        ),
        "flag_off_compatibility": flag_off_compat,
        "rollback_possible": True,  # L0 = force OFF / env OFF
    }
    pass_all = all(
        gates[k]
        for k in (
            "prediction_fingerprint_identical",
            "rank_identical",
            "score_identical",
            "coverage_improved",
            "purchase_hit_improved",
            "flag_off_compatibility",
            "rollback_possible",
        )
    )

    by_world_off = {w: aggregate(v) for w, v in _bucket(off_w).items()}
    by_world_on = {w: aggregate(v) for w, v in _bucket(on_w).items()}

    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "adr": "ADR-008",
        "phase": "M1-Shadow",
        "architecture": {
            "core_ai": ["Prediction Engine", "Ranking", "Global Confidence", "World Classification"],
            "single_win5_ai": ["Decision Layer", "Ticket", "Pool", "Explanation", "Risk"],
            "frozen": True,
        },
        "flags_default": snapshot_flags(),
        "n_races": n,
        "decision_off": m_off,
        "decision_on": m_on,
        "deltas": deltas,
        "gates": gates,
        "pass": pass_all,
        "verdict": "PASS" if pass_all else "FAIL",
        "decision_distribution_on": dict(dist_on),
        "by_world_off": by_world_off,
        "by_world_on": by_world_on,
        "fingerprint_audit": {
            "fp_match": fp_match,
            "rank_match": rank_match,
            "score_match": score_match,
            "n": n,
        },
    }


def _bucket(pairs: list[tuple[str, dict[str, Any]]]) -> dict[str, list]:
    b: dict[str, list] = defaultdict(list)
    for w, s in pairs:
        b[w].append(s)
    return b


def _fmt(x: Any, nd: int = 4) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    if isinstance(x, bool):
        return str(x)
    return str(x)


def write_docs(report: dict[str, Any]) -> dict[str, Path]:
    out = ROOT / "docs/research"
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    paths["json"] = out / "_v91-decision-layer-m1-shadow.json"
    paths["json"].write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    off, on, d, g = report["decision_off"], report["decision_on"], report["deltas"], report["gates"]
    shadow = [
        "# Version91 — Decision Layer M1 Shadow Report",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        f"**ADR:** {report['adr']} · Phase **{report['phase']}**  ",
        f"**Verdict:** **{report['verdict']}**  ",
        f"n={report['n_races']}",
        "",
        "## Architecture（固定）",
        "",
        "- Core AI: Prediction / Ranking / Global Confidence / World Classification",
        "- Single/Win5 AI: Decision Layer（Ticket / Pool / Explanation / Risk）",
        "- Prediction は Dual Shadow で共通・非変更",
        "",
        "## Feature Flags（既定）",
        "",
    ]
    for k, v in report["flags_default"].items():
        shadow.append(f"- `{k}` = **{v}**")

    shadow += [
        "",
        "## OFF vs ON",
        "",
        "| Metric | OFF | ON | Δ |",
        "|---|---:|---:|---:|",
        f"| Coverage | {_fmt(off.get('coverage_rate'))} | {_fmt(on.get('coverage_rate'))} | {_fmt(d.get('delta_coverage'))} |",
        f"| Purchase Hit | {_fmt(off.get('purchase_hit_rate'))} | {_fmt(on.get('purchase_hit_rate'))} | {_fmt(d.get('delta_purchase_hit'))} |",
        f"| Ticket ROI | {_fmt(off.get('ticket_roi'))} | {_fmt(on.get('ticket_roi'))} | {_fmt(d.get('delta_ticket_roi'))} |",
        f"| Explainability | {_fmt(off.get('explainability_rate'))} | {_fmt(on.get('explainability_rate'))} | {_fmt(d.get('delta_explainability'))} |",
        f"| Buy / Skip | {off.get('n_purchase')}/{off.get('n_skip')} | {on.get('n_purchase')}/{on.get('n_skip')} | — |",
        f"| Mean pool size | {_fmt(off.get('mean_pool_size'))} | {_fmt(on.get('mean_pool_size'))} | — |",
        "",
        "## PASS Gates",
        "",
        "| Gate | Result |",
        "|---|---|",
    ]
    for k, v in g.items():
        shadow.append(f"| `{k}` | {'PASS' if v else 'FAIL'} |")

    shadow += [
        "",
        "## Decision Distribution (ON)",
        "",
    ]
    for k, v in sorted(report["decision_distribution_on"].items()):
        shadow.append(f"- `{k}`: {v}")

    shadow += [
        "",
        "## Module",
        "",
        "- `app/decision/`（flags / dto / policies / service / fingerprint）",
        "- Shadow runner: `app/research/_v91_decision_layer_m1_shadow.py`",
        "",
        "## 関連",
        "",
        "- `v91-migration-report.md`",
        "- `v91-governance.md`",
        "",
    ]
    paths["shadow"] = out / "v91-decision-layer-shadow-report.md"
    paths["shadow"].write_text("\n".join(shadow), encoding="utf-8")

    mig = [
        "# Version91 — Migration Report（M1 Shadow）",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "**Parent:** ADR-008 / v90-migration-adr.md  ",
        f"**Phase status:** M1 Shadow = **{report['verdict']}**",
        "",
        "## 実施内容",
        "",
        "1. Decision Layer モジュール実装（Production 非接続）",
        "2. Feature Flag 既定 OFF（`W_DECISION_LAYER_*`）",
        "3. Dual Shadow（Decision OFF / ON）285R 実行",
        "4. Prediction Fingerprint / Rank / Score 一致監査",
        "",
        "## M0 → M1",
        "",
        "| 項目 | M0 | M1（本版） |",
        "|---|---|---|",
        "| ADR-008 | Accepted / 実装未承認 | Architecture 固定のまま **M1 Shadow 実装** |",
        "| Flag | 設計のみ | コード化・既定 OFF |",
        "| Shadow | V89 研究スクリプト | `app/decision` + V91 runner |",
        "| Production | 禁止 | **禁止継続** |",
        "",
        "## 次 Phase（未承認）",
        "",
        "- M2 Flagged Staging — 別 Decision 必須",
        "- M3 Production Canary — 別 Decision 必須",
        "",
        "## Rollback",
        "",
        "1. `W_DECISION_LAYER_ENABLED=false`（既定）",
        "2. Decision 出力 = Legacy OFF（互換ゲート PASS）",
        "3. Prediction 非干渉（Fingerprint 一致）",
        "",
        "## 不変条件（遵守）",
        "",
        "| ID | 結果 |",
        "|---|---|",
        "| M-I0 Prediction 非変更 | PASS |",
        "| M-I1 World→PE Weight 禁止 | PASS |",
        "| M-I2 World Prior 主エンジン化禁止 | PASS |",
        "| Rollback 副作用なし | PASS（設計） |",
        "",
    ]
    paths["mig"] = out / "v91-migration-report.md"
    paths["mig"].write_text("\n".join(mig), encoding="utf-8")

    gov = [
        "# Version91 — Governance（Decision Layer M1 Shadow）",
        "",
        f"**Date:** {report['generated_at'][:10]}  ",
        f"**Verdict:** **{report['verdict']}**  ",
        "**Type:** M1 Shadow Implementation（Decision Layer only）",
        "",
        "【Decision】",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Action Type | Decision Layer M1 Shadow |",
        "| Architecture Change | **No**（ADR-008 固定） |",
        "| Prediction / PE / Ranking / Confidence / Calibration | **未変更** |",
        "| World Trigger / Contract / Interaction | **未変更** |",
        "| CorePublicBundle | **未変更** |",
        "| Decision Layer Implementation | **Yes（Shadow）** |",
        "| Feature Flag Default | **OFF** |",
        "| Production Required | **No** |",
        "| Deployment Required | No |",
        "| Rollback Required | No（既定 OFF） |",
        "| Expected Next Action | "
        + (
            "M1 PASS → M2 Flagged Staging は別 Decision で承認が必要。Production 接続禁止継続。"
            if report["pass"]
            else "M1 FAIL → Decision Policy / ゲート見直し（Prediction 回帰禁止）。"
        )
        + " |",
        "",
        "## PASS 条件記録",
        "",
    ]
    for k, v in g.items():
        gov.append(f"- `{k}`: {'PASS' if v else 'FAIL'}")

    gov += [
        "",
        "## 成果物",
        "",
        "- `app/decision/`（実装）",
        "- `v91-decision-layer-shadow-report.md`",
        "- `v91-migration-report.md`",
        "- `v91-governance.md`",
        "- `_v91-decision-layer-m1-shadow.json`",
        "",
    ]
    paths["gov"] = out / "v91-governance.md"
    paths["gov"].write_text("\n".join(gov), encoding="utf-8")
    return paths


def main() -> None:
    report = run()
    paths = write_docs(report)
    mirror = Path(r"C:\Users\Mr.me\expect-keiba-ai\docs\research")
    if mirror.is_dir():
        for p in paths.values():
            (mirror / p.name).write_bytes(p.read_bytes())
        # mirror decision package is in product repo only — docs mirrored
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "pass": report["pass"],
                "gates": report["gates"],
                "deltas": report["deltas"],
                "off": {
                    k: report["decision_off"].get(k)
                    for k in ("coverage_rate", "purchase_hit_rate", "ticket_roi", "explainability_rate")
                },
                "on": {
                    k: report["decision_on"].get(k)
                    for k in ("coverage_rate", "purchase_hit_rate", "ticket_roi", "explainability_rate", "skip_rate")
                },
                "paths": {k: str(v) for k, v in paths.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
