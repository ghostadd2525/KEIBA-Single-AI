Python sqlite3.Connection.backup / restore rehearsal v2
=======================================================

PACK=production_python_backup_restore_rehearsal_v2_20260911
THIS IS NOT A PRODUCTION BACKUP EXECUTION PACK.

v1 production_python_backup_restore_rehearsal_20260911.zip
(SHA256=ba896e345231e69ca7203d27ee312470786bcb969ad6818618ff13fbef7f1f6f)
is CHANGES_REQUIRED and is not overwritten.

Owner live schema inventory is imported as canonical:
  AUDIT_STATUS=SUCCESS
  SQLITE_VERSION=3.45.1
  SCHEMA_MIGRATIONS_COUNT=22
  HAS_019_FINAL_PREDICTIONS=YES
  HAS_020_SERIES=YES
  HAS_021_SERIES=YES
  HAS_PERSIST_019=NO
  HAS_PERSIST_022=NO
  PREDICTIONS_COLUMN_COUNT=8
  PREDICTIONS_EXISTING_COLUMNS=id,race_id,core_race_id,engine_source,fallback_reason,model_version,bundle_json,created_at
  PREDICTIONS_EXISTING_INDEX=idx_predictions_race(race_id,created_at)
  LIVE_SCHEMA_022_STRUCTURAL_COMPATIBILITY=YES

v2 contract
  1. source = file:<path>?mode=ro + uri=True + PRAGMA query_only=ON (verified)
  2. dest directory 0700 / dest file 0600 verified immediately after create
  3. writes a .tmp staging file; on failure staging is removed and completed dest is not left
  4. PRODUCTION_BACKUP_EXECUTED=YES only after a Production-named source is actually backed up
     (this pack never points at live Production; a fake-named isolated path proves the flag)
  5. table/index/trigger/view canonical SQL SHA compare
  6. schema_migrations + integrity_check + SHA256 + DB identity
  7. WAL committed snapshot test
  8. overwrite / disk full / integrity / schema / permission fail-closed
  9. self-contained fixture (no workspace migration tree)
  10. no Production backup execution and no Production APPLY

Re-run: python3 run_tests.py
