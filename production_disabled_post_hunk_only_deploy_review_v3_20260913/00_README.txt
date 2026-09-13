Disabled POST hunk-only code-deploy review v3
=============================================

PACK=production_disabled_post_hunk_only_deploy_review_v3_20260913
KIND=HUNK_ONLY_CODE_DEPLOY_REVIEW_V3
THIS IS NOT A PRODUCTION EXECUTION PACK.
THIS IS NOT AN APPLY PACK.
Cursor must not SSH. Do not deploy from this bundle.

Purpose
-------
Same hunk-only candidates as v1/v2. Owner return ZIPs for the two
live ops files are now attached and ingested as live canon.

  1. live app/main.py is the base
  2. apply only the two review-v6 POST insertions
  3. keep every Production-only byte in live main.py
  4. precondition every deploy target with live SHA or ABSENT
  5. bundle live prediction_capacity.py and final_prediction_store.py
     as live canon / SHA precondition ONLY (not deploy candidates)
  6. leave PREDICTION_RUNS_ENABLED=0
  7. leave EXPECT_AI_ALLOW_MIGRATION_022 unset/0
  8. do not migrate / POST / restart / reload / change env or systemd

Candidate main.py (unchanged from hunk-only v1)
----------------------------------------------
live bytes + two insertions only
SIZE=48345
SHA256=a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c

Live canon NOT deploy
---------------------
app/ops/prediction_capacity.py
  SIZE=15241
  SHA256=c351bd9753d20994156e00141d564a55a42891983ecab5b2c5c55a32d9908f1e
  DEPLOY_CANDIDATE=NO
app/ops/final_prediction_store.py
  SIZE=22775
  SHA256=40352ff56b3267533267d5de9c893f3bda8963d5fe121474f7785b0152594a12
  DEPLOY_CANDIDATE=NO

Owner return ZIP SHA (verified, ingested)
-----------------------------------------
prediction_capacity_capture_windows_20260913.zip
  SHA256=c04f27e6bc9016927c9a902268ccfeb5a8ac8a62117ca74948b90bc7cbbea843
final_prediction_store_capture_windows_20260913_02.zip
  SHA256=f24d10d28ab99286894e36f60ff53fba3b89c087cac8afaa607c95a5b7670f8d

Independent re-run (no git clone, no Production)
------------------------------------------------
  sha256sum -c SHA256SUMS.txt
  python3 run_tests.py

run_tests.py:
  1. pack self-tests
  2. extract bundled origin/main 25a3f88
  3. overlay v6 files, then hunked main.py, then live ops canon
  4. 52 tests x2
  5. DELETE-journal 4-process concurrency x20
  6. extra Challenge / RA / GET row-delta=0 regressions

Do not overwrite hunk-only v1 ZIP
  f194488073a98a54fc4fafcadb808f32d3e0b8e53665dcb317da7c7662824db4
Do not overwrite hunk-only v2 ZIP
  9de787a0089ca2f6d3f5388f788a2f6246469dcc35ac3f110bcd1758952c3518
Owner capture v3 ZIP (live main/repository/bridge)
  f460685bcb59d837cca2f9b2c9154f51bf1d354f062ad6c26810bd86f2103a4a

This build
----------
LIVE_OPS_PRESENT_IN_THIS_BUILD=YES
Owner return ZIPs were attached and ingested via zipfile (Windows
backslash members accepted). Capture-tool fixtures are rejected.
Do not invent those files.

Do not create a Production deploy/execution pack from this run.

NEXT_STEP=INDEPENDENT_REVIEW_OF_HUNK_ONLY_V3_BUNDLE
PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_DEPLOY_APPROVED=NO
POST_CODE_PRODUCTION_DEPLOYED=NO
