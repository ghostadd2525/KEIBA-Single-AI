Disabled POST code deploy — review bundle v2
===========================================

PACK=production_disabled_post_code_deploy_review_v2_20260912
SUPERSEDES_REVIEW=production_disabled_post_code_deploy_review_20260912
V1_ZIP_SHA256=474cb805c99d81235287b0a2a8a74fe9406c88f963024b98e6e1bf9a8154caaf
V1_ZIP_OVERWRITE=NO
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
  022_REAPPLY=NO
  SYSTEMD_CHANGED=NO
  ENV_CHANGED=NO

v1 CHANGES_REQUIRED fixes
-------------------------
P0-1: PREDICTION_RUNS_ENABLED disabled check runs in app/main.py
      before importing app.predictions.runs. If that import
      raises, disabled mode still returns 503 PREDICTION_RUNS_DISABLED
      with infer 0 / save 0.
P0-2: python3 run_tests.py materializes origin/main 25a3f88,
      overlays files/, and re-runs unittest. It does not treat
      bundled tests/*.log as a pass. If the base commit cannot
      be materialized: RECORDED_LOCAL_TESTS_ONLY and no
      INDEPENDENT_TEST_EXECUTION_PASS.
P1: Production deploy_files excludes corpus / RAEVAL holdout /
    archived 019 + README after dependency proof.
    Live compare stays a separate Owner read-only step.
    If live main.py SHA != origin/main, apply only the POST
    route hunk + new files. Do not replace main.py wholesale.

Canonical local implementation:
  review v4 files (Prediction Run) + review v5 022 rebase of db.py
  origin/main base commit: 25a3f88b8aab61a5462c06efa133b21865ef6083

Do not overwrite:
  production_disabled_post_code_deploy_review_20260912.zip
  production_single_ai_prediction_run_local_review_v4_20260911.zip
  production_single_ai_prediction_run_local_review_v5_022_20260911.zip
  any APPLY / backup / measure ZIP

Independent test re-run:
  python3 run_tests.py
  Optional: EXPECT_AI_BUNDLE_BASE=/path/to/KEIBA-Single-AI

Production live code was not fetched (Cursor SSH forbidden).
See 01_docs/production_live_compare_procedure.txt.

After independent review PASS and Owner deploy approval, a separate
execution pack may be created. Do not create it from this bundle run.

NEXT_STEP=INDEPENDENT_REVIEW_OF_DISABLED_POST_CODE_DEPLOY_V2_BUNDLE
