Disabled POST hunk-only 工程1 Owner deploy execution pack v2
===========================================================

PACK=production_disabled_post_hunk_only_step1_owner_deploy_execution_v2_20260913
KIND=OWNER_STEP1_CODE_DEPLOY_EXECUTION_V2_REVIEW
THIS IS AN EXECUTION PACK FOR INDEPENDENT REVIEW.
IT IS NOT APPROVED TO RUN ON PRODUCTION.

Cursor must not SSH. Owner Windows PowerShell 5.1 only.
Do not execute OWNER_DEPLOY_V2.ps1 until independent review PASS
and later explicit Owner v2 deploy approval.
Do not run v1 OWNER_DEPLOY.ps1.

Why v2
------
v1 FAIL → CODE_RESTORED. Root cause: v1 ran
  systemctl restart expect-ai.service
without sudo. ubuntu has sudo -n restart NOPASSWD.
Production is RESTORED_AND_HEALTHY. 11 candidate bytes unchanged.

Purpose
-------
Deploy the same 11 hunk-only v3 code files onto Production with
PREDICTION_RUNS_ENABLED left unset/0. Schema 022 stays COMMITTED.
Do not migrate. Do not reapply 022. Do not POST write runs.
Do not change env or systemd definitions.

Approved candidate main.py (unchanged from v1)
----------------------------------------------
live Production bytes + two review-v6 POST insertions only
SIZE=48345
SHA256=a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c
Wholesale replace with origin/main or review-v6 main.py is forbidden.

Restart (the v2 change)
-----------------------
Exactly:
  sudo -n systemctl restart expect-ai.service
Timeout 60s (not 8s). Transcript always records
SYSTEMCTL_RESTART_EXIT and redacted stderr.
Timeout classifies SUCCESS / FAIL / UNKNOWN from unit state.
Success requires LoadState=loaded, ActiveState=active, MainPID>0,
and MainPID or ExecMainStartTimestamp changed from pre-deploy.
Postcheck: health 200, disabled POST 503, GET regression, row delta=0.
Postcheck failure: restore code only, then one recovery restart
with the same sudo -n argv.

How to review (no Production)
-----------------------------
  sha256sum -c SHA256SUMS.txt
  python3 run_tests.py

How Owner would run later (not now)
-----------------------------------
  Windows PowerShell 5.1
  02_powershell/OWNER_DEPLOY_V2.ps1
  Requires OWNER_PRODUCTION_STEP1_V2_DEPLOY_APPROVED=1
  Wrapper never sets that env.
  Wrapper never forwards OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED.
  Pack/payload SHA is verified before SSH.

Do not overwrite hunk-only v1/v2/v3 ZIPs, 022 APPLY ZIPs, or the
old execution ZIP a8d226c3....
Do not merge the PR from this pack.
Do not create extra capture packs.

PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_DEPLOY_APPROVED=NO
POST_CODE_PRODUCTION_DEPLOYED=NO
OLD_EXECUTION_PACK_RERUN_ALLOWED=NO
NEXT_STEP=INDEPENDENT_REVIEW_OF_STEP1_OWNER_DEPLOY_EXECUTION_V2_PACK
