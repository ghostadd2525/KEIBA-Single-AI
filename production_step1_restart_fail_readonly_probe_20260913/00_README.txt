Read-only Owner probe for step1 RESTART_FAIL + CODE_RESTORED
===========================================================

PACK=production_step1_restart_fail_readonly_probe_20260913
KIND=OWNER_READONLY_RESTART_FAIL_STATE_PROBE
THIS IS A READ-ONLY DIAGNOSIS PACK FOR INDEPENDENT REVIEW.
IT IS NOT A DEPLOY PACK. IT IS NOT A CAPTURE PACK.
IT IS NOT APPROVED TO RUN ON PRODUCTION.

Cursor must not SSH. Owner Windows PowerShell 5.1 only.
Do not execute OWNER_PROBE.ps1 until independent review PASS.
Do not re-run OWNER_DEPLOY.ps1. Do not restart or reload.

Source of truth (already returned and reviewed)
----------------------------------------------
Owner transcript FILE=
  production_disabled_post_hunk_only_step1_owner_deploy_execution_20260913_output_20260913_151821.txt
SSH_STARTED=YES SSH_TIMEOUT=NO SSH_EXIT_RAW=2
PRECONDITIONS_PASS=YES BACKUP_RECORDED=YES FILES_REPLACED=YES
HALT_REASON=RESTART_FAIL RESTART_EXECUTED=NO CODE_RESTORED=YES
DEPLOY_PHASE=RESTORED POST_CODE_PRODUCTION_DEPLOYED=NO
STEP1_DEPLOY_RESULT=FAILED_AND_RESTORED

Purpose
-------
Confirm the restored Production state after the failed restart,
without changing disk, env, systemd, schema, or process.

Checks (stdout only on Production; no files written there)
1. 11 targets restored to pre-deploy SHA / ABSENT
2. app/main.py is live 7486a9ad... not candidate a4970e70...
3. live ops 2-file SHA unchanged
4. expect-ai.service LoadState / ActiveState / MainPID / ActiveEnterTimestamp
5. bounded journalctl around the deploy window (no secrets / env / bodies)
6. ubuntu restart privilege via sudo -n -l only
7. never systemctl restart/reload
8. PREDICTION_RUNS_ENABLED / EXPECT_AI_ALLOW_MIGRATION_022/019 unset/0
9. schema 23 versions / 12 columns / partial UNIQUE, sqlite mode=ro
10. GET /health read-only
11. predictions row count before/after GET, delta=0

How to review (no Production)
-----------------------------
  sha256sum -c SHA256SUMS.txt
  python3 run_tests.py

How Owner would run later (not now)
-----------------------------------
  Windows PowerShell 5.1
  02_powershell/OWNER_PROBE.ps1
  Requires OWNER_READONLY_STEP1_PROBE_APPROVED=1
  Wrapper never sets that env.
  Wrapper never forwards OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED.
  Pack/payload SHA is verified before SSH.

PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_DEPLOY_PS1_RERUN_ALLOWED=NO
REAPPLY_ALLOWED=NO
POST_CODE_PRODUCTION_DEPLOYED=NO
NEXT_STEP=INDEPENDENT_REVIEW_OF_STEP1_READONLY_RESTART_FAIL_PROBE_PACK
