Production 022 APPLY / rollback / regression plan
=================================================

PACK=production_022_apply_rollback_regression_plan_20260911
KIND=REVIEW_PLAN_ONLY
NOT AN EXECUTION PACK.
Do not run 022 on Production from this pack.
Do not create an APPLY execution pack from this directory.

This pack is separate from:
  production_backup_owner_execution_20260911
Backup success is a precondition, not a simultaneous step.

Imported independent reviews
----------------------------
BACKUP_V2_INDEPENDENT_REVIEW_COMPLETE=YES
  ZIP_SHA256=9653f26224679d750ea1c3f578a0b8dda0e2178dab5b8ad464ee8cf9a42b9a5a
LIVE_SCHEMA_022_REHEARSAL_PASS=YES
  ZIP_SHA256=0ae58ef51b41336f2d71f761dc391aef5ede9cc8a29889c0d8eeb236bc6c8ee3
Claimed rehearsal v1 ZIP is audit-only and must not be reused:
  SHA256=7981db7fff2d8a8d0a057bf66aeddca72a37c842cdf66c926dd5d3f9ac4c1037

Hard gates (plan)
-----------------
1. Owner backup pack must have succeeded first
   APPLY_PRECONDITION_BACKUP_PASS=YES
   backup failure => APPLY forbidden
2. Default PREDICTION_RUNS_ENABLED=0
3. After 022, POST remains disabled
4. GET / UI / Conversation / RA / Challenge are not changed
5. POST enable and site switch are a later, separate change
6. PRODUCTION_APPLY_READY=NO until a future Owner-approved execution pack
7. PR #23-#29 must not merge as part of this plan

Re-run: python3 run_tests.py
This only validates documents and refuse-closed gates.
