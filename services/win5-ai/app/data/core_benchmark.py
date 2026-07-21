# -*- coding: utf-8 -*-
"""Prediction Core accuracy KPIs — labeled backtest vs frozen baseline."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_platform.core.facade import evaluate_candidates

from .training.metrics import (
    brier_score,
    expected_calibration_error,
    log_loss,
    ndcg_at_k,
    rank_relevance,
)

REGRESSION_METRICS = (
    "hit_at_1",
    "hit_at_3",
    "hit_at_5",
    "mrr",
    "ndcg_at_5",
    "brier_score",
    "log_loss",
    "ece",
)

HIGHER_IS_BETTER = {
    "hit_at_1",
    "hit_at_3",
    "hit_at_5",
    "mrr",
    "ndcg_at_5",
}


def _platform_data() -> Path | None:
    root = (os.environ.get("AI_PLATFORM_ROOT") or "").strip()
    if root:
        data = Path(root) / "data"
        if data.is_dir():
            return data
    return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RaceBenchmarkRow:
    race_id: str
    field_size: int
    winner_horse_number: int | None
    predicted_top1_horse_number: int | None
    hit_at_1: bool
    hit_at_3: bool
    hit_at_5: bool
    reciprocal_rank: float
    ndcg_at_5: float
    feature_source: str | None
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "race_id": self.race_id,
            "field_size": self.field_size,
            "winner_horse_number": self.winner_horse_number,
            "predicted_top1_horse_number": self.predicted_top1_horse_number,
            "hit_at_1": self.hit_at_1,
            "hit_at_3": self.hit_at_3,
            "hit_at_5": self.hit_at_5,
            "reciprocal_rank": self.reciprocal_rank,
            "ndcg_at_5": round(self.ndcg_at_5, 4),
            "feature_source": self.feature_source,
            "error": self.error,
        }


@dataclass
class CoreKpiSummary:
    races_total: int = 0
    races_evaluated: int = 0
    races_skipped: int = 0
    hit_at_1: float = 0.0
    hit_at_3: float = 0.0
    hit_at_5: float = 0.0
    mrr: float = 0.0
    ndcg_at_5: float = 0.0
    brier_score: float = 0.0
    log_loss: float = 0.0
    ece: float = 0.0
    avg_field_size: float = 0.0
    by_feature_source: dict[str, int] = field(default_factory=dict)
    rows: list[RaceBenchmarkRow] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "generated_at": _now(),
            "races_total": self.races_total,
            "races_evaluated": self.races_evaluated,
            "races_skipped": self.races_skipped,
            "hit_at_1": round(self.hit_at_1, 4),
            "hit_at_3": round(self.hit_at_3, 4),
            "hit_at_5": round(self.hit_at_5, 4),
            "mrr": round(self.mrr, 4),
            "ndcg_at_5": round(self.ndcg_at_5, 4),
            "brier_score": round(self.brier_score, 4),
            "log_loss": round(self.log_loss, 4),
            "ece": round(self.ece, 4),
            "avg_field_size": round(self.avg_field_size, 2),
            "by_feature_source": dict(self.by_feature_source),
            "rows": [r.as_dict() for r in self.rows],
        }


@dataclass
class RaceLabelSet:
    by_number: dict[int, int]
    by_name: dict[str, int]
    winner_number: int | None = None
    winner_name: str | None = None

    @property
    def field_size(self) -> int:
        return len(self.by_number) or len(self.by_name)


def load_labeled_races(
    *,
    result_paths: list[Path] | None = None,
    race_ids: list[str] | None = None,
) -> dict[str, RaceLabelSet]:
    """
    Return labeled races with finish ranks keyed by horse number and name.
    """
    data_dir = _platform_data()
    paths = result_paths or []
    if not paths and data_dir:
        paths = [
            data_dir / "win5_resultwithdate.csv",
            data_dir / "demo_win5_resultwithdate.csv",
        ]

    labels: dict[str, RaceLabelSet] = {}
    for path in paths:
        if not path.exists():
            continue
        frame = _read_csv(path)
        if "race_id" not in frame.columns:
            continue
        rank_col = "finish_rank" if "finish_rank" in frame.columns else None
        if not rank_col:
            continue
        name_col = "horse_name" if "horse_name" in frame.columns else None
        for rid, group in frame.groupby(frame["race_id"].astype(str)):
            if race_ids and rid not in race_ids:
                continue
            by_number: dict[int, int] = {}
            by_name: dict[str, int] = {}
            for _, row in group.iterrows():
                hn = _as_int(row.get("horse_number"))
                fr = _as_int(row.get(rank_col))
                if fr is None or fr <= 0:
                    if _as_int(row.get("target_win")) == 1 and hn is not None:
                        fr = 1
                    else:
                        continue
                if hn is not None:
                    by_number[hn] = fr
                if name_col:
                    name = _normalize_name(row.get(name_col))
                    if name:
                        by_name[name] = fr
            if not by_number and not by_name:
                continue
            winner_number = _winner_number(by_number)
            winner_name = _winner_name(by_name, by_number)
            if winner_number is None and winner_name is None:
                continue
            labels[rid] = RaceLabelSet(
                by_number=by_number,
                by_name=by_name,
                winner_number=winner_number,
                winner_name=winner_name,
            )
    return labels


def run_core_benchmark(
    *,
    race_ids: list[str] | None = None,
    result_paths: list[Path] | None = None,
) -> CoreKpiSummary:
    """Evaluate Core predictions against labeled finish ranks."""
    labels = load_labeled_races(result_paths=result_paths, race_ids=race_ids)
    target_ids = sorted(labels.keys())
    summary = CoreKpiSummary(races_total=len(target_ids))

    hits1 = hits3 = hits5 = mrr_sum = ndcg_sum = 0
    field_sizes: list[int] = []
    cal_y_true: list[int] = []
    cal_y_prob: list[float] = []

    for rid in target_ids:
        label = labels[rid]
        row = RaceBenchmarkRow(
            race_id=rid,
            field_size=label.field_size,
            winner_horse_number=label.winner_number,
            predicted_top1_horse_number=None,
            hit_at_1=False,
            hit_at_3=False,
            hit_at_5=False,
            reciprocal_rank=0.0,
            ndcg_at_5=0.0,
            feature_source=None,
        )
        try:
            ce = evaluate_candidates(rid)
            if ce is None:
                row.error = "unresolved"
                summary.rows.append(row)
                summary.races_skipped += 1
                continue

            ctx = ce.get("context") or {}
            row.feature_source = ctx.get("feature_source")
            src = row.feature_source or "unknown"
            summary.by_feature_source[src] = summary.by_feature_source.get(src, 0) + 1

            predicted = _ranked_predictions(ce.get("candidates") or [])
            if predicted:
                top_hn, _top_name = predicted[0][:2]
                row.predicted_top1_horse_number = top_hn

            winner_n = label.winner_number
            winner_name = label.winner_name
            if winner_n is None and winner_name is None:
                row.error = "no_winner_label"
                summary.rows.append(row)
                summary.races_skipped += 1
                continue

            if _winner_in_top(predicted, winner_n, winner_name, k=1):
                row.hit_at_1 = True
                hits1 += 1
            if _winner_in_top(predicted, winner_n, winner_name, k=3):
                row.hit_at_3 = True
                hits3 += 1
            if _winner_in_top(predicted, winner_n, winner_name, k=5):
                row.hit_at_5 = True
                hits5 += 1
            rr = _reciprocal_rank(predicted, winner_n, winner_name)
            if rr > 0:
                row.reciprocal_rank = rr
                mrr_sum += rr

            relevances = _relevances_in_predicted_order(predicted, label)
            row.ndcg_at_5 = ndcg_at_k(relevances, 5)
            ndcg_sum += row.ndcg_at_5

            y_true, y_prob = _calibration_pairs(ce.get("candidates") or [], label)
            cal_y_true.extend(y_true)
            cal_y_prob.extend(y_prob)

            field_sizes.append(row.field_size)
            summary.races_evaluated += 1
        except Exception as exc:
            row.error = str(exc)
            summary.races_skipped += 1
        summary.rows.append(row)

    n = summary.races_evaluated
    if n:
        summary.hit_at_1 = hits1 / n
        summary.hit_at_3 = hits3 / n
        summary.hit_at_5 = hits5 / n
        summary.mrr = mrr_sum / n
        summary.ndcg_at_5 = ndcg_sum / n
        summary.avg_field_size = sum(field_sizes) / len(field_sizes)
    if cal_y_true:
        summary.brier_score = brier_score(cal_y_true, cal_y_prob)
        summary.log_loss = log_loss(cal_y_true, cal_y_prob)
        summary.ece = expected_calibration_error(cal_y_true, cal_y_prob)
    return summary


def compare_to_baseline(
    summary: CoreKpiSummary | dict[str, Any],
    baseline: dict[str, Any],
    *,
    tolerance: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Return pass/fail vs frozen KPI baseline."""
    tol = tolerance or baseline.get("tolerance") or {}
    current = summary.as_dict() if isinstance(summary, CoreKpiSummary) else summary
    base = baseline.get("kpi") or baseline

    checks: dict[str, Any] = {}
    ok = True
    for metric in REGRESSION_METRICS:
        if metric not in base and metric not in current:
            continue
        cur = float(current.get(metric) or 0.0)
        ref = float(base.get(metric) or 0.0)
        min_delta = float(tol.get(metric, 0.0))
        if metric in HIGHER_IS_BETTER:
            passed = cur + 1e-9 >= ref - min_delta
            min_allowed = ref - min_delta
        else:
            passed = cur <= ref + min_delta + 1e-9
            min_allowed = ref + min_delta
        checks[metric] = {
            "current": cur,
            "baseline": ref,
            "min_allowed": min_allowed,
            "passed": passed,
            "direction": "higher" if metric in HIGHER_IS_BETTER else "lower",
        }
        if not passed:
            ok = False

    return {
        "ok": ok,
        "checks": checks,
        "baseline_schema": baseline.get("schema_version"),
        "baseline_generated_at": baseline.get("generated_at"),
    }


def save_benchmark_report(
    summary: CoreKpiSummary,
    *,
    path: Path | None = None,
) -> Path:
    report_dir = Path(
        os.environ.get("EXPECT_AI_REPORT_DIR")
        or Path(__file__).resolve().parents[1] / "var" / "reports"
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    out = path or report_dir / "core_kpi_benchmark.json"
    payload = {
        "schema_version": "core-kpi-benchmark/1.0",
        "generated_at": _now(),
        "kpi": {
            "hit_at_1": summary.hit_at_1,
            "hit_at_3": summary.hit_at_3,
            "hit_at_5": summary.hit_at_5,
            "mrr": summary.mrr,
            "ndcg_at_5": summary.ndcg_at_5,
            "brier_score": summary.brier_score,
            "log_loss": summary.log_loss,
            "ece": summary.ece,
            "races_evaluated": summary.races_evaluated,
            "avg_field_size": summary.avg_field_size,
        },
        "detail": summary.as_dict(),
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, low_memory=False)


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _winner_number(ranks: dict[int, int]) -> int | None:
    for hn, fr in ranks.items():
        if fr == 1:
            return hn
    return None


def _normalize_name(value: Any) -> str:
    return str(value or "").strip()


def _winner_name(by_name: dict[str, int], by_number: dict[int, int]) -> str | None:
    for name, fr in by_name.items():
        if fr == 1:
            return name
    return None


def _ranked_predictions(
    candidates: list[dict[str, Any]],
) -> list[tuple[int | None, str, float]]:
    ordered = sorted(candidates, key=lambda c: int(c.get("Rank") or 999))
    out: list[tuple[int | None, str, float]] = []
    for c in ordered:
        hn = _as_int(c.get("HorseNumber"))
        name = _normalize_name(c.get("CandidateID"))
        conf = float(c.get("Confidence") or 0.0)
        out.append((hn, name, conf))
    return out


def _finish_rank_for_prediction(
    hn: int | None,
    name: str,
    label: RaceLabelSet,
) -> int | None:
    if hn is not None and hn in label.by_number:
        return label.by_number[hn]
    if name and name in label.by_name:
        return label.by_name[name]
    return None


def _relevances_in_predicted_order(
    predicted: list[tuple[int | None, str, float]],
    label: RaceLabelSet,
) -> list[float]:
    relevances: list[float] = []
    for hn, name, _conf in predicted:
        fr = _finish_rank_for_prediction(hn, name, label)
        relevances.append(rank_relevance(fr))
    return relevances


def _calibration_pairs(
    candidates: list[dict[str, Any]],
    label: RaceLabelSet,
) -> tuple[list[int], list[float]]:
    y_true: list[int] = []
    y_prob: list[float] = []
    for c in candidates:
        hn = _as_int(c.get("HorseNumber"))
        name = _normalize_name(c.get("CandidateID"))
        fr = _finish_rank_for_prediction(hn, name, label)
        if fr is None:
            continue
        y_true.append(1 if fr == 1 else 0)
        y_prob.append(float(c.get("Confidence") or 0.0))
    return y_true, y_prob


def _prediction_matches(
    hn: int | None,
    name: str,
    winner_number: int | None,
    winner_name: str | None,
) -> bool:
    if winner_number is not None and hn is not None and hn == winner_number:
        return True
    if winner_name and name and name == winner_name:
        return True
    return False


def _winner_in_top(
    predicted: list[tuple[int | None, str, float]],
    winner_number: int | None,
    winner_name: str | None,
    *,
    k: int,
) -> bool:
    for hn, name, _conf in predicted[:k]:
        if _prediction_matches(hn, name, winner_number, winner_name):
            return True
    return False


def _reciprocal_rank(
    predicted: list[tuple[int | None, str, float]],
    winner_number: int | None,
    winner_name: str | None,
) -> float:
    for i, (hn, name, _conf) in enumerate(predicted):
        if _prediction_matches(hn, name, winner_number, winner_name):
            return 1.0 / (i + 1)
    return 0.0


def _ranked_horse_numbers(candidates: list[dict[str, Any]]) -> list[int]:
    """Legacy helper — horse numbers only (may omit NaN entries)."""
    out: list[int] = []
    for hn, _name, _conf in _ranked_predictions(candidates):
        if hn is not None:
            out.append(hn)
    return out
