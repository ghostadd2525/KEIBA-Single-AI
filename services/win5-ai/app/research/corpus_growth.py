# -*- coding: utf-8 -*-
"""
Research Corpus Growth (continuation)

Accumulate Evidence Snapshots and grow segment sample sizes.
Reporting + harvest orchestration only.

FORBIDDEN:
  Prediction / PE / CE / AI / Challenge / Resolver /
  Shadow product wiring / ResultAutomation / Production
  Improvement implementation into product
"""
from __future__ import annotations

import json
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .config import evidence_root, repo_root
from .prediction_corpus import TARGETS

SCHEMA_VERSION = "expect-corpus-growth/1.0"

SEGMENT_FOCUS = (
    "young_horse",
    "maiden",
    "stakes",
    "turf",
    "dirt",
    "distance",
    "going",
    "pop_band",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _week_id(dt: datetime | None = None) -> str:
    d = dt or datetime.now(timezone.utc)
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _pct(v: Any) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{100.0 * float(v):.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def _delta(after: Any, before: Any) -> Any:
    if after is None and before is None:
        return None
    try:
        a = 0 if after is None else after
        b = 0 if before is None else before
        return a - b
    except TypeError:
        return None


def _axis_counts(atlas: dict[str, Any], axis: str) -> dict[str, int]:
    rows = (atlas.get("by_axis") or {}).get(axis) or []
    out: dict[str, int] = {}
    for r in rows:
        seg = str(r.get("segment") or "unknown")
        out[seg] = int(r.get("n") or 0)
    return out


def _sum_keys(d: dict[str, int], keys: set[str]) -> int:
    return sum(int(d.get(k) or 0) for k in keys)


def snapshot_metrics(*, reports: Path, corpus_json: Path) -> dict[str, Any]:
    """Read-only metrics from existing research artifacts."""
    corpus = _load_json(corpus_json)
    # Prefer slim summary fields; fall back if only records present
    if not corpus.get("prediction_count") and corpus.get("records"):
        corpus = {
            **corpus,
            "prediction_count": len(corpus.get("records") or []),
        }

    atlas = _load_json(reports / "v16-weakness-atlas.json")
    if not atlas.get("by_axis"):
        atlas = _load_json(reports / "v15-weakness-atlas.json")

    meta = _load_json(reports / "v16-metadata-completion.json")
    kb = _load_json(reports / "v18-knowledge-base.json")
    v17 = _load_json(reports / "v17-evidence-discovery.json")

    cov_corpus = corpus.get("coverage") or {}
    cov_meta = meta.get("summary") or {}
    kb_sum = kb.get("summary") or {}
    conf = kb_sum.get("by_confidence") or {}
    if not conf and kb.get("entries"):
        conf = dict(Counter(e.get("confidence") for e in kb["entries"]))

    by_surface = corpus.get("by_surface") or {}
    by_distance = corpus.get("by_distance") or {}
    by_age = corpus.get("by_age") or {}
    by_class_family = _axis_counts(atlas, "class_family")
    by_going = _axis_counts(atlas, "going")
    by_pop = _axis_counts(atlas, "pop_band")
    by_surface_atlas = _axis_counts(atlas, "surface")
    by_distance_atlas = _axis_counts(atlas, "distance_bucket")

    maiden_n = _sum_keys(
        by_age, {"2yo_maiden", "3yo_maiden"}
    ) or _sum_keys(by_class_family, {"maiden"})
    # also count maiden class_family if age empty
    if maiden_n == 0:
        maiden_n = int(by_class_family.get("maiden") or 0)
    stakes_n = int(by_class_family.get("stakes") or 0)

    evidence_n = int(
        cov_corpus.get("with_evidence_snapshot")
        or (atlas.get("sample") or {}).get("with_evidence")
        or (v17.get("sample") or {}).get("with_evidence")
        or 0
    )
    prediction_n = int(corpus.get("prediction_count") or 0)
    young_n = int(corpus.get("young_horse_count") or 0)
    tie_n = int(corpus.get("tie_count") or 0)
    knowledge_n = int(kb_sum.get("entry_count") or len(kb.get("entries") or []))

    segments = {
        "young_horse": young_n,
        "maiden": maiden_n,
        "stakes": stakes_n,
        "turf": int(by_surface.get("turf") or by_surface_atlas.get("turf") or 0),
        "dirt": int(by_surface.get("dirt") or by_surface_atlas.get("dirt") or 0),
        "distance": dict(by_distance or by_distance_atlas),
        "going": dict(by_going),
        "pop_band": dict(by_pop),
        "by_age": dict(by_age),
        "by_class_family": dict(by_class_family),
        "by_surface": dict(by_surface or by_surface_atlas),
    }

    return {
        "captured_at": _now(),
        "prediction": prediction_n,
        "evidence": evidence_n,
        "knowledge": knowledge_n,
        "tie": tie_n,
        "young_horse": young_n,
        "coverage": {
            "with_prediction_bundle": cov_corpus.get("with_prediction_bundle"),
            "with_race_result": cov_corpus.get("with_race_result"),
            "with_evidence_snapshot": cov_corpus.get("with_evidence_snapshot"),
            "with_shadow_result": cov_corpus.get("with_shadow_result"),
            "mean_metadata_before": cov_meta.get("mean_coverage_before"),
            "mean_metadata_after": cov_meta.get("mean_coverage_after"),
        },
        "confidence": {
            "High": int(conf.get("High") or 0),
            "Medium": int(conf.get("Medium") or 0),
            "Low": int(conf.get("Low") or 0),
            "Exploratory": int(conf.get("Exploratory") or 0),
        },
        "targets": TARGETS,
        "gap": {
            "prediction": max(TARGETS["prediction"] - prediction_n, 0),
            "tie": max(TARGETS["tie"] - tie_n, 0),
            "young_horse": max(TARGETS["young_horse"] - young_n, 0),
        },
        "segments": segments,
        "atlas_sample": atlas.get("sample") or {},
        "v17_sample": v17.get("sample") or {},
    }


def diff_metrics(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    keys = ("prediction", "evidence", "knowledge", "tie", "young_horse")
    scalar = {k: _delta(after.get(k), before.get(k)) for k in keys}

    conf_b = before.get("confidence") or {}
    conf_a = after.get("confidence") or {}
    conf_delta = {
        k: _delta(conf_a.get(k), conf_b.get(k))
        for k in ("High", "Medium", "Low", "Exploratory")
    }

    cov_b = before.get("coverage") or {}
    cov_a = after.get("coverage") or {}
    cov_delta = {
        k: _delta(cov_a.get(k), cov_b.get(k))
        for k in (
            "with_prediction_bundle",
            "with_race_result",
            "with_evidence_snapshot",
            "with_shadow_result",
            "mean_metadata_after",
        )
    }

    seg_b = before.get("segments") or {}
    seg_a = after.get("segments") or {}
    seg_delta: dict[str, Any] = {}
    for k in ("young_horse", "maiden", "stakes", "turf", "dirt"):
        seg_delta[k] = _delta(seg_a.get(k), seg_b.get(k))
    for nested in ("distance", "going", "pop_band"):
        nb = seg_b.get(nested) or {}
        na = seg_a.get(nested) or {}
        keys_n = set(nb) | set(na)
        seg_delta[nested] = {
            key: _delta(na.get(key), nb.get(key)) for key in sorted(keys_n)
        }

    return {
        "scalar": scalar,
        "confidence": conf_delta,
        "coverage": cov_delta,
        "segments": seg_delta,
    }


# ---------------------------------------------------------------------------
# Growth cycle — existing collectors only
# ---------------------------------------------------------------------------

StepFn = Callable[[], Any]


def _step_backfill() -> dict[str, Any]:
    from app.research.collector.runner import ResearchCollectorRunner
    from app.research.config import CollectorSettings

    settings = CollectorSettings.from_env()
    return ResearchCollectorRunner(settings).backfill(batch_size=20, max_rounds=40)


def _step_once() -> dict[str, Any]:
    from app.research.collector.runner import ResearchCollectorRunner
    from app.research.config import CollectorSettings

    settings = CollectorSettings.from_env()
    return ResearchCollectorRunner(settings).run_once()


def _step_historical() -> dict[str, Any]:
    from app.research.historical_bundle_ingest import run_and_write

    return run_and_write(rebuild_corpus=True)


def _step_corpus() -> dict[str, Any]:
    from app.research.prediction_corpus import run_and_write

    return run_and_write()


def _step_metadata() -> dict[str, Any]:
    from app.research.metadata_completion import run_and_write

    return run_and_write()


def _step_weakness() -> dict[str, Any]:
    from app.research.weakness_atlas import run_and_write

    return run_and_write()


def _step_discovery() -> dict[str, Any]:
    from app.research.evidence_discovery import run_and_write

    return run_and_write()


def _step_knowledge() -> dict[str, Any]:
    from app.research.knowledge_base import run_and_write

    return run_and_write()


GROWTH_PIPELINE: list[tuple[str, StepFn]] = [
    ("harvest_backfill", _step_backfill),
    ("harvest_once", _step_once),
    ("historical_bundle_ingest", _step_historical),
    ("build_prediction_corpus", _step_corpus),
    ("metadata_completion", _step_metadata),
    ("weakness_atlas", _step_weakness),
    ("evidence_discovery", _step_discovery),
    ("knowledge_base", _step_knowledge),
]


class CorpusGrowthOperation:
    def __init__(self) -> None:
        self.root = repo_root()
        self.evidence = evidence_root()
        self.reports = self.evidence / "reports"
        self.corpus_json = self.evidence / "corpus" / "v11-prediction-corpus.json"
        self.ops_dir = self.evidence / "ops" / "corpus_growth"
        self.docs = self.root / "docs" / "research"

    def _prev_snapshot(self, week: str) -> dict[str, Any]:
        self.ops_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(p for p in self.ops_dir.glob("*.json") if p.stem != week)
        if files:
            return _load_json(files[-1])
        # bootstrap from v111 growth doc era if present
        return {}

    def run(self, *, report_only: bool = False) -> dict[str, Any]:
        week = _week_id()
        before = snapshot_metrics(reports=self.reports, corpus_json=self.corpus_json)
        prev_ops = self._prev_snapshot(week)
        if prev_ops.get("after"):
            # WoW baseline prefers last completed ops after-metrics
            before_wow = prev_ops["after"]
        else:
            before_wow = before

        step_results: dict[str, Any] = {}
        errors: list[dict[str, str]] = []

        if not report_only:
            for name, fn in GROWTH_PIPELINE:
                try:
                    out = fn()
                    slim: dict[str, Any] = {"ok": True}
                    if isinstance(out, dict):
                        for k in (
                            "enqueued",
                            "processed",
                            "prediction_count",
                            "tie_count",
                            "young_horse_count",
                            "summary",
                            "week_id",
                            "sample",
                            "_outputs",
                        ):
                            if k in out:
                                slim[k] = out.get(k)
                    step_results[name] = slim
                except Exception as exc:  # noqa: BLE001
                    errors.append(
                        {
                            "step": name,
                            "error": str(exc),
                            "trace": traceback.format_exc()[-600:],
                        }
                    )
                    step_results[name] = {"ok": False, "error": str(exc)}

        after = snapshot_metrics(reports=self.reports, corpus_json=self.corpus_json)
        cycle_diff = diff_metrics(before, after)
        wow_diff = diff_metrics(before_wow, after)

        report = {
            "schema_version": SCHEMA_VERSION,
            "week_id": week,
            "generated_at": _now(),
            "product_mutation": False,
            "improvement_implementation": False,
            "purpose": "Mature research corpus / Evidence Snapshot accumulation",
            "pipeline": {
                "steps": step_results,
                "errors": errors,
                "report_only": report_only,
            },
            "before": before,
            "after": after,
            "cycle_diff": cycle_diff,
            "wow_diff": wow_diff,
            "weekly_kpis": {
                "Prediction": after.get("prediction"),
                "Evidence": after.get("evidence"),
                "Knowledge": after.get("knowledge"),
                "Coverage": after.get("coverage"),
                "Confidence": after.get("confidence"),
            },
            "segment_focus": SEGMENT_FOCUS,
            "targets": TARGETS,
        }

        self.ops_dir.mkdir(parents=True, exist_ok=True)
        (self.ops_dir / f"{week}.json").write_text(
            json.dumps(
                {
                    "week_id": week,
                    "generated_at": report["generated_at"],
                    "after": after,
                    "weekly_kpis": report["weekly_kpis"],
                    "wow_diff": wow_diff,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return report


def _fmt_seg_table(title: str, before: Any, after: Any, delta: Any) -> list[str]:
    lines = [f"### {title}", "", "| Key | Before | After | Δ |", "|-----|-------:|------:|--:|"]
    if isinstance(after, dict):
        keys = sorted(set(before or {}) | set(after or {}) | set(delta or {}))
        for k in keys:
            b = (before or {}).get(k)
            a = (after or {}).get(k)
            d = (delta or {}).get(k)
            d_s = f"+{d}" if isinstance(d, (int, float)) and d > 0 else str(d)
            lines.append(f"| `{k}` | {b} | {a} | {d_s} |")
    else:
        d = delta
        d_s = f"+{d}" if isinstance(d, (int, float)) and d > 0 else str(d)
        lines.append(f"| total | {before} | {after} | {d_s} |")
    lines.append("")
    return lines


def write_corpus_growth_md(report: dict[str, Any], path: Path) -> None:
    before = report.get("before") or {}
    after = report.get("after") or {}
    cdiff = report.get("cycle_diff") or {}
    wdiff = report.get("wow_diff") or {}
    scalar = cdiff.get("scalar") or {}
    wow_s = wdiff.get("scalar") or {}
    lines = [
        "# Research Corpus Growth",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"**Week:** `{report.get('week_id')}`  ",
        "**Scope:** Research materials only / Improvement implementation FORBIDDEN  ",
        "",
        "## Weekly KPIs",
        "",
        "| Metric | Before | After | Cycle Δ | WoW Δ |",
        "|--------|-------:|------:|--------:|------:|",
    ]
    for label, key in (
        ("Prediction", "prediction"),
        ("Evidence", "evidence"),
        ("Knowledge", "knowledge"),
        ("Tie", "tie"),
        ("Young Horse", "young_horse"),
    ):
        d = scalar.get(key)
        w = wow_s.get(key)
        d_s = f"+{d}" if isinstance(d, (int, float)) and d > 0 else str(d)
        w_s = f"+{w}" if isinstance(w, (int, float)) and w > 0 else str(w)
        lines.append(
            f"| {label} | {before.get(key)} | {after.get(key)} | {d_s} | {w_s} |"
        )

    cov_a = after.get("coverage") or {}
    cov_b = before.get("coverage") or {}
    cov_d = cdiff.get("coverage") or {}
    lines += [
        "",
        "## Coverage",
        "",
        "| Layer | Before | After | Δ |",
        "|-------|-------:|------:|--:|",
        f"| Evidence Snapshot | {cov_b.get('with_evidence_snapshot')} | {cov_a.get('with_evidence_snapshot')} | {cov_d.get('with_evidence_snapshot')} |",
        f"| Prediction Bundle | {cov_b.get('with_prediction_bundle')} | {cov_a.get('with_prediction_bundle')} | {cov_d.get('with_prediction_bundle')} |",
        f"| Race Result | {cov_b.get('with_race_result')} | {cov_a.get('with_race_result')} | {cov_d.get('with_race_result')} |",
        f"| Metadata mean | {_pct(cov_b.get('mean_metadata_after'))} | {_pct(cov_a.get('mean_metadata_after'))} | {cov_d.get('mean_metadata_after')} |",
        "",
        "## Confidence",
        "",
        "| Level | Before | After | Δ |",
        "|-------|-------:|------:|--:|",
    ]
    conf_a = after.get("confidence") or {}
    conf_b = before.get("confidence") or {}
    conf_d = cdiff.get("confidence") or {}
    for lvl in ("High", "Medium", "Low", "Exploratory"):
        d = conf_d.get(lvl)
        d_s = f"+{d}" if isinstance(d, (int, float)) and d > 0 else str(d)
        lines.append(
            f"| {lvl} | {conf_b.get(lvl)} | {conf_a.get(lvl)} | {d_s} |"
        )

    seg_a = after.get("segments") or {}
    seg_b = before.get("segments") or {}
    seg_d = cdiff.get("segments") or {}
    lines += ["", "## Segment sample growth", ""]
    for key, title in (
        ("young_horse", "Young Horse"),
        ("maiden", "未勝利 (maiden)"),
        ("stakes", "重賞 (stakes)"),
        ("turf", "芝 (turf)"),
        ("dirt", "ダート (dirt)"),
    ):
        lines += _fmt_seg_table(title, seg_b.get(key), seg_a.get(key), seg_d.get(key))
    lines += _fmt_seg_table(
        "距離 (distance)",
        seg_b.get("distance"),
        seg_a.get("distance"),
        seg_d.get("distance"),
    )
    lines += _fmt_seg_table(
        "馬場 (going)",
        seg_b.get("going"),
        seg_a.get("going"),
        seg_d.get("going"),
    )
    lines += _fmt_seg_table(
        "人気帯 (pop_band)",
        seg_b.get("pop_band"),
        seg_a.get("pop_band"),
        seg_d.get("pop_band"),
    )

    gap = after.get("gap") or {}
    lines += [
        "## Targets / Gap",
        "",
        f"- Prediction: `{after.get('prediction')}` / `{TARGETS['prediction']}` (gap `{gap.get('prediction')}`)",
        f"- Tie: `{after.get('tie')}` / `{TARGETS['tie']}` (gap `{gap.get('tie')}`)",
        f"- Young Horse: `{after.get('young_horse')}` / `{TARGETS['young_horse']}` (gap `{gap.get('young_horse')}`)",
        "",
        "## Pipeline",
        "",
    ]
    for name, res in ((report.get("pipeline") or {}).get("steps") or {}).items():
        if res.get("error"):
            lines.append(f"- `{name}`: FAIL `{res.get('error')}`")
        else:
            lines.append(f"- `{name}`: ok")
    errs = (report.get("pipeline") or {}).get("errors") or []
    if errs:
        lines += ["", "### Errors", ""]
        for e in errs:
            lines.append(f"- `{e.get('step')}`: {e.get('error')}")

    lines += [
        "",
        "## Guardrails",
        "",
        "- Evidence Snapshot accumulation only",
        "- No Prediction / PE / CE / AI improvement implementation",
        "- Knowledge maturity via sample growth, not product wiring",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_segments_md(report: dict[str, Any], path: Path) -> None:
    after = report.get("after") or {}
    seg = after.get("segments") or {}
    lines = [
        "# Research Corpus Growth — Segment Inventory",
        "",
        f"**Week:** `{report.get('week_id')}`  ",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        f"- Young Horse: `{seg.get('young_horse')}`",
        f"- Maiden: `{seg.get('maiden')}`",
        f"- Stakes: `{seg.get('stakes')}`",
        f"- Turf: `{seg.get('turf')}`",
        f"- Dirt: `{seg.get('dirt')}`",
        "",
        "## Distance",
        "",
        "| Bucket | N |",
        "|--------|--:|",
    ]
    for k, v in sorted((seg.get("distance") or {}).items()):
        lines.append(f"| `{k}` | {v} |")
    lines += ["", "## Going", "", "| Going | N |", "|-------|--:|"]
    for k, v in sorted((seg.get("going") or {}).items()):
        lines.append(f"| `{k}` | {v} |")
    lines += ["", "## Popularity band", "", "| Band | N |", "|------|--:|"]
    for k, v in sorted((seg.get("pop_band") or {}).items()):
        lines.append(f"| `{k}` | {v} |")
    lines += ["", "## Age group", "", "| Age | N |", "|-----|--:|"]
    for k, v in sorted((seg.get("by_age") or {}).items()):
        lines.append(f"| `{k}` | {v} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write(*, report_only: bool = False) -> dict[str, Any]:
    ops = CorpusGrowthOperation()
    report = ops.run(report_only=report_only)
    docs = ops.docs
    growth_md = docs / "v23-corpus-growth.md"
    seg_md = docs / "v23-corpus-segments.md"
    write_corpus_growth_md(report, growth_md)
    write_segments_md(report, seg_md)
    json_path = ops.evidence / "reports" / "v23-corpus-growth.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report["_outputs"] = {
        "growth_md": str(growth_md),
        "segments_md": str(seg_md),
        "json": str(json_path),
    }
    return report
