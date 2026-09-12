These logs are evidence of a pack-author ZIP-only re-run of
python3 run_tests.py (bundled origin/main 25a3f88 tar + overlay,
52 tests OK twice, DELETE-journal concurrency x20 OK).

They are not a pass condition. Reviewers must first run
`sha256sum -c SHA256SUMS.txt`, then `python3 run_tests.py`.
No external git clone is required.
INDEPENDENT_TEST_EXECUTION_PASS is printed only after a live run
that verifies the bundled base SHA, overlays files/, asserts
neither _connect_idempotent() nor migrate() writes journal_mode,
then asserts Ran 52 tests / OK twice and
test_separate_process_concurrency x20 all PASS on DELETE fixture.
