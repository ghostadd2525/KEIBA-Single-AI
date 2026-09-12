Disabled POST code deploy — review bundle v4
===========================================

PACK=production_disabled_post_code_deploy_review_v4_20260912
SUPERSEDES_REVIEW=production_disabled_post_code_deploy_review_v3_20260912
V1_ZIP=production_disabled_post_code_deploy_review_20260912.zip
V1_ZIP_SHA256=474cb805c99d81235287b0a2a8a74fe9406c88f963024b98e6e1bf9a8154caaf
V2_ZIP=production_disabled_post_code_deploy_review_v2_20260912.zip
V2_ZIP_SHA256=38b6ea058335663a54b10263657195b26eea05146532a6d07019da90dd11a620
V3_ZIP=production_disabled_post_code_deploy_review_v3_20260912.zip
V3_ZIP_SHA256=b324b9d94478e32987e62166ccb8032ab4dd480732b2b9a1f1138bbc524820c7
V1_ZIP_OVERWRITE=NO
V2_ZIP_OVERWRITE=NO
V3_ZIP_OVERWRITE=NO
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

v3 independent review
---------------------
PASS: ZIP SHA / integrity / bundled 25a3f88 base / 2565 files /
overlay 32 / ZIP-only 51 tests / INDEPENDENT_TEST_EXECUTION_PASS /
files/ and deploy_files.txt unchanged from v2 / no Production ops.
CHANGES_REQUIRED: top-level SHA256SUMS.txt did not match FLAGS.txt
because FLAGS was edited after SUMS was generated.

v4 fix
------
files/, deploy_files.txt, bundled base, and test content are
unchanged from v3. After every other file is finalized,
SHA256SUMS.txt is regenerated last. Independent extract must
pass `sha256sum -c SHA256SUMS.txt` before run_tests.py, then
`python3 run_tests.py` must print Ran 51 tests / OK /
INDEPENDENT_TEST_EXECUTION_PASS.

Canonical local implementation:
  review v4 files + review v5 022 rebase of db.py + v2 gate
  origin/main base commit: 25a3f88b8aab61a5462c06efa133b21865ef6083

Do not overwrite:
  production_disabled_post_code_deploy_review_20260912.zip
  production_disabled_post_code_deploy_review_v2_20260912.zip
  production_disabled_post_code_deploy_review_v3_20260912.zip
  any APPLY / backup / measure ZIP

Independent re-run (no git clone):
  sha256sum -c SHA256SUMS.txt
  python3 run_tests.py

Do not create a Production deploy/execution pack from this run.

NEXT_STEP=INDEPENDENT_REVIEW_OF_DISABLED_POST_CODE_DEPLOY_V4_BUNDLE
