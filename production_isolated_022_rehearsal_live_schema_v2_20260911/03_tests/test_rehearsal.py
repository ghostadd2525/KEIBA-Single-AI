#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2 isolated 022 rehearsal tests. Assert the full Owner 22-name set."""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REHEARSE = ROOT / "02_code" / "rehearse.py"
FLAGS = ROOT / "FLAGS.txt"
LIVE = ROOT / "02_code" / "live_schema.sql"

OWNER = [
    "001_init",
    "002_race_identity",
    "003_supply_platform",
    "004_user_domain",
    "005_results_eval",
    "006_result_automation",
    "007_collect_c0",
    "008_collect_contract_1_1",
    "009_user_race_results",
    "010_user_progress_audit",
    "011_research_evidence",
    "012_research_snapshot_features",
    "013_research_prediction_corpus",
    "014_research_historical_ingest",
    "015_research_race_meta",
    "016_research_knowledge_base",
    "017_research_knowledge_validation",
    "018_research_candidate_review",
    "019_final_predictions",
    "020_research_corpus_canonical",
    "020_user_challenge_lifecycle",
    "021_user_challenge_point_events",
]
FAKES = ("020_live_series", "021_live_series")


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def kv(out: str, key: str) -> str:
    prefix = key + "="
    found = ""
    for line in out.splitlines():
        if line.startswith(prefix):
            found = line[len(prefix):]
    return found


def main() -> int:
    failures: list[str] = []
    src = REHEARSE.read_text(encoding="utf-8")
    ast.parse(src)
    expect(True, "ast_parse", failures)
    banned = os.sep + os.path.join("workspace", "services", "win5-ai")
    expect(banned not in src, "rehearse_self_contained", failures)
    expect("idx_predictions_race" in LIVE.read_text(encoding="utf-8"), "live_index_sql", failures)
    flags = FLAGS.read_text(encoding="utf-8")
    expect("NEXT_STEP=INDEPENDENT_REVIEW_OF_022_REHEARSAL_V2" in flags, "next_step_not_stale", failures)
    expect("BACKUP_V2_AND_LIVE_SCHEMA_BASED_ISOLATED_REHEARSAL" not in flags, "old_next_step_absent", failures)
    expect("PRODUCTION_BACKUP_EXECUTION_PACK=NO" in flags, "no_exec_pack", failures)
    expect("CLAIMED_WRONG_SEED_ZIP_OVERWRITTEN=NO" in flags, "claimed_zip_kept", failures)

    env = os.environ.copy()
    env["PREDICTION_RUNS_ENABLED"] = "0"
    env.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
    r = subprocess.run([sys.executable, str(REHEARSE)], capture_output=True, text=True, env=env, cwd=str(ROOT))
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    out = r.stdout or ""
    expect(r.returncode == 0, "rehearse_exit0", failures)
    expect(kv(out, "SEEDED_MIGRATION_COUNT") == "22", "seeded_count_22", failures)
    expect(kv(out, "SEEDED_MIGRATION_SET_MATCH_OWNER") == "YES", "set_match", failures)
    expect(kv(out, "SEEDED_MISSING_COUNT") == "0", "missing_0", failures)
    expect(kv(out, "SEEDED_EXTRA_COUNT") == "0", "extra_0", failures)
    expect(kv(out, "SEEDED_DUPLICATE_COUNT") == "0", "dupes_0", failures)
    expect(kv(out, "SEEDED_FAKE_020_021_COUNT") == "0", "fakes_0", failures)
    seeded = kv(out, "SEEDED_SCHEMA_MIGRATIONS").split(",")
    expect(seeded == OWNER, "seeded_names_exact_list", failures)
    expect(set(seeded) == set(OWNER), "seeded_names_exact_set", failures)
    expect(len(seeded) == 22, "seeded_len", failures)
    expect(all(f not in seeded for f in FAKES), "no_fake_names_in_seeded_list", failures)
    expect(kv(out, "PREDICTIONS_COLUMNS_MATCH_OWNER") == "YES", "pred_cols", failures)
    expect(kv(out, "IDX_PREDICTIONS_RACE_MATCH_OWNER") == "YES", "pred_index", failures)
    expect(kv(out, "MIGRATION_FIRST_APPLY_PASS") == "YES", "first_apply", failures)
    expect(kv(out, "MIGRATION_SECOND_APPLY_NOOP") == "YES", "second_noop", failures)
    expect(kv(out, "MIGRATION_PARTIAL_REPAIR_PASS") == "YES", "partial_repair", failures)
    expect(kv(out, "MIGRATION_WRONG_INDEX_REPAIR_PASS") == "YES", "wrong_index_repair", failures)
    expect(kv(out, "EXISTING_NULL_ROW_COMPAT") == "YES", "null_300", failures)
    expect(kv(out, "CONVERSATION_RA_CHALLENGE_NULL_COMPAT") == "YES", "legacy_null", failures)
    expect(kv(out, "ROLLBACK_INDEX_ABSENT") == "YES", "rollback_index", failures)
    expect(kv(out, "ROLLBACK_COLUMNS_REMAIN") == "YES", "rollback_cols", failures)
    expect(kv(out, "PREDICTION_RUNS_ENABLED") == "0", "runs_disabled", failures)
    expect(kv(out, "HTTP_STARTED") == "NO", "no_http", failures)
    expect(kv(out, "GET_SURFACE_MODIFIED") == "NO", "no_get", failures)
    expect(kv(out, "NEXT_STEP") == "INDEPENDENT_REVIEW_OF_022_REHEARSAL_V2", "next_step_emit", failures)
    expect("BACKUP_V2_AND_LIVE_SCHEMA_BASED_ISOLATED_REHEARSAL" not in out, "old_next_step_not_emitted", failures)
    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
