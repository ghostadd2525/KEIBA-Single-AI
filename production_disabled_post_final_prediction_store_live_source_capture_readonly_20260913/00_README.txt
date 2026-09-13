Read-only Production capture — final_prediction_store.py only
==========================================================

PACK=production_disabled_post_final_prediction_store_live_source_capture_readonly_20260913
KIND=OWNER_READ_ONLY_FINAL_PREDICTION_STORE_CAPTURE
THIS IS NOT A PRODUCTION DEPLOY PACK.
THIS IS NOT AN APPLY PACK.
THIS IS NOT AN EXECUTION PACK.
THIS IS NOT A HUNK-ONLY RE-REVIEW.
Cursor must not SSH.
Owner must not run this until independent review of this capture pack PASSes.

Why
---
Owner independently verified the prediction_capacity.py capture:

  CAPTURE_RESULT=GO
  CAPTURE_ZIP_SHA256=c04f27e6bc9016927c9a902268ccfeb5a8ac8a62117ca74948b90bc7cbbea843
  FILE=app/ops/prediction_capacity.py
  SIZE=15241
  SHA256=c351bd9753d20994156e00141d564a55a42891983ecab5b2c5c55a32d9908f1e
  TRANSCRIPT_MANIFEST_FILE_SHA_MATCH=YES
  PYTHON_COMPILE=PASS

prediction_capacity.py is NOT a deploy candidate.
It is a Production existing-file SHA precondition and live canon for
repro tests only.

Overlay of origin/main 25a3f88 + the 11 hunk-only deploy
candidates + that live prediction_capacity.py, then review v6 52 tests:

  Ran 52 tests
  FAILED (failures=3)
  ModuleNotFoundError: No module named 'app.ops.final_prediction_store'

Failed contracts:
  GET detail response
  GET zero-write regression
  schema-not-ready existing GET regression

prediction_capacity.py real import closure (no stub/mock):
  stdlib: copy, os, threading, time, dataclasses, typing
  existing: app.engine.adapters.prediction_adapter
  missing on origin/main:
    app.ops.final_prediction_store
    symbols: get_store, persistent_store_enabled

Read-only search of git history, origin/main 25a3f88,
Production GIT_HEAD f02c50e, review/hunk/capture ZIPs, and
artifacts found NO Production-identical app/ops/final_prediction_store.py. Identity cannot be proven.

This pack captures that one file, read-only, after independent review
and Owner approval. Capture is not executed from this run.

  CAPTURE_REL=app/ops/final_prediction_store.py
  OWNER_EXECUTE_NOW=NO
  STUB_OR_MOCK_SUCCESS=NO
  EXECUTION_PACK=NO
  PREDICTION_CAPACITY_DEPLOY_CANDIDATE=NO

After Owner returns live bytes (later):
  1. verify SHA/size of the captured file
  2. inspect its import closure (no stub)
  3. overlay onto origin/main 25a3f88:
       the 11 hunk-only deploy candidates
       plus live prediction_capacity.py (canon, not deploy)
       plus this live final_prediction_store.py (canon, not deploy)
  4. re-run review v6 52 tests twice
  5. DELETE-journal 4-process concurrency x20
  6. live GET / Conversation / Challenge / RA regressions
Those steps are NOT in this pack.

Do not overwrite:
  hunk-only review ZIP
    f194488073a98a54fc4fafcadb808f32d3e0b8e53665dcb317da7c7662824db4
  prediction_capacity capture pack ZIP
    9f91bebe1646d8686ec182ff8b70e12b215526508e4c62b7eb86055c25b6a143
  Owner prediction_capacity return ZIP
    c04f27e6bc9016927c9a902268ccfeb5a8ac8a62117ca74948b90bc7cbbea843
  capture v1/v2/v3, live-compare, or review v1-v6 ZIPs

Self-test (review environment only)
-----------------------------------
  python3 run_tests.py

NEXT_STEP=INDEPENDENT_REVIEW_OF_READONLY_FINAL_PREDICTION_STORE_CAPTURE
PRODUCTION_CODE_DEPLOY_ALLOWED=NO
OWNER_DEPLOY_APPROVED=NO
POST_CODE_PRODUCTION_DEPLOYED=NO
