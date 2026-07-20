#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prediction Core failure analysis — mock_fallback classification + stage trace."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
platform = Path(os.environ.get("AI_PLATFORM_ROOT") or ROOT.parents[2])
if (platform / "ai_platform").is_dir() and str(platform) not in sys.path:
    sys.path.insert(0, str(platform))

os.environ.setdefault("AI_ENGINE", "real")

import app.core  # noqa: F401 — FeatureLoader DB bridge

from app.data.race_resolver import resolve_identity  # noqa: E402
from app.engine import data  # noqa: E402
from app.engine.adapters import prediction_adapter, single_prediction_mapper as mapper  # noqa: E402
from ai_platform.core.candidate_evaluation import CorePipeline  # noqa: E402
from ai_platform.core.facade import predict_ranking  # noqa: E402


def trace_core(core_id: str) -> dict:
    pipe = CorePipeline()
    out: dict = {"core_race_id": core_id, "stages": {}}

    loaded = pipe.load_race_input(core_id)
    if loaded is None:
        out["stop"] = "load_race_input"
        return out
    runners, source = loaded
    out["stages"]["load_race_input"] = {"ok": True, "rows": len(runners), "source": Path(source).name}

    try:
        fm = pipe.features.build_feature_matrix(runners)
        out["stages"]["FeatureGenerator"] = {
            "ok": True,
            "missing_feature_count": fm["feature_meta"]["missing_feature_count"],
            "feature_count": len(fm["feature_names"]),
        }
    except Exception as exc:
        out["stop"] = "FeatureGenerator"
        out["error"] = str(exc)
        return out

    try:
        scores = pipe.scoring.score_candidates(fm)
        out["stages"]["Scorer"] = {
            "ok": True,
            "predict_mode": scores.get("_predict_mode"),
            "model_source": scores.get("_model_source"),
        }
    except Exception as exc:
        out["stop"] = "Scorer"
        out["error"] = str(exc)
        return out

    try:
        ranking = pipe.ranking.build_ranking(scores)
        out["stages"]["Ranker"] = {"ok": True, "horses": len(ranking["ranking"])}
    except Exception as exc:
        out["stop"] = "Ranker"
        out["error"] = str(exc)
        return out

    try:
        meta = pipe.world.build_race_meta(scores["_source_frame"])
        conf = pipe.confidence.build_confidence(scores, meta)
        out["stages"]["ConfidenceBuilder"] = {"ok": True, "overall": round(conf["overall"], 6)}
    except Exception as exc:
        out["stop"] = "ConfidenceBuilder"
        out["error"] = str(exc)
        return out

    try:
        world = pipe.world.classify_world(conf, meta)
        out["stages"]["WorldClassifier"] = {
            "ok": True,
            "world": world["world"],
            "sub_world": world["sub_world"],
        }
    except Exception as exc:
        out["stop"] = "WorldClassifier"
        out["error"] = str(exc)
        return out

    out["stop"] = "success"
    return out


def main() -> None:
    catalog = data.load_races().get("races") or []
    _, meta = prediction_adapter.list_with_meta()
    prov = meta.get("items") or []

    reason_counter: Counter = Counter()
    stop_counter: Counter = Counter()
    rows: list[dict] = []

    for race in catalog:
        rid = str(race.get("race_id") or "")
        ident = resolve_identity(rid, race_meta=race)
        core_id = ident.core_race_id if ident else None
        diag = mapper.diagnose_inference(rid, race)
        reason = "real_ai" if diag.get("ok") else str(diag.get("fallback_reason") or "unknown")
        reason_counter[reason] += 1

        row: dict = {
            "public_race_id": rid,
            "core_race_id": core_id or diag.get("core_race_id"),
            "engine_source": "real_ai" if diag.get("ok") else "mock_fallback",
            "fallback_reason": reason if reason != "real_ai" else None,
            "detail": diag.get("detail"),
        }

        if not core_id:
            row["stop_stage"] = "RaceResolver"
            stop_counter["RaceResolver"] += 1
        elif reason == "market_feature_missing":
            row["stop_stage"] = "load_race_input"
            stop_counter["load_race_input"] += 1
            trace = trace_core(core_id) if core_id else {}
            row["core_trace"] = trace
        elif reason == "real_ai":
            trace = trace_core(core_id) if core_id else {}
            row["stop_stage"] = trace.get("stop", "success")
            stop_counter[row["stop_stage"]] += 1
            row["core_trace"] = trace
        else:
            row["stop_stage"] = reason
            stop_counter[reason] += 1

        rows.append(row)

    total = len(rows)
    report = {
        "total_races": total,
        "real_ai_count": reason_counter.get("real_ai", 0),
        "real_ai_rate_pct": round(100 * reason_counter.get("real_ai", 0) / total, 1) if total else 0,
        "mock_fallback_count": total - reason_counter.get("real_ai", 0),
        "by_fallback_reason": dict(reason_counter),
        "by_fallback_reason_pct": {
            k: round(100 * v / total, 1) for k, v in sorted(reason_counter.items(), key=lambda x: -x[1])
        },
        "by_stop_stage": dict(stop_counter),
        "platform_available": mapper.locate_ai_platform_root() is not None,
        "races": rows,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
