Fresh Production backup Owner pack
==================================

PACK=production_backup_owner_execution_fresh_20260912
PACK_KIND=FRESH_PRODUCTION_BACKUP_OWNER_PACK
Owner runs only 02_powershell/OWNER_BACKUP.ps1
Created, not approved, not executed.

This pack copies the live Production DB at execution time into a new
timestamped directory. It does not APPLY 022. It does not restore.
It does not delete, overwrite, or reuse the historical backup.

v5 APPLY pack stays a local-design artifact. Do not overwrite or run it.
Do not create a v5 APPLY fix pack from this work.

Imported v5 independent review (pack not changed):
  V5_ZIP_SHA256=60cef7b2354d2c3a4b49e6a5f687537cc6188936ccbf9534ba070ca7667f84d8
  V5_STDIN_SHA256=b75b3fa2d0e1d1314e3a29571db48ab7e8ff197d1f292074ce280791dcf4b183
  V5_LOCAL_DESIGN_REVIEW=PASS
  V5_OWNER_EXECUTION_ALLOWED=NO
Reason imported: when fresh backup canon is unset, the v5 remote payload
halts before GET/APPLY, but OWNER_APPLY.ps1 starts SSH if the approval
variable is 1. That is not an SSH-before HALT.

Historical backup (audit only; not APPLY canon; do not touch):
  PATH=/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups/20260911T175303Z/expect_ai.db
  SHA256=f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d
  SIZE=105967616
  IDENTITY=66305:287106
A dest path that contains 20260911T175303Z, or that resolves to that
file/inode, HALTs HISTORICAL_BACKUP_DEST_REFUSED before copy.

Live source to copy (at execution time, not the historical file):
  CANONICAL_SOURCE=/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db
  DEV/INO=66305:349935
  LAST_MEASURED_SIZE=107237376
  LAST_MEASURED_PRED_ROWS=301

This pack does not pin APPLY backup canon. After this backup is created
and verified, a later final APPLY pack must embed the new path/SHA/dev/ino
in the Windows wrapper and HALT before SSH if that canon is unset.

backup_contract.py stays byte-identical
  SHA256=55890bbdff280548c43bb53f80930049e83ba16fb7d2abe2b7c1c7e34b91c66e
PS1 sends 02_powershell/owner_backup_stdin.py byte-for-byte to `python3 -`.
It does not concatenate Python files at runtime.
from __future__ import appears once.

Do not overwrite backup Owner v1-v4, APPLY v1-v5, measurement v1/v2,
or the APPLY plan ZIP. Do not merge PR #23-#40.

After unzip: sha256sum -c SHA256SUMS.txt
Re-run: python3 run_tests.py
Rebuild stdin after editing sources:
  python3 02_powershell/build_stdin_payload.py

PRODUCTION_022_APPLY_EXECUTION_ALLOWED=NO
OWNER_APPLY_APPROVED=NO
APPLY_EXECUTED=NO
PRODUCTION_BACKUP_EXECUTION_ALLOWED=NO
NEXT_STEP=INDEPENDENT_REVIEW_OF_FRESH_BACKUP_OWNER_PACK
