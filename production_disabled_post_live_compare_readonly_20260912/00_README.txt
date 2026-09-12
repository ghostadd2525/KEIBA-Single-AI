Owner read-only Production live compare
======================================

PACK=production_disabled_post_live_compare_readonly_20260912
V4_REVIEW_BUNDLE=PASS
V4_ZIP_SHA256=77ecd36924719fbcfd3cdb0a58e19fc8160013e6267201be48e1199634676f74
THIS IS NOT A PRODUCTION DEPLOY PACK.
THIS IS NOT AN APPLY PACK.
Cursor must not SSH.

v4 code review passed. This pack only lets Owner collect
live evidence on the Production SSH host. No write, restart,
env change, migration, code copy, or POST.

How to run
----------
1. SSH to Production as usual.
2. Do not copy this pack onto Production.
3. Paste the entire contents of OWNER_LIVE_COMPARE.sh into the
   remote shell, or: bash -s < OWNER_LIVE_COMPARE.sh from a local
   stdin pipe. Stdout only.
4. Return the full stdout transcript.

Do not:
  tee / redirect to a Production file
  systemctl restart / edit
  export PREDICTION_RUNS_ENABLED
  export EXPECT_AI_ALLOW_MIGRATION_022
  run migrate()
  POST /v1/prediction-runs
  create a deploy/APPLY pack from this run

See:
  01_docs/production_live_compare_procedure.txt  (v4, unchanged intent)
  01_docs/judgment_table.txt
  01_docs/go_stop.txt

NEXT_STEP=OWNER_READ_ONLY_LIVE_COMPARE
