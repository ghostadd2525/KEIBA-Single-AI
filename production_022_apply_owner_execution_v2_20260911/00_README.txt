Production 022 APPLY Owner execution v2
=======================================

PACK=production_022_apply_owner_execution_v2_20260911
Owner runs only 02_powershell/OWNER_APPLY.ps1
Created, not approved for Production execution.

v1 independent review = CHANGES_REQUIRED. This v2 pack is new.
Do not overwrite the v1 ZIP.

V1_ZIP_SHA256=a34855f3dc7967f7801b05cdfad80099b6b5b261b1c2970019fca22cb53335ab
V1_STDIN_PAYLOAD_SHA256=15ed986425eed779ea8ef5a1bd4b7beca5dbeb4eb041d67b9b64064a15b321fc

This pack applies 022_prediction_run_idempotency schema only,
in one RW transaction (BEGIN IMMEDIATE). POST stays disabled.
No site switch. No systemd/EnvironmentFile write.

Owner backup canon imported (unchanged):
  OUTPUT_SHA256=7b30a200067f75ca1bf4f7802d804c80cf6f364c1971e682781cf2f3207458bf
  BACKUP_PATH=/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups/20260911T175303Z/expect_ai.db
  BACKUP_SHA256=f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d
  SOURCE_IDENTITY=66305:349935
  BACKUP_IDENTITY=66305:287106

APPLY plan remains PASS and is not changed:
  SHA256=82d632dcac8169ea15181f80d4a3bc78213850a722cb56b877e2ff4e23aa453d

Do not run until independent review of this v2 pack.
Windows PowerShell 5.1 Parser.ParseFile is Owner-confirmed after that review.
This Linux host records pwsh Language.Parser.ParseFile only.

Re-run: python3 run_tests.py
