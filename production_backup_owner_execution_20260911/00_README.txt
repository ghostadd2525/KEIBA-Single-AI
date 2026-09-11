Production backup Owner execution pack
======================================

PACK=production_backup_owner_execution_20260911
KIND=OWNER_EXECUTION_PACK
PURPOSE=BACKUP_ONLY
THIS PACK IS CREATED BUT NOT APPROVED AND NOT EXECUTED.

Uses the independently reviewed backup v2 contract byte-identical:
  REVIEWED_BACKUP_V2_ZIP_SHA256=9653f26224679d750ea1c3f578a0b8dda0e2178dab5b8ad464ee8cf9a42b9a5a
  REVIEWED_BACKUP_CONTRACT_SHA256=55890bbdff280548c43bb53f80930049e83ba16fb7d2abe2b7c1c7e34b91c66e

Canonical source (Owner live schema inventory):
  /home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db
  open: file:<path>?mode=ro + uri=True + PRAGMA query_only=ON

Dest:
  dedicated UTC timestamp directory under --dest-root
  directory 0700 / file 0600
  dest-root must not be the source parent or a shared directory

This pack does not:
  apply 022
  change systemd / env
  enable PREDICTION_RUNS_ENABLED
  set OWNER_PRODUCTION_BACKUP_APPROVED
  merge PR #23-#29
  overwrite existing ZIPs
  reuse claimed rehearsal v1 ZIP
    SHA256=7981db7fff2d8a8d0a057bf66aeddca72a37c842cdf66c926dd5d3f9ac4c1037

Backup failure => APPLY forbidden.
Backup success => APPLY_PRECONDITION_BACKUP_PASS=YES only.
PRODUCTION_APPLY_READY remains NO.

Re-run local tests: python3 run_tests.py
Owner steps: 00_docs/OWNER_STEPS.txt
