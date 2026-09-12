final v2 022 APPLY — Owner outcome record (corrected)
====================================================

This directory is a record only. It is not an APPLY pack.
Do not treat this record as a new execution pack.
Do not re-run final v2. Do not re-apply 022.

Imported independent review of the existing final v2 pack:

  FINAL_V2_ZIP_SHA256=bcf3020a4b4e3356f5ff7edb22dc499ded37332451669e58b4ebeca8691005e3
  STDIN_SHA256=9a506fa195ddc4b88eaabfe10a28967fa46c537e8443ada6ef629531e93e18cf
  FINAL_022_APPLY_PACK_REVIEW_RESULT=PASS
  WINDOWS_PS51_PARSEFILE=PASS

Correction of the previous record:
  RETRACTED: APPLY_EXECUTED=NO
  RETRACTED: NEXT_STEP=OWNER_RUNS_FINAL_V2_OWNER_APPLY_PS1_ON_WINDOWS

Owner canonical log (imported, not re-run):
  production_022_apply_owner_execution_final_v2_20260912_output_20260912_110613.txt
  LOG_SHA256=0d87136ea41f467a802bd170e10442a8cc8277613ab98de610829694ba480412

  PRODUCTION_022_SCHEMA_APPLIED=YES
  APPLY_EXECUTED=YES
  APPLY_PHASE=COMMITTED
  REMOTE_APPLY_EXECUTED=YES
  REMOTE_APPLY_PHASE=COMMITTED
  POST_APPLY_INTERNAL_REGRESSION=PASS
  POST_APPLY_PUBLIC_SMOKE=FAILED_HTTP_403
  POST_REMAINS_DISABLED=YES
  ROLLBACK_EXECUTED=NO

AUDIT_STATUS=FAILED and SSH_EXIT=2 are from the post-COMMIT public
smoke 403 on https://expect-keiba.com/. They do not mean the 022
transaction rolled back or was not applied.

Next step is Owner-browser visual confirmation and read-only 403
diagnosis only. Cursor does not SSH, APPLY, rollback, or restore.

  NEXT_STEP=READ_ONLY_PUBLIC_403_DIAGNOSIS_AND_OWNER_BROWSER_SMOKE
