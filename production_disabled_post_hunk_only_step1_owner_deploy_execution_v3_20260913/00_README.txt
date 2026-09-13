Disabled POST hunk-only 工程1 Owner deploy execution pack v3
===========================================================

PACK=production_disabled_post_hunk_only_step1_owner_deploy_execution_v3_20260913
KIND=OWNER_STEP1_CODE_DEPLOY_EXECUTION_V3_REVIEW
THIS IS AN EXECUTION PACK FOR INDEPENDENT REVIEW.
IT IS NOT APPROVED TO RUN ON PRODUCTION.

Cursor must not SSH. Owner Windows PowerShell 5.1 only.
Do not execute OWNER_DEPLOY_V3.ps1 until independent review PASS
and later explicit Owner v3 deploy approval.
Do not run v1 OWNER_DEPLOY.ps1 or v2 OWNER_DEPLOY_V2.ps1.

Why v3
------
v2 FAIL → CODE_RESTORED. Restart itself succeeded:
  sudo -n systemctl restart expect-ai.service
  SYSTEMCTL_RESTART_EXIT=0 RESTART_MAINPID_CHANGED=YES
  RESTART_OUTCOME=SUCCESS
Then a single GET /health failed (HTTP_FAIL). Recovery restore ran.
Production is RESTORED. 11 candidate bytes unchanged.
v3 adds bounded readiness polling after a successful deploy restart.
Hypothesis POST_RESTART_STARTUP_WAIT_INSUFFICIENT is the design basis
and is not independently re-proven in this pack.

Purpose
-------
Deploy the same 11 hunk-only v3 code files onto Production with
PREDICTION_RUNS_ENABLED left unset/0. Schema 022 stays COMMITTED.
Do not migrate. Do not reapply 022. Do not POST write runs.
Do not change env or systemd definitions.

Approved candidate main.py (unchanged from v1/v2)
-------------------------------------------------
live Production bytes + two review-v6 POST insertions only
SIZE=48345
SHA256=a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c
Wholesale replace with origin/main or review-v6 main.py is forbidden.

Restart (unchanged from v2)
---------------------------
Exactly:
  sudo -n systemctl restart expect-ai.service
Timeout 60s. Transcript records SYSTEMCTL_RESTART_EXIT and redacted stderr.

Readiness (the v3 change)
-------------------------
After deploy restart SUCCESS, do not judge /health in a single shot.
Poll read-only systemctl show + GET /health until PASS or timeout.
  READINESS_POLL_TIMEOUT_S=45
  READINESS_POLL_INTERVAL_S=1.0
  READINESS_HTTP_TIMEOUT_S=2
  READINESS_MAX_ATTEMPTS=45
No infinite wait. No arbitrary long sleep-only wait.
Timeout => READINESS_TIMEOUT => code restore + one recovery restart
(same v2 safety boundary). systemd unit files and env are not edited.

How to review (no Production)
-----------------------------
  sha256sum -c SHA256SUMS.txt
  python3 run_tests.py

How Owner would run later (not now)
-----------------------------------
  Windows PowerShell 5.1
  02_powershell/OWNER_DEPLOY_V3.ps1
  Requires OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED=1
  Wrapper never sets that env.
  Wrapper never forwards OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED
  or OWNER_PRODUCTION_STEP1_V2_DEPLOY_APPROVED.
  Pack/payload SHA is verified before SSH.

Do not overwrite hunk-only v1/v2/v3 ZIPs, 022 APPLY ZIPs,
v1 execution ZIP a8d226c3..., v2 execution ZIP 20a273c7...,
or probe ZIP d9cff97f....
Do not merge the PR from this pack.
Do not create extra capture packs.

PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_DEPLOY_APPROVED=NO
POST_CODE_PRODUCTION_DEPLOYED=NO
OLD_EXECUTION_PACK_RERUN_ALLOWED=NO
V2_RERUN_ALLOWED=NO
NEXT_STEP=INDEPENDENT_REVIEW_OF_STEP1_OWNER_DEPLOY_EXECUTION_V3_PACK
