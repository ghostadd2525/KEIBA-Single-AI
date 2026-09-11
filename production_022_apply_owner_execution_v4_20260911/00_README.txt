Production 022 APPLY Owner execution v4
=======================================

PACK=production_022_apply_owner_execution_v4_20260911
Owner runs only 02_powershell/OWNER_APPLY.ps1
Created, not approved for Production execution.

v1/v2/v3 independent reviews = CHANGES_REQUIRED. This v4 pack is new.
Do not overwrite the v1, v2, or v3 ZIP.

Remote hard deadline is 120s. Wrapper timeout is 240s, which is longer
than remote + drain 20s + kill-drain 8s + 40s buffer.
HTTP local/public timeouts are 3s. SQLite busy_timeout is 8s.
Commit is refused if remaining time is below 70s.
After commit, APPLY_EXECUTED=YES and APPLY_PHASE=COMMITTED are flushed
immediately; a later deadline fail still returns that committed state
before wrapper kill. Timeout fixtures keep those lines in drained stdout.

Public GET smoke validates JSON/HTML contracts with bounded reads and
redirect guards. SITE_UI_VISUAL_CHECKED=NO; Owner browser review is separate.

After unzip, required:
  sha256sum -c SHA256SUMS.txt

Do not run until independent review of this v4 pack.
Re-run: python3 run_tests.py
