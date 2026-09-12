These logs are evidence of a pack-author ZIP-only re-run of
python3 run_tests.py (bundled origin/main 25a3f88 tar + overlay,
51 tests OK).

They are not a pass condition. Reviewers must execute run_tests.py
from the extracted ZIP. No external git clone is required.
INDEPENDENT_TEST_EXECUTION_PASS is printed only after a live run
that verifies the bundled base SHA, overlays files/, and asserts
Ran 51 tests / OK.
