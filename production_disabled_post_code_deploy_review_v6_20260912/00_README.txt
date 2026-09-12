Disabled POST code deploy — review bundle v6
===========================================

PACK=production_disabled_post_code_deploy_review_v6_20260912
SUPERSEDES_REVIEW=production_disabled_post_code_deploy_review_v5_20260912
V1_ZIP=production_disabled_post_code_deploy_review_20260912.zip
V1_ZIP_SHA256=474cb805c99d81235287b0a2a8a74fe9406c88f963024b98e6e1bf9a8154caaf
V2_ZIP=production_disabled_post_code_deploy_review_v2_20260912.zip
V2_ZIP_SHA256=38b6ea058335663a54b10263657195b26eea05146532a6d07019da90dd11a620
V3_ZIP=production_disabled_post_code_deploy_review_v3_20260912.zip
V3_ZIP_SHA256=b324b9d94478e32987e62166ccb8032ab4dd480732b2b9a1f1138bbc524820c7
V4_ZIP=production_disabled_post_code_deploy_review_v4_20260912.zip
V4_ZIP_SHA256=77ecd36924719fbcfd3cdb0a58e19fc8160013e6267201be48e1199634676f74
V5_ZIP=production_disabled_post_code_deploy_review_v5_20260912.zip
V5_ZIP_SHA256=8a9b50705fc9c23ac4f62610fe0ec6f79b1248f76277fbdec7d827cf98015c84
V1_ZIP_OVERWRITE=NO
V2_ZIP_OVERWRITE=NO
V3_ZIP_OVERWRITE=NO
V4_ZIP_OVERWRITE=NO
V5_ZIP_OVERWRITE=NO
ACTIVE_STEP=1_POST_CODE_PRODUCTION_DEPLOY_PREPARATION
THIS IS NOT A PRODUCTION EXECUTION PACK.
THIS IS NOT AN APPLY PACK.
LIVE_COMPARE_V4_DO_NOT_RUN=YES

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
  WAL_ENABLE_IMPLICIT=NO

v5 independent review
---------------------
PASS: ZIP SHA / SHA256SUMS 66 files / 51 tests x2 / concurrency 20/20 /
_connect_idempotent() no longer sets journal_mode on each connect.
CHANGES_REQUIRED: migrate() still called ensure_wal_journal(conn)
unconditionally. main() calls migrate() on Production startup, so
step-1 disabled-POST code could change the live journal_mode and
create -wal/-shm. That contradicts:
  - disabled POST code only
  - migrate() no-op when 022 is already applied
  - step-1 does not change Production DB
  - no implicit WAL change

v6 fix
------
migrate() does not call ensure_wal_journal().
ensure_wal_journal() is removed. inspect_journal_mode() is read-only.
_connect_idempotent() still does not change journal_mode.
busy_timeout=30000 and isolation_level=IMMEDIATE stay.
WAL enable is not implemented. If needed later, it is a separate
Owner approval and a step-2 precondition before POST enable.
Counterexample: WAL-unset DELETE fixture + migrate() leaves DELETE
and does not create -wal/-shm.
test_separate_process_concurrency uses journal_mode=DELETE and is
run 20 times. Full suite is 52 tests (v5's 51 + the counterexample)
and is run twice.
SHA256SUMS.txt is generated last.

Canonical local implementation:
  review v6 files + no implicit WAL + v2 gate
  origin/main base commit: 25a3f88b8aab61a5462c06efa133b21865ef6083

Do not overwrite:
  production_disabled_post_code_deploy_review_20260912.zip
  production_disabled_post_code_deploy_review_v2_20260912.zip
  production_disabled_post_code_deploy_review_v3_20260912.zip
  production_disabled_post_code_deploy_review_v4_20260912.zip
  production_disabled_post_code_deploy_review_v5_20260912.zip
  any APPLY / backup / measure / live-compare ZIP

Do not run live-compare v4. Its recorded SHAs will not match v5/v6.

Independent re-run (no git clone):
  sha256sum -c SHA256SUMS.txt
  python3 run_tests.py

Do not create a Production deploy/execution pack from this run.

NEXT_STEP=INDEPENDENT_REVIEW_OF_DISABLED_POST_CODE_DEPLOY_V6_BUNDLE
