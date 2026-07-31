# -*- coding: utf-8 -*-
"""A-05 Shadow harness — batch orchestration (Lab-only).

Does not start production Shadow evaluation by default.
shadow_runtime_enabled must be explicitly True to run the A-05 arm.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .. import flags
from .comparator import build_comparator_report
from .config import ShadowSettings, load_shadow_settings
from .logger import ShadowLogger
from .metrics import build_metrics_bundle
from .runner import run_shadow_race

LAB_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = LAB_ROOT / "baselines" / "a05_shadow"


def run_shadow_batch(
    corpus: list[dict[str, Any]],
    *,
    settings: ShadowSettings | None = None,
    production_picks: dict[str, str] | None = None,
    write_logs: bool = True,
) -> dict[str, Any]:
    """Run Shadow over a Lab-shaped corpus.

    production_picks: optional map race_id -> production decision pick.
    When omitted, Control = Lab identity (flags OFF).
    """
    settings = settings or load_shadow_settings()
    production_picks = production_picks or {}
    # Prove production Flag default remains OFF before batch
    flags.reset_flags_to_default()
    prod_default_off = flags.F_V3_A05_ADM_FAVSAFE_ENABLED is False

    records: list[dict[str, Any]] = []
    for row in corpus:
        rid = str(row.get("race_id") or "")
        ctx = row.get("context") or {"race_id": rid, "field_size": len(row.get("runners") or [])}
        rec = run_shadow_race(
            ctx,
            row.get("runners") or [],
            production_pick=production_picks.get(rid),
            winner_id=row.get("winner_id"),
            winner_rank=row.get("winner_rank"),
            purchase_eligible=bool(row.get("purchase_eligible", True)),
            settings=settings,
        )
        rec["purchase_eligible"] = bool(row.get("purchase_eligible", True))
        records.append(rec)

    logger_path = None
    if write_logs and settings.shadow_runtime_enabled:
        logger = ShadowLogger(settings)
        logger.write_many(records)
        logger_path = str(logger.path)

    # Flag default must still be OFF after batch
    flags.reset_flags_to_default()
    prod_default_off_after = flags.F_V3_A05_ADM_FAVSAFE_ENABLED is False

    bundle = build_metrics_bundle(
        records,
        settings=settings,
        production_a05_default_off=prod_default_off and prod_default_off_after,
        a03_co_enabled=False,
        window_days=None,
        control_path_healthy=True,
    )
    return {
        "records": records,
        "n": len(records),
        "log_path": logger_path,
        "production_a05_default_off": prod_default_off_after,
        **bundle,
    }


def write_shadow_artifacts(
    result: dict[str, Any],
    *,
    out_dir: Path | None = None,
) -> dict[str, str]:
    out = out_dir or ARTIFACTS
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "metrics": out / "shadow_metrics.json",
        "comparator": out / "shadow_comparator_report.json",
        "acceptance": out / "shadow_acceptance.json",
        "settings": out / "shadow_settings.json",
        "sample_records": out / "shadow_sample_records.json",
    }
    paths["metrics"].write_text(
        json.dumps(result.get("metrics") or {}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    comp = build_comparator_report(result.get("records") or [])
    paths["comparator"].write_text(
        json.dumps(comp, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    paths["acceptance"].write_text(
        json.dumps(result.get("acceptance") or {}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    paths["settings"].write_text(
        json.dumps(result.get("settings") or {}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # Keep artifacts small — first 20 records
    sample = (result.get("records") or [])[:20]
    paths["sample_records"].write_text(
        json.dumps(sample, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {k: str(v) for k, v in paths.items()}


__all__ = ["run_shadow_batch", "write_shadow_artifacts", "ARTIFACTS"]
