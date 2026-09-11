Production backup Owner execution v2
====================================

PACK=production_backup_owner_execution_v2_20260911
Owner runs only 02_powershell/OWNER_BACKUP.ps1
This pack is created, not approved, and not executed.

v1 Owner pack is CHANGES_REQUIRED audit trail:
  SHA256=35ef43ad03c0da93f76d85b3513ae8dcb32506468c22012e4bcd098ee6b33e19
  Do not overwrite or reuse it as the execution pack.

APPLY plan ZIP is independently reviewed PASS and is not changed:
  SHA256=82d632dcac8169ea15181f80d4a3bc78213850a722cb56b877e2ff4e23aa453d

What v2 changes
---------------
1. Windows PowerShell 5.1 OWNER_BACKUP.ps1 is the only Owner entry
2. Python bytes travel on SSH stdin (python3 -)
3. Production host is not assumed to already have 02_code/owner_backup.py
4. Source must match Owner inventory schema before backup starts
5. dest/ino must match a recorded inventory identity
   Owner inventory return did not include dest/ino
   This pack does not invent dest/ino
   INVENTORY_DEV_INO_ABSENT => HALT and require a new read-only inventory

Hard rules
----------
No SCP / remote mkdir from the wrapper / sudo / persistent env change
No 022 APPLY in this pack
Wrapper never sets OWNER_PRODUCTION_BACKUP_APPROVED
Without Owner explicit env, halt before SSH
EXPECT_AI_ALLOW_MIGRATION_022 set => halt
PREDICTION_RUNS_ENABLED=1 => halt
Backup file stays on the Production timestamp directory
Windows Downloads gets stdout audit only
No DB bytes / base64 / SCP exfil

Re-run: python3 run_tests.py
