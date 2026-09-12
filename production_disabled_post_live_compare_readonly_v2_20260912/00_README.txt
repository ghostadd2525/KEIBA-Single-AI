Owner read-only Production live compare v2
=========================================

PACK=production_disabled_post_live_compare_readonly_v2_20260912
KIND=OWNER_READ_ONLY_LIVE_COMPARE_V2
V4_REVIEW_BUNDLE=PASS
V4_ZIP_SHA256=77ecd36924719fbcfd3cdb0a58e19fc8160013e6267201be48e1199634676f74
V1_PACK=production_disabled_post_live_compare_readonly_20260912
V1_ZIP_NOT_OVERWRITTEN=YES
V4_REVIEW_ZIP_NOT_OVERWRITTEN=YES
THIS IS NOT A PRODUCTION DEPLOY PACK.
THIS IS NOT AN APPLY PACK.
Cursor must not SSH.
Owner must not run this until independent review of v2 PASSes.

Why v2
------
v1 procedure was CHANGES_REQUIRED.
P0-1: snapshot.py expected SHA was a 59-char hand typo in the presented
      command block. v2 regenerates all 11 hashes from
      v4_reference/file_sha256.txt + actual files. No hand-typed deploy SHA.
P0-2: INDEX_CONTRACT now checks tbl_name, PRAGMA UNIQUE, exact columns,
      SQL target predictions(idempotency_key), and
      WHERE idempotency_key IS NOT NULL.
P1-1: Each of the 6 MUST_ABSENT files emits a specific STOP_REASON
      when PRESENT and forces COMPARE_RESULT=STOP.
P1-2: ExecStart is redacted. Environment raw values are not printed.

How to run (after independent review PASSes)
--------------------------------------------
1. SSH to Production as usual.
2. Do not copy this pack onto Production.
3. Paste OWNER_LIVE_COMPARE.sh (byte-identical to
   OWNER_PASTE_COMMAND_BLOCK.sh) into the remote shell, or
   bash -s < OWNER_LIVE_COMPARE.sh from local stdin. Stdout only.
4. Return the full stdout transcript.

Do not:
  tee / redirect to a Production file
  systemctl restart / edit
  export PREDICTION_RUNS_ENABLED
  export EXPECT_AI_ALLOW_MIGRATION_022
  run migrate()
  POST /v1/prediction-runs
  create a deploy/APPLY pack from this run

Self-test (review environment only)
-----------------------------------
  python3 run_tests.py

NEXT_STEP=INDEPENDENT_REVIEW_OF_OWNER_READ_ONLY_LIVE_COMPARE_V2
PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_DEPLOY_APPROVED=NO
POST_CODE_PRODUCTION_DEPLOYED=NO
