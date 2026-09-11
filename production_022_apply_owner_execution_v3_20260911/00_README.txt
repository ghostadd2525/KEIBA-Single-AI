Production 022 APPLY Owner execution v3
=======================================

PACK=production_022_apply_owner_execution_v3_20260911
Owner runs only 02_powershell/OWNER_APPLY.ps1
Created, not approved for Production execution.

v1 and v2 independent reviews = CHANGES_REQUIRED. This v3 pack is new.
Do not overwrite the v1 or v2 ZIP.

V1_ZIP_SHA256=a34855f3dc7967f7801b05cdfad80099b6b5b261b1c2970019fca22cb53335ab
V2_ZIP_SHA256=f3152cdd3f92418da9c7a1f5227410f8fdff94e161ca3dda09c1e33c76bee75c

After unzip, required:
  sha256sum -c SHA256SUMS.txt

This pack applies 022_prediction_run_idempotency schema only,
in one RW transaction (BEGIN IMMEDIATE). POST stays disabled.
No site switch. No systemd/EnvironmentFile write.
Public GET smoke is part of the same remote procedure after COMMIT.
If that smoke cannot run here, POST_APPLY_REGRESSION_PASS is
PENDING_PUBLIC_SMOKE, not YES.

Owner backup canon imported (unchanged):
  BACKUP_PATH=/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups/20260911T175303Z/expect_ai.db
  BACKUP_SHA256=f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d
  SOURCE_IDENTITY=66305:349935
  BACKUP_IDENTITY=66305:287106

APPLY plan remains PASS and is not changed:
  SHA256=82d632dcac8169ea15181f80d4a3bc78213850a722cb56b877e2ff4e23aa453d

Do not run until independent review of this v3 pack.
Windows PowerShell 5.1 Parser.ParseFile is Owner-confirmed after that review.

Re-run: python3 run_tests.py
