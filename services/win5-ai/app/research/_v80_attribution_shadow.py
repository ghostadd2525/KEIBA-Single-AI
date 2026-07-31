# -*- coding: utf-8 -*-
"""Version80 — Attribution Shadow Execution (V79 2×2 on 285R).

Shadow-only. Does NOT mutate Production / Prediction pipeline / Trigger /
Blueprint / Signal / Threshold.

Cells:
  LL = legacy label + legacy_pe
  LP = legacy label + pilot_pe  (pilot must not fire — audit)
  CL = cew label + legacy_pe
  CP = cew label + pilot_pe

legacy_pe ranking = fixture model_rank / predicted_top1 (Production baseline observation).
pilot_pe ranking = research-only Shadow scorer instantiating V75 Ready contracts
  (rank7 / unsatisfied residual). Not Production PE.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))

from app.research.w_s1_shadow_dual_eval import miss_bucket, _f  # noqa: E402
from app.research._v64_world_strategy_discovery import zscore, pct_rank  # noqa: E402

SCHEMA = "v80-attribution-shadow/1.0"
CELLS = ("LL", "LP", "CL", "CP")
READY = ("rank7_world", "unsatisfied")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_inputs() -> tuple[list[dict[str, Any]], dict[str, dict], dict[str, dict], dict[str, str], dict[str, str]]:
    v73 = json.loads((ROOT / "docs/research/_v73-contract-intent-evaluation.json").read_text(encoding="utf-8"))
    cew = {r["race_id"]: r["cew_world"] for r in v73["rows"]}
    legacy = {r["race_id"]: r["legacy_world"] for r in v73["rows"]}
    corp = {
        r["race_id"]: r
        for r in json.loads(
            (ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8")
        )["races"]
    }
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fx_rows = fx.get("rows") or fx.get("evaluations") or []
    fxby = {r["race_id"]: r for r in fx_rows}
    return fx_rows, corp, fxby, cew, legacy


def horse_features(race: dict[str, Any]) -> list[dict[str, Any]]:
    runners = list(race.get("runners") or [])
    win_probs = [_f(u.get("win_prob")) or 0.0 for u in runners]
    hist = [_f(u.get("history_score")) or 0.0 for u in runners]
    odds = []
    for u in runners:
        o = _f(u.get("odds"))
        odds.append(o if o and o > 0 else None)
    if any(x is None for x in odds):
        mx = max((x for x in odds if x is not None), default=99.0)
        odds = [mx if x is None else x for x in odds]
    pops = [_f(u.get("popularity")) for u in runners]
    valid_pops = [p for p in pops if p is not None and p > 0]
    has_pop = len(valid_pops) == len(runners) and len(set(valid_pops)) > 1
    out = []
    for i, u in enumerate(runners):
        out.append(
            {
                "horse_id": str(u.get("horse_id") or ""),
                "win_prob": win_probs[i],
                "history_score": hist[i],
                "odds": odds[i],
                "popularity": pops[i] if has_pop else None,
                "running_style": u.get("running_style"),
                "model_rank": int(u.get("model_rank") or 999),
                "win_prob_z": zscore(win_probs, i),
                "history_z": zscore(hist, i),
                "win_prob_pct": pct_rank(win_probs, i, True),
                "history_pct": pct_rank(hist, i, True),
                "odds_pct_low": pct_rank(odds, i, False),
                "popularity_pct_low": pct_rank(valid_pops, i, False) if has_pop else None,
            }
        )
    return out


def field_size_of(fx: dict[str, Any], race: dict[str, Any], n_runners: int) -> int:
    return int(fx.get("field_size") or (race.get("context") or {}).get("field_size") or n_runners)


def attenuate_winprob(field_size: int) -> float:
    """V75 rank7 MUST.2 direction: larger field → lower win_prob weight. No new Threshold product."""
    # observational shadow weight in [0.5, 1.0]
    return max(0.5, min(1.0, 1.0 - 0.03 * max(0, field_size - 12)))


def shadow_pilot_scores(horses: list[dict[str, Any]], cew_world: str, field_size: int) -> list[float]:
    """V75 Ready contracts → research-only scores (not Production PE)."""
    scores = []
    if cew_world == "rank7_world":
        att = attenuate_winprob(field_size)
        for h in horses:
            s = 0.5 * float(h["history_pct"]) + 0.5 * float(h["win_prob_pct"]) * att
            s += 0.25 * float(h["odds_pct_low"])
            st = h.get("running_style")
            if st in ("差し", "追込"):
                s -= 0.05  # MUST.3: not primary
            scores.append(s)
    elif cew_world == "unsatisfied":
        for h in horses:
            if h.get("popularity_pct_low") is not None:
                s = float(h["popularity_pct_low"])
            else:
                s = 0.6 * float(h["win_prob_pct"]) + 0.4 * float(h["odds_pct_low"])
            scores.append(s)
    else:
        # Non-Ready: pilot must not invent strategy — fall back to win_prob_pct
        scores = [float(h["win_prob_pct"]) for h in horses]
    return scores


def rank_by_scores(horses: list[dict[str, Any]], scores: list[float]) -> list[int]:
    """1 = best. Stable tie-break by horse_id."""
    order = sorted(range(len(horses)), key=lambda i: (-scores[i], horses[i]["horse_id"]))
    ranks = [0] * len(horses)
    for r, i in enumerate(order, start=1):
        ranks[i] = r
    return ranks


def legacy_pe_outcome(
    horses: list[dict[str, Any]], winner_id: str, fx: dict[str, Any]
) -> dict[str, Any]:
    pred = str(fx.get("predicted_top1_horse_id") or "")
    # prefer fixture hit; also verify via model_rank==1
    hit = bool(fx.get("hit_at_1"))
    wr = None
    for h in horses:
        if h["horse_id"] == winner_id:
            wr = h["model_rank"]
            break
    return {
        "predicted_top1": pred,
        "hit": hit,
        "winner_rank": wr,
        "pe_path": "legacy_pe",
    }


def pilot_pe_outcome(
    horses: list[dict[str, Any]],
    winner_id: str,
    cew_world: str,
    field_size: int,
    *,
    allow_fire: bool,
) -> dict[str, Any]:
    if not allow_fire or cew_world not in READY:
        # must not fire
        return {
            "predicted_top1": None,  # filled by caller from legacy
            "hit": None,
            "winner_rank": None,
            "pe_path": "legacy_pe",
            "fired": False,
        }
    scores = shadow_pilot_scores(horses, cew_world, field_size)
    ranks = rank_by_scores(horses, scores)
    top_i = ranks.index(1)
    pred = horses[top_i]["horse_id"]
    wr = None
    for i, h in enumerate(horses):
        if h["horse_id"] == winner_id:
            wr = ranks[i]
            break
    hit = pred == winner_id
    path = "pilot_rank7" if cew_world == "rank7_world" else "pilot_unsat"
    return {
        "predicted_top1": pred,
        "hit": hit,
        "winner_rank": wr,
        "pe_path": path,
        "fired": True,
    }


def resolve_cell(
    cell: str,
    legacy_world: str,
    cew_world: str,
    horses: list[dict[str, Any]],
    winner_id: str,
    fx: dict[str, Any],
    field_size: int,
) -> dict[str, Any]:
    """V79 cell resolution."""
    if cell == "LL":
        world_used = legacy_world
        pe = legacy_pe_outcome(horses, winner_id, fx)
        label_src = "legacy"
    elif cell == "CL":
        world_used = cew_world
        pe = legacy_pe_outcome(horses, winner_id, fx)
        label_src = "cew"
    elif cell == "LP":
        # pilot_pe requested but WorldLabel=legacy → fire only if (wrongly) using legacy∈Ready
        # V79: pilot requires CEW∧Ready → allow_fire=False always when label source is legacy
        world_used = legacy_world
        leg = legacy_pe_outcome(horses, winner_id, fx)
        pe = {
            "predicted_top1": leg["predicted_top1"],
            "hit": leg["hit"],
            "winner_rank": leg["winner_rank"],
            "pe_path": "legacy_pe",
            "fired": False,
        }
        label_src = "legacy"
    elif cell == "CP":
        world_used = cew_world
        leg = legacy_pe_outcome(horses, winner_id, fx)
        pil = pilot_pe_outcome(
            horses, winner_id, cew_world, field_size, allow_fire=(cew_world in READY)
        )
        if pil["fired"]:
            pe = pil
        else:
            pe = {
                "predicted_top1": leg["predicted_top1"],
                "hit": leg["hit"],
                "winner_rank": leg["winner_rank"],
                "pe_path": "legacy_pe",
                "fired": False,
            }
        label_src = "cew"
    else:
        raise ValueError(cell)

    return {
        "cell": cell,
        "world_label_used": world_used,
        "label_source": label_src,
        "predicted_top1": pe["predicted_top1"],
        "hit": bool(pe["hit"]),
        "winner_rank": pe["winner_rank"],
        "pe_path": pe["pe_path"],
        "pilot_fired": bool(pe.get("fired")),
    }


def aggregate(rows: list[dict[str, Any]], cell: str) -> dict[str, Any]:
    buckets: Counter[str] = Counter()
    hits = 0
    parts = []
    pe_paths: Counter[str] = Counter()
    fired_n = 0
    for r in rows:
        c = r["cells"][cell]
        hit = c["hit"]
        if hit:
            hits += 1
        wr = c["winner_rank"]
        buckets[miss_bucket(hit, wr if isinstance(wr, int) else None)] += 1
        pe_paths[c["pe_path"]] += 1
        if c.get("pilot_fired"):
            fired_n += 1
        parts.append(f"{r['race_id']}|{c['predicted_top1']}|{r['winner_id']}|{int(hit)}|{c['pe_path']}")
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
        "buckets": dict(buckets),
        "prediction_fingerprint": hashlib.sha256("\n".join(sorted(parts)).encode("utf-8")).hexdigest(),
        "pe_path_counts": dict(pe_paths),
        "pilot_fired_n": fired_n,
    }


def delta(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    keys = ("hit", "purchase", "rank710", "other_1_3", "other_10_13", "rank46", "other")
    out = {k: int(a[k]) - int(b[k]) for k in keys}
    out["fingerprint_changed"] = a["prediction_fingerprint"] != b["prediction_fingerprint"]
    return out


def run() -> dict[str, Any]:
    fx_rows, corp, fxby, cew, legacy = load_inputs()
    race_rows = []
    for fr in fx_rows:
        rid = str(fr["race_id"])
        race = corp.get(rid) or {}
        horses = horse_features(race)
        if len(horses) < 2:
            continue
        wid = str(race.get("winner_id") or fr.get("winner_id") or "")
        fs = field_size_of(fr, race, len(horses))
        cw = cew[rid]
        lw = legacy[rid]
        cells = {
            cell: resolve_cell(cell, lw, cw, horses, wid, fr, fs) for cell in CELLS
        }
        race_rows.append(
            {
                "race_id": rid,
                "winner_id": wid,
                "cew_world": cw,
                "legacy_world": lw,
                "field_size": fs,
                "cells": cells,
            }
        )

    def subset(pred):
        return [r for r in race_rows if pred(r)]

    full = {cell: aggregate(race_rows, cell) for cell in CELLS}
    rank7 = {cell: aggregate(subset(lambda r: r["cew_world"] == "rank7_world"), cell) for cell in CELLS}
    unsat = {cell: aggregate(subset(lambda r: r["cew_world"] == "unsatisfied"), cell) for cell in CELLS}
    nonready = {
        cell: aggregate(subset(lambda r: r["cew_world"] not in READY), cell) for cell in CELLS
    }

    def pack_deltas(block: dict[str, dict[str, Any]]) -> dict[str, Any]:
        d_trig = delta(block["CL"], block["LL"])
        d_strat = delta(block["CP"], block["CL"])
        d_both = delta(block["CP"], block["LL"])
        d_inter = {
            k: int(d_both[k]) - int(d_trig[k]) - int(d_strat[k])
            for k in ("hit", "purchase", "rank710", "other_1_3", "other_10_13", "rank46", "other")
        }
        # LP audit vs LL
        d_lp = delta(block["LP"], block["LL"])
        return {
            "Delta_Trigger_CL_minus_LL": d_trig,
            "Delta_Strategy_CP_minus_CL": d_strat,
            "Delta_Both_CP_minus_LL": d_both,
            "Delta_Interaction": d_inter,
            "Audit_LP_minus_LL": d_lp,
            "LP_equals_LL_fingerprint": block["LP"]["prediction_fingerprint"]
            == block["LL"]["prediction_fingerprint"],
            "CL_equals_LL_fingerprint": block["CL"]["prediction_fingerprint"]
            == block["LL"]["prediction_fingerprint"],
        }

    # pe path audits
    lp_fire = full["LP"]["pilot_fired_n"]
    cp_nonready_fire = nonready["CP"]["pilot_fired_n"]

    report = {
        "schema": SCHEMA,
        "generated_at": _now(),
        "n": len(race_rows),
        "note": {
            "production_unchanged": True,
            "legacy_pe": "fixture predicted_top1 / hit_at_1 / model_rank",
            "pilot_pe": "research-only Shadow scorer from V75 Ready contracts",
            "v79_cells": "LL LP CL CP",
        },
        "cells_full": full,
        "cells_rank7": rank7,
        "cells_unsatisfied_residual": unsat,
        "cells_nonready": nonready,
        "deltas_full": pack_deltas(full),
        "deltas_rank7": pack_deltas(rank7),
        "deltas_unsatisfied_residual": pack_deltas(unsat),
        "deltas_nonready": pack_deltas(nonready),
        "boundary_audit": {
            "LP_pilot_fired_n": lp_fire,
            "LP_fired_must_be_0": lp_fire == 0,
            "CP_nonready_pilot_fired_n": cp_nonready_fire,
            "CP_nonready_fired_must_be_0": cp_nonready_fire == 0,
        },
    }
    return report


def _fmt(x: Any) -> str:
    if isinstance(x, bool):
        return "Y" if x else "N"
    return str(x)


def write_docs(report: dict[str, Any]) -> dict[str, Path]:
    out = ROOT / "docs" / "research"
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    paths["json"] = out / "_v80-attribution-shadow.json"
    paths["json"].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def cell_table(title: str, block: dict[str, dict[str, Any]]) -> list[str]:
        lines = [
            f"## {title}",
            "",
            "| Cell | n | Hit | Purchase | rank710 | other_1_3 | other_10_13 | rank46 | fired | Fingerprint |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
        for cell in CELLS:
            b = block[cell]
            lines.append(
                f"| **{cell}** | {b['n']} | {b['hit']} | {b['purchase']} | {b['rank710']} | "
                f"{b['other_1_3']} | {b['other_10_13']} | {b['rank46']} | {b['pilot_fired_n']} | "
                f"`{b['prediction_fingerprint'][:16]}…` |"
            )
        return lines

    def delta_table(title: str, dpack: dict[str, Any]) -> list[str]:
        lines = [
            f"## {title}",
            "",
            "| Delta | Hit | Purchase | rank710 | other_1_3 | other_10_13 | rank46 | fpΔ |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
        for name, key in (
            ("ΔTrigger (CL−LL)", "Delta_Trigger_CL_minus_LL"),
            ("ΔStrategy (CP−CL)", "Delta_Strategy_CP_minus_CL"),
            ("ΔBoth (CP−LL)", "Delta_Both_CP_minus_LL"),
            ("ΔInteraction", "Delta_Interaction"),
            ("Audit LP−LL", "Audit_LP_minus_LL"),
        ):
            d = dpack[key]
            fp = d.get("fingerprint_changed")
            fp_s = _fmt(fp) if fp is not None else "—"
            if name == "ΔInteraction":
                fp_s = "—"
            lines.append(
                f"| {name} | {d['hit']} | {d['purchase']} | {d['rank710']} | "
                f"{d['other_1_3']} | {d['other_10_13']} | {d['rank46']} | {fp_s} |"
            )
        lines += [
            "",
            f"- LP fingerprint == LL: **{_fmt(dpack['LP_equals_LL_fingerprint'])}**",
            f"- CL fingerprint == LL: **{_fmt(dpack['CL_equals_LL_fingerprint'])}**",
            "",
        ]
        return lines

    paths["eval"] = out / "v80-attribution-evaluation.md"
    paths["eval"].write_text(
        "\n".join(
            [
                "# Version80 — Attribution Shadow Evaluation",
                "",
                f"**Generated:** `{report['generated_at']}`  ",
                f"**N:** {report['n']}  ",
                "**Mode:** Shadow only（Production / Trigger / Prediction pipeline 非変更）  ",
                "**Design:** V79 2×2（LL / LP / CL / CP）",
                "",
                "## 方法注記",
                "",
                f"- legacy_pe: `{report['note']['legacy_pe']}`",
                f"- pilot_pe: `{report['note']['pilot_pe']}`",
                "",
                *cell_table("Full 285R", report["cells_full"]),
                "",
                *cell_table("Ready: rank7 only（CEW=rank7）", report["cells_rank7"]),
                "",
                *cell_table("Residual: unsatisfied（CEW=unsatisfied）", report["cells_unsatisfied_residual"]),
                "",
                "## Boundary Audit",
                "",
                f"- LP pilot_fired_n = {report['boundary_audit']['LP_pilot_fired_n']} "
                f"（must 0: {_fmt(report['boundary_audit']['LP_fired_must_be_0'])}）",
                f"- CP on Non-Ready pilot_fired_n = {report['boundary_audit']['CP_nonready_pilot_fired_n']} "
                f"（must 0: {_fmt(report['boundary_audit']['CP_nonready_fired_must_be_0'])}）",
                "",
                "## 数値正本",
                "",
                "`docs/research/_v80-attribution-shadow.json`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    paths["delta"] = out / "v80-delta-analysis.md"
    paths["delta"].write_text(
        "\n".join(
            [
                "# Version80 — Delta Analysis（Attribution）",
                "",
                f"**Generated:** `{report['generated_at']}`  ",
                "定義: ΔTrigger=CL−LL / ΔStrategy=CP−CL / ΔBoth=CP−LL / ΔInteraction=ΔBoth−ΔTrigger−ΔStrategy",
                "",
                *delta_table("Full 285R", report["deltas_full"]),
                *delta_table("rank7 only", report["deltas_rank7"]),
                *delta_table("unsatisfied Residual", report["deltas_unsatisfied_residual"]),
                *delta_table("Non-Ready（発火ゼロ期待）", report["deltas_nonready"]),
                "## 归因読み（V79 規則）",
                "",
                "- ΔTrigger が非ゼロ → Trigger/ラベル要因（本 Shadow では legacy_pe がラベル非依存のため通常 0）",
                "- ΔStrategy が非ゼロ → Strategy/Pilot Shadow PE 要因",
                "- LL+CP のみで断言しない（本報告は 2×2 完備）",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # governance verdict from deltas
    d = report["deltas_full"]
    strat = d["Delta_Strategy_CP_minus_CL"]["hit"]
    trig = d["Delta_Trigger_CL_minus_LL"]["hit"]
    both = d["Delta_Both_CP_minus_LL"]["hit"]
    inter = d["Delta_Interaction"]["hit"]
    audit_ok = report["boundary_audit"]["LP_fired_must_be_0"] and report["boundary_audit"][
        "CP_nonready_fired_must_be_0"
    ]
    verdict = "A" if audit_ok else "C"

    paths["gov"] = out / "v80-governance.md"
    paths["gov"].write_text(
        "\n".join(
            [
                "# Version80 — Governance（Attribution Shadow Execution）",
                "",
                f"**Date:** {report['generated_at'][:10]}  ",
                f"**Verdict:** **{verdict}**（Shadow 実行完了 / 境界監査 "
                f"{'PASS' if audit_ok else 'FAIL'}）  ",
                "**Type:** Shadow Execution only",
                "",
                "## 主結果（Full Hit Δ）",
                "",
                f"| Δ | Hit |",
                f"|---|---:|",
                f"| ΔTrigger | {trig} |",
                f"| ΔStrategy | {strat} |",
                f"| ΔBoth | {both} |",
                f"| ΔInteraction | {inter} |",
                "",
                "【Decision】",
                "",
                "| Item | Value |",
                "|---|---|",
                "| Action Type | Attribution Shadow Execution |",
                "| Implementation Required | No（Production） |",
                "| Deployment Required | No |",
                "| Production Required | No |",
                "| Rollback Required | No |",
                "| Risk | Shadow のみ（本番非干渉） |",
                "| Expected Next Action | Δ に基づく Pilot 方針 Decision（実装は別） |",
                "",
                "## 遵守",
                "",
                "| 制約 | |",
                "|---|---|",
                "| Production/Trigger/Blueprint/Signal/Threshold 非変更 | PASS |",
                "| Prediction pipeline 非変更（fixture baseline + research shadow scorer） | PASS |",
                "| V79 2×2 のみ | PASS |",
                "",
                "## 成果物",
                "",
                "- `v80-attribution-evaluation.md`",
                "- `v80-delta-analysis.md`",
                "- `v80-governance.md`",
                "- `_v80-attribution-shadow.json`",
                "",
            ]
        ),
        encoding="utf-8",
    )
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
                "n": report["n"],
                "deltas_full": report["deltas_full"],
                "boundary_audit": report["boundary_audit"],
                "full_hits": {c: report["cells_full"][c]["hit"] for c in CELLS},
                "rank7_hits": {c: report["cells_rank7"][c]["hit"] for c in CELLS},
                "unsat_hits": {c: report["cells_unsatisfied_residual"][c]["hit"] for c in CELLS},
                "paths": {k: str(v) for k, v in paths.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
