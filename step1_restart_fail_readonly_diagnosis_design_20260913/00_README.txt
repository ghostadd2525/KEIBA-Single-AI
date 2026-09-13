Read-only diagnosis DESIGN for step1 RESTART_FAIL + CODE_RESTORED
================================================================

THIS IS NOT A DEPLOY PACK.
THIS IS NOT AN EXECUTION PACK.
THIS IS NOT A CAPTURE PACK.
Do not run OWNER_DEPLOY.ps1 again.
Do not systemctl restart or reload.
Cursor does not SSH.

Owner result used as foundation (no full transcript attached)
------------------------------------------------------------
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
022 schema / DB / env / systemd definitions reported unchanged.
Production code reported restored from the immediate pre-deploy backup.
Step1 is incomplete. Re-run of the reviewed deploy pack is forbidden.

Purpose of this design
----------------------
Explain why HALT_REASON=RESTART_FAIL is consistent with the existing
payload, list the evidence the original pack did not emit, and specify
the read-only checks that can confirm:
  1. why `systemctl restart expect-ai.service` failed
  2. that disk is back at pre-deploy SHA/ABSENT
  3. that flags and schema 23/12/partial UNIQUE are unchanged
  4. whether the running process could still have loaded candidate bytes

Do not create a replacement deploy pack from this document.
A later Owner-gated read-only probe pack may be built from 01_docs/
only after this design is accepted. That probe must not restart.
