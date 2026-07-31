# -*- coding: utf-8 -*-
"""Version97 — Affinity Decision Value Shadow (research only).

Question: Does Near Miss Affinity add statistical value to Decision
vs baseline unsatisfied Policy?

Locks: Prediction / Trigger / CEW / World / product Decision implementation.
Shadow policies are simulated in this runner only (実装禁止).
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))

from app.decision.dto import (  # noqa: E402
    ConfidenceDisplayDTO,
    DecisionDTO,
    ExplanationDTO,
    PredictionView,
    RiskDisplayDTO,
    TicketLeg,
)
from app.decision.policies import UNIT  # noqa: E402
from app.decision.service import build_prediction_view  # noqa: E402
from app.research._v91_decision_layer_m1_shadow import (  # noqa: E402
    aggregate,
    load_corpus_rows,
    settle,
)

SCHEMA = "v97-affinity-decision-value-shadow/1.0"
AFFINITY_WORLDS = ("core_world", "midupper_world", "midhole_world", "rank7_world")
NEAR_PRIORITY = AFFINITY_WORLDS
HIGH_SUPPRESS = {"core_world", "midupper_world"}
MID_SUPPRESS = {"midhole_world", "rank7_world"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_dual() -> dict[str, dict[str, Any]]:
    path = ROOT / "docs/implementation/w-s1-dual-eval-rows.jsonl"
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            out[str(r["race_id"])] = r
    return out


def near_miss_meta(trace: dict[str, Any]) -> dict[str, Any] | None:
    """Return Near Miss metadata or None if Pure Residual / not near miss."""
    near_worlds = []
    for w in AFFINITY_WORLDS:
        t = (trace or {}).get(w) or {}
        if t.get("must") and t.get("exclude"):
            near_worlds.append(w)
    if not near_worlds:
        return None
    primary = None
    for w in NEAR_PRIORITY:
        if w in near_worlds:
            primary = w
            break
    # must_affinity per world (research definition = V96)
    must_n = {"core_world": 2, "midupper_world": 3, "midhole_world": 2, "rank7_world": 3}
    affinity = {}
    for w in AFFINITY_WORLDS:
        t = (trace or {}).get(w) or {}
        gaps = list(t.get("must_gaps") or [])
        if t.get("must"):
            affinity[w] = 1.0
        else:
            affinity[w] = max(0.0, (must_n[w] - len(gaps)) / must_n[w])
    return {
        "residual_class": "NEAR_MISS",
        "near_world": primary,
        "near_worlds": near_worlds,
        "affinity": affinity,
        "affinity_top": max(AFFINITY_WORLDS, key=lambda w: (affinity[w], -NEAR_PRIORITY.index(w))),
    }


def baseline_unsatisfied(view: PredictionView) -> DecisionDTO:
    """V95/V88 unsatisfied conservative Policy (Shadow simulation)."""
    top1 = view.predicted_top1
    by_rank = sorted(view.horses, key=lambda h: int(h.get("model_rank") or 999))
    pool = tuple(str(h.get("horse_id") or "") for h in by_rank[:1] if h.get("horse_id"))
    mass = float(by_rank[0].get("win_prob") or 0.0) if by_rank else 0.0
    return DecisionDTO(
        mode="ON",
        action="BUY",
        world_id="unsatisfied",
        tickets=(TicketLeg(type="win", horse_id=top1, stake=UNIT),),
        pool=pool or (top1,),
        explanation=ExplanationDTO(
            template="unsatisfied_residual",
            text="特定 World 未充足（残余）。独自勝ち筋を主張しない。",
            world_tag="unsatisfied",
        ),
        confidence_display=ConfidenceDisplayDTO(
            value=mass, label="generic", suppressed=False, world_tag="unsatisfied"
        ),
        risk_display=RiskDisplayDTO(budget=UNIT, level="standard", skip=False),
        prediction_fingerprint=view.prediction_fingerprint,
        flag_snapshot={"shadow": True, "policy": "baseline_unsatisfied"},
    )


def affinity_aware_near_miss(view: PredictionView, meta: dict[str, Any]) -> DecisionDTO:
    """V95 Risk profiles as actionable Shadow Decision (Ticket stays conservative band).

    HIGH suppress (core/midupper): SKIP
    MID suppress (midhole/rank7): BUY stake=0.5×UNIT
    Never copies Positive World Ticket Strategy (DL-C6).
    """
    top1 = view.predicted_top1
    by_rank = sorted(view.horses, key=lambda h: int(h.get("model_rank") or 999))
    pool = tuple(str(h.get("horse_id") or "") for h in by_rank[:1] if h.get("horse_id")) or (top1,)
    mass = float(by_rank[0].get("win_prob") or 0.0) if by_rank else 0.0
    nw = meta["near_world"]
    tmpl = f"near_miss:{nw}"
    text = f"{nw} 仮説に近いが Exclusion により未 MATCH。勝ち筋確定ではない。"

    if nw in HIGH_SUPPRESS:
        return DecisionDTO(
            mode="ON",
            action="SKIP",
            world_id="unsatisfied",
            tickets=(),
            pool=pool,
            explanation=ExplanationDTO(template=tmpl, text=text, world_tag="unsatisfied"),
            confidence_display=ConfidenceDisplayDTO(
                value=mass, label="near_miss_suppressed", suppressed=True, world_tag=nw
            ),
            risk_display=RiskDisplayDTO(budget=0.0, level="high_suppress", skip=True),
            prediction_fingerprint=view.prediction_fingerprint,
            flag_snapshot={
                "shadow": True,
                "policy": "affinity_aware",
                "near_world": nw,
                "risk": "high_suppress",
            },
        )

    # MID suppress — still BUY, reduced stake only (no World Ticket copy)
    stake = UNIT * 0.5
    return DecisionDTO(
        mode="ON",
        action="BUY",
        world_id="unsatisfied",
        tickets=(TicketLeg(type="win", horse_id=top1, stake=stake),),
        pool=pool,
        explanation=ExplanationDTO(template=tmpl, text=text, world_tag="unsatisfied"),
        confidence_display=ConfidenceDisplayDTO(
            value=mass, label="near_miss_caution", suppressed=True, world_tag=nw
        ),
        risk_display=RiskDisplayDTO(budget=stake, level="mid_suppress", skip=False),
        prediction_fingerprint=view.prediction_fingerprint,
        flag_snapshot={
            "shadow": True,
            "policy": "affinity_aware",
            "near_world": nw,
            "risk": "mid_suppress",
        },
    )


def bootstrap_delta_roi(
    base_settled: list[dict[str, Any]],
    sh_settled: list[dict[str, Any]],
    n_boot: int = 2000,
    seed: int = 42,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    n = len(base_settled)
    if n == 0:
        return {"status": "empty"}
    deltas = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        b_stake = sum(base_settled[i]["stake"] for i in idx)
        s_stake = sum(sh_settled[i]["stake"] for i in idx)
        b_pnl = sum(base_settled[i]["pnl"] for i in idx)
        s_pnl = sum(sh_settled[i]["pnl"] for i in idx)
        b_roi = (b_pnl / b_stake) if b_stake > 0 else 0.0
        s_roi = (s_pnl / s_stake) if s_stake > 0 else 0.0
        # If shadow stakes all 0 (all skip), define ROI delta as -baseline_roi
        # (avoiding capital) → use pnl delta / baseline_stake as capital-efficiency proxy
        if s_stake <= 0:
            deltas.append((-b_pnl / b_stake) if b_stake > 0 else 0.0)  # avoided loss rate
        else:
            deltas.append(s_roi - b_roi)
    arr = np.array(deltas, dtype=float)
    lo, hi = np.quantile(arr, [0.025, 0.975])
    return {
        "n_boot": n_boot,
        "delta_roi_mean": float(arr.mean()),
        "delta_roi_ci95": [float(lo), float(hi)],
        "ci_excludes_0_positive": bool(lo > 0),
        "ci_excludes_0_negative": bool(hi < 0),
        "note": "If shadow all-skip in a draw, delta uses avoided-loss vs baseline stake",
    }


def bootstrap_delta_metric(
    base_settled: list[dict[str, Any]],
    sh_settled: list[dict[str, Any]],
    metric: str,
    n_boot: int = 2000,
    seed: int = 43,
) -> dict[str, Any]:
    """Bootstrap delta for purchase_hit_rate or buy_rate / coverage_rate."""
    rng = np.random.default_rng(seed)
    n = len(base_settled)
    deltas = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        bs = [base_settled[i] for i in idx]
        ss = [sh_settled[i] for i in idx]
        mb, ms = aggregate(bs), aggregate(ss)
        vb, vs = mb.get(metric), ms.get(metric)
        if vb is None and vs is None:
            deltas.append(0.0)
        elif vb is None:
            deltas.append(float(vs))
        elif vs is None:
            # shadow no purchases → purchase_hit undefined; treat as 0 delta penalty
            deltas.append(0.0 - float(vb))
        else:
            deltas.append(float(vs) - float(vb))
    arr = np.array(deltas, dtype=float)
    lo, hi = np.quantile(arr, [0.025, 0.975])
    return {
        "metric": metric,
        "delta_mean": float(arr.mean()),
        "ci95": [float(lo), float(hi)],
        "ci_excludes_0_positive": bool(lo > 0),
        "ci_excludes_0_negative": bool(hi < 0),
    }


def verdict_from(
    m_base: dict[str, Any],
    m_sh: dict[str, Any],
    boot_roi: dict[str, Any],
    boot_hit: dict[str, Any],
    fp_ok: bool,
) -> dict[str, Any]:
    if not fp_ok:
        return {
            "verdict": "INVALID",
            "affinity_has_decision_value": False,
            "reason": "Prediction fingerprint 不一致 — Shadow 無効",
        }

    d_roi = None
    if m_base.get("ticket_roi") is not None and m_sh.get("ticket_roi") is not None:
        d_roi = float(m_sh["ticket_roi"]) - float(m_base["ticket_roi"])
    elif m_sh.get("ticket_roi") is None and (m_base.get("total_stake") or 0) > 0:
        # all skip shadow → value as capital preservation (pnl improvement if base was negative)
        d_roi = None

    d_pnl = float(m_sh["ticket_pnl"]) - float(m_base["ticket_pnl"])
    hit_pos = bool(boot_hit.get("ci_excludes_0_positive"))
    roi_pos = bool(boot_roi.get("ci_excludes_0_positive"))
    roi_neg = bool(boot_roi.get("ci_excludes_0_negative"))

    # Statistical value for Decision:
    # VALUE if ROI CI >0 OR (PnL↑ and not ROI CI <0) with actionable divergence
    buy_div = abs(float(m_sh.get("buy_rate") or 0) - float(m_base.get("buy_rate") or 0)) > 1e-9

    if not buy_div:
        return {
            "verdict": "NO_VALUE",
            "affinity_has_decision_value": False,
            "reason": "Affinity-aware が Baseline と購入行動が同一 — Decision 差分なし",
        }

    if roi_pos or (d_pnl > 0 and not roi_neg and (boot_roi.get("delta_roi_mean") or 0) > 0):
        return {
            "verdict": "VALUE",
            "affinity_has_decision_value": True,
            "reason": (
                "Near Miss Affinity Risk 抑制が Baseline より Ticket PnL/ROI を改善"
                + ("（ROI CI が 0 を上回る）" if roi_pos else "（点推定改善・CI は境界）")
            ),
            "delta_pnl": d_pnl,
            "delta_roi_point": d_roi,
        }

    if roi_neg and d_pnl < 0:
        return {
            "verdict": "NO_VALUE",
            "affinity_has_decision_value": False,
            "reason": "Affinity-aware は ROI/PnL を統計的に悪化",
            "delta_pnl": d_pnl,
        }

    # Purchase Hit が有意に悪化し、PnL も悪化 → Decision 価値なし
    if boot_hit.get("ci_excludes_0_negative") and d_pnl < 0:
        return {
            "verdict": "NO_VALUE",
            "affinity_has_decision_value": False,
            "reason": (
                "Affinity Risk 抑制は Buy を大きく減らすが、"
                "残購入の Purchase Hit が有意に悪化し Ticket PnL も悪化。"
                " Near Miss Affinity の高抑制 SKIP は本コーパスで Decision 価値を示さない。"
            ),
            "delta_pnl": d_pnl,
            "delta_roi_point": d_roi,
        }

    return {
        "verdict": "INCONCLUSIVE",
        "affinity_has_decision_value": False,
        "reason": (
            "購入行動は変わるが、ROI/Hit の統計的優位が未確定"
            f"（ROI CI={boot_roi.get('delta_roi_ci95')}, Hit CI={boot_hit.get('ci95')}）"
        ),
        "delta_pnl": d_pnl,
        "purchase_hit_ci_positive": hit_pos,
    }


def run() -> dict[str, Any]:
    rows = load_corpus_rows()
    dual = load_dual()

    base_nm, sh_nm = [], []
    by_near: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    stability = {
        "action_agree": 0,
        "n": 0,
        "template_changed": 0,
        "fp_ok": 0,
        "transitions": Counter(),
    }
    per_race = []

    n_unsat = 0
    n_near = 0
    n_pure = 0

    for race in rows:
        if race["cew_world"] != "unsatisfied":
            continue
        n_unsat += 1
        rid = race["race_id"]
        trace = (dual.get(rid) or {}).get("decision_trace") or {}
        meta = near_miss_meta(trace)
        if meta is None:
            n_pure += 1
            continue
        n_near += 1

        view = build_prediction_view(
            race_id=rid,
            world_id="unsatisfied",
            predicted_top1=race["predicted_top1"],
            winner_id=race["winner_id"],
            horses=race["horses"],
            field_size=race["field_size"],
        )
        d_base = baseline_unsatisfied(view)
        d_sh = affinity_aware_near_miss(view, meta)

        fp_ok = (
            d_base.prediction_fingerprint
            == d_sh.prediction_fingerprint
            == view.prediction_fingerprint
        )
        if fp_ok:
            stability["fp_ok"] += 1
        stability["n"] += 1
        if d_base.action == d_sh.action:
            stability["action_agree"] += 1
        else:
            stability["transitions"][f"{d_base.action}->{d_sh.action}"] += 1
        tb = d_base.explanation.template if d_base.explanation else None
        ts = d_sh.explanation.template if d_sh.explanation else None
        if tb != ts:
            stability["template_changed"] += 1

        # ranks unchanged
        assert race["rank_snapshot"] == [h["model_rank"] for h in race["horses"]]

        s_b = settle(d_base, race)
        s_s = settle(d_sh, race)
        # explain_ok for shadow templates: treat near_miss:* as intentional
        s_b["explain_ok"] = tb == "unsatisfied_residual"
        s_s["explain_ok"] = bool(ts and str(ts).startswith("near_miss:"))
        s_b["near_world"] = meta["near_world"]
        s_s["near_world"] = meta["near_world"]

        base_nm.append(s_b)
        sh_nm.append(s_s)
        by_near[meta["near_world"]].append((s_b, s_s))
        per_race.append(
            {
                "race_id": rid,
                "near_world": meta["near_world"],
                "affinity": meta["affinity"],
                "baseline_action": d_base.action,
                "shadow_action": d_sh.action,
                "baseline_pnl": s_b["pnl"],
                "shadow_pnl": s_s["pnl"],
                "fp_ok": fp_ok,
            }
        )

    m_base = aggregate(base_nm)
    m_sh = aggregate(sh_nm)
    boot_roi = bootstrap_delta_roi(base_nm, sh_nm)
    boot_hit = bootstrap_delta_metric(base_nm, sh_nm, "purchase_hit_rate")
    boot_cov = bootstrap_delta_metric(base_nm, sh_nm, "coverage_rate", seed=44)
    boot_buy = bootstrap_delta_metric(base_nm, sh_nm, "buy_rate", seed=45)

    by_near_metrics = {}
    for nw, pairs in by_near.items():
        bb = [p[0] for p in pairs]
        ss = [p[1] for p in pairs]
        mb, ms = aggregate(bb), aggregate(ss)
        by_near_metrics[nw] = {
            "n": len(pairs),
            "baseline": mb,
            "affinity_aware": ms,
            "delta_roi": (
                None
                if mb.get("ticket_roi") is None or ms.get("ticket_roi") is None
                else float(ms["ticket_roi"]) - float(mb["ticket_roi"])
            ),
            "delta_pnl": float(ms["ticket_pnl"]) - float(mb["ticket_pnl"]),
            "delta_buy_rate": float(ms["buy_rate"]) - float(mb["buy_rate"]),
            "delta_purchase_hit": (
                None
                if mb.get("purchase_hit_rate") is None or ms.get("purchase_hit_rate") is None
                else float(ms["purchase_hit_rate"]) - float(mb["purchase_hit_rate"])
            ),
        }

    fp_ok = stability["fp_ok"] == stability["n"] and stability["n"] > 0
    verd = verdict_from(m_base, m_sh, boot_roi, boot_hit, fp_ok)

    stability_out = {
        "n_near_miss": stability["n"],
        "prediction_fingerprint_identical": fp_ok,
        "action_agreement_rate": stability["action_agree"] / stability["n"] if stability["n"] else None,
        "template_change_rate": stability["template_changed"] / stability["n"] if stability["n"] else None,
        "action_transitions": dict(stability["transitions"]),
        "decision_stability_note": (
            "低 action_agreement は Risk 抑制が効いていることを示す。"
            " Prediction 安定（fingerprint）が Decision Stability の必須条件。"
        ),
    }

    deltas = {
        "delta_ticket_roi": (
            None
            if m_base.get("ticket_roi") is None or m_sh.get("ticket_roi") is None
            else float(m_sh["ticket_roi"]) - float(m_base["ticket_roi"])
        ),
        "delta_ticket_pnl": float(m_sh["ticket_pnl"]) - float(m_base["ticket_pnl"]),
        "delta_purchase_hit": (
            None
            if m_base.get("purchase_hit_rate") is None or m_sh.get("purchase_hit_rate") is None
            else float(m_sh["purchase_hit_rate"]) - float(m_base["purchase_hit_rate"])
        ),
        "delta_coverage": float(m_sh["coverage_rate"]) - float(m_base["coverage_rate"]),
        "delta_buy_rate": float(m_sh["buy_rate"]) - float(m_base["buy_rate"]),
    }

    report = {
        "schema": SCHEMA,
        "generated_at": _now(),
        "purpose": "Evaluate whether Near Miss Affinity has statistical Decision value",
        "locks": ["Prediction", "Trigger", "CEW", "World", "product Decision impl"],
        "scope": {
            "population": "Near Miss only",
            "n_unsatisfied": n_unsat,
            "n_near_miss": n_near,
            "n_pure_residual_excluded": n_pure,
        },
        "policies": {
            "baseline": "unsatisfied conservative BUY Top1 UNIT",
            "affinity_aware": {
                "core_world/midupper_world": "SKIP (high_suppress)",
                "midhole_world/rank7_world": "BUY stake=0.5×UNIT (mid_suppress)",
                "forbidden": "Positive World Ticket Strategy copy",
            },
        },
        "baseline": m_base,
        "affinity_aware": m_sh,
        "deltas": deltas,
        "bootstrap": {
            "roi": boot_roi,
            "purchase_hit": boot_hit,
            "coverage": boot_cov,
            "buy_rate": boot_buy,
        },
        "by_near_world": by_near_metrics,
        "decision_stability": stability_out,
        "verdict": verd,
        "per_race_sample": per_race[:12],
    }
    return report


def write_docs(report: dict[str, Any]) -> dict[str, str]:
    docs = ROOT / "docs/research"
    docs.mkdir(parents=True, exist_ok=True)
    jpath = docs / "_v97-affinity-decision-value-shadow.json"
    jpath.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def fmt(x: Any) -> str:
        if x is None:
            return "—"
        if isinstance(x, float):
            return f"{x:.4f}"
        return str(x)

    b, s = report["baseline"], report["affinity_aware"]
    d = report["deltas"]
    v = report["verdict"]
    st = report["decision_stability"]
    boot = report["bootstrap"]

    main = [
        "# Version97 — Affinity Decision Value Shadow",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        f"**Scope:** Near Miss only (n={report['scope']['n_near_miss']})  ",
        "**Locks:** Prediction / Trigger / CEW / World · **製品実装禁止**  ",
        "**Question:** Affinity は Decision に統計的価値を持つか？",
        "",
        "## Verdict",
        "",
        f"**`{v['verdict']}`** — affinity_has_decision_value = **{v['affinity_has_decision_value']}**",
        "",
        v.get("reason") or "",
        "",
        "## Policies",
        "",
        f"- Baseline: `{report['policies']['baseline']}`",
        f"- Affinity-aware: `{json.dumps(report['policies']['affinity_aware'], ensure_ascii=False)}`",
        "",
        "## Metrics（Near Miss）",
        "",
        "| Metric | Baseline | Affinity-aware | Δ |",
        "|---|---:|---:|---:|",
        f"| Ticket ROI | {fmt(b.get('ticket_roi'))} | {fmt(s.get('ticket_roi'))} | {fmt(d.get('delta_ticket_roi'))} |",
        f"| Ticket PnL | {fmt(b.get('ticket_pnl'))} | {fmt(s.get('ticket_pnl'))} | {fmt(d.get('delta_ticket_pnl'))} |",
        f"| Purchase Hit | {fmt(b.get('purchase_hit_rate'))} | {fmt(s.get('purchase_hit_rate'))} | {fmt(d.get('delta_purchase_hit'))} |",
        f"| Coverage | {fmt(b.get('coverage_rate'))} | {fmt(s.get('coverage_rate'))} | {fmt(d.get('delta_coverage'))} |",
        f"| Buy Rate | {fmt(b.get('buy_rate'))} | {fmt(s.get('buy_rate'))} | {fmt(d.get('delta_buy_rate'))} |",
        f"| Skip Rate | {fmt(b.get('skip_rate'))} | {fmt(s.get('skip_rate'))} | — |",
        "",
        "## Bootstrap（統計）",
        "",
        f"- ΔROI mean={fmt(boot['roi'].get('delta_roi_mean'))} CI95={boot['roi'].get('delta_roi_ci95')} "
        f"excludes0+={boot['roi'].get('ci_excludes_0_positive')}",
        f"- ΔPurchaseHit mean={fmt(boot['purchase_hit'].get('delta_mean'))} CI95={boot['purchase_hit'].get('ci95')}",
        f"- ΔBuyRate mean={fmt(boot['buy_rate'].get('delta_mean'))} CI95={boot['buy_rate'].get('ci95')}",
        "",
        "## Decision Stability",
        "",
        f"- Prediction fingerprint identical: **{st['prediction_fingerprint_identical']}**",
        f"- Action agreement: **{fmt(st['action_agreement_rate'])}**",
        f"- Template change rate: **{fmt(st['template_change_rate'])}**",
        f"- Transitions: `{st['action_transitions']}`",
        "",
        st["decision_stability_note"],
        "",
        "## By near_world",
        "",
        "| near_world | n | ΔROI | ΔPnL | ΔBuy | ΔHit |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for nw, m in sorted(report["by_near_world"].items(), key=lambda x: -x[1]["n"]):
        main.append(
            f"| `{nw}` | {m['n']} | {fmt(m['delta_roi'])} | {fmt(m['delta_pnl'])} | "
            f"{fmt(m['delta_buy_rate'])} | {fmt(m['delta_purchase_hit'])} |"
        )

    main += [
        "",
        "## 方法",
        "",
        "1. CEW=unsatisfied かつ Near Miss（must∧exclude）のみ。",
        "2. Baseline = unsatisfied 保守 BUY。",
        "3. Affinity-aware = V95 Risk（高抑制 SKIP / 中抑制 stake半減）。Positive Ticket コピー禁止。",
        "4. Prediction fingerprint 不変を必須ゲート。",
        "",
        "## 関連",
        "",
        "- `v96-affinity-matrix.md`",
        "- `v95-decision-policy.md`",
        "- `v97-governance.md`",
        "",
    ]
    mpath = docs / "v97-affinity-decision-value-shadow.md"
    mpath.write_text("\n".join(main), encoding="utf-8")

    gov = [
        "# Version97 — Governance",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Action Type | Affinity Decision Value Shadow |",
        "| Implementation Required | **No**（製品コード非変更） |",
        "| Deployment Required | No |",
        f"| Verdict | `{v['verdict']}` |",
        f"| Affinity Decision Value | **{v['affinity_has_decision_value']}** |",
        "| CEW/World/Prediction Change | **No** |",
        "| Risk | Low |",
        "| Expected Next Action | VALUE なら Explain/Risk Shadow の製品配線を別 Decision。NO_VALUE/INCONCLUSIVE なら Affinity は注記のみ |",
        "",
        "## Hard locks",
        "",
        "- Prediction / Trigger / CEW / World Meaning",
        "- Positive World Ticket の Near Miss コピー禁止（DL-C6）",
        "- 本フェーズで `app/decision/*` へ Affinity を実装しない",
        "",
    ]
    gpath = docs / "v97-governance.md"
    gpath.write_text("\n".join(gov), encoding="utf-8")

    return {"json": str(jpath), "report": str(mpath), "gov": str(gpath)}


def main() -> None:
    report = run()
    paths = write_docs(report)
    print(
        json.dumps(
            {
                "scope": report["scope"],
                "verdict": report["verdict"],
                "deltas": report["deltas"],
                "baseline_roi": report["baseline"].get("ticket_roi"),
                "shadow_roi": report["affinity_aware"].get("ticket_roi"),
                "decision_stability": report["decision_stability"],
                "bootstrap_roi": report["bootstrap"]["roi"],
                "paths": paths,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
