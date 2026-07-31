# -*- coding: utf-8 -*-
"""A-05 Shadow implementation smoke tests (not a live evaluation window)."""
from __future__ import annotations

import unittest

from v3_lab import flags
from v3_lab.shadow import (
    aggregate_shadow_metrics,
    build_race_diff_record,
    classify_diff,
    evaluate_acceptance,
    load_shadow_settings,
    run_shadow_race,
)
from v3_lab.shadow.harness import run_shadow_batch, write_shadow_artifacts


def _race(rid: str, *, field: int = 12, winner_rank: int = 1) -> dict:
    runners = []
    for i in range(1, field + 1):
        style = "senko" if i < 7 else ("oikomi" if i == 8 else "senko")
        runners.append(
            {
                "horse_id": f"{rid}-H{i}",
                "model_rank": i,
                "win_prob": max(0.02, 0.20 - 0.01 * (i - 1)),
                "odds": 3.0 + i,
                "history_score": 0.70 if i >= 7 else 0.20 - 0.01 * (i - 1),
                "running_style": style,
                "popularity": i,
            }
        )
    winner_id = f"{rid}-H{winner_rank}"
    return {
        "race_id": rid,
        "context": {"race_id": rid, "field_size": field},
        "runners": runners,
        "winner_id": winner_id,
        "winner_rank": winner_rank,
        "purchase_eligible": True,
    }


class A05ShadowImplTest(unittest.TestCase):
    def test_production_flag_default_remains_off(self) -> None:
        flags.reset_flags_to_default()
        self.assertFalse(flags.F_V3_A05_ADM_FAVSAFE_ENABLED)
        s = load_shadow_settings()
        self.assertFalse(s.shadow_runtime_enabled)

    def test_fail_open_keeps_control(self) -> None:
        race = _race("sh-fail", winner_rank=1)
        settings = load_shadow_settings(shadow_runtime_enabled=True, fail_open=True)

        # Force shadow failure by temporarily breaking A-05 import path via bad runners type
        # Use production_pick and ensure exception path: empty context ok; inject via monkeypatch
        from v3_lab.shadow import runner as runner_mod

        original = runner_mod._shadow_pick_a05

        def boom(*_a, **_k):
            raise RuntimeError("forced_shadow_failure")

        runner_mod._shadow_pick_a05 = boom  # type: ignore
        try:
            rec = run_shadow_race(
                race["context"],
                race["runners"],
                production_pick=f"{race['race_id']}-H1",
                winner_id=race["winner_id"],
                winner_rank=1,
                settings=settings,
            )
        finally:
            runner_mod._shadow_pick_a05 = original  # type: ignore

        self.assertEqual(rec["control_pick"], f"{race['race_id']}-H1")
        self.assertFalse(rec["shadow_ok"])
        self.assertIsNotNone(rec["shadow_error"])
        self.assertFalse(rec["purchase_executed"])
        flags.reset_flags_to_default()
        self.assertFalse(flags.F_V3_A05_ADM_FAVSAFE_ENABLED)

    def test_runtime_disabled_skips_a05(self) -> None:
        race = _race("sh-off")
        settings = load_shadow_settings(shadow_runtime_enabled=False)
        rec = run_shadow_race(
            race["context"],
            race["runners"],
            production_pick=f"{race['race_id']}-H1",
            winner_id=race["winner_id"],
            settings=settings,
        )
        self.assertEqual(rec["shadow_error"], "shadow_runtime_disabled")
        self.assertIsNone(rec["shadow_pick"])
        self.assertFalse(flags.F_V3_A05_ADM_FAVSAFE_ENABLED)

    def test_batch_smoke_and_artifacts(self) -> None:
        corpus = [
            _race("sh-1", winner_rank=1),
            _race("sh-2", winner_rank=8),
        ]
        settings = load_shadow_settings(shadow_runtime_enabled=True, phase="S0")
        result = run_shadow_batch(corpus, settings=settings, write_logs=False)
        self.assertEqual(2, result["n"])
        self.assertTrue(result["production_a05_default_off"])
        self.assertIn("metrics", result)
        self.assertIn("acceptance", result)
        paths = write_shadow_artifacts(result)
        self.assertTrue(paths["comparator"].endswith("shadow_comparator_report.json"))
        for rec in result["records"]:
            d = build_race_diff_record(rec)
            self.assertIn(
                d["status"],
                {
                    "unchanged_hit",
                    "unchanged_miss",
                    "improved",
                    "worsened",
                    "worsened_winner_rank1",
                    "unlabeled",
                    "pick_changed_unlabeled",
                },
            )
            classify_diff(rec)
        m = aggregate_shadow_metrics(result["records"], settings=settings)
        acc = evaluate_acceptance(m, settings=settings, window_days=1)
        self.assertIn("hard_checks", acc)
        flags.reset_flags_to_default()
        self.assertFalse(flags.F_V3_A05_ADM_FAVSAFE_ENABLED)


if __name__ == "__main__":
    unittest.main()
