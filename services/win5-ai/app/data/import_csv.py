# -*- coding: utf-8 -*-
"""CSV → DB import (races / features)."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .db import migrate
from .repository import FeatureRepository, RaceRepository


def _as_int(v: Any) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def import_races_csv(path: Path, *, source: str | None = None) -> int:
    migrate()
    repo = RaceRepository()
    count = 0
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            race_id = (row.get("race_id") or "").strip()
            date = (row.get("date") or "").strip()[:10]
            venue = (row.get("course") or row.get("venue") or "").strip()
            race_no = _as_int(row.get("race_number") or row.get("race_no"))
            if not race_id or not date or not venue or not race_no:
                continue
            repo.upsert(
                {
                    "race_id": race_id,
                    "date": date,
                    "venue": venue,
                    "race_no": race_no,
                    "surface": row.get("target_surface") or row.get("surface"),
                    "distance": _as_int(row.get("target_distance") or row.get("distance")),
                    "class_label": row.get("race_name") or row.get("class_label"),
                    "field_size": _as_int(row.get("horse_count") or row.get("field_size")),
                    "source": source or path.name,
                    "extra": {k: v for k, v in row.items() if k not in {
                        "race_id", "date", "course", "venue", "race_number", "race_no"
                    }},
                }
            )
            count += 1
    return count


def import_features_csv(path: Path, *, feature_set: str = "runners_pace_market") -> int:
    migrate()
    repo = FeatureRepository()
    count = 0
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            race_id = (row.get("race_id") or "").strip()
            if not race_id:
                continue
            hn = _as_int(row.get("horse_number"))
            repo.upsert_row(
                race_id=race_id,
                horse_number=hn,
                horse_id=(row.get("horse_id") or None),
                payload=dict(row),
                feature_set=feature_set,
                source_file=str(path),
            )
            count += 1
    return count


def export_races_json(path: Path) -> int:
    catalog = RaceRepository().as_catalog()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(catalog.get("races") or [])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Expect AI CSV import/export")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_r = sub.add_parser("import-races")
    p_r.add_argument("csv")

    p_f = sub.add_parser("import-features")
    p_f.add_argument("csv")
    p_f.add_argument("--feature-set", default="runners_pace_market")

    p_e = sub.add_parser("export-races")
    p_e.add_argument("json_out")

    p_m = sub.add_parser("migrate")

    args = parser.parse_args(argv)
    if args.cmd == "migrate":
        print("applied", migrate())
        return 0
    if args.cmd == "import-races":
        n = import_races_csv(Path(args.csv))
        print(f"imported_races={n}")
        return 0
    if args.cmd == "import-features":
        n = import_features_csv(Path(args.csv), feature_set=args.feature_set)
        print(f"imported_features={n}")
        return 0
    if args.cmd == "export-races":
        n = export_races_json(Path(args.json_out))
        print(f"exported_races={n}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
