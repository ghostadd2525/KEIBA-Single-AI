# -*- coding: utf-8 -*-
"""
Win5AI legacy vs PI API pipeline output comparison.

Compares runners.csv, horse_history_raw.csv, runners_pace_market_features.csv
for the same race (date + venue + race_no / numeric_race_id).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Dataset definitions
# ---------------------------------------------------------------------------

DATASET_FILES = {
    "runners": "runners.csv",
    "horse_history_raw": "horse_history_raw.csv",
    "runners_pace_market_features": "runners_pace_market_features.csv",
}

# Columns excluded from value comparison (format / schema noise)
SKIP_COMPARE_COLS = frozenset({
    "race_id",  # legacy: 2026-07-19-01-10 vs PI: 20260719_10_福島
    "date_x", "date_y", "course_x", "course_y",
    "race_number_x", "race_number_y", "race_name_x", "race_name_y",
    "target_surface_x", "target_surface_y", "target_distance_x", "target_distance_y",
    "turn_x", "turn_y", "weather_x", "weather_y", "track_condition_x", "track_condition_y",
    "_runner_date_dt",
})

# Raw / parse-level columns (string or direct HTML parse)
RUNNERS_RAW_COLS = frozenset({
    "horse_name", "horse_url", "sex", "age", "weight_carried", "jockey",
    "odds", "popularity", "frame_number", "horse_number",
    "course", "race_name", "target_surface", "target_distance",
    "turn", "weather", "track_condition", "numeric_race_id", "date", "race_number",
})

HISTORY_RAW_COLS = frozenset({
    "history_date", "history_place", "history_race_name", "history_class",
    "history_frame_number", "history_horse_number", "history_distance_text",
    "history_surface", "history_distance", "history_course_condition",
    "history_finish", "history_popularity", "history_odds", "history_last3f",
    "history_margin", "history_weight", "history_passing", "history_time",
    "history_jockey", "history_horse_weight", "history_weather",
    "corner1", "corner2", "corner3", "corner4",
    "horse_name", "sex", "age", "jockey_today", "horse_url",
})

FEATURE_COMPUTED_COLS = frozenset({
    "history_count", "history_confidence", "last_finish", "last3_avg_finish",
    "avg_finish", "corner4_count", "last3_avg_corner4", "avg_corner4",
    "front_rate", "running_style", "style_confidence", "style_source",
    "same_distance_count", "same_distance_avg_finish",
    "same_surface_count", "same_surface_avg_finish",
    "distance_score", "history_score", "layoff_days", "layoff_penalty",
    "corner4_restored_flag", "used_history_date_col",
    "grade_points_last3_raw", "grade_points_last3",
    "stayer_grade_points_last3_raw", "stayer_grade_points_last3",
    "grade_distance_style_points_last3_raw", "grade_distance_style_points_last3",
    "style_distance_fit_weight", "grade_sample_confidence",
    "gate", "field_size", "gate_risk_score", "inside_traffic_risk",
    "style_disadvantage_score", "pace_collapse_risk_v2",
    "nige_count", "senkou_count", "sashi_count", "oikomi_count",
    "pace_pressure", "pace_pressure_rate", "pace_type",
    "race_label", "win5_leg",
})

JOIN_KEYS = {
    "runners": ["horse_id"],
    "horse_history_raw": ["horse_id", "history_date", "history_race_name"],
    "runners_pace_market_features": ["horse_id"],
}

# Remaining-difference taxonomy (Phase Y-4)
REMAINING_CAUSE_ORDER = (
    "parse_difference",
    "missing_data",
    "feature_calc_difference",
    "netkeiba_spec_difference",
)

NUMERIC_RTOL = 1e-4
NUMERIC_ATOL = 0.02

CAUSE_NETKEIBA = "netkeiba_spec_difference"
CAUSE_PARSE = "parse_difference"
CAUSE_FEATURE = "feature_calc_difference"
CAUSE_LEGACY = "legacy_bug"
CAUSE_SCHEMA = "schema_difference"
CAUSE_MISSING = "missing_data"

NETKEIBA_TIMING_COLS = frozenset({"odds", "popularity", "odds_today", "popularity_today"})


@dataclass
class DiffRow:
    dataset: str
    horse_id: str
    column: str
    legacy_value: Any
    pi_value: Any
    diff_abs: Optional[float]
    diff_pct: Optional[float]
    cause: str
    history_index: Optional[int] = None
    join_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "horse_id": self.horse_id,
            "history_index": self.history_index,
            "column": self.column,
            "legacy_value": self.legacy_value,
            "pi_value": self.pi_value,
            "diff_abs": self.diff_abs,
            "diff_pct": self.diff_pct,
            "cause": self.cause,
            "join_key": self.join_key,
        }


@dataclass
class DatasetReport:
    name: str
    legacy_rows: int = 0
    pi_rows: int = 0
    legacy_horse_ids: set[str] = field(default_factory=set)
    pi_horse_ids: set[str] = field(default_factory=set)
    only_legacy_horses: set[str] = field(default_factory=set)
    only_pi_horses: set[str] = field(default_factory=set)
    common_horses: set[str] = field(default_factory=set)
    compared_cells: int = 0
    matched_cells: int = 0
    missing_legacy: int = 0
    missing_pi: int = 0
    diffs: list[DiffRow] = field(default_factory=list)
    columns_only_legacy: list[str] = field(default_factory=list)
    columns_only_pi: list[str] = field(default_factory=list)
    columns_compared: list[str] = field(default_factory=list)

    @property
    def match_rate(self) -> float:
        if self.compared_cells == 0:
            return 0.0
        return self.matched_cells / self.compared_cells

    @property
    def cause_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for d in self.diffs:
            counts[d.cause] = counts.get(d.cause, 0) + 1
        return counts


@dataclass
class CompareResult:
    date: str
    venue: str
    race_no: int
    numeric_race_id: str
    datasets: dict[str, DatasetReport] = field(default_factory=dict)
    legacy_normalization: dict[str, Any] = field(default_factory=dict)

    @property
    def overall_match_rate(self) -> float:
        total = sum(r.compared_cells for r in self.datasets.values())
        matched = sum(r.matched_cells for r in self.datasets.values())
        if total == 0:
            return 0.0
        return matched / total

    @property
    def all_diffs(self) -> list[DiffRow]:
        out: list[DiffRow] = []
        for r in self.datasets.values():
            out.extend(r.diffs)
        return out

    @property
    def passes_target(self) -> bool:
        return self.adjusted_match_rate >= 0.99

    @property
    def adjusted_match_rate(self) -> float:
        """Match rate treating netkeiba odds/popularity timing gaps as expected."""
        exempt = sum(
            1 for d in self.all_diffs
            if d.cause == CAUSE_NETKEIBA and d.column in NETKEIBA_TIMING_COLS
        )
        total = sum(r.compared_cells for r in self.datasets.values())
        matched = sum(r.matched_cells for r in self.datasets.values())
        if total == 0:
            return 0.0
        return (matched + exempt) / total

    @property
    def remaining_cause_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for d in self.all_diffs:
            if d.cause in REMAINING_CAUSE_ORDER:
                counts[d.cause] = counts.get(d.cause, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _normalize_horse_id(val: Any) -> str:
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _normalize_numeric_race_id(val: Any) -> str:
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _is_blank(val: Any) -> bool:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return True
    if pd.isna(val):
        return True
    s = str(val).strip()
    return s in {"", "nan", "None", "NaT", "<NA>"}


def _normalize_url(val: Any) -> str:
    s = str(val).strip().rstrip("/") if not _is_blank(val) else ""
    return s


def _normalize_str(val: Any) -> str:
    if _is_blank(val):
        return ""
    s = str(val).strip()
    s = s.replace("\u3000", " ").replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s)
    return s


def _to_float(val: Any) -> Optional[float]:
    if _is_blank(val):
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _values_equal(col: str, legacy_val: Any, pi_val: Any) -> tuple[bool, Optional[float], Optional[float]]:
    """Return (equal, diff_abs, diff_pct)."""
    if col in ("horse_url",):
        return _normalize_url(legacy_val) == _normalize_url(pi_val), None, None

    if col.endswith("_date") or col == "date":
        l = _normalize_str(legacy_val).replace("/", "-")
        p = _normalize_str(pi_val).replace("/", "-")
        # normalize 2026/06/01 vs 2026-06-01
        l = re.sub(r"[^0-9]", "", l[:10]) if l else ""
        p = re.sub(r"[^0-9]", "", p[:10]) if p else ""
        return l == p, None, None

    lf = _to_float(legacy_val)
    pf = _to_float(pi_val)
    if lf is not None or pf is not None:
        if lf is None and pf is None:
            return True, None, None
        if lf is None or pf is None:
            return False, None, None
        diff = abs(lf - pf)
        denom = max(abs(lf), abs(pf), 1e-9)
        pct = diff / denom
        equal = math.isclose(lf, pf, rel_tol=NUMERIC_RTOL, abs_tol=NUMERIC_ATOL)
        return equal, diff, pct

    ls = _normalize_str(legacy_val)
    ps = _normalize_str(pi_val)
    return ls == ps, None, None


def _classify_cause(dataset: str, col: str, legacy_val: Any, pi_val: Any) -> str:
    if col in SKIP_COMPARE_COLS:
        return CAUSE_LEGACY

    if col in NETKEIBA_TIMING_COLS and not _is_blank(legacy_val) and _is_blank(pi_val):
        return CAUSE_NETKEIBA

    if _is_blank(legacy_val) and not _is_blank(pi_val):
        return CAUSE_MISSING
    if not _is_blank(legacy_val) and _is_blank(pi_val):
        return CAUSE_MISSING

    if dataset == "runners" and col in RUNNERS_RAW_COLS:
        return CAUSE_PARSE
    if dataset == "horse_history_raw" and col in HISTORY_RAW_COLS:
        return CAUSE_PARSE
    if dataset == "runners_pace_market_features" and col in FEATURE_COMPUTED_COLS:
        return CAUSE_FEATURE
    if dataset == "runners_pace_market_features" and col in RUNNERS_RAW_COLS:
        return CAUSE_PARSE
    if dataset == "runners_pace_market_features" and col in HISTORY_RAW_COLS:
        return CAUSE_PARSE

    if col in FEATURE_COMPUTED_COLS:
        return CAUSE_FEATURE
    if col in HISTORY_RAW_COLS or col in RUNNERS_RAW_COLS:
        return CAUSE_PARSE

    return CAUSE_SCHEMA


def normalize_legacy_history(
    *,
    legacy_dir: Path,
    numeric_race_id: str,
    client: Any | None = None,
    output_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Re-fetch missing horses for legacy history (Phase Y-2).

    Legacy history gaps are treated as legacy-side incompleteness, not PI defects.
    """
    from .netkeiba.client import NetkeibaClient
    from .netkeiba.horse_history import build_history_rows, fetch_horse_history

    runners_path = legacy_dir / "runners.csv"
    history_path = legacy_dir / "horse_history_raw.csv"
    legacy_history = filter_by_race(read_csv_flex(history_path), numeric_race_id) if history_path.exists() else pd.DataFrame()
    legacy_history = prepare_df(legacy_history, dataset="horse_history_raw")

    runners = filter_by_race(read_csv_flex(runners_path), numeric_race_id) if runners_path.exists() else pd.DataFrame()
    runners = prepare_df(runners)
    if runners.empty:
        return legacy_history, {"status": "no_runners", "refetched_horses": []}

    expected_horses = set(runners["horse_id"].dropna().astype(str))
    legacy_horses = set(legacy_history["horse_id"].dropna().astype(str)) if not legacy_history.empty else set()
    missing_horses = sorted(expected_horses - legacy_horses)

    info: dict[str, Any] = {
        "status": "ok",
        "expected_horses": len(expected_horses),
        "legacy_horses_before": len(legacy_horses),
        "missing_horses_before": missing_horses,
        "refetched_horses": [],
        "refetched_rows": 0,
    }

    if not missing_horses:
        if output_dir:
            out = output_dir / "horse_history_raw.csv"
            output_dir.mkdir(parents=True, exist_ok=True)
            legacy_history.to_csv(out, index=False, encoding="utf-8-sig")
            info["output_path"] = str(out)
        return legacy_history, info

    netkeiba = client or NetkeibaClient(min_interval_sec=2.0)
    supplemental: list[dict[str, Any]] = []
    for hid in missing_horses:
        runner_row = runners[runners["horse_id"] == hid].iloc[0].to_dict()
        try:
            parsed = fetch_horse_history(netkeiba, hid)
        except Exception as exc:
            info.setdefault("fetch_errors", []).append({"horse_id": hid, "error": str(exc)})
            continue
        if not parsed:
            continue
        supplemental.extend(build_history_rows(runner_row, parsed))
        info["refetched_horses"].append(hid)

    if supplemental:
        sup_df = pd.DataFrame(supplemental)
        sup_df = prepare_df(sup_df, dataset="horse_history_raw")
        combined = pd.concat([legacy_history, sup_df], ignore_index=True)
        info["refetched_rows"] = len(sup_df)
    else:
        combined = legacy_history

    # Backfill horse_number / odds_today from legacy runners (original export gaps).
    if not combined.empty and not runners.empty and "horse_id" in combined.columns:
        runner_cols = runners.set_index("horse_id")
        for col, src in (("horse_number", "horse_number"), ("odds_today", "odds"), ("popularity_today", "popularity")):
            if col not in combined.columns or src not in runner_cols.columns:
                continue
            for hid in combined["horse_id"].astype(str).unique():
                if hid not in runner_cols.index:
                    continue
                val = runner_cols.at[hid, src]
                mask = (combined["horse_id"].astype(str) == hid) & combined[col].isna()
                combined.loc[mask, col] = val

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        out = output_dir / "horse_history_raw.csv"
        combined.to_csv(out, index=False, encoding="utf-8-sig")
        info["output_path"] = str(out)

    info["legacy_horses_after"] = combined["horse_id"].nunique() if not combined.empty else 0
    return combined, info


# ---------------------------------------------------------------------------
# Data loading / filtering
# ---------------------------------------------------------------------------

def read_csv_flex(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.read_csv(path, encoding="utf-8", errors="replace")


def filter_by_race(df: pd.DataFrame, numeric_race_id: str) -> pd.DataFrame:
    if df.empty:
        return df
    work = df.copy()
    if "numeric_race_id" in work.columns:
        work["_nrid"] = work["numeric_race_id"].apply(_normalize_numeric_race_id)
        nrid = _normalize_numeric_race_id(numeric_race_id)
        return work[work["_nrid"] == nrid].drop(columns=["_nrid"])
    return work.iloc[0:0]


def _normalize_history_date(val: Any) -> str:
    if _is_blank(val):
        return ""
    s = _normalize_str(val).replace("/", "-")
    digits = re.sub(r"[^0-9]", "", s)
    return digits[:8] if len(digits) >= 8 else digits


def _normalize_history_race_name(val: Any) -> str:
    return _normalize_str(val)


def prepare_df(df: pd.DataFrame, *, dataset: str = "") -> pd.DataFrame:
    work = df.copy()
    if "horse_id" in work.columns:
        work["horse_id"] = work["horse_id"].apply(_normalize_horse_id)
    if "numeric_race_id" in work.columns:
        work["numeric_race_id"] = work["numeric_race_id"].apply(_normalize_numeric_race_id)
    if "history_index" in work.columns:
        work["history_index"] = pd.to_numeric(work["history_index"], errors="coerce").astype("Int64")
    if dataset == "horse_history_raw":
        if "history_date" in work.columns:
            work["history_date"] = work["history_date"].apply(_normalize_history_date)
        if "history_race_name" in work.columns:
            work["history_race_name"] = work["history_race_name"].apply(_normalize_history_race_name)
    return work


def resolve_numeric_race_id(
    legacy_dir: Path,
    date: str,
    venue: str,
    race_no: int,
) -> Optional[str]:
    """Resolve numeric_race_id from legacy runners.csv."""
    runners_path = legacy_dir / "runners.csv"
    if not runners_path.exists():
        return None
    df = read_csv_flex(runners_path)
    if "course" in df.columns and "race_number" in df.columns:
        mask = (
            df["date"].astype(str).str.strip() == date
        ) & (
            df["course"].astype(str).str.strip() == venue
        ) & (
            pd.to_numeric(df["race_number"], errors="coerce") == race_no
        )
        hit = df[mask]
        if not hit.empty and "numeric_race_id" in hit.columns:
            return _normalize_numeric_race_id(hit.iloc[0]["numeric_race_id"])
    if "numeric_race_id" in df.columns:
        return _normalize_numeric_race_id(df.iloc[0]["numeric_race_id"])
    return None


# ---------------------------------------------------------------------------
# Core comparison
# ---------------------------------------------------------------------------

def compare_dataset(
    name: str,
    legacy_df: pd.DataFrame,
    pi_df: pd.DataFrame,
    *,
    ignore_pi_only_horses: bool = False,
    legacy_incomplete_horses: set[str] | None = None,
) -> DatasetReport:
    report = DatasetReport(name=name)
    legacy_df = prepare_df(legacy_df, dataset=name)
    pi_df = prepare_df(pi_df, dataset=name)

    report.legacy_rows = len(legacy_df)
    report.pi_rows = len(pi_df)

    if "horse_id" in legacy_df.columns:
        report.legacy_horse_ids = set(legacy_df["horse_id"].dropna().astype(str))
    if "horse_id" in pi_df.columns:
        report.pi_horse_ids = set(pi_df["horse_id"].dropna().astype(str))

    report.only_legacy_horses = report.legacy_horse_ids - report.pi_horse_ids
    report.only_pi_horses = report.pi_horse_ids - report.legacy_horse_ids
    report.common_horses = report.legacy_horse_ids & report.pi_horse_ids

    legacy_cols = set(legacy_df.columns)
    pi_cols = set(pi_df.columns)
    report.columns_only_legacy = sorted(legacy_cols - pi_cols - SKIP_COMPARE_COLS)
    report.columns_only_pi = sorted(pi_cols - legacy_cols - SKIP_COMPARE_COLS)

    common_cols = sorted(
        (legacy_cols & pi_cols) - SKIP_COMPARE_COLS - {"horse_id", "history_index"}
    )
    report.columns_compared = common_cols

    join_keys = JOIN_KEYS.get(name, ["horse_id"])
    legacy_incomplete = legacy_incomplete_horses or set()

    for hk in report.only_legacy_horses | report.only_pi_horses:
        if ignore_pi_only_horses and hk in report.only_pi_horses and hk in legacy_incomplete:
            continue
        cause = CAUSE_NETKEIBA
        side = "legacy_only" if hk in report.only_legacy_horses else "pi_only"
        report.diffs.append(DiffRow(
            dataset=name,
            horse_id=hk,
            column="(horse_id)",
            legacy_value=hk if side == "legacy_only" else "",
            pi_value=hk if side == "pi_only" else "",
            diff_abs=None,
            diff_pct=None,
            cause=cause,
            join_key=side,
        ))

    if legacy_df.empty and pi_df.empty:
        return report

    if legacy_df.empty or pi_df.empty:
        report.missing_legacy = report.legacy_rows
        report.missing_pi = report.pi_rows
        return report

    for key in join_keys:
        if key not in legacy_df.columns:
            legacy_df[key] = ""
        if key not in pi_df.columns:
            pi_df[key] = ""

    # Deduplicate on join keys to prevent merge fan-out
    legacy_df = legacy_df.drop_duplicates(subset=join_keys, keep="last")
    pi_df = pi_df.drop_duplicates(subset=join_keys, keep="last")

    merged = legacy_df.merge(
        pi_df,
        on=join_keys,
        how="inner",
        suffixes=("_legacy", "_pi"),
    )

    for _, row in merged.iterrows():
        horse_id = _normalize_horse_id(row.get("horse_id", ""))
        hist_idx = row.get("history_index_legacy", row.get("history_index"))
        if pd.isna(hist_idx):
            hist_idx = row.get("history_index_pi")
        hist_idx_int = int(hist_idx) if pd.notna(hist_idx) else None

        for col in common_cols:
            lv = row.get(f"{col}_legacy", row.get(col))
            pv = row.get(f"{col}_pi", row.get(col))

            report.compared_cells += 1

            if _is_blank(lv) and _is_blank(pv):
                report.matched_cells += 1
                continue

            equal, diff_abs, diff_pct = _values_equal(col, lv, pv)
            if equal:
                report.matched_cells += 1
                continue

            if _is_blank(lv):
                report.missing_legacy += 1
            if _is_blank(pv):
                report.missing_pi += 1

            cause = _classify_cause(name, col, lv, pv)
            report.diffs.append(DiffRow(
                dataset=name,
                horse_id=horse_id,
                column=col,
                legacy_value=lv,
                pi_value=pv,
                diff_abs=diff_abs,
                diff_pct=diff_pct,
                cause=cause,
                history_index=hist_idx_int,
                join_key="|".join(str(row.get(k, "")) for k in join_keys),
            ))

    return report


def compare_all(
    *,
    date: str,
    venue: str,
    race_no: int,
    legacy_dir: Path,
    pi_dir: Path,
    numeric_race_id: Optional[str] = None,
    normalize_legacy: bool = True,
) -> CompareResult:
    nrid = numeric_race_id or resolve_numeric_race_id(legacy_dir, date, venue, race_no)
    if not nrid:
        raise FileNotFoundError(
            f"numeric_race_id could not be resolved for {date} {venue} {race_no}R"
        )

    result = CompareResult(
        date=date,
        venue=venue,
        race_no=race_no,
        numeric_race_id=nrid,
    )

    legacy_history_override: pd.DataFrame | None = None
    legacy_incomplete_horses: set[str] = set()
    if normalize_legacy:
        norm_dir = legacy_dir.parent / "legacy_normalized" / f"{date}_{venue}_{race_no:02d}R"
        legacy_history_override, norm_info = normalize_legacy_history(
            legacy_dir=legacy_dir,
            numeric_race_id=nrid,
            output_dir=norm_dir,
        )
        result.legacy_normalization = norm_info
        legacy_incomplete_horses = set(norm_info.get("missing_horses_before") or [])

    for name, filename in DATASET_FILES.items():
        legacy_path = legacy_dir / filename
        pi_path = pi_dir / filename

        if name == "horse_history_raw" and legacy_history_override is not None:
            legacy_df = legacy_history_override.copy()
        else:
            legacy_df = filter_by_race(read_csv_flex(legacy_path), nrid) if legacy_path.exists() else pd.DataFrame()
        pi_df = filter_by_race(read_csv_flex(pi_path), nrid) if pi_path.exists() else pd.DataFrame()

        result.datasets[name] = compare_dataset(
            name,
            legacy_df,
            pi_df,
            ignore_pi_only_horses=(name == "horse_history_raw"),
            legacy_incomplete_horses=legacy_incomplete_horses,
        )

    return result


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------

def write_diff_csv(result: CompareResult, path: Path) -> None:
    rows = [d.to_dict() for d in result.all_diffs]
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=[
            "dataset", "horse_id", "history_index", "column",
            "legacy_value", "pi_value", "diff_abs", "diff_pct", "cause", "join_key",
        ])
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def result_to_metrics(result: CompareResult) -> dict[str, Any]:
    """Extract match-rate metrics from a CompareResult."""
    datasets: dict[str, float] = {}
    for name, ds in result.datasets.items():
        datasets[name] = round(ds.match_rate, 6)
    return {
        "overall": round(result.overall_match_rate, 6),
        "adjusted_excl_netkeiba_odds": round(result.adjusted_match_rate, 6),
        "diff_rows": len(result.all_diffs),
        "remaining_by_cause": result.remaining_cause_counts,
        "datasets": datasets,
    }


def load_baseline(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    import json
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_report_md(
    result: CompareResult,
    path: Path,
    *,
    legacy_dir: Path,
    pi_dir: Path,
    baseline: dict[str, Any] | None = None,
) -> None:
    lines: list[str] = []
    lines.append("# Win5AI vs PI API 比較レポート")
    lines.append("")
    lines.append("## 対象レース")
    lines.append("")
    lines.append(f"| 項目 | 値 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 日付 | {result.date} |")
    lines.append(f"| 会場 | {result.venue} |")
    lines.append(f"| レース番号 | {result.race_no}R |")
    lines.append(f"| numeric_race_id | {result.numeric_race_id} |")
    lines.append(f"| Legacy ディレクトリ | `{legacy_dir}` |")
    lines.append(f"| PI ディレクトリ | `{pi_dir}` |")
    lines.append("")

    rate = result.overall_match_rate
    adjusted = result.adjusted_match_rate
    target = 0.99
    status = "PASS" if result.passes_target else "FAIL"
    lines.append("## 総合結果")
    lines.append("")
    lines.append(f"- **一致率**: {rate:.2%}")
    lines.append(f"- **調整一致率** (netkeibaオッズ/人気タイミング差除外): {adjusted:.2%}")
    lines.append(f"- **目標**: {target:.0%} 以上（調整一致率で判定）")
    lines.append(f"- **判定**: **{status}**")
    lines.append(f"- **差分行数**: {len(result.all_diffs)}")
    lines.append("")

    if baseline:
        lines.append("## Before / After 一致率比較")
        lines.append("")
        lines.append("| データセット | Before | After | 変化 |")
        lines.append("|-------------|--------|-------|------|")
        before_overall = baseline.get("overall", 0.0)
        after_overall = result.overall_match_rate
        lines.append(
            f"| **総合** | {before_overall:.2%} | {after_overall:.2%} | {after_overall - before_overall:+.2%} |"
        )
        before_ds = baseline.get("datasets") or {}
        for name, ds in result.datasets.items():
            b = before_ds.get(name, 0.0)
            a = ds.match_rate
            lines.append(f"| {name} | {b:.2%} | {a:.2%} | {a - b:+.2%} |")
        before_diffs = baseline.get("diff_rows", 0)
        lines.append(
            f"| 差分行数 | {before_diffs} | {len(result.all_diffs)} | {len(result.all_diffs) - before_diffs:+d} |"
        )
        lines.append("")
        if baseline.get("note"):
            lines.append(f"*{baseline['note']}*")
            lines.append("")

    remaining = result.remaining_cause_counts
    remaining_total = sum(remaining.values())
    netkeiba_cnt = remaining.get("netkeiba_spec_difference", 0)
    actionable_total = remaining_total - netkeiba_cnt
    total_cells = sum(ds.compared_cells for ds in result.datasets.values())
    lines.append("## Remaining Difference")
    lines.append("")
    lines.append(f"- **残差件数（全分類）**: {remaining_total}")
    lines.append(f"- **残差件数（netkeiba_spec除外）**: {actionable_total}")
    lines.append(f"- **残差一致率（4分類ベース）**: {result.overall_match_rate:.2%}")
    lines.append(f"- **調整一致率（netkeiba_spec除外）**: {result.adjusted_match_rate:.2%}")
    if total_cells > 0:
        lines.append(f"- **比較セル総数**: {total_cells}")
    lines.append("")
    lines.append("| 分類 | 件数 | 説明 |")
    lines.append("|------|------|------|")
    remaining_desc = {
        "parse_difference": "HTMLパース差（sex/age/馬番/斤量/jockey 等）",
        "missing_data": "片方のみ値あり（取得失敗・欠損）",
        "feature_calc_difference": "特徴量計算差（history_score / running_style 等）",
        "netkeiba_spec_difference": "netkeiba仕様・取得タイミング差（odds/人気/HTML構造）",
    }
    for cause in REMAINING_CAUSE_ORDER:
        cnt = remaining.get(cause, 0)
        lines.append(f"| `{cause}` | {cnt} | {remaining_desc.get(cause, '')} |")
    lines.append("")

    if result.legacy_normalization:
        norm = result.legacy_normalization
        lines.append("### Legacy history 正規化 (Phase Y-2)")
        lines.append("")
        lines.append(f"- 期待 horse_id 数: {norm.get('expected_horses', '—')}")
        lines.append(f"- 正規化前 Legacy horse_id 数: {norm.get('legacy_horses_before', '—')}")
        missing = norm.get("missing_horses_before") or []
        if missing:
            lines.append(f"- 欠損していた horse_id ({len(missing)}): {', '.join(missing)}")
        refetched = norm.get("refetched_horses") or []
        if refetched:
            lines.append(f"- AJAX 再取得した horse_id ({len(refetched)}): {', '.join(refetched)}")
        if norm.get("output_path"):
            lines.append(f"- 正規化出力: `{norm.get('output_path')}`")
        lines.append("")

    # Cause summary
    all_causes: dict[str, int] = {}
    for ds in result.datasets.values():
        for cause, cnt in ds.cause_counts.items():
            all_causes[cause] = all_causes.get(cause, 0) + cnt

    lines.append("## 差分原因分類")
    lines.append("")
    lines.append("| 原因分類 | 件数 | 説明 |")
    lines.append("|---------|------|------|")
    cause_desc = {
        CAUSE_NETKEIBA: "netkeiba仕様差（取得タイミング・HTML構造・馬の増減）",
        CAUSE_PARSE: "パース差（HTML解析ロジックの違い）",
        CAUSE_FEATURE: "特徴量差（集計ロジックまたは入力データ差）",
        CAUSE_LEGACY: "Legacy側既知差異（race_id形式等、比較対象外列）",
        CAUSE_SCHEMA: "スキーマ差異（列名・merge由来列の有無）",
        CAUSE_MISSING: "欠損項目（片方のみ値あり）",
    }
    for cause in [CAUSE_NETKEIBA, CAUSE_PARSE, CAUSE_FEATURE, CAUSE_MISSING, CAUSE_SCHEMA, CAUSE_LEGACY]:
        cnt = all_causes.get(cause, 0)
        if cnt > 0:
            lines.append(f"| `{cause}` | {cnt} | {cause_desc.get(cause, '')} |")
    lines.append("")

    for name, ds in result.datasets.items():
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"| 指標 | Legacy | PI |")
        lines.append(f"|------|--------|-----|")
        lines.append(f"| 行数 | {ds.legacy_rows} | {ds.pi_rows} |")
        lines.append(f"| horse_id 数 | {len(ds.legacy_horse_ids)} | {len(ds.pi_horse_ids)} |")
        lines.append(f"| 共通 horse_id | {len(ds.common_horses)} | |")
        lines.append(f"| Legacy のみ | {len(ds.only_legacy_horses)} | |")
        lines.append(f"| PI のみ | {len(ds.only_pi_horses)} | |")
        lines.append(f"| 比較セル数 | {ds.compared_cells} | |")
        lines.append(f"| 一致セル数 | {ds.matched_cells} | |")
        lines.append(f"| **一致率** | **{ds.match_rate:.2%}** | |")
        lines.append(f"| 欠損 (Legacy) | {ds.missing_legacy} | |")
        lines.append(f"| 欠損 (PI) | {ds.missing_pi} | |")
        lines.append("")

        if ds.only_legacy_horses:
            lines.append(f"**Legacy のみの horse_id**: {', '.join(sorted(ds.only_legacy_horses))}")
            lines.append("")
        if ds.only_pi_horses:
            lines.append(f"**PI のみの horse_id**: {', '.join(sorted(ds.only_pi_horses))}")
            lines.append("")

        if ds.columns_only_legacy:
            lines.append(f"**Legacy のみの列** ({len(ds.columns_only_legacy)}): "
                         f"{', '.join(ds.columns_only_legacy[:20])}"
                         + (" ..." if len(ds.columns_only_legacy) > 20 else ""))
            lines.append("")
        if ds.columns_only_pi:
            lines.append(f"**PI のみの列** ({len(ds.columns_only_pi)}): "
                         f"{', '.join(ds.columns_only_pi[:20])}"
                         + (" ..." if len(ds.columns_only_pi) > 20 else ""))
            lines.append("")

        if ds.diffs:
            lines.append("### 差分詳細（上位20件）")
            lines.append("")
            lines.append("| horse_id | 列 | Legacy | PI | 差分 | 原因 |")
            lines.append("|----------|-----|--------|-----|------|------|")
            for d in ds.diffs[:20]:
                diff_str = ""
                if d.diff_abs is not None:
                    diff_str = f"{d.diff_abs:.4f}"
                lv = str(d.legacy_value)[:30]
                pv = str(d.pi_value)[:30]
                hidx = f" [{d.history_index}]" if d.history_index is not None else ""
                lines.append(
                    f"| {d.horse_id}{hidx} | `{d.column}` | {lv} | {pv} | {diff_str} | {d.cause} |"
                )
            if len(ds.diffs) > 20:
                lines.append(f"| ... | | | | | 他 {len(ds.diffs) - 20} 件は compare_diff.csv 参照 |")
            lines.append("")

    lines.append("## 推奨アクション")
    lines.append("")
    if result.passes_target:
        lines.append("- 一致率99%以上を達成。PI API パイプラインは Win5AI 互換と判断可能。")
    else:
        causes = all_causes
        if causes.get(CAUSE_PARSE, 0) > 0:
            lines.append("- **パース差**: shutuba / horse page パーサを legacy 版と突合")
        if causes.get(CAUSE_FEATURE, 0) > 0:
            lines.append("- **特徴量差**: 入力 history 行が一致しているか確認後、features.py の式を再検証")
        if causes.get(CAUSE_NETKEIBA, 0) > 0:
            lines.append("- **netkeiba仕様差**: 取得時刻差による odds/人気変動、または HTML 構造変更を確認")
        if causes.get(CAUSE_MISSING, 0) > 0:
            lines.append("- **欠損項目**: PI pipeline の fetch 失敗ログを確認")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
