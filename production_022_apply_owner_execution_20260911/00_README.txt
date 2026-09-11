Production 022 APPLY Owner execution
====================================

PACK=production_022_apply_owner_execution_20260911
Owner runs only 02_powershell/OWNER_APPLY.ps1
Created, not approved for Production execution.

This pack applies 022_prediction_run_idempotency schema only.
POST /v1/prediction-runs stays disabled.
No site switch. No systemd/EnvironmentFile write.

Owner backup canon imported:
  OUTPUT_SHA256=7b30a200067f75ca1bf4f7802d804c80cf6f364c1971e682781cf2f3207458bf
  BACKUP_PATH=/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups/20260911T175303Z/expect_ai.db
  BACKUP_SHA256=f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d
  SOURCE_IDENTITY=66305:349935
  BACKUP_IDENTITY=66305:287106

APPLY plan remains PASS and is not changed:
  SHA256=82d632dcac8169ea15181f80d4a3bc78213850a722cb56b877e2ff4e23aa453d

Do not run until independent review of this pack.

Re-run: python3 run_tests.py
