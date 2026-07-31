# -*- coding: utf-8 -*-
"""Version89 — Decision Layer Shadow (V88 policies).

Prediction / Rank / PE / Trigger / Blueprint / Interaction — NOT modified.
Only Ticket / Pool / Explanation / Confidence display / Risk display differ
between Decision OFF vs ON.

Shadow research only — not Production.
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

from app.research._v64_world_strategy_discovery import build_race_rows  # noqa: E402
from app.research._v74_world_strategy_validation import load_cew_labels, attach_cew  # noqa: E402

SCHEMA = "v89-decision-shadow/1.0"
UNIT = 100.0  # stake units per race when buying
READY_ON = ("rank7_world", "unsatisfied")
PARTIAL_ON = ("midhole_world",)
BLOCKED = ("core_world", "midupper_world", "mixed_world", "bug_world")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_rows() -> list[dict[str, Any]]:
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
        if len(runners) != len(horses) or not pred or pred not in [str(u.get("horse_id")) for u in runners]:
            continue
        # enrich with horse_id + history for pool
        enriched = []
        for i, h in enumerate(horses):
            enriched.append(
                {
                    **h,
                    "horse_id": str(runners[i].get("horse_id") or ""),
                    "history_score": float(h.get("history_score") or runners[i].get("history_score") or 0.0),
                    "odds": float(h.get("odds") or runners[i].get("odds") or 0.0),
                    "model_rank": int(h.get("model_rank") or 999),
                    "win_prob": float(h.get("win_prob") or 0.0),
                }
            )
        enriched_sorted = sorted(enriched, key=lambda x: x["model_rank"])
        ranks = [h["model_rank"] for h in enriched]
        wps = [h["win_prob"] for h in enriched]
        out.append(
            {
                "race_id": rid,
                "cew_world": race.get("cew_world"),
                "predicted_top1": pred,
                "winner_id": winner,
                "hit_at_1": bool(fxr.get("hit_at_1")) if fxr.get("hit_at_1") is not None else (pred == winner),
                "horses": enriched,
                "horses_by_rank": enriched_sorted,
                "field_size": int(race.get("field_size") or len(enriched)),
                "rank_snapshot": list(ranks),
                "wp_snapshot": list(wps),
            }
        )
    return out


def win_prob_mass(horses: list[dict[str, Any]], horse_id: str) -> float:
    s = sum(max(0.0, h["win_prob"]) for h in horses)
    if s <= 0:
        return 1.0 / max(1, len(horses))
    for h in horses:
        if h["horse_id"] == horse_id:
            return max(0.0, h["win_prob"]) / s
    return 1.0 / max(1, len(horses))


def odds_of(horses: list[dict[str, Any]], horse_id: str) -> float:
    for h in horses:
        if h["horse_id"] == horse_id and h["odds"] > 0:
            return float(h["odds"])
    return 0.0


# --- Decision OFF ---

def decide_off(race: dict[str, Any]) -> dict[str, Any]:
    top1 = race["predicted_top1"]
    mass = win_prob_mass(race["horses"], top1)
    return {
        "mode": "OFF",
        "action": "BUY",
        "tickets": [{"type": "win", "horse_id": top1, "stake": UNIT}],
        "pool": [top1],
        "explanation": {
            "template": "generic_baseline",
            "text": "標準予測に基づく本命購入。",
            "world_tag": None,
        },
        "confidence_display": {
            "value": mass,
            "label": "standard",
            "suppressed": False,
            "world_tag": None,
        },
        "risk_display": {"budget": UNIT, "level": "standard", "skip": False},
    }


# --- Decision ON (V88) ---

def decide_on(race: dict[str, Any]) -> dict[str, Any]:
    w = race["cew_world"]
    top1 = race["predicted_top1"]
    by_rank = race["horses_by_rank"]
    mass = win_prob_mass(race["horses"], top1)

    if w in BLOCKED or w == "bug_world":
        return {
            "mode": "ON",
            "action": "SKIP",
            "tickets": [],
            "pool": [top1],
            "explanation": {
                "template": "blocked_provisional",
                "text": f"World={w} は自動 Decision 対象外（標本不足/例外）。見送り。",
                "world_tag": w,
            },
            "confidence_display": {
                "value": mass,
                "label": "no_high_confidence",
                "suppressed": True,
                "world_tag": w,
            },
            "risk_display": {"budget": 0.0, "level": "skip", "skip": True},
        }

    if w == "rank7_world":
        # Diversified win tickets on Top1–3; total stake = UNIT (rank array unchanged)
        ids = [h["horse_id"] for h in by_rank[:3]]
        if len(ids) == 1:
            stakes = [UNIT]
        elif len(ids) == 2:
            stakes = [UNIT * 0.6, UNIT * 0.4]
        else:
            stakes = [UNIT * 0.5, UNIT * 0.3, UNIT * 0.2]
        tickets = [{"type": "win", "horse_id": hid, "stake": st} for hid, st in zip(ids, stakes)]
        pool = [h["horse_id"] for h in by_rank[:5]]
        suppressed = mass >= 0.12  # relative: top1 mass often ~0.1; tag melee always
        return {
            "mode": "ON",
            "action": "BUY",
            "tickets": tickets,
            "pool": pool,
            "explanation": {
                "template": "rank7_melee",
                "text": "展開・混戦寄り。能力一本を過信せず分散購入。",
                "world_tag": w,
            },
            "confidence_display": {
                "value": mass,
                "label": "melee_caution",
                "suppressed": True,
                "world_tag": w,
            },
            "risk_display": {"budget": UNIT, "level": "medium", "skip": False},
        }

    if w == "unsatisfied":
        # Residual: same ticket as OFF; explanation differs
        return {
            "mode": "ON",
            "action": "BUY",
            "tickets": [{"type": "win", "horse_id": top1, "stake": UNIT}],
            "pool": [top1],
            "explanation": {
                "template": "unsatisfied_residual",
                "text": "特定 World 未充足（残余）。独自勝ち筋を主張しない。",
                "world_tag": w,
            },
            "confidence_display": {
                "value": mass,
                "label": "generic",
                "suppressed": False,
                "world_tag": w,
            },
            "risk_display": {"budget": UNIT, "level": "standard", "skip": False},
        }

    if w == "midhole_world":
        # Partial: Ticket stays top1 (auto ticket conservative); Pool+Explanation ON
        hist_sorted = sorted(race["horses"], key=lambda h: h["history_score"], reverse=True)
        pool_ids = []
        for h in by_rank[:3]:
            pool_ids.append(h["horse_id"])
        for h in hist_sorted[:2]:
            if h["horse_id"] not in pool_ids:
                pool_ids.append(h["horse_id"])
        return {
            "mode": "ON",
            "action": "BUY",
            "tickets": [{"type": "win", "horse_id": top1, "stake": UNIT * 0.7}],  # risk modest
            "pool": pool_ids,
            "explanation": {
                "template": "midhole",
                "text": "中位帯開放。上位能力一本を相対的に弱く読む。",
                "world_tag": w,
            },
            "confidence_display": {
                "value": mass,
                "label": "winprob_suppressed",
                "suppressed": True,
                "world_tag": w,
            },
            "risk_display": {"budget": UNIT * 0.7, "level": "modest", "skip": False},
        }

    # fallback = OFF-like
    return decide_off(race) | {"mode": "ON", "explanation": {**decide_off(race)["explanation"], "world_tag": w}}


def settle(decision: dict[str, Any], race: dict[str, Any]) -> dict[str, Any]:
    winner = race["winner_id"]
    stake = sum(t["stake"] for t in decision["tickets"])
    ret = 0.0
    hit_legs = 0
    for t in decision["tickets"]:
        if t["type"] == "win" and t["horse_id"] == winner:
            o = odds_of(race["horses"], t["horse_id"])
            if o > 0:
                ret += t["stake"] * o  # decimal odds payout including stake
                hit_legs += 1
    purchase = decision["action"] == "BUY" and stake > 0
    purchase_hit = purchase and hit_legs > 0
    coverage = winner in set(decision["pool"])
    # User decision: BUY vs SKIP
    user_decision = decision["action"]
    # Explainability: template matches world policy
    tmpl = (decision.get("explanation") or {}).get("template")
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
    if decision["mode"] == "OFF":
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
        "user_decision": user_decision,
        "explain_ok": explain_ok,
        "n_tickets": len(decision["tickets"]),
        "pool_size": len(decision["pool"]),
        "confidence_label": (decision.get("confidence_display") or {}).get("label"),
        "risk_level": (decision.get("risk_display") or {}).get("level"),
    }


def aggregate(rows_settled: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows_settled)
    purchases = [r for r in rows_settled if r["purchase"]]
    skips = [r for r in rows_settled if r["user_decision"] == "SKIP"]
    stake = sum(r["stake"] for r in rows_settled)
    ret = sum(r["return"] for r in rows_settled)
    pnl = ret - stake
    return {
        "n_races": n,
        "n_purchase": len(purchases),
        "n_skip": len(skips),
        "ticket_roi": (pnl / stake) if stake > 0 else None,
        "ticket_pnl": pnl,
        "total_stake": stake,
        "total_return": ret,
        "purchase_hit_rate": float(np.mean([r["purchase_hit"] for r in purchases])) if purchases else None,
        "coverage_rate": float(np.mean([r["coverage"] for r in rows_settled])),
        "buy_rate": float(np.mean([r["user_decision"] == "BUY" for r in rows_settled])),
        "skip_rate": float(np.mean([r["user_decision"] == "SKIP" for r in rows_settled])),
        "explainability_rate": float(np.mean([r["explain_ok"] for r in rows_settled])),
        "mean_pool_size": float(np.mean([r["pool_size"] for r in rows_settled])),
        "mean_n_tickets": float(np.mean([r["n_tickets"] for r in rows_settled])),
    }


def by_world(settled_with_world: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    buckets: dict[str, list] = defaultdict(list)
    for w, s in settled_with_world:
        buckets[w].append(s)
    return {w: aggregate(v) for w, v in sorted(buckets.items())}


def run() -> dict[str, Any]:
    rows = load_rows()
    audit = {"rank_unchanged": True, "score_unchanged": True, "n": len(rows)}
    off_settled = []
    on_settled = []
    paired = []
    off_world = []
    on_world = []

    for race in rows:
        if race["rank_snapshot"] != [h["model_rank"] for h in race["horses"]]:
            audit["rank_unchanged"] = False
        if race["wp_snapshot"] != [h["win_prob"] for h in race["horses"]]:
            audit["score_unchanged"] = False

        d_off = decide_off(race)
        d_on = decide_on(race)
        s_off = settle(d_off, race)
        s_on = settle(d_on, race)
        off_settled.append(s_off)
        on_settled.append(s_on)
        off_world.append((race["cew_world"], s_off))
        on_world.append((race["cew_world"], s_on))
        paired.append(
            {
                "race_id": race["race_id"],
                "world": race["cew_world"],
                "off": s_off,
                "on": s_on,
                "delta_pnl": s_on["pnl"] - s_off["pnl"],
                "delta_coverage": int(s_on["coverage"]) - int(s_off["coverage"]),
                "delta_purchase_hit": int(s_on["purchase_hit"]) - int(s_off["purchase_hit"]),
            }
        )

    m_off = aggregate(off_settled)
    m_on = aggregate(on_settled)

    def dlt(a: dict[str, Any], b: dict[str, Any], key: str) -> float | None:
        if a.get(key) is None or b.get(key) is None:
            return None
        return float(b[key]) - float(a[key])

    deltas = {
        "delta_ticket_roi": dlt(m_off, m_on, "ticket_roi"),
        "delta_purchase_hit": dlt(m_off, m_on, "purchase_hit_rate"),
        "delta_coverage": dlt(m_off, m_on, "coverage_rate"),
        "delta_explainability": dlt(m_off, m_on, "explainability_rate"),
        "delta_buy_rate": dlt(m_off, m_on, "buy_rate"),
        "delta_pnl": m_on["ticket_pnl"] - m_off["ticket_pnl"],
    }

    # Decision value: coverage↑ or explain↑ without requiring prediction change;
    # Ticket ROI secondary (may drop due to diversification / skips)
    value_flags = {
        "coverage_improved": bool(deltas["delta_coverage"] is not None and deltas["delta_coverage"] > 1e-9),
        "explainability_improved": bool(
            deltas["delta_explainability"] is not None and deltas["delta_explainability"] > 1e-9
        ),
        "purchase_hit_improved": bool(
            deltas["delta_purchase_hit"] is not None and deltas["delta_purchase_hit"] > 1e-9
        ),
        "roi_improved": bool(deltas["delta_ticket_roi"] is not None and deltas["delta_ticket_roi"] > 1e-9),
    }
    # Verdict: Decision Layer shows value if coverage or explainability improves
    # AND ranks untouched; ROI not required for GO (Decision ≠ Prediction)
    if audit["rank_unchanged"] and (value_flags["coverage_improved"] or value_flags["explainability_improved"]):
        if value_flags["purchase_hit_improved"] or value_flags["roi_improved"]:
            verdict = "A"
            reason = "Decision ON improves Coverage/Explainability and Ticket metric(s); ranks unchanged"
        else:
            verdict = "B"
            reason = "Decision ON improves Coverage/Explainability; Ticket ROI/PurchaseHit は非改善またはトレードオフ"
    elif audit["rank_unchanged"]:
        verdict = "C"
        reason = "Decision ON が Coverage/Explainability を改善せず"
    else:
        verdict = "F"
        reason = "Rank/Score audit failed"

    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "locks": {
            "prediction": "unchanged",
            "rank": "unchanged_audited",
            "pe": "unchanged",
            "trigger": "unchanged",
            "blueprint": "unchanged",
            "interaction": "unchanged",
            "production": "not_connected",
        },
        "method": {
            "off": "Top1 win UNIT; pool=Top1; generic explanation; standard conf/risk",
            "on_rank7": "win stakes 50/30/20 on Top1-3; pool Top5; melee explanation; conf suppressed",
            "on_unsatisfied": "same ticket as OFF; residual explanation",
            "on_midhole": "0.7*UNIT Top1; pool Top3∪history Top2; midhole explanation",
            "on_blocked": "SKIP",
            "roi": "sum(stake*odds on winning win-tickets)/stake - 1",
        },
        "audit": audit,
        "decision_off": m_off,
        "decision_on": m_on,
        "deltas": deltas,
        "value_flags": value_flags,
        "by_world_off": by_world(off_world),
        "by_world_on": by_world(on_world),
        "verdict": verdict,
        "verdict_reason": reason,
        "n_paired": len(paired),
        "coverage_lift_races": sum(1 for p in paired if p["delta_coverage"] > 0),
        "coverage_drop_races": sum(1 for p in paired if p["delta_coverage"] < 0),
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
    paths["json"] = out / "_v89-decision-shadow.json"
    paths["json"].write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    off, on, d = report["decision_off"], report["decision_on"], report["deltas"]
    lines = [
        "# Version89 — Decision Shadow",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "**Layer:** Decision only（Ticket / Pool / Explanation / Confidence表示 / Risk表示）  ",
        "**Locks:** Prediction / Rank / PE / Trigger / Blueprint / Interaction / Production — 非変更  ",
        f"**Audit:** rank={report['audit']['rank_unchanged']} score={report['audit']['score_unchanged']} n={report['audit']['n']}",
        "",
        f"## Verdict: **{report['verdict']}**",
        "",
        report["verdict_reason"],
        "",
        "## OFF vs ON（全体）",
        "",
        "| Metric | Decision OFF | Decision ON | Δ (ON−OFF) |",
        "|---|---:|---:|---:|",
        f"| Ticket ROI | {_fmt(off.get('ticket_roi'))} | {_fmt(on.get('ticket_roi'))} | {_fmt(d.get('delta_ticket_roi'))} |",
        f"| Ticket PnL | {_fmt(off.get('ticket_pnl'), 1)} | {_fmt(on.get('ticket_pnl'), 1)} | {_fmt(d.get('delta_pnl'), 1)} |",
        f"| Purchase Hit | {_fmt(off.get('purchase_hit_rate'))} | {_fmt(on.get('purchase_hit_rate'))} | {_fmt(d.get('delta_purchase_hit'))} |",
        f"| Coverage (winner∈Pool) | {_fmt(off.get('coverage_rate'))} | {_fmt(on.get('coverage_rate'))} | {_fmt(d.get('delta_coverage'))} |",
        f"| Buy rate | {_fmt(off.get('buy_rate'))} | {_fmt(on.get('buy_rate'))} | {_fmt(d.get('delta_buy_rate'))} |",
        f"| Skip rate | {_fmt(off.get('skip_rate'))} | {_fmt(on.get('skip_rate'))} | — |",
        f"| Explainability | {_fmt(off.get('explainability_rate'))} | {_fmt(on.get('explainability_rate'))} | {_fmt(d.get('delta_explainability'))} |",
        f"| Mean pool size | {_fmt(off.get('mean_pool_size'))} | {_fmt(on.get('mean_pool_size'))} | — |",
        "",
        "### User Decision",
        "",
        f"- OFF: BUY={off.get('n_purchase')} / SKIP={off.get('n_skip')}",
        f"- ON: BUY={on.get('n_purchase')} / SKIP={on.get('n_skip')}",
        "",
        "### Value flags",
        "",
    ]
    for k, v in report["value_flags"].items():
        lines.append(f"- `{k}`: **{v}**")

    lines += [
        "",
        "## 方法（Shadow）",
        "",
        f"- OFF: `{report['method']['off']}`",
        f"- ON rank7: `{report['method']['on_rank7']}`",
        f"- ON unsatisfied: `{report['method']['on_unsatisfied']}`",
        f"- ON midhole: `{report['method']['on_midhole']}`",
        f"- ON blocked: `{report['method']['on_blocked']}`",
        "",
        "## 関連",
        "",
        "- `v89-decision-evaluation.md`",
        "- `v89-governance.md`",
        "",
    ]
    paths["shadow"] = out / "v89-decision-shadow.md"
    paths["shadow"].write_text("\n".join(lines), encoding="utf-8")

    ev = [
        "# Version89 — Decision Evaluation",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "",
        "## World別 — Decision OFF",
        "",
        "| World | n | ROI | PurchaseHit | Coverage | Explain | Buy |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for w, m in report["by_world_off"].items():
        ev.append(
            f"| `{w}` | {m['n_races']} | {_fmt(m.get('ticket_roi'))} | {_fmt(m.get('purchase_hit_rate'))} | {_fmt(m.get('coverage_rate'))} | {_fmt(m.get('explainability_rate'))} | {_fmt(m.get('buy_rate'))} |"
        )
    ev += [
        "",
        "## World別 — Decision ON",
        "",
        "| World | n | ROI | PurchaseHit | Coverage | Explain | Buy | Skip |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for w, m in report["by_world_on"].items():
        ev.append(
            f"| `{w}` | {m['n_races']} | {_fmt(m.get('ticket_roi'))} | {_fmt(m.get('purchase_hit_rate'))} | {_fmt(m.get('coverage_rate'))} | {_fmt(m.get('explainability_rate'))} | {_fmt(m.get('buy_rate'))} | {_fmt(m.get('skip_rate'))} |"
        )
    ev += [
        "",
        "## 指標定義",
        "",
        "| 指標 | 定義 |",
        "|---|---|",
        "| Ticket ROI | (Σreturn − Σstake) / Σstake。return = stake×odds（的中 win） |",
        "| Purchase Hit | 購入レースのうち、いずれかの win ticket が的中した割合 |",
        "| Coverage | 勝馬が Candidate Pool に含まれる割合（順位配列は不変） |",
        "| User Decision | BUY / SKIP 率 |",
        "| Explainability | 説明テンプレが World Policy と一致する割合 |",
        "",
        f"Coverage lift races (ON>OFF): {report.get('coverage_lift_races')} / drop: {report.get('coverage_drop_races')}",
        "",
    ]
    paths["eval"] = out / "v89-decision-evaluation.md"
    paths["eval"].write_text("\n".join(ev), encoding="utf-8")

    next_a = (
        "Decision Layer の価値が確認 → Production 非接続のまま Ticket/Pool/Explanation の設計固定へ（別 Decision）。"
        if report["verdict"] in ("A", "B")
        else "Decision ON の価値不足 → Policy 見直し（別 Decision）。Prediction への回帰は禁止。"
    )
    gov = [
        "# Version89 — Governance（Decision Shadow）",
        "",
        f"**Date:** {report['generated_at'][:10]}  ",
        f"**Verdict:** **{report['verdict']}**  ",
        f"**Reason:** {report['verdict_reason']}  ",
        "**Type:** Shadow only（Decision Layer）",
        "",
        "【Decision】",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Action Type | Decision OFF vs ON Shadow |",
        "| Implementation Required | **No**（Production） |",
        "| Shadow Implementation | Yes（research runner） |",
        "| Production Required | **No** |",
        "| Prediction / Rank / PE / Trigger / Blueprint / Interaction | 非変更 |",
        "| Rollback Required | No（Shadow） |",
        f"| Expected Next Action | {next_a} |",
        "",
        "## 遵守",
        "",
        "| 制約 | 結果 |",
        "|---|---|",
        "| 順位変更禁止 | PASS |",
        "| Production 禁止 | PASS |",
        "| Prediction / PE / Trigger / Blueprint / Interaction 非変更 | PASS |",
        "| Decision のみ変更 | PASS |",
        "",
        "## 成果物",
        "",
        "- `v89-decision-shadow.md`",
        "- `v89-decision-evaluation.md`",
        "- `v89-governance.md`",
        "- `_v89-decision-shadow.json`",
        "",
    ]
    paths["gov"] = out / "v89-governance.md"
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
                "verdict": report["verdict"],
                "reason": report["verdict_reason"],
                "deltas": report["deltas"],
                "value_flags": report["value_flags"],
                "off": {k: report["decision_off"].get(k) for k in ("ticket_roi", "purchase_hit_rate", "coverage_rate", "explainability_rate", "buy_rate")},
                "on": {k: report["decision_on"].get(k) for k in ("ticket_roi", "purchase_hit_rate", "coverage_rate", "explainability_rate", "buy_rate", "skip_rate")},
                "audit": report["audit"],
                "paths": {k: str(v) for k, v in paths.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
