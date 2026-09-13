Read-only diagnosis DESIGN for step1 RESTART_FAIL + CODE_RESTORED
================================================================

THIS IS NOT A DEPLOY PACK.
THIS IS NOT AN EXECUTION PACK.
THIS IS NOT A CAPTURE PACK.
Do not run OWNER_DEPLOY.ps1 again.
Do not create a replacement deploy pack from this document.
Do not systemctl restart or reload.
Do not sudo -n systemctl restart.
Cursor does not SSH.
Additional capture is not required for this design.

Frozen Owner result
-------------------
STEP1_DEPLOY_RESULT=FAILED_AND_RESTORED
PRECONDITIONS_PASS=YES
BACKUP_RECORDED=YES
FILES_REPLACED=YES
RESTART_EXECUTED=NO
HALT_REASON=RESTART_FAIL
CODE_RESTORED=YES
DEPLOY_PHASE=RESTORED
POST_CODE_PRODUCTION_DEPLOYED=NO
SSH_EXIT=2
AUDIT_STATUS=FAILED
REAPPLY_ALLOWED=NO
OWNER_DEPLOY_PS1_RERUN_ALLOWED=NO
PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_READONLY_STEP1_PROBE_APPROVED=YES
NEXT_STEP=OWNER_RUNS_REVIEWED_READONLY_RESTART_FAILURE_STATE_PROBE

022 schema / DB / env / systemd definitions reported unchanged.
Production code reported restored from the immediate pre-deploy backup.
Step1 is incomplete. Re-run of the reviewed deploy pack is forbidden.

Owner log used as foundation
----------------------------
FILE=production_disabled_post_hunk_only_step1_owner_deploy_execution_20260913_output_20260913_151821.txt
STARTED=2026-09-13T15:18:21
FINISHED=2026-09-13T15:18:44
BACKUP_DIR=/home/ubuntu/KEIBA-Single-AI/var/code_backups/20260913T061824Z
Imported copy:
  production_step1_restart_fail_readonly_probe_20260913/01_docs/owner_transcript_imported.txt

Purpose
-------
From that transcript + reviewed stdin bytes, record what is already
known and specify the remaining read-only checks for:
  1. exact systemctl restart exit code and stderr (historical; do not re-issue)
  2. whether ubuntu can restart expect-ai.service
  3. whether sudo -n systemctl restart is permitted (list only; do not run it)
  4. current LoadState / ActiveState / MainPID
  5. whether all 11 targets are back at pre-deploy SHA / ABSENT
  6. PREDICTION_RUNS_ENABLED / EXPECT_AI_ALLOW_MIGRATION_022/019 unset or 0
  7. schema 23 versions / 12 columns / partial UNIQUE still held

See 01_docs/seven_targets_log_diagnosis.txt and
01_docs/readonly_command_plan.txt.

A probe ZIP already exists and is frozen
(production_step1_restart_fail_readonly_probe_20260913.zip
SHA256 d9cff97f381a5ad36a4c743a7d85ba9d3840e90405f379525115987b807ddb9e).
Independent review of that ZIP is PASS.
Owner is approved to run OWNER_PROBE.ps1 once from Windows PS 5.1 after
setting OWNER_READONLY_STEP1_PROBE_APPROVED=1 (literal 1, not YES).
Cursor does not SSH. Do not run OWNER_DEPLOY.ps1. Do not restart.
