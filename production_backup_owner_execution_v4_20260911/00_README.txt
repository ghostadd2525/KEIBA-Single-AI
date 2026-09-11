Production backup Owner execution v4
====================================

PACK=production_backup_owner_execution_v4_20260911
Owner runs only 02_powershell/OWNER_BACKUP.ps1
Created, not approved, not executed.

v3 is FAILED_RUNTIME_PAYLOAD_SYNTAX audit trail:
  SHA256=6a36403eb758fb2a176480bd8fb05fc001a1d878888513e49588ca18cc6327f8
  OUTPUT_SHA256=5b7bbea040506c0fdd1d8afec976bac7c6264bd7753ecc497ea5b024a4448dd3
Do not overwrite or rerun v3.

APPLY plan remains PASS and is not changed:
  SHA256=82d632dcac8169ea15181f80d4a3bc78213850a722cb56b877e2ff4e23aa453d

v4 payload
----------
PS1 sends 02_powershell/owner_backup_stdin.py byte-for-byte to `python3 -`.
It does not concatenate Python files at runtime.
from __future__ import appears once, at the allowed start of that file.
backup_contract.py stays byte-identical
  SHA256=55890bbdff280548c43bb53f80930049e83ba16fb7d2abe2b7c1c7e34b91c66e

Gates kept from v3
------------------
INVENTORY_SOURCE_DEV=66305
INVENTORY_SOURCE_INO=349935
live dest/ino match or DB_DRIFT=YES
Owner schema 22 / predictions 8 / idx_predictions_race
persist 019/022 absent, new 4 columns absent, partial UNIQUE absent
Production systemd/process/EnvironmentFile effective env
HALT if 022/019/POST effective 1 or undetermined
Owner approval required before SSH

Re-run: python3 run_tests.py
Rebuild stdin after editing sources:
  python3 02_powershell/build_stdin_payload.py
