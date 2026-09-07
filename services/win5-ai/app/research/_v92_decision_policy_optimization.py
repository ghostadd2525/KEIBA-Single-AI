# -*- coding: utf-8 -*-
"""Version92 — Decision Policy Optimization (Pareto Front).

Search rank7 Top2..5 × Pool4..7 inside Decision Layer only.
ADR-008 / Prediction / Architecture unchanged.
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

from app.decision.dto import DecisionDTO  # noqa: E402
from app.decision.policy_params import M1_RANK7, Rank7PolicyParams, search_grid  # noqa: E402
from app.decision.service import apply_decision, build_prediction_view  # noqa: E402
from app.research._v64_world_strategy_discovery import build_race_rows  # noqa: E402
from app.research._v74_world_strategy_validation import attach_cew, load_cew_labels  # noqa: E402
from app.research._v91_decision_layer_m1_shadow import (  # noqa: E402
    aggregate,
    load_corpus_rows,
    odds_of,
    settle,
)

SCHEMA = "v92-decision-policy-optimization/1.0"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def settle_ext(decision: DecisionDTO, race: dict[str, Any]) -> dict[str, Any]:
    s = settle(decision, race)
    # Hit = prediction top1 hit (unchanged by Decision); still reported
    s["prediction_hit"] = bool(race.get("hit_at_1"))
    if "hit_at_1" not in race:
        s["prediction_hit"] = race["predicted_top1"] == race["winner_id"]
    # Decision hit = any purchased win ticket hits (same as purchase_hit when BUY)
    s["decision_hit"] = bool(s["purchase_hit"]) if s["purchase"] else False
    return s


def evaluate_policy(rows: list[dict[str, Any]], params: Rank7PolicyParams) -> dict[str, Any]:
    settled_all = []
    settled_r7 = []
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
        d_on = apply_decision(view, force_mode="ON", rank7_params=params)
        if d_on.prediction_fingerprint != view.prediction_fingerprint:
            fp_ok = False
        s = settle_ext(d_on, race)
        settled_all.append(s)
        if race["cew_world"] == "rank7_world":
            settled_r7.append(s)

    m_all = aggregate(settled_all)
    m_r7 = aggregate(settled_r7) if settled_r7 else {"n_races": 0}
    # extra rates
    for m, settled in ((m_all, settled_all), (m_r7, settled_r7)):
        if not settled:
            continue
        m["prediction_hit_rate"] = float(np.mean([r["prediction_hit"] for r in settled]))
        m["decision_hit_rate"] = float(np.mean([r["decision_hit"] for r in settled]))
        m["hit_rate"] = m["decision_hit_rate"]
        m["mean_n_tickets"] = float(np.mean([r["n_tickets"] for r in settled]))

    return {
        "params": params.to_dict(),
        "fingerprint_ok": fp_ok,
        "all": m_all,
        "rank7": m_r7,
    }


def pareto_front(
    points: list[dict[str, Any]],
    *,
    x_key: str = "purchase_hit_rate",
    y_key: str = "ticket_roi",
    scope: str = "rank7",
) -> list[dict[str, Any]]:
    """Maximize x_key and y_key (non-dominated)."""
    usable = []
    for p in points:
        m = p.get(scope) or {}
        if m.get("n_races", 0) <= 0:
            continue
        if m.get(x_key) is None or m.get(y_key) is None:
            continue
        usable.append(p)

    front = []
    for p in usable:
        mx, my = p[scope][x_key], p[scope][y_key]
        dominated = False
        for q in usable:
            if q is p:
                continue
            qx, qy = q[scope][x_key], q[scope][y_key]
            if (qx >= mx and qy >= my) and (qx > mx or qy > my):
                dominated = True
                break
        if not dominated:
            front.append(p)
    front.sort(key=lambda p: (p[scope][x_key], p[scope][y_key]), reverse=True)
    return front


def pick_recommendations(front: list[dict[str, Any]], all_points: list[dict[str, Any]]) -> dict[str, Any]:
    """Recommend max-ROI, max-Hit, and balanced on rank7 Pareto."""
    if not front:
        return {}
    max_roi = max(front, key=lambda p: p["rank7"]["ticket_roi"])
    max_hit = max(front, key=lambda p: p["rank7"]["purchase_hit_rate"])
    # balanced: normalize hit & roi on front then maximize sum
    hits = [p["rank7"]["purchase_hit_rate"] for p in front]
    rois = [p["rank7"]["ticket_roi"] for p in front]
    hmin, hmax = min(hits), max(hits)
    rmin, rmax = min(rois), max(rois)

    def norm(p: dict[str, Any]) -> float:
        h = p["rank7"]["purchase_hit_rate"]
        r = p["rank7"]["ticket_roi"]
        hn = 0.5 if hmax <= hmin else (h - hmin) / (hmax - hmin)
        rn = 0.5 if rmax <= rmin else (r - rmin) / (rmax - rmin)
        cov = p["rank7"].get("coverage_rate") or 0.0
        return 0.45 * hn + 0.45 * rn + 0.10 * cov

    balanced = max(front, key=norm)
    m1 = next((p for p in all_points if p["params"]["id"] == M1_RANK7.id()), None)
    return {
        "max_ticket_roi": {
            "id": max_roi["params"]["id"],
            "params": max_roi["params"],
            "rank7": _slim_metrics(max_roi["rank7"]),
        },
        "max_purchase_hit": {
            "id": max_hit["params"]["id"],
            "params": max_hit["params"],
            "rank7": _slim_metrics(max_hit["rank7"]),
        },
        "balanced_hit_roi": {
            "id": balanced["params"]["id"],
            "params": balanced["params"],
            "rank7": _slim_metrics(balanced["rank7"]),
            "score": norm(balanced),
        },
        "m1_baseline": {
            "id": M1_RANK7.id(),
            "params": M1_RANK7.to_dict(),
            "rank7": _slim_metrics(m1["rank7"]) if m1 else None,
            "on_pareto": bool(m1 and m1 in front),
        },
    }


def _slim_metrics(m: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "n_races",
        "ticket_roi",
        "ticket_pnl",
        "purchase_hit_rate",
        "coverage_rate",
        "hit_rate",
        "prediction_hit_rate",
        "buy_rate",
        "skip_rate",
        "mean_pool_size",
        "mean_n_tickets",
        "decision_distribution",
    )
    return {k: m.get(k) for k in keys}


def run() -> dict[str, Any]:
    rows = load_corpus_rows()
    # attach fixture hit_at_1
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fxby = {r["race_id"]: r for r in (fx.get("rows") or fx.get("evaluations") or [])}
    for race in rows:
        fr = fxby.get(race["race_id"]) or {}
        if fr.get("hit_at_1") is not None:
            race["hit_at_1"] = bool(fr["hit_at_1"])
        else:
            race["hit_at_1"] = race["predicted_top1"] == race["winner_id"]

    grid = search_grid()
    results = []
    for params in grid:
        results.append(evaluate_policy(rows, params))

    front = pareto_front(results)
    # also coverage-hit pareto for secondary
    front_cov = pareto_front(results, x_key="coverage_rate", y_key="ticket_roi")
    recs = pick_recommendations(front, results)

    # table sorted by purchase hit then roi
    ranked = sorted(
        results,
        key=lambda p: (
            -(p["rank7"].get("purchase_hit_rate") or -1),
            -(p["rank7"].get("ticket_roi") or -1),
            -(p["rank7"].get("coverage_rate") or -1),
        ),
    )

    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "adr": "ADR-008 (unchanged)",
        "scope": "Decision Layer policy params only (rank7 Top×Pool grid)",
        "n_races": len(rows),
        "n_rank7": sum(1 for r in rows if r["cew_world"] == "rank7_world"),
        "grid_size": len(grid),
        "m1_default": M1_RANK7.to_dict(),
        "results": [
            {
                "params": r["params"],
                "fingerprint_ok": r["fingerprint_ok"],
                "rank7": _slim_metrics(r["rank7"]),
                "all": _slim_metrics(r["all"]),
            }
            for r in ranked
        ],
        "pareto_front_hit_roi": [
            {"params": p["params"], "rank7": _slim_metrics(p["rank7"])} for p in front
        ],
        "pareto_front_coverage_roi": [
            {"params": p["params"], "rank7": _slim_metrics(p["rank7"])} for p in front_cov
        ],
        "recommendations": recs,
        "recommended_default": recs.get("balanced_hit_roi"),
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
    paths["json"] = out / "_v92-decision-policy-optimization.json"
    paths["json"].write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Pareto report
    pareto_md = [
        "# Version92 — Decision Policy Pareto Front",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "**Axes (rank7):** maximize Purchase Hit × Ticket ROI  ",
        "**Grid:** Top2–5 × Pool4–7（16点）  ",
        "ADR-008 / Prediction 非変更",
        "",
        "## Pareto Front（Hit × ROI）",
        "",
        "| Policy | Top | Pool | PurchaseHit | TicketROI | Coverage | Hit | Buy |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for p in report["pareto_front_hit_roi"]:
        pr, m = p["params"], p["rank7"]
        pareto_md.append(
            f"| `{pr['id']}` | {pr['ticket_top_n']} | {pr['pool_size']} | {_fmt(m.get('purchase_hit_rate'))} | {_fmt(m.get('ticket_roi'))} | {_fmt(m.get('coverage_rate'))} | {_fmt(m.get('hit_rate'))} | {_fmt(m.get('buy_rate'))} |"
        )

    pareto_md += [
        "",
        "## Pareto Front（Coverage × ROI）",
        "",
        "| Policy | Top | Pool | Coverage | TicketROI | PurchaseHit |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for p in report["pareto_front_coverage_roi"]:
        pr, m = p["params"], p["rank7"]
        pareto_md.append(
            f"| `{pr['id']}` | {pr['ticket_top_n']} | {pr['pool_size']} | {_fmt(m.get('coverage_rate'))} | {_fmt(m.get('ticket_roi'))} | {_fmt(m.get('purchase_hit_rate'))} |"
        )

    rec = report["recommendations"]
    pareto_md += [
        "",
        "## 推奨点",
        "",
        f"- **Max ROI:** `{rec['max_ticket_roi']['id']}` ROI={_fmt(rec['max_ticket_roi']['rank7'].get('ticket_roi'))} Hit={_fmt(rec['max_ticket_roi']['rank7'].get('purchase_hit_rate'))}",
        f"- **Max Purchase Hit:** `{rec['max_purchase_hit']['id']}` Hit={_fmt(rec['max_purchase_hit']['rank7'].get('purchase_hit_rate'))} ROI={_fmt(rec['max_purchase_hit']['rank7'].get('ticket_roi'))}",
        f"- **Balanced (Hit+ROI):** `{rec['balanced_hit_roi']['id']}` Hit={_fmt(rec['balanced_hit_roi']['rank7'].get('purchase_hit_rate'))} ROI={_fmt(rec['balanced_hit_roi']['rank7'].get('ticket_roi'))}",
        f"- **M1 baseline:** `{rec['m1_baseline']['id']}` on_pareto={rec['m1_baseline'].get('on_pareto')}",
        "",
        f"**Recommended default (Shadow):** `{report['recommended_default']['id']}`",
        "",
    ]
    paths["pareto"] = out / "v92-pareto-front.md"
    paths["pareto"].write_text("\n".join(pareto_md), encoding="utf-8")

    # Full optimization table
    opt = [
        "# Version92 — Decision Policy Optimization",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        f"n_all={report['n_races']} / n_rank7={report['n_rank7']} / grid={report['grid_size']}",
        "",
        "## 全探索結果（rank7 主表）",
        "",
        "| Policy | Top | Pool | PurchaseHit | ROI | Coverage | Hit | PredHit | Buy | Skip | PnL |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in report["results"]:
        pr, m = r["params"], r["rank7"]
        opt.append(
            f"| `{pr['id']}` | {pr['ticket_top_n']} | {pr['pool_size']} | {_fmt(m.get('purchase_hit_rate'))} | {_fmt(m.get('ticket_roi'))} | {_fmt(m.get('coverage_rate'))} | {_fmt(m.get('hit_rate'))} | {_fmt(m.get('prediction_hit_rate'))} | {_fmt(m.get('buy_rate'))} | {_fmt(m.get('skip_rate'))} | {_fmt(m.get('ticket_pnl'), 1)} |"
        )

    opt += [
        "",
        "## Decision Distribution（推奨 Balanced・rank7）",
        "",
    ]
    bal = report["recommended_default"]["rank7"].get("decision_distribution") or {}
    for k, v in bal.items():
        opt.append(f"- `{k}`: {v}")

    opt += [
        "",
        "## 実装",
        "",
        "- `app/decision/policy_params.py`",
        "- `world_decision(..., rank7_params=)`",
        "- 既定は互換のため **M1 (Top3/Pool5)** のまま。推奨点は Shadow 既定候補として文書化。",
        "",
        "## 関連",
        "",
        "- `v92-pareto-front.md`",
        "- `v92-governance.md`",
        "",
    ]
    paths["opt"] = out / "v92-decision-policy-optimization.md"
    paths["opt"].write_text("\n".join(opt), encoding="utf-8")

    rec_id = report["recommended_default"]["id"]
    gov = [
        "# Version92 — Governance（Decision Policy Optimization）",
        "",
        f"**Date:** {report['generated_at'][:10]}  ",
        f"**Verdict:** **A**（16点探索完了 / Pareto 作成 / 推奨=`{rec_id}`）  ",
        "**Type:** Decision Layer parameter optimization only",
        "",
        "【Decision】",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Action Type | Decision Policy Optimization |",
        "| ADR-008 | **未変更** |",
        "| Architecture / Prediction / Ranking / Confidence / Calibration / World / Trigger | **未変更** |",
        "| Decision Layer params | **探索・文書化** |",
        "| Production default policy change | **No**（M1 互換維持。推奨は Shadow 候補） |",
        "| Production Required | **No** |",
        f"| Expected Next Action | 推奨 `{rec_id}` を Shadow 既定候補として M2 前レビュー（別 Decision）。ADR-008 変更禁止継続 |",
        "",
        "## 推奨サマリ",
        "",
        f"- Max ROI: `{rec['max_ticket_roi']['id']}`",
        f"- Max Purchase Hit: `{rec['max_purchase_hit']['id']}`",
        f"- Balanced: `{rec['balanced_hit_roi']['id']}`",
        "",
        "## 成果物",
        "",
        "- `v92-decision-policy-optimization.md`",
        "- `v92-pareto-front.md`",
        "- `v92-governance.md`",
        "- `_v92-decision-policy-optimization.json`",
        "",
    ]
    paths["gov"] = out / "v92-governance.md"
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
                "recommended": report["recommended_default"],
                "pareto_n": len(report["pareto_front_hit_roi"]),
                "pareto_ids": [p["params"]["id"] for p in report["pareto_front_hit_roi"]],
                "recs": {
                    k: v.get("id")
                    for k, v in report["recommendations"].items()
                    if isinstance(v, dict) and "id" in v
                },
                "paths": {k: str(v) for k, v in paths.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
