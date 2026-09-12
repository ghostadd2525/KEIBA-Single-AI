These logs are evidence of a pack-author independent re-run of
python3 run_tests.py (origin/main 25a3f88 overlay + 51 tests OK).

They are not a pass condition. Reviewers must execute run_tests.py.
If the base commit cannot be materialized, that script prints
RECORDED_LOCAL_TESTS_ONLY and does not set
INDEPENDENT_TEST_EXECUTION_PASS.
