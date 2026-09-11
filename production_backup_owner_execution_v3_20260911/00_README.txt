Production backup Owner execution v3
====================================

PACK=production_backup_owner_execution_v3_20260911
Owner runs only 02_powershell/OWNER_BACKUP.ps1
Created, not approved, not executed.

v2 is CHANGES_REQUIRED audit trail:
  SHA256=5675a8a3f4171e466620dc51c6e626667417a8f57e2df769730129da6da0409a
Do not overwrite or run v2.

APPLY plan remains PASS and is not changed:
  SHA256=82d632dcac8169ea15181f80d4a3bc78213850a722cb56b877e2ff4e23aa453d

P0 fixes vs v2
--------------
1. Owner inventory identity is embedded:
   INVENTORY_SOURCE_DEV=66305
   INVENTORY_SOURCE_INO=349935
   INVENTORY_DEV_INO_ABSENT is withdrawn.
2. Live source dest/ino must match before backup. Mismatch => DB_DRIFT=YES.
   size/mtime are recorded only.
3. Production env is read-only from systemd show Environment/EnvironmentFiles
   (LoadState=loaded unit only) and the service process environ.
   Windows login env is not evidence and is not forwarded.
4. HALT if PREDICTION_RUNS_ENABLED / EXPECT_AI_ALLOW_MIGRATION_022 /
   EXPECT_AI_ALLOW_MIGRATION_019 effective is 1, or if effective cannot
   be determined (unit not loaded, MainPID set but /proc unread,
   EnvironmentFile configured but unreadable). Only SET/UNSET and 0/1
   are logged. Raw Environment is not logged.

Re-run: python3 run_tests.py
