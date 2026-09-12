Owner read-only Production live compare v4
=========================================

PACK=production_disabled_post_live_compare_readonly_v4_20260912
KIND=OWNER_READ_ONLY_LIVE_COMPARE_V4
V4_REVIEW_BUNDLE=PASS
V4_REVIEW_ZIP_SHA256=77ecd36924719fbcfd3cdb0a58e19fc8160013e6267201be48e1199634676f74
V1_ZIP_NOT_OVERWRITTEN=YES
V2_ZIP_NOT_OVERWRITTEN=YES
V3_ZIP_NOT_OVERWRITTEN=YES
V4_REVIEW_ZIP_NOT_OVERWRITTEN=YES
THIS IS NOT A PRODUCTION DEPLOY PACK.
THIS IS NOT AN APPLY PACK.
Cursor must not SSH.
Owner must not run this until independent review of this v4 pack PASSes.

Why v4
------
v3 independent review was CHANGES_REQUIRED.

P0-1: Every git invocation uses --no-optional-locks via git_cmd().
      Regular git status can refresh .git/index and is forbidden.
      No GIT_OPTIONAL_LOCKS export and no git config on Production.

P1: LoadState is valid only when it is exactly loaded (case-insensitive).
    Empty, missing, not-found, error, bad-setting, and any other value
    are systemd_unit_not_loaded and COMPARE_RESULT=STOP.

v3 PASS items are unchanged: systemd evidence gaps, ExecStart allowlist,
generated 11 SHA, index contract, MUST_ABSENT STOP, identical scripts.

Self-test (review environment only)
-----------------------------------
  python3 run_tests.py

NEXT_STEP=INDEPENDENT_REVIEW_OF_OWNER_READ_ONLY_LIVE_COMPARE_V4
OWNER_EXECUTE_NOW=NO
PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_DEPLOY_APPROVED=NO
POST_CODE_PRODUCTION_DEPLOYED=NO
