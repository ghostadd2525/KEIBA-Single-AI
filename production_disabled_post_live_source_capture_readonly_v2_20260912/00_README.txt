Owner read-only Production live-source capture
==============================================

PACK=production_disabled_post_live_source_capture_readonly_v2_20260912
KIND=OWNER_READ_ONLY_LIVE_SOURCE_CAPTURE_V2
THIS IS NOT A PRODUCTION DEPLOY PACK.
THIS IS NOT AN APPLY PACK.
THIS IS NOT A LIVE-COMPARE RE-RUN.
Cursor must not SSH.
Owner must not run this until independent review of this capture pack PASSes.

Purpose
-------
Capture Production live bytes of exactly three files, via stdout only,
and save them on Windows only:

  app/main.py
  app/data/repository/__init__.py
  app/core/feature_loader_bridge.py

For each file record: resolved path, size, SHA256.
Emit an in-memory tar.gz as base64 on stdout. Windows saves exact
Owner-script bytes via SSH stdin (PowerShell 5.1 ReadAllBytes; no
Get-Content -Raw). Production is read-only open only. No Production
file create/change.
No SCP upload. No env dump. No sqlite. No race_id collection.
No secrets.

After Owner returns the captured bytes, run the local three-way diff:

  origin/main 25a3f88
  Production live (captured)
  code-deploy review v6 candidates

Do not overwrite existing review / live-compare / APPLY / backup /
live-source capture v1 ZIPs.
Do not create a Production deploy/execution pack from this run.

Ingested live-compare v5 Owner transcript (do not re-run v5)
------------------------------------------------------------
OWNER_LOG_SHA256=4a65fd2ca5f54284268975d90d28e65222c785421b204567bb3bf1780be28c94
COMPARE_RESULT=GO
GIT_HEAD=f02c50e8174d1537d829af3a0da6cc41d450baae
GIT_BRANCH=main
GIT_BEHIND_ORIGIN_MAIN=52
WORKTREE_DIRTY=YES

COMPARE_RESULT=GO is not a deploy approval.
PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_DEPLOY_APPROVED=NO
POST_CODE_PRODUCTION_DEPLOYED=NO

Live facts already recorded by v5 (not re-collected here):
  systemd loaded / active
  PREDICTION_RUNS_ENABLED=UNSET
  EXPECT_AI_ALLOW_MIGRATION_022=UNSET
  EXPECT_AI_ALLOW_MIGRATION_019=UNSET
  migrations=23, 022 row present, persist 019 ABSENT
  predictions=12 columns, partial UNIQUE OK
  POST code not deployed
  app/main.py=DIVERGENT (hunk-only later; never wholesale replace)
  app/data/db.py=MATCH_ORIGIN_MAIN
  app/data/repository/__init__.py=DIFFER
  app/core/feature_loader_bridge.py=DIFFER

Do not git pull / checkout / reset / merge / PR merge on Production.

Self-test (review environment only)
-----------------------------------
  python3 run_tests.py

NEXT_STEP=INDEPENDENT_REVIEW_OF_READONLY_LIVE_SOURCE_CAPTURE_V2
OWNER_EXECUTE_NOW=NO
PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_DEPLOY_APPROVED=NO
POST_CODE_PRODUCTION_DEPLOYED=NO
CURSOR_PRODUCTION_SSH=NO
DEPLOY_EXECUTION_PACK=NO
