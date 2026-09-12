Disabled POST code deploy — review bundle
========================================

PACK=production_disabled_post_code_deploy_review_20260912
ACTIVE_STEP=1_POST_CODE_PRODUCTION_DEPLOY_PREPARATION
THIS IS NOT A PRODUCTION EXECUTION PACK.
THIS IS NOT AN APPLY PACK.

022 schema is already COMMITTED on Production. This bundle only
prepares the Prediction Run code for a later Owner deploy while
POST stays disabled.

  PREDICTION_RUNS_ENABLED=0
  SITE_CORPUS_ACCUMULATION_ACTIVE=NO
  POST_CALL_ALLOWED=NO
  PRODUCTION_CODE_DEPLOY_ALLOWED=NO
  OWNER_DEPLOY_APPROVED=NO

Canonical local implementation:
  review v4 files (Prediction Run) + review v5 022 rebase of db.py
  origin/main base commit: 25a3f88b8aab61a5462c06efa133b21865ef6083

Do not overwrite:
  production_single_ai_prediction_run_local_review_20260910.zip
  production_single_ai_prediction_run_local_review_v2_20260911.zip
  production_single_ai_prediction_run_local_review_v3_20260911.zip
  production_single_ai_prediction_run_local_review_v4_20260911.zip
  production_single_ai_prediction_run_local_review_v5_022_20260911.zip
  any APPLY / backup / measure ZIP

Production live code was not fetched (Cursor SSH forbidden).
See 01_docs/production_live_compare_procedure.txt.

After independent review PASS and Owner deploy approval, a separate
execution pack may be created. Do not create it from this bundle run.

NEXT_STEP=INDEPENDENT_REVIEW_OF_DISABLED_POST_CODE_DEPLOY_BUNDLE
