Disabled POST hunk-only code-deploy review
=========================================

PACK=production_disabled_post_hunk_only_deploy_review_20260913
KIND=HUNK_ONLY_CODE_DEPLOY_REVIEW
THIS IS NOT A PRODUCTION EXECUTION PACK.
THIS IS NOT AN APPLY PACK.
THIS IS NOT A LIVE-COMPARE RE-RUN.
THIS IS NOT A CAPTURE RE-RUN.
Cursor must not SSH. Do not deploy from this bundle.

Purpose
-------
Build the step-1 Production code-deploy *candidates* from Owner-captured
live bytes, not from origin/main and not from review-v6 wholesale main.py.

  1. live app/main.py is the base
  2. apply only the two review-v6 POST insertions
  3. keep every Production-only byte in live main.py
  4. precondition every deploy target with live SHA or ABSENT
  5. leave PREDICTION_RUNS_ENABLED=0
  6. leave EXPECT_AI_ALLOW_MIGRATION_022 unset/0
  7. do not migrate / POST / restart / reload / change env or systemd

Owner capture canon (PASS, do not overwrite)
--------------------------------------------
ZIP=live_source_capture_v3_windows_20260913.zip
ZIP_SHA256=f460685bcb59d837cca2f9b2c9154f51bf1d354f062ad6c26810bd86f2103a4a
extracted/app/main.py
  SIZE=45983
  SHA256=7486a9ad7578e9ccdf883eaaac85f0b0de7ba329e286302b8d2f57db81d79235
extracted/app/data/repository/__init__.py
  SIZE=12823
  SHA256=557713a95b0e9f5a8f798eeb5e525c85adab3063b2e6529ee0be2155bb29992b
extracted/app/core/feature_loader_bridge.py
  SIZE=1408
  SHA256=e06e6ee971e2ae8d07bbcee4501ab9024052de52dd119ea007cb71481ae5272e

Related canon (do not overwrite)
--------------------------------
code-deploy review v6 ZIP SHA256=
  548b274facc2b4f8ffba8b854a6e009d8b7455fb816dcde9550eb9b364329373
origin/main commit=25a3f88b8aab61a5462c06efa133b21865ef6083
Production 022 schema=COMMITTED
PREDICTION_RUNS_ENABLED remains disabled

Three-way (already recorded)
----------------------------
live repository/__init__.py == origin/main != v6 candidate
live feature_loader_bridge.py == origin/main != v6 candidate
live main.py != origin/main != v6 candidate
live main.py is not in git history (Production worktree dirty)
Therefore wholesale main.py replace is forbidden.

Candidate main.py
-----------------
live bytes + two insertions only
SIZE=48345
SHA256=a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c
Reproduce with:
  python3 apply_live_post_hunk.py --write

Other deploy candidates are the review-v6 files (not live, because
live SHA == origin/main and v6 is the reviewed change).

Independent re-run (no git clone, no Production)
------------------------------------------------
  sha256sum -c SHA256SUMS.txt
  python3 run_tests.py

Do not treat any log file as success. Re-run the tests.

Do not create a Production deploy/execution pack from this run.

PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_DEPLOY_APPROVED=NO
POST_CODE_PRODUCTION_DEPLOYED=NO
NEXT_STEP=INDEPENDENT_REVIEW_OF_HUNK_ONLY_CODE_DEPLOY_BUNDLE
