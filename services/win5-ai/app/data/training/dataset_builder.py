# -*- coding: utf-8 -*-
"""Training Dataset Builder — PC-3B priority."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ..db import connect, migrate


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _platform_data() -> Path:
    root = (os.environ.get("AI_PLATFORM_ROOT") or "").strip()
    if root:
        p = Path(root) / "data"
        if p.is_dir():
            return p
    for candidate in (
        Path(__file__).resolve().parents[4],
        Path(__file__).resolve().parents[3],
    ):
        if (candidate / "data").is_dir():
            return candidate / "data"
    return Path(__file__).resolve().parents[4] / "data"


def _read_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            df = pd.read_csv(path, encoding=enc, low_memory=False)
            df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
            return df
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, low_memory=False)


def _normalize_name(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
        .str.replace("\u3000", " ", regex=False)
        .str.strip()
        .str.replace(" ", "", regex=False)
    )


@dataclass
class SourceSpec:
    name: str
    feature_path: Path
    result_path: Path


@dataclass
class DatasetBuildResult:
    train: pd.DataFrame = field(default_factory=pd.DataFrame)
    validation: pd.DataFrame = field(default_factory=pd.DataFrame)
    test: pd.DataFrame = field(default_factory=pd.DataFrame)
    full: pd.DataFrame = field(default_factory=pd.DataFrame)
    report: dict[str, Any] = field(default_factory=dict)
    output_dir: Path | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "report": self.report,
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "splits": {
                "train_rows": int(len(self.train)),
                "validation_rows": int(len(self.validation)),
                "test_rows": int(len(self.test)),
            },
        }


class TrainingDatasetBuilder:
    """Collect multi-year features + labels, split, and emit statistics."""

    DEFAULT_SOURCE_NAMES = (
        ("main", "runners_pace_market_features.csv", "win5_resultwithdate.csv"),
        ("demo", "demo_runners_pace_market_features.csv", "demo_win5_resultwithdate.csv"),
    )

    def __init__(self, data_dir: Path | None = None) -> None:
        migrate()
        self.data_dir = data_dir or _platform_data()
        self.output_dir = Path(
            os.environ.get("EXPECT_AI_TRAINING_DIR")
            or Path(__file__).resolve().parents[2] / "var" / "training"
        )

    def default_sources(self) -> list[SourceSpec]:
        return [
            SourceSpec(name, self.data_dir / feature, self.data_dir / result)
            for name, feature, result in self.DEFAULT_SOURCE_NAMES
        ]

    def build(
        self,
        *,
        sources: list[SourceSpec] | None = None,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        min_rows_for_training: int = 500,
        year_from: int | None = None,
        year_to: int | None = None,
        write_csv: bool = True,
    ) -> DatasetBuildResult:
        frames: list[pd.DataFrame] = []
        source_stats: list[dict[str, Any]] = []

        for spec in sources or self.default_sources():
            merged, stat = self._merge_source(spec)
            source_stats.append(stat)
            if merged is not None and not merged.empty:
                merged["source"] = spec.name
                frames.append(merged)

        if not frames:
            report = {
                "schema_version": "training-dataset/1.0",
                "generated_at": _now(),
                "ready_for_training": False,
                "reason": "no_labeled_rows",
                "sources": source_stats,
            }
            return DatasetBuildResult(report=report)

        full = pd.concat(frames, ignore_index=True)
        full = self._dedupe(full)
        full = self._apply_year_filter(full, year_from, year_to)
        full = self._ensure_labels(full)

        if full.empty:
            report = {
                "schema_version": "training-dataset/1.0",
                "generated_at": _now(),
                "ready_for_training": False,
                "reason": "empty_after_filter",
                "sources": source_stats,
            }
            return DatasetBuildResult(report=report)

        train, val, test = self._split_by_date(full, train_ratio, val_ratio)
        report = self._statistics(full, train, val, test, source_stats)
        report["ready_for_training"] = int(len(full)) >= min_rows_for_training
        report["min_rows_for_training"] = min_rows_for_training

        out_dir = self.output_dir
        if write_csv:
            out_dir.mkdir(parents=True, exist_ok=True)
            train.to_csv(out_dir / "train.csv", index=False, encoding="utf-8-sig")
            val.to_csv(out_dir / "validation.csv", index=False, encoding="utf-8-sig")
            test.to_csv(out_dir / "test.csv", index=False, encoding="utf-8-sig")
            full.to_csv(out_dir / "full.csv", index=False, encoding="utf-8-sig")
            (out_dir / "dataset_report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._persist_registry(report)

        return DatasetBuildResult(
            train=train,
            validation=val,
            test=test,
            full=full,
            report=report,
            output_dir=out_dir if write_csv else None,
        )

    def _merge_source(self, spec: SourceSpec) -> tuple[pd.DataFrame | None, dict[str, Any]]:
        stat: dict[str, Any] = {"name": spec.name, "feature_path": str(spec.feature_path)}
        if not spec.feature_path.exists() or not spec.result_path.exists():
            stat["status"] = "missing_files"
            return None, stat

        feat = _read_csv(spec.feature_path)
        result = _read_csv(spec.result_path)
        req_f = ["race_id", "horse_name"]
        req_r = ["race_id", "horse_name", "finish_rank", "target_win", "result_date"]
        if any(c not in feat.columns for c in req_f):
            stat["status"] = "feature_columns_missing"
            return None, stat
        if any(c not in result.columns for c in req_r):
            stat["status"] = "result_columns_missing"
            return None, stat

        result = self._filter_result_rows(result)
        if result.empty:
            stat["status"] = "no_usable_labels"
            return None, stat

        feat = feat.copy()
        result = result.copy()
        feat["race_id_norm"] = feat["race_id"].astype(str).str.strip()
        feat["horse_name_norm"] = _normalize_name(feat["horse_name"])
        result["race_id_norm"] = result["race_id"].astype(str).str.strip()
        result["horse_name_norm"] = _normalize_name(result["horse_name"])

        merged = feat.merge(
            result[
                [
                    "race_id_norm",
                    "horse_name_norm",
                    "finish_rank",
                    "target_win",
                    "result_date",
                ]
            ],
            on=["race_id_norm", "horse_name_norm"],
            how="inner",
        )
        result_races = set(result["race_id_norm"].unique())
        race_mask = merged["race_id_norm"].isin(result_races)
        merged = merged[race_mask].copy()
        merged["target_win"] = pd.to_numeric(merged["target_win"], errors="coerce").fillna(0).astype(int)
        merged["finish_rank"] = pd.to_numeric(merged.get("finish_rank"), errors="coerce")
        merged["result_date"] = pd.to_datetime(merged["result_date"], errors="coerce")

        stat.update(
            {
                "status": "ok",
                "feature_rows": int(len(feat)),
                "result_rows": int(len(result)),
                "merged_rows": int(len(merged)),
                "races": int(merged["race_id_norm"].nunique()),
                "winners": int(merged["target_win"].sum()),
            }
        )
        return merged, stat

    def _filter_result_rows(self, result: pd.DataFrame) -> pd.DataFrame:
        work = result.copy()
        target = pd.to_numeric(work["target_win"], errors="coerce")
        valid = target.isin([0, 1])
        race_date = work["race_id"].astype(str).str.extract(r"^(\d{4}-\d{2}-\d{2})")[0]
        race_dt = pd.to_datetime(race_date, errors="coerce")
        res_dt = pd.to_datetime(work["result_date"], errors="coerce")
        date_ok = race_dt.notna() & res_dt.notna() & (race_dt.dt.normalize() == res_dt.dt.normalize())
        return work[valid & date_ok].copy()

    def _dedupe(self, df: pd.DataFrame) -> pd.DataFrame:
        keys = [c for c in ["race_id_norm", "horse_name_norm", "result_date"] if c in df.columns]
        if not keys:
            keys = [c for c in ["race_id", "horse_name"] if c in df.columns]
        if keys:
            return df.drop_duplicates(subset=keys, keep="last").reset_index(drop=True)
        return df

    def _apply_year_filter(
        self,
        df: pd.DataFrame,
        year_from: int | None,
        year_to: int | None,
    ) -> pd.DataFrame:
        if "result_date" not in df.columns:
            return df
        dates = pd.to_datetime(df["result_date"], errors="coerce")
        if year_from is not None:
            df = df[dates.dt.year >= year_from]
            dates = pd.to_datetime(df["result_date"], errors="coerce")
        if year_to is not None:
            df = df[dates.dt.year <= year_to]
        return df.reset_index(drop=True)

    def _ensure_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        if "label_win" not in df.columns:
            df = df.copy()
            df["label_win"] = pd.to_numeric(df.get("target_win"), errors="coerce").fillna(0).astype(int)
        if "label_relevance" not in df.columns:
            df = df.copy()

            def rel(row: pd.Series) -> float:
                fr = row.get("finish_rank")
                if pd.isna(fr) or fr <= 0:
                    return 0.0
                if fr == 1:
                    return 1.0
                if fr <= 3:
                    return 0.5
                return 0.0

            df["label_relevance"] = df.apply(rel, axis=1)
        return df

    def _split_by_date(
        self,
        df: pd.DataFrame,
        train_ratio: float,
        val_ratio: float,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        work = df.sort_values("result_date").reset_index(drop=True)
        n = len(work)
        if n == 0:
            empty = work.iloc[0:0]
            return empty, empty, empty
        t_end = int(n * train_ratio)
        v_end = int(n * (train_ratio + val_ratio))
        return work.iloc[:t_end], work.iloc[t_end:v_end], work.iloc[v_end:]

    def _statistics(
        self,
        full: pd.DataFrame,
        train: pd.DataFrame,
        val: pd.DataFrame,
        test: pd.DataFrame,
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        dates = pd.to_datetime(full["result_date"], errors="coerce")
        by_year = (
            dates.dt.year.value_counts().sort_index().astype(int).to_dict()
            if dates.notna().any()
            else {}
        )
        feature_cols = [
            c
            for c in full.columns
            if c
            not in {
                "race_id",
                "horse_name",
                "race_id_norm",
                "horse_name_norm",
                "target_win",
                "finish_rank",
                "result_date",
                "label_win",
                "label_relevance",
                "source",
            }
        ]
        null_rates = {}
        for col in feature_cols[:40]:
            null_rates[col] = round(float(full[col].isna().mean()), 4)

        def split_summary(part: pd.DataFrame) -> dict[str, Any]:
            if part.empty:
                return {"rows": 0, "races": 0, "win_rate": 0.0}
            return {
                "rows": int(len(part)),
                "races": int(part["race_id_norm"].nunique() if "race_id_norm" in part.columns else part["race_id"].nunique()),
                "win_rate": round(float(part["label_win"].mean()), 4),
            }

        return {
            "schema_version": "training-dataset/1.0",
            "generated_at": _now(),
            "sources": sources,
            "totals": {
                "rows": int(len(full)),
                "races": int(full["race_id_norm"].nunique() if "race_id_norm" in full.columns else full["race_id"].nunique()),
                "winners": int(full["label_win"].sum()),
                "date_min": str(dates.min())[:10] if dates.notna().any() else None,
                "date_max": str(dates.max())[:10] if dates.notna().any() else None,
            },
            "by_year": {str(k): v for k, v in by_year.items()},
            "splits": {
                "train": split_summary(train),
                "validation": split_summary(val),
                "test": split_summary(test),
            },
            "feature_null_rates_top40": null_rates,
        }

    def _persist_registry(self, report: dict[str, Any]) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS training_datasets (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  generated_at TEXT NOT NULL,
                  ready INTEGER NOT NULL,
                  rows_total INTEGER,
                  report_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT INTO training_datasets(generated_at, ready, rows_total, report_json)
                VALUES (?,?,?,?)
                """,
                (
                    report.get("generated_at") or _now(),
                    1 if report.get("ready_for_training") else 0,
                    int((report.get("totals") or {}).get("rows") or 0),
                    json.dumps(report, ensure_ascii=False),
                ),
            )
            conn.commit()
        finally:
            conn.close()
