Owner read-only Production live compare v5
=========================================

PACK=production_disabled_post_live_compare_readonly_v5_20260912
KIND=OWNER_READ_ONLY_LIVE_COMPARE_V5
CODE_DEPLOY_REVIEW_V6=PASS
V6_REVIEW_ZIP_SHA256=548b274facc2b4f8ffba8b854a6e009d8b7455fb816dcde9550eb9b364329373
CANON=code-deploy review v6 deploy_files + file SHA
V1_ZIP_NOT_OVERWRITTEN=YES
V2_ZIP_NOT_OVERWRITTEN=YES
V3_ZIP_NOT_OVERWRITTEN=YES
V4_ZIP_NOT_OVERWRITTEN=YES
LIVE_COMPARE_V4_DO_NOT_RUN=YES
THIS IS NOT A PRODUCTION DEPLOY PACK.
THIS IS NOT AN APPLY PACK.
Cursor must not SSH.
Owner must not run this until independent review of this v5 pack PASSes.

Why v5
------
code-deploy review v6 is PASS. live-compare v4 still embeds v4/v5-era
candidate SHAs for db.py / repository/__init__.py. Those no longer
match v6. Do not run live-compare v1-v4 against v6.

v5 keeps v4 read-only contracts:
  - every git call uses --no-optional-locks via git_cmd()
  - LoadState valid only when exactly loaded
  - ExecStart allowlist / no raw Environment print
  - MUST_ABSENT PRESENT is STOP
  - 11 generated deploy hashes, never hand-typed

v5 additions from v6 canon:
  - candidate SHAs from review v6 (db.py 81fc91ad…, repository 9624699e…)
  - SCHEMA_MIGRATIONS_COUNT must be 23
  - PREDICTIONS_COLUMN_COUNT must be 12
  - active persist 019 row / file must be ABSENT
  - EXPECT_AI_ALLOW_MIGRATION_019 effective must be UNSET or ZERO
  - ActiveState must be active
  - flag ONE or schema mismatch => COMPARE_RESULT=STOP

Self-test (review environment only)
-----------------------------------
  python3 run_tests.py

Do not create a Production deploy/execution pack from this run.

NEXT_STEP=INDEPENDENT_REVIEW_OF_OWNER_READ_ONLY_LIVE_COMPARE_V5
OWNER_EXECUTE_NOW=NO
PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_DEPLOY_APPROVED=NO
POST_CODE_PRODUCTION_DEPLOYED=NO
