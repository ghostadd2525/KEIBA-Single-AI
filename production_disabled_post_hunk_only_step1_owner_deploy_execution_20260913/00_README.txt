Disabled POST hunk-only 工程1 Owner deploy execution pack
=======================================================

PACK=production_disabled_post_hunk_only_step1_owner_deploy_execution_20260913
KIND=OWNER_STEP1_CODE_DEPLOY_EXECUTION_REVIEW
THIS IS AN EXECUTION PACK FOR INDEPENDENT REVIEW.
IT IS NOT APPROVED TO RUN ON PRODUCTION.

Cursor must not SSH. Owner Windows PowerShell 5.1 only.
Do not execute OWNER_DEPLOY.ps1 until independent review PASS
and later explicit Owner deploy approval.

Purpose
-------
Deploy the 11 hunk-only v3 code files onto Production with
PREDICTION_RUNS_ENABLED left unset/0. Schema 022 stays COMMITTED.
Do not migrate. Do not reapply 022. Do not POST write runs.
Do not change env or systemd definitions.

Approved candidate main.py
--------------------------
live Production bytes + two review-v6 POST insertions only
SIZE=48345
SHA256=a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c
Wholesale replace with origin/main or review-v6 main.py is forbidden.

Live ops (verify SHA, do not deploy)
------------------------------------
app/ops/prediction_capacity.py
app/ops/final_prediction_store.py

Restart
-------
Code is imported at process start. After approved file replace,
exactly one `systemctl restart expect-ai.service` is required.
No sudo. No other unit. Not executed before Owner deploy approval.
Failure restore restarts once more only if a deploy restart already ran.

How to review (no Production)
-----------------------------
  sha256sum -c SHA256SUMS.txt
  python3 run_tests.py

How Owner would run later (not now)
-----------------------------------
  Windows PowerShell 5.1
  02_powershell/OWNER_DEPLOY.ps1
  Requires OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED=1
  Wrapper never sets that env.
  Pack/payload SHA is verified before SSH.

Do not overwrite hunk-only v1/v2/v3 ZIPs or 022 APPLY ZIPs.
Do not merge the PR from this pack.
Do not create extra capture packs unless a real P0 gap is found.

PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_DEPLOY_APPROVED=NO
POST_CODE_PRODUCTION_DEPLOYED=NO
NEXT_STEP=INDEPENDENT_REVIEW_OF_STEP1_OWNER_DEPLOY_EXECUTION_PACK
