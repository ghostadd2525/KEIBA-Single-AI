#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "02_powershell" / "baseline_disabled_post_dry_run.py"
PS1 = ROOT / "02_powershell" / "OWNER_READONLY.ps1"
FLAGS = ROOT / "FLAGS.txt"
BAN = ROOT / "V1_V4_DO_NOT_OVERWRITE.txt"
CONSTRAINTS = ROOT / "04_constraints.txt"


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def main() -> int:
    failures: list[str] = []
    src = PY.read_text(encoding="utf-8")
    ps = PS1.read_text(encoding="utf-8")
    flags = FLAGS.read_text(encoding="utf-8")
    ban = BAN.read_text(encoding="utf-8")
    cons = CONSTRAINTS.read_text(encoding="utf-8")

    ast.parse(src)
    expect(True, "python_ast_parse", failures)

    expect('method="POST"' not in src and "method='POST'" not in src, "no_post_method", failures)
    expect('method="GET"' in src, "get_only_request", failures)
    expect("/v1/predictions/" not in src, "no_detail_path", failures)
    expect("quote(" not in src, "no_url_quote_id", failures)
    expect("Never call POST /v1/prediction-runs" in src, "never_post_doc", failures)
    expect("/v1/challenge/monthly" not in src or "Never GET /v1/challenge/monthly" in src, "no_challenge_monthly_call", failures)
    expect("conversation/chat" not in src, "no_conversation_chat", failures)
    expect("admin/results/run" not in src, "no_ra_run", failures)
    expect("127.0.0.1:8000" in src, "loopback_only", failures)
    expect("mode=ro" in src, "sqlite_ro", failures)
    expect("INSERT INTO" not in src and "UPDATE " not in src and "DELETE " not in src, "no_sql_write", failures)
    expect("ALTER TABLE" not in src, "no_alter", failures)
    expect("DROP INDEX" not in src, "no_drop_index", failures)
    expect("CREATE INDEX" not in src, "no_create_index", failures)
    expect(".backup" not in src, "no_sqlite_backup", failures)
    expect("shutil.copy" not in src, "no_shutil_copy", failures)
    expect("systemctl start" not in src, "no_systemd_start", failures)
    expect("systemctl restart" not in src, "no_systemd_restart", failures)
    expect("EXPECT_AI_ALLOW_MIGRATION_019=1" not in src, "no_enable_019", failures)
    expect("PREDICTION_RUNS_ENABLED=1" not in src, "no_enable_post", failures)
    expect("os.environ[" not in src or "os.environ.setdefault" in src, "no_env_assign", failures)
    expect("git push" not in src, "no_git_push", failures)
    expect("SELECT COUNT(*) FROM predictions" in src, "count_predictions", failures)
    expect("PRAGMA table_info(predictions)" in src, "pragma_columns", failures)
    expect("PRAGMA index_list(predictions)" in src, "pragma_indexes", failures)
    expect("uq_predictions_idempotency_key_not_null" in src, "index_name", failures)
    expect("PARTIAL_UNIQUE_INDEX_ONLY" in src, "rollback_target", failures)
    expect("NO_RESEARCH_WEEK" in src, "research_week_flag", failures)
    expect("NO_NOT_EVALUATED" in src, "today_pred_not_success", failures)
    expect("date=2099-01-01" in src or "SAFE_EMPTY_DATE" in src, "safe_empty_date", failures)

    expect("??" not in ps, "ps51_no_null_coalesce", failures)
    expect(" && " not in ps, "ps51_no_andand", failures)
    expect(" || " not in ps, "ps51_no_oror", failures)
    expect("python3 -" in ps, "stdin", failures)
    expect("scp " not in ps.lower(), "no_scp", failures)
    expect("POST_ENDPOINT_CALLED=NO" in ps, "ps_no_post", failures)
    expect("MIGRATION_019_APPLY=NO" in ps, "ps_no_019", failures)
    expect("DETAIL_GET_ALLOWED=NO" in ps, "ps_no_detail", failures)
    expect("refuse_overwrite_existing_output" in ps, "ps_no_overwrite_out", failures)
    expect("baseline_disabled_post_dry_run_readonly_20260911_output_" in ps, "ps_output_name", failures)
    start_i = ps.find("[void]$proc.Start()")
    out_i = ps.find("$stdoutTask = $proc.StandardOutput.ReadToEndAsync()")
    err_i = ps.find("$stderrTask = $proc.StandardError.ReadToEndAsync()")
    wait_i = ps.find("$proc.WaitForExit($TimeoutMs)")
    expect(start_i != -1 and out_i > start_i and out_i < wait_i, "stdout_drain_before_wait", failures)
    expect(start_i != -1 and err_i > start_i and err_i < wait_i, "stderr_drain_before_wait", failures)

    expect("PRODUCTION_DRY_RUN_READY=NO" in flags, "flag_dry_run_no", failures)
    expect("PRODUCTION_APPLY_READY=NO" in flags, "flag_apply_no", failures)
    expect("OWNER_APPLY_APPROVED=NO" in flags, "flag_owner_no", failures)
    expect("APPLY_EXECUTED=NO" in flags, "flag_exec_no", failures)
    expect("PR23_MERGED=NO" in flags, "flag_pr23", failures)
    expect("LOCAL_IMPLEMENTATION_APPROVED=YES" in flags, "flag_local_yes", failures)
    expect("V4_ZIP_OVERWRITTEN=NO" in flags, "flag_v4_keep", failures)
    expect("4fd4dc88315f7dbab3f495dea249ad1fcb715b375a64de85762a779571aa2c80" in ban, "ban_v4_sha", failures)
    expect("POST /v1/prediction-runs" in cons, "cons_no_post", failures)
    expect("GET /v1/predictions/{race_id}" in cons, "cons_no_detail", failures)

    sys.path.insert(0, str(PY.parent))
    import baseline_disabled_post_dry_run as audit  # type: ignore

    expect(audit.research_week_active(datetime(2026, 9, 11, 12, 0, tzinfo=timezone(timedelta(hours=9)))), "rw_yes_sep11", failures)
    expect(not audit.research_week_active(datetime(2026, 9, 12, 0, 0, tzinfo=timezone(timedelta(hours=9)))), "rw_no_sep12", failures)

    ok, why = audit.backup_possible(exists=True, readable=True, parent_writable=True, sqlite_cli=True, copy_executed=False)
    expect(ok and why == "POSSIBLE_NOT_EXECUTED", "backup_possible", failures)
    bad, why_bad = audit.backup_possible(exists=True, readable=True, parent_writable=True, sqlite_cli=True, copy_executed=True)
    expect((not bad) and why_bad == "COPY_EXECUTED_FORBIDDEN", "backup_no_copy", failures)

    absent = audit.classify_019(columns={"id", "race_id"}, index_names={"idx_predictions_race"}, index_sql=None, migrations={"001_init"})
    expect(absent["status"] == "absent" and not absent["applied"] and not absent["rollback_needed"], "019_absent", failures)
    complete_sql = "CREATE UNIQUE INDEX uq_predictions_idempotency_key_not_null ON predictions(idempotency_key) WHERE idempotency_key IS NOT NULL"
    complete = audit.classify_019(
        columns=set(audit.RUN_COLUMNS) | {"id"},
        index_names={audit.IDEMPOTENCY_INDEX},
        index_sql=complete_sql,
        migrations={audit.MIGRATION_019},
    )
    expect(complete["status"] == "complete" and complete["applied"] and complete["rollback_needed"], "019_complete", failures)
    mismatch = audit.classify_019(
        columns=set(audit.RUN_COLUMNS),
        index_names={audit.IDEMPOTENCY_INDEX},
        index_sql="CREATE INDEX uq_predictions_idempotency_key_not_null ON predictions(race_id)",
        migrations=set(),
    )
    expect(mismatch["status"] == "error", "019_mismatch_error", failures)

    env = audit.envelope_schema({"ok": True, "data": [{"race_id": "x"}], "meta": {"engine": "mock"}})
    expect(env["schema_ok"] and env["data_type"] == "list", "envelope_ok", failures)
    env2 = audit.envelope_schema({"ok": True, "data": [{"race_id": "y"}], "meta": {"engine": "mock"}})
    expect(audit.schemas_equal(env, env2), "envelope_equal_keys", failures)

    enabled, src_en = audit.prediction_runs_enabled_effective({"proc": None, "systemd": None, "live_default": None})
    expect((not enabled) and "defaults_to_0" in src_en, "enabled_default_0", failures)
    enabled1, _ = audit.prediction_runs_enabled_effective({"proc": "1", "systemd": None, "live_default": None})
    expect(enabled1, "enabled_proc_1", failures)

    parsed = audit.parse_environ_blob("PREDICTION_RUNS_ENABLED=0\0AI_API_KEY=secret\0AI_ENGINE=mock")
    expect(parsed.get("PREDICTION_RUNS_ENABLED") == "0", "parse_flag", failures)
    expect("AI_API_KEY" not in parsed, "parse_skip_secret", failures)

    legacy = audit.source_uses_legacy_insert(
        'INSERT INTO predictions(\n              race_id, engine_source, fallback_reason, model_version, bundle_json, created_at\n            ) VALUES (?,?,?,?,?,?)'
    )
    expect(legacy, "legacy_insert_true", failures)
    not_legacy = audit.source_uses_legacy_insert(
        "INSERT INTO predictions(\n race_id, persist_source, bundle_json\n) VALUES (?,?,?)"
    )
    expect(not not_legacy, "legacy_insert_false_when_persist", failures)

    compared = audit.live_vs_review({"app/main.py": None})
    expect((not compared["equal"]) and compared["missing"] >= 1, "live_mismatch_expected", failures)
    all_match = {k: v for k, v in audit.REVIEW_FILE_SHA256.items()}
    compared_eq = audit.live_vs_review(all_match)
    expect(compared_eq["equal"], "live_equal_when_hashes_match", failures)

    print("ALL_PASS" if not failures else "FAIL_COUNT=%d" % len(failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
