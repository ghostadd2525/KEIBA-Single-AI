Owner read-only Production live compare v3
=========================================

PACK=production_disabled_post_live_compare_readonly_v3_20260912
KIND=OWNER_READ_ONLY_LIVE_COMPARE_V3
V4_REVIEW_BUNDLE=PASS
V4_ZIP_SHA256=77ecd36924719fbcfd3cdb0a58e19fc8160013e6267201be48e1199634676f74
V1_PACK=production_disabled_post_live_compare_readonly_20260912
V2_PACK=production_disabled_post_live_compare_readonly_v2_20260912
V1_ZIP_NOT_OVERWRITTEN=YES
V2_ZIP_NOT_OVERWRITTEN=YES
V4_REVIEW_ZIP_NOT_OVERWRITTEN=YES
THIS IS NOT A PRODUCTION DEPLOY PACK.
THIS IS NOT AN APPLY PACK.
Cursor must not SSH.
Owner must not run this until independent review of v3 PASSes.

Why v3
------
v2 independent review was CHANGES_REQUIRED.

P0-1: systemd show failure / missing unit / missing ExecStart /
      missing WorkingDirectory / unverified effective env on an
      active service are EVIDENCE_GAPS and force COMPARE_RESULT=STOP.
      LoadState is collected; not-found / error is STOP.

P0-2: ExecStart stdout is allowlist-only. Denylist secret-name
      matching is gone. Flag values, positionals, KEY=VALUE, URL/DSN/
      userinfo/Bearer/credential forms are never printed.

v2 PASS items are unchanged: generated 11 SHA, index contract,
MUST_ABSENT 6-file STOP, identical paste scripts.

How to run (after independent review PASSes)
--------------------------------------------
1. SSH to Production as usual.
2. Do not copy this pack onto Production.
3. Paste OWNER_LIVE_COMPARE.sh (byte-identical to
   OWNER_PASTE_COMMAND_BLOCK.sh) into the remote shell.
   Stdout only.
4. Return the full stdout transcript.

Self-test (review environment only)
-----------------------------------
  python3 run_tests.py

NEXT_STEP=INDEPENDENT_REVIEW_OF_OWNER_READ_ONLY_LIVE_COMPARE_V3
OWNER_EXECUTE_NOW=NO
PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_DEPLOY_APPROVED=NO
POST_CODE_PRODUCTION_DEPLOYED=NO
