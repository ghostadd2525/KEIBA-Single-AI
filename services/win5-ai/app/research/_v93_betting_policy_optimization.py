# -*- coding: utf-8 -*-
"""Version93 — Betting Policy Optimization (Shadow only).

Fix Decision structure to V92 RECOMMENDED (Top5/Pool7).
Search betting knobs: legs / alloc / skip / budget.
Constraint: Coverage >= V92 baseline (rank7).
Objective: maximize Ticket ROI.
ADR-008 / Prediction unchanged.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))

from app.decision.betting_params import (  # noqa: E402
    V92_BASELINE_BETTING,
    BettingPolicyParams,
    betting_search_grid,
)
from app.decision.policies import _ticket_ev  # noqa: E402
from app.decision.service import apply_decision, build_prediction_view  # noqa: E402
from app.research._v91_decision_layer_m1_shadow import aggregate, load_corpus_rows, settle  # noqa: E402

SCHEMA = "v93-betting-policy-optimization/1.0"
COVERAGE_EPS = 1e-9


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def settle_bet(decision, race: dict[str, Any], view) -> dict[str, Any]:
    s = settle(decision, race)
    # planned EV (ex-ante) using same approx as skip policy
    ev = 0.0
    for t in decision.tickets:
        ev += _ticket_ev(view, t.horse_id, t.stake)
    s["planned_ev"] = ev
    s["prediction_hit"] = bool(race.get("hit_at_1"))
    return s


def evaluate_betting(rows: list[dict[str, Any]], bet: BettingPolicyParams) -> dict[str, Any]:
    settled_r7 = []
    settled_all = []
    fp_ok = True
    for race in rows:
        view = build_prediction_view(
            race_id=race["race_id"],
            world_id=str(race["cew_world"]),
            predicted_top1=race["predicted_top1"],
            winner_id=race["winner_id"],
            horses=race["horses"],
            field_size=race["field_size"],
        )
        d = apply_decision(view, force_mode="ON", betting_params=bet)
        if d.prediction_fingerprint != view.prediction_fingerprint:
            fp_ok = False
        s = settle_bet(d, race, view)
        settled_all.append(s)
        if race["cew_world"] == "rank7_world":
            settled_r7.append(s)

    def enrich(m: dict[str, Any], settled: list[dict[str, Any]]) -> dict[str, Any]:
        if not settled:
            return m
        m = dict(m)
        stake = sum(r["stake"] for r in settled)
        m["expected_value_total"] = float(sum(r["planned_ev"] for r in settled))
        m["expected_value_per_unit"] = (
            float(sum(r["planned_ev"] for r in settled) / stake) if stake > 0 else None
        )
        # EV only on bought races
        bought = [r for r in settled if r["purchase"]]
        if bought:
            bs = sum(r["stake"] for r in bought)
            m["expected_value_on_buys"] = float(sum(r["planned_ev"] for r in bought) / bs) if bs > 0 else None
        else:
            m["expected_value_on_buys"] = None
        m["prediction_hit_rate"] = float(np.mean([r["prediction_hit"] for r in settled]))
        m["mean_n_tickets"] = float(np.mean([r["n_tickets"] for r in settled]))
        return m

    m_r7 = enrich(aggregate(settled_r7), settled_r7) if settled_r7 else {"n_races": 0}
    m_all = enrich(aggregate(settled_all), settled_all)
    return {"params": bet.to_dict(), "fingerprint_ok": fp_ok, "rank7": m_r7, "all": m_all}


def _slim(m: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "n_races",
        "ticket_roi",
        "ticket_pnl",
        "purchase_hit_rate",
        "coverage_rate",
        "buy_rate",
        "skip_rate",
        "expected_value_total",
        "expected_value_per_unit",
        "expected_value_on_buys",
        "prediction_hit_rate",
        "mean_pool_size",
        "mean_n_tickets",
        "decision_distribution",
    )
    return {k: m.get(k) for k in keys}


def run() -> dict[str, Any]:
    rows = load_corpus_rows()
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fxby = {r["race_id"]: r for r in (fx.get("rows") or fx.get("evaluations") or [])}
    for race in rows:
        fr = fxby.get(race["race_id"]) or {}
        race["hit_at_1"] = bool(fr["hit_at_1"]) if fr.get("hit_at_1") is not None else (
            race["predicted_top1"] == race["winner_id"]
        )

    baseline = evaluate_betting(rows, V92_BASELINE_BETTING)
    cov_floor = float(baseline["rank7"]["coverage_rate"])

    grid = betting_search_grid()
    results = [evaluate_betting(rows, bet) for bet in grid]

    feasible = [
        r
        for r in results
        if (r["rank7"].get("coverage_rate") or -1) + COVERAGE_EPS >= cov_floor and r["fingerprint_ok"]
    ]
    # maximize ROI among feasible
    feasible_sorted = sorted(
        feasible,
        key=lambda r: (
            -(r["rank7"].get("ticket_roi") if r["rank7"].get("ticket_roi") is not None else -1e9),
            -(r["rank7"].get("purchase_hit_rate") or 0),
            -(r["rank7"].get("expected_value_on_buys") or -1e9),
        ),
    )
    best = feasible_sorted[0] if feasible_sorted else None

    # secondary: best ROI with skip_rate constraints mild, or best EV
    best_ev = None
    if feasible:
        best_ev = max(
            feasible,
            key=lambda r: (
                r["rank7"].get("expected_value_on_buys")
                if r["rank7"].get("expected_value_on_buys") is not None
                else -1e9
            ),
        )

    ranked = sorted(
        results,
        key=lambda r: (
            -(r["rank7"].get("ticket_roi") if r["rank7"].get("ticket_roi") is not None else -1e9),
            -(r["rank7"].get("coverage_rate") or 0),
        ),
    )

    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "adr": "ADR-008 (unchanged)",
        "decision_baseline": V92_BASELINE_BETTING.to_dict(),
        "coverage_floor_rank7": cov_floor,
        "n_races": len(rows),
        "n_rank7": sum(1 for r in rows if r["cew_world"] == "rank7_world"),
        "grid_size": len(grid),
        "n_feasible": len(feasible),
        "baseline": {
            "params": baseline["params"],
            "rank7": _slim(baseline["rank7"]),
        },
        "best_roi_under_coverage": {
            "params": best["params"],
            "rank7": _slim(best["rank7"]),
            "all": _slim(best["all"]),
        }
        if best
        else None,
        "best_ev_under_coverage": {
            "params": best_ev["params"],
            "rank7": _slim(best_ev["rank7"]),
        }
        if best_ev
        else None,
        "top20_feasible": [
            {"params": r["params"], "rank7": _slim(r["rank7"])} for r in feasible_sorted[:20]
        ],
        "top10_overall_by_roi": [
            {
                "params": r["params"],
                "rank7": _slim(r["rank7"]),
                "feasible": (r["rank7"].get("coverage_rate") or -1) + COVERAGE_EPS >= cov_floor,
            }
            for r in ranked[:10]
        ],
    }


def _fmt(x: Any, nd: int = 4) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def write_docs(report: dict[str, Any]) -> dict[str, Path]:
    out = ROOT / "docs/research"
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    paths["json"] = out / "_v93-betting-policy-optimization.json"
    paths["json"].write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    best = report.get("best_roi_under_coverage")
    base = report["baseline"]
    opt = [
        "# Version93 — Betting Policy Optimization",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "**Decision structure:** V92 `Top5_Pool7` 固定  ",
        f"**Coverage floor (rank7):** {_fmt(report['coverage_floor_rank7'])}  ",
        f"grid={report['grid_size']} / feasible={report['n_feasible']}",
        "",
        "## Baseline（V92 betting）",
        "",
        f"`{base['params']['id']}`",
        "",
        f"- ROI={_fmt(base['rank7'].get('ticket_roi'))} / PurchaseHit={_fmt(base['rank7'].get('purchase_hit_rate'))} / "
        f"Coverage={_fmt(base['rank7'].get('coverage_rate'))} / EV_on_buys={_fmt(base['rank7'].get('expected_value_on_buys'))}",
        "",
        "## 最適（Coverage 維持 ∩ ROI 最大）",
        "",
    ]
    if best:
        pr, m = best["params"], best["rank7"]
        opt += [
            f"**`{pr['id']}`**",
            "",
            f"- buy_legs={pr['buy_legs']} / alloc={pr['alloc']} / skip={pr['skip']} / budget={pr['budget_scale']}",
            f"- Ticket ROI={_fmt(m.get('ticket_roi'))} (Δ vs baseline {_fmt((m.get('ticket_roi') or 0)-(base['rank7'].get('ticket_roi') or 0))})",
            f"- Purchase Hit={_fmt(m.get('purchase_hit_rate'))}",
            f"- Coverage={_fmt(m.get('coverage_rate'))}",
            f"- EV_on_buys={_fmt(m.get('expected_value_on_buys'))}",
            f"- Buy={_fmt(m.get('buy_rate'))} / Skip={_fmt(m.get('skip_rate'))}",
            "",
        ]
    else:
        opt += ["（feasible なし）", ""]

    opt += [
        "## Top20 feasible（rank7 ROI順）",
        "",
        "| Policy | Legs | Alloc | Skip | Bud | ROI | Hit | Cov | EV | Buy | SkipRate |",
        "|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in report["top20_feasible"]:
        pr, m = r["params"], r["rank7"]
        opt.append(
            f"| `{pr['id']}` | {pr['buy_legs']} | {pr['alloc']} | {pr['skip']} | {pr['budget_scale']} | "
            f"{_fmt(m.get('ticket_roi'))} | {_fmt(m.get('purchase_hit_rate'))} | {_fmt(m.get('coverage_rate'))} | "
            f"{_fmt(m.get('expected_value_on_buys'))} | {_fmt(m.get('buy_rate'))} | {_fmt(m.get('skip_rate'))} |"
        )

    opt += [
        "",
        "## 方法",
        "",
        "- 券種: win のみ（複勝オッズ/着順なしのため）",
        "- 購入点数: buy_legs 1–5（V92 Top5 候補内）",
        "- 配分: equal / decay / top_heavy / mass_prop",
        "- Skip: none / ev_neg / mass_lt_08 / mass_lt_10 / field_gt_16",
        "- Budget: 0.5 / 1.0 × UNIT",
        "- Pool は常に Pool7 → Coverage を構造的に維持",
        "",
        "## 関連",
        "",
        "- `v93-betting-pareto.md`",
        "- `v93-governance.md`",
        "",
    ]
    paths["opt"] = out / "v93-betting-policy-optimization.md"
    paths["opt"].write_text("\n".join(opt), encoding="utf-8")

    # compact "pareto-like" report: feasible frontier ROI vs Hit
    front = []
    for r in report["top20_feasible"]:
        # rebuild from feasible_sorted already roi-ordered; compute non-dominated on hit×roi among all feasible via top20 is weak
        front.append(r)
    # Better: compute from json top20 only for display; full front from all feasible in report we only saved top20
    # Re-read from results via top20 is enough for doc; add note

    pareto = [
        "# Version93 — Betting Policy Results（Coverage-constrained）",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "目的: Coverage ≥ V92 Top5_Pool7 を満たす Betting のうち **Ticket ROI 最大**",
        "",
        f"## Winner",
        "",
    ]
    if best:
        pareto += [
            f"- `{best['params']['id']}`",
            f"- ROI={_fmt(best['rank7'].get('ticket_roi'))} / Coverage={_fmt(best['rank7'].get('coverage_rate'))} / "
            f"PurchaseHit={_fmt(best['rank7'].get('purchase_hit_rate'))} / Skip={_fmt(best['rank7'].get('skip_rate'))}",
            "",
        ]
    if report.get("best_ev_under_coverage"):
        be = report["best_ev_under_coverage"]
        pareto += [
            "## Best EV (secondary)",
            "",
            f"- `{be['params']['id']}` EV_on_buys={_fmt(be['rank7'].get('expected_value_on_buys'))} "
            f"ROI={_fmt(be['rank7'].get('ticket_roi'))}",
            "",
        ]
    pareto += [
        "## Baseline vs Winner",
        "",
        "| | ROI | PurchaseHit | Coverage | EV_buys | Buy | Skip |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| V92 baseline | {_fmt(base['rank7'].get('ticket_roi'))} | {_fmt(base['rank7'].get('purchase_hit_rate'))} | {_fmt(base['rank7'].get('coverage_rate'))} | {_fmt(base['rank7'].get('expected_value_on_buys'))} | {_fmt(base['rank7'].get('buy_rate'))} | {_fmt(base['rank7'].get('skip_rate'))} |",
    ]
    if best:
        m = best["rank7"]
        pareto.append(
            f"| Winner | {_fmt(m.get('ticket_roi'))} | {_fmt(m.get('purchase_hit_rate'))} | {_fmt(m.get('coverage_rate'))} | {_fmt(m.get('expected_value_on_buys'))} | {_fmt(m.get('buy_rate'))} | {_fmt(m.get('skip_rate'))} |"
        )
    pareto.append("")
    paths["pareto"] = out / "v93-betting-pareto.md"
    paths["pareto"].write_text("\n".join(pareto), encoding="utf-8")

    win_id = best["params"]["id"] if best else "none"
    gov = [
        "# Version93 — Governance（Betting Policy Optimization）",
        "",
        f"**Date:** {report['generated_at'][:10]}  ",
        f"**Verdict:** **A**（Coverage 制約下 ROI 最適化完了 / winner=`{win_id}`）  ",
        "**Type:** Shadow only（Decision Layer Betting）",
        "",
        "【Decision】",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Action Type | Betting Policy Optimization |",
        "| ADR-008 / Architecture / Prediction | **未変更** |",
        "| Decision structure | V92 Top5_Pool7 固定 |",
        "| Production policy change | **No**（Shadow 推奨のみ） |",
        "| Production Required | **No** |",
        f"| Expected Next Action | Winner `{win_id}` を Shadow Betting 既定候補としてレビュー（別 Decision / M2 前） |",
        "",
        "## 成果物",
        "",
        "- `v93-betting-policy-optimization.md`",
        "- `v93-betting-pareto.md`",
        "- `v93-governance.md`",
        "- `_v93-betting-policy-optimization.json`",
        "- `app/decision/betting_params.py`",
        "",
    ]
    paths["gov"] = out / "v93-governance.md"
    paths["gov"].write_text("\n".join(gov), encoding="utf-8")
    return paths


def main() -> None:
    report = run()
    paths = write_docs(report)
    mirror = Path(r"C:\Users\Mr.me\expect-keiba-ai\docs\research")
    if mirror.is_dir():
        for p in paths.values():
            (mirror / p.name).write_bytes(p.read_bytes())
    print(
        json.dumps(
            {
                "coverage_floor": report["coverage_floor_rank7"],
                "n_feasible": report["n_feasible"],
                "baseline_roi": report["baseline"]["rank7"].get("ticket_roi"),
                "best": report.get("best_roi_under_coverage"),
                "best_ev_id": (report.get("best_ev_under_coverage") or {}).get("params", {}).get("id"),
                "paths": {k: str(v) for k, v in paths.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
