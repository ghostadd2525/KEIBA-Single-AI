Disabled POST code deploy — review bundle v5
===========================================

PACK=production_disabled_post_code_deploy_review_v5_20260912
SUPERSEDES_REVIEW=production_disabled_post_code_deploy_review_v4_20260912
V1_ZIP=production_disabled_post_code_deploy_review_20260912.zip
V1_ZIP_SHA256=474cb805c99d81235287b0a2a8a74fe9406c88f963024b98e6e1bf9a8154caaf
V2_ZIP=production_disabled_post_code_deploy_review_v2_20260912.zip
V2_ZIP_SHA256=38b6ea058335663a54b10263657195b26eea05146532a6d07019da90dd11a620
V3_ZIP=production_disabled_post_code_deploy_review_v3_20260912.zip
V3_ZIP_SHA256=b324b9d94478e32987e62166ccb8032ab4dd480732b2b9a1f1138bbc524820c7
V4_ZIP=production_disabled_post_code_deploy_review_v4_20260912.zip
V4_ZIP_SHA256=77ecd36924719fbcfd3cdb0a58e19fc8160013e6267201be48e1199634676f74
V1_ZIP_OVERWRITE=NO
V2_ZIP_OVERWRITE=NO
V3_ZIP_OVERWRITE=NO
V4_ZIP_OVERWRITE=NO
ACTIVE_STEP=1_POST_CODE_PRODUCTION_DEPLOY_PREPARATION
THIS IS NOT A PRODUCTION EXECUTION PACK.
THIS IS NOT AN APPLY PACK.

022 schema is already COMMITTED on Production. This bundle only
prepares the Prediction Run code for a later Owner deploy while
POST stays disabled.

  PREDICTION_RUNS_ENABLED=0
  EXPECT_AI_ALLOW_MIGRATION_022=unset/0
  SITE_CORPUS_ACCUMULATION_ACTIVE=NO
  POST_CALL_ALLOWED=NO
  PRODUCTION_CODE_DEPLOY_ALLOWED=NO
  OWNER_DEPLOY_APPROVED=NO
  POST_CODE_PRODUCTION_DEPLOYED=NO
  022_REAPPLY=NO
  SYSTEMD_CHANGED=NO
  ENV_CHANGED=NO

v4 independent review
---------------------
PASS: ZIP SHA / integrity / SHA256SUMS all files / bundled 25a3f88
base 2565 files / disabled gate / deploy_files.txt.
CHANGES_REQUIRED: first independent `python3 run_tests.py` failed
test_separate_process_concurrency with
  sqlite3.OperationalError: database is locked
at app/data/repository/__init__.py _connect_idempotent()
  PRAGMA journal_mode = WAL
The same ZIP passed on re-run. Concurrent processes each changed
journal_mode on connect. That is a flaky test, not a lock swallow.

v5 fix
------
_connect_idempotent() no longer changes journal_mode.
busy_timeout=30000 and isolation_level=IMMEDIATE stay.
WAL, when wanted, is initialized once in app.data.db.migrate()
via ensure_wal_journal(): read current mode, write WAL only when
it is not already WAL. database is locked is not swallowed.
4 processes / same key: one prediction_id, one create, rest replay,
predictions row count 1.
run_tests.py re-runs the 51-test suite twice and
test_separate_process_concurrency 20 times in a row.
SHA256SUMS.txt is generated last after every other file is final.

Canonical local implementation:
  review v5 files + review v5 022 rebase of db.py + v2 gate
  origin/main base commit: 25a3f88b8aab61a5462c06efa133b21865ef6083

Do not overwrite:
  production_disabled_post_code_deploy_review_20260912.zip
  production_disabled_post_code_deploy_review_v2_20260912.zip
  production_disabled_post_code_deploy_review_v3_20260912.zip
  production_disabled_post_code_deploy_review_v4_20260912.zip
  any APPLY / backup / measure ZIP

Independent re-run (no git clone):
  sha256sum -c SHA256SUMS.txt
  python3 run_tests.py

Do not create a Production deploy/execution pack from this run.

NEXT_STEP=INDEPENDENT_REVIEW_OF_DISABLED_POST_CODE_DEPLOY_V5_BUNDLE
