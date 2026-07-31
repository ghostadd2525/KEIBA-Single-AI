# -*- coding: utf-8 -*-
"""CLI — Version21 Causal Evidence Research."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.causal_evidence import run_and_write


def main() -> int:
    argparse.ArgumentParser(
        description="V21 Causal Evidence — Feature→Condition→Outcome (research only)"
    ).parse_args()
    report = run_and_write()
    print(
        json.dumps(
            {
                "ok": True,
                "sample": report.get("sample"),
                "n_condition_effects": len(report.get("condition_effects") or []),
                "n_3way": len(
                    (report.get("interactions") or {}).get("interactions_3way") or []
                ),
                "n_4way": len(
                    (report.get("interactions") or {}).get("interactions_4way") or []
                ),
                "outputs": report.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
