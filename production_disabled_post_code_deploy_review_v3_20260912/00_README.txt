Disabled POST code deploy — review bundle v3
===========================================

PACK=production_disabled_post_code_deploy_review_v3_20260912
SUPERSEDES_REVIEW=production_disabled_post_code_deploy_review_v2_20260912
V1_ZIP=production_disabled_post_code_deploy_review_20260912.zip
V1_ZIP_SHA256=474cb805c99d81235287b0a2a8a74fe9406c88f963024b98e6e1bf9a8154caaf
V2_ZIP=production_disabled_post_code_deploy_review_v2_20260912.zip
V2_ZIP_SHA256=38b6ea058335663a54b10263657195b26eea05146532a6d07019da90dd11a620
V1_ZIP_OVERWRITE=NO
V2_ZIP_OVERWRITE=NO
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

v2 independent review
---------------------
P0-1 PASS: disabled check before app.predictions.runs import
P1 PASS: corpus / RAEVAL / archived 019 excluded from deploy_files
P0 remaining: receiving env had no BASE_COMMIT object, so
run_tests.py printed RECORDED_LOCAL_TESTS_ONLY and could not
reproduce the 51-test run.

v3 harness fix
--------------
ZIP-only independent execution. No external git clone required.
base/ ships the origin/main 25a3f88 tree as a tar.gz plus SHA
manifest. run_tests.py verifies commit/SHA, extracts to a
temp directory, overlays files/, runs unittest, asserts 51 tests,
and prints INDEPENDENT_TEST_EXECUTION_PASS only on success.
Bundled tests/*.log is not a pass condition.

Implementation files/ and 01_docs/deploy_files.txt are unchanged
from v2.

Canonical local implementation:
  review v4 files + review v5 022 rebase of db.py + v2 gate
  origin/main base commit: 25a3f88b8aab61a5462c06efa133b21865ef6083

Do not overwrite:
  production_disabled_post_code_deploy_review_20260912.zip
  production_disabled_post_code_deploy_review_v2_20260912.zip
  production_single_ai_prediction_run_local_review_v4_20260911.zip
  production_single_ai_prediction_run_local_review_v5_022_20260911.zip
  any APPLY / backup / measure ZIP

Independent test re-run (no git clone):
  python3 run_tests.py

Production live code was not fetched (Cursor SSH forbidden).
See 01_docs/production_live_compare_procedure.txt.

Do not create a Production deploy/execution pack from this run.

NEXT_STEP=INDEPENDENT_REVIEW_OF_DISABLED_POST_CODE_DEPLOY_V3_BUNDLE
