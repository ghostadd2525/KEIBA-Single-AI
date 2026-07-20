# -*- coding: utf-8 -*-
"""CSV → DB import (ETL pipeline wrapper)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .db import migrate
from .etl import EtlPipeline, import_day, run_scheduled_etl
from .validation import validate_all_races
from .repository import RaceRepository


def import_races_csv(path: Path, *, source: str | None = None) -> int:
    result = EtlPipeline().import_races_csv(path, source=source)
    return result.races


def import_features_csv(path: Path, *, feature_set: str = "runners_pace_market") -> int:
    result = EtlPipeline().import_features_csv(path, feature_set=feature_set)
    return result.features


def export_races_json(path: Path) -> int:
    catalog = RaceRepository().as_catalog()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(catalog.get("races") or [])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Expect AI CSV import/export (ETL)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_r = sub.add_parser("import-races")
    p_r.add_argument("csv")

    p_f = sub.add_parser("import-features")
    p_f.add_argument("csv")
    p_f.add_argument("--feature-set", default="runners_pace_market")

    p_d = sub.add_parser("import-day")
    p_d.add_argument("data_dir")
    p_d.add_argument("--date", default="", help="YYYY-MM-DD subdir (optional)")

    p_s = sub.add_parser("schedule")
    p_s.add_argument("race_date", help="YYYY-MM-DD")
    p_s.add_argument("--source", default="", help="csv|database|api|jra")
    p_s.add_argument("--data-dir", default="")

    p_v = sub.add_parser("validate")
    p_v.add_argument("--date", default="", help="YYYY-MM-DD filter (optional)")

    p_e = sub.add_parser("export-races")
    p_e.add_argument("json_out")

    sub.add_parser("migrate")

    args = parser.parse_args(argv)
    if args.cmd == "migrate":
        print("applied", migrate())
        return 0
    if args.cmd == "import-races":
        result = EtlPipeline().import_races_csv(Path(args.csv))
        print(f"imported_races={result.races} skipped={result.skipped}")
        return 0
    if args.cmd == "import-features":
        result = EtlPipeline().import_features_csv(
            Path(args.csv), feature_set=args.feature_set
        )
        print(
            f"imported_features={result.features} entries={result.entries} "
            f"horses={result.horses} skipped={result.skipped}"
        )
        return 0
    if args.cmd == "import-day":
        result = import_day(Path(args.data_dir), race_date=args.date or None)
        print(json.dumps(result.as_dict(), ensure_ascii=False))
        return 0
    if args.cmd == "schedule":
        from pathlib import Path as P

        result = run_scheduled_etl(
            args.race_date,
            source_type=args.source or None,
            data_dir=P(args.data_dir) if args.data_dir else None,
        )
        print(json.dumps(result.as_dict(), ensure_ascii=False))
        return 0
    if args.cmd == "validate":
        out = validate_all_races(race_date=args.date or None)
        print(json.dumps(out, ensure_ascii=False))
        return 0
    if args.cmd == "export-races":
        n = export_races_json(Path(args.json_out))
        print(f"exported_races={n}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
