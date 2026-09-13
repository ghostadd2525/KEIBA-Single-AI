Disabled POST hunk-only code-deploy review v2
=============================================

PACK=production_disabled_post_hunk_only_deploy_review_v2_20260913
KIND=HUNK_ONLY_CODE_DEPLOY_REVIEW_V2
THIS IS NOT A PRODUCTION EXECUTION PACK.
THIS IS NOT AN APPLY PACK.
Cursor must not SSH. Do not deploy from this bundle.

Purpose
-------
Same hunk-only candidates as v1, plus complete live dependencies
so the review v6 52-test overlay can run on live-based main.py.

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
Owner capture v3 ZIP (live main/repository/bridge)
  f460685bcb59d837cca2f9b2c9154f51bf1d354f062ad6c26810bd86f2103a4a

This build
----------
LIVE_OPS_PRESENT_IN_THIS_BUILD=NO
Owner return ZIPs for the two ops files were not attached here.
run_tests.py is fail-closed: OVERLAY_SUITE=NOT_RUN.
Do not invent those files. Do not use capture-tool fixtures.
See 01_docs/owner_return_intake.txt.

Do not create a Production deploy/execution pack from this run.

NEXT_STEP=INDEPENDENT_REVIEW_OF_HUNK_ONLY_V2_BUNDLE
PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_DEPLOY_APPROVED=NO
POST_CODE_PRODUCTION_DEPLOYED=NO
