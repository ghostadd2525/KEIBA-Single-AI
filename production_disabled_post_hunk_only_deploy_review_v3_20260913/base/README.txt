Bundled origin/main base — local test harness only
=================================================

This directory is NOT a Production deploy tree.
Do not copy base/ onto Production.

BASE_COMMIT=25a3f88b8aab61a5462c06efa133b21865ef6083
SCOPE=full origin/main tree (tests need public/ mocks plus win5-ai)
TAR=origin_main_25a3f88.tar.gz
Verify IDENTITY.txt TAR_SHA256 and SHA256SUMS.txt before use.
run_tests.py performs that verification, extracts to a temp dir,
overlays ../files/, and runs 51 unit tests.

External git clone is not required.
