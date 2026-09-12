final v2 022 APPLY — Owner scope approval record
===============================================

This directory is an approval record only.
It is not an APPLY pack. It contains no OWNER_APPLY.ps1 and no stdin payload.
Do not treat this record as a new execution pack.

Imported independent review of the existing final v2 pack:

  FINAL_V2_ZIP_SHA256=bcf3020a4b4e3356f5ff7edb22dc499ded37332451669e58b4ebeca8691005e3
  STDIN_SHA256=9a506fa195ddc4b88eaabfe10a28967fa46c537e8443ada6ef629531e93e18cf
  FINAL_022_APPLY_PACK_REVIEW_RESULT=PASS
  WINDOWS_PS51_PARSEFILE=PASS
  PS_VERSION=5.1.26100.9444
  PS_EDITION=Desktop
  PARSE_ERROR_COUNT=0

Agent verification of the already-published ZIP (read-only):
  ZIP_SHA256_MATCH=YES
  STDIN_SHA256_MATCH=YES
  FINAL_V2_PACK_OVERWRITE=NO

Owner explicit scope:
  OWNER_SCOPE_APPROVED=022_SCHEMA_APPLY_ONLY
  OWNER_APPLY_APPROVED=YES
  APPROVED_PACK=production_022_apply_owner_execution_final_v2_20260912
  PREDICTION_RUNS_ENABLED_MUST_STAY=0

Approved action:
  Owner, from Windows PowerShell 5.1, runs the reviewed final v2
  02_powershell/OWNER_APPLY.ps1 once.
  That run may apply 022 schema migration to the Production DB using
  the pinned fresh backup as canon, then do the pack's same-run
  read-only regression checks.

Cursor must only record this approval.
Cursor must not open Production SSH and must not APPLY.

  CURSOR_PRODUCTION_SSH_ALLOWED=NO
  CURSOR_APPLY_ALLOWED=NO
  OWNER_LOCAL_EXECUTION_REQUIRED=YES
  NEXT_STEP=OWNER_RUNS_FINAL_V2_OWNER_APPLY_PS1_ON_WINDOWS
