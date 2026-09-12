Production 022 APPLY Owner execution final
=========================================

PACK=production_022_apply_owner_execution_final_20260912
PACK_VERSION=final
This pack pins the Owner-verified fresh Production backup as the only
APPLY backup canon. It is created for independent review. It is not
approved for Production execution.

Do not overwrite APPLY v1-v5, measurement v1/v2, backup Owner packs,
or the APPLY plan ZIP. Do not execute this pack from this agent.

Imported fresh backup Owner canon (not re-run):
  OWNER_BACKUP_STATUS=SUCCESS
  BACKUP_PATH=/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups/20260912T013332Z/expect_ai.db
  BACKUP_SHA256=32dfe70339a7237442d08a032d019ec03abbb8b85d0c90fa39d385e54da07e6a
  BACKUP_IDENTITY=66305:287343
  BACKUP_SIZE=107413504
  SOURCE_IDENTITY=66305:349935
  OWNER_LOG_SHA256=f3525b6fea85526083224b38a7d48271ae6a356c3af4bf67908efa07c852495d

Historical backup remains audit evidence only:
  PATH=/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups/20260911T175303Z/expect_ai.db
  SHA256=f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d
Using that path/SHA as APPLY canon HALTs STALE_BACKUP_NOT_APPLY_CANON.
The Windows wrapper also HALTs before SSH if canon is unset, pending,
historical, or mismatched.

v5 local design is the base. Endpoint-separated HTTP limits stay:
  INTERNAL_HEALTH=65536
  INTERNAL_LIST=2097152
  INTERNAL_DETAIL=262144
  PUBLIC_JSON=262144
  PUBLIC_HTML=524288

v5 review imported:
  V5_LOCAL_DESIGN_REVIEW=PASS
  V5_OWNER_EXECUTION_ALLOWED=NO
Reason: v5 remote HALTed before GET/APPLY when canon was unset, but
OWNER_APPLY.ps1 started SSH when approval was 1. This final pack pins
canon in the wrapper and HALTs before SSH if it is not the fresh backup.

After unzip: sha256sum -c SHA256SUMS.txt
Re-run: python3 run_tests.py

PRODUCTION_022_APPLY_EXECUTION_ALLOWED=NO
OWNER_APPLY_APPROVED=NO
APPLY_EXECUTED=NO
NEXT_STEP=INDEPENDENT_REVIEW_OF_FINAL_022_APPLY_PACK
