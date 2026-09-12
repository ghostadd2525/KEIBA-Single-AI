Production 022 APPLY Owner execution v5 (local design)
=====================================================

PACK=production_022_apply_owner_execution_v5_20260912
This is step 1: local v5 APPLY pack with measured HTTP limits.
Created, not approved for Production execution.
Do not re-run measurement v2. Do not APPLY.

v4 Owner log HALT_REASON=HTTP_BODY_OVERSIZED at a single 262144 JSON cap.
measurement v2 Owner canon (imported, not re-run):
  OUTPUT_SHA256=df96d93c11efb6e078b6756e6d9ab561cc68b70f6b6ee67d67d6b2a4f082de7e
  OWNER_MEASURE_STATUS=SUCCESS
  INTERNAL_LIST_BYTES=583853
  INTERNAL_DETAIL_BYTES=18563
  PRED_ROW_DELTA=0
  APPLY_EXECUTED=NO

Endpoint-separated APPLY HTTP limits (not one HTTP_MAX_JSON_BYTES):
  INTERNAL_HEALTH=65536
  INTERNAL_LIST=2097152   (~3.59x measured 583853)
  INTERNAL_DETAIL=262144  (~14.1x measured 18563)
  PUBLIC_JSON=262144
  PUBLIC_HTML=524288
Oversized still emits HTTP_ENDPOINT_CLASS / HTTP_BYTES_READ_AT_LEAST / HTTP_LIMIT_BYTES.

Historical backup is audit evidence only. It is NOT v5 APPLY canon.
  BACKUP_PATH=/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups/20260911T175303Z/expect_ai.db
  BACKUP_SHA256=f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d
  BACKUP_SIZE=105967616
Live source size is now 107237376 and predictions rows=301 (was 300).
Restoring that backup would lose newer rows. This pack HALTs
STALE_BACKUP_NOT_APPLY_CANON / APPLY_BACKUP_CANON_UNSET.

Progress:
  1 this pack (local design)
  2 v5 independent review
  3 Windows PowerShell 5.1 ParseFile
  4 Owner decision
  5 fresh Production backup in a separate approved pack
  6 verify that new backup
  7 new final pack that pins the new backup canon
  8 final independent review
  9 Owner explicit APPLY approval
  10 APPLY

Do not overwrite measurement v1/v2 or APPLY v1-v4 ZIPs.
Do not delete or overwrite the historical backup.

After unzip: sha256sum -c SHA256SUMS.txt
Re-run: python3 run_tests.py

PRODUCTION_022_APPLY_EXECUTION_ALLOWED=NO
OWNER_APPLY_APPROVED=NO
APPLY_EXECUTED=NO
NEXT_STEP=V5_LOCAL_DESIGN_WITH_MEASURED_LIMITS_THEN_FRESH_BACKUP
