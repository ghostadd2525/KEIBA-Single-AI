Read-only Production capture — prediction_capacity.py only
=======================================================

PACK=production_disabled_post_prediction_capacity_live_source_capture_readonly_20260913
KIND=OWNER_READ_ONLY_PREDICTION_CAPACITY_CAPTURE
THIS IS NOT A PRODUCTION DEPLOY PACK.
THIS IS NOT AN APPLY PACK.
THIS IS NOT AN EXECUTION PACK.
THIS IS NOT A HUNK-ONLY RE-REVIEW.
Cursor must not SSH.
Owner must not run this until independent review of this capture pack PASSes.

Why
---
Independent review of the hunk-only bundle was CHANGES_REQUIRED.
Overlaying the live-based candidate main.py onto review v6 / origin/main
25a3f88 failed 9 tests:

  ImportError: cannot import name 'prediction_capacity' from 'app.ops'

live main.py has a Production-only hard dependency:

  from .ops import prediction_capacity

Read-only search of git history, origin/main 25a3f88, Production GIT_HEAD
f02c50e, review v6 files, and existing ZIPs / artifacts found NO
app/ops/prediction_capacity.py. Identity cannot be proven.

This pack captures that one file, read-only, after independent review
and Owner approval. Capture is not executed from this run.

  CAPTURE_REL=app/ops/prediction_capacity.py
  OWNER_EXECUTE_NOW=NO
  STUB_OR_MOCK_SUCCESS=NO

After Owner returns live bytes (later):
  1. verify SHA/size of the captured file
  2. inspect its import closure (no stub)
  3. overlay the 11 hunk-only deploy candidates plus this live file
     onto origin/main 25a3f88
  4. re-run review v6 52 tests twice
  5. DELETE-journal 4-process concurrency x20
  6. live GET / Conversation / Challenge / RA regressions
Those steps are NOT in this pack.

Do not overwrite:
  hunk-only review ZIP
    f194488073a98a54fc4fafcadb808f32d3e0b8e53665dcb317da7c7662824db4
  capture v1/v2/v3, live-compare, or review v1-v6 ZIPs

Self-test (review environment only)
-----------------------------------
  python3 run_tests.py

NEXT_STEP=INDEPENDENT_REVIEW_OF_READONLY_PREDICTION_CAPACITY_CAPTURE
PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_DEPLOY_APPROVED=NO
POST_CODE_PRODUCTION_DEPLOYED=NO
