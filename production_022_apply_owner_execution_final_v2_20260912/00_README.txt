Production 022 APPLY Owner execution final v2
============================================

PACK=production_022_apply_owner_execution_final_v2_20260912
PACK_VERSION=final_v2
This pack imports the independent review of the final APPLY pack
(ZIP SHA256=4f80248bc8d7520db66e12089be578ee9606e4a6d7bd9d22271d33d39bc32916)
and adds a Windows wrapper stdin SHA256 enforcement gate.

Do not overwrite the existing final pack ZIP, APPLY v1-v5,
measurement v1/v2, backup Owner packs, or the APPLY plan ZIP.
Do not execute this pack from this agent.

P0 imported from independent review:
  FINAL_022_APPLY_PACK_REVIEW=CHANGES_REQUIRED
  The final OWNER_APPLY.ps1 logged STDIN_PAYLOAD_SHA256 but did not
  compare it to the pinned digest before SSH. This v2 wrapper compares
  the payload bytes to
  9a506fa195ddc4b88eaabfe10a28967fa46c537e8443ada6ef629531e93e18cf
  and HALTs before SSH on mismatch.

owner_apply_stdin.py is byte-identical to the reviewed final payload.
Do not change it.

Imported fresh backup Owner canon (not re-run):
  OWNER_BACKUP_STATUS=SUCCESS
  BACKUP_PATH=/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups/20260912T013332Z/expect_ai.db
  BACKUP_SHA256=32dfe70339a7237442d08a032d019ec03abbb8b85d0c90fa39d385e54da07e6a
  BACKUP_IDENTITY=66305:287343
  BACKUP_SIZE=107413504
  SOURCE_IDENTITY=66305:349935
  OWNER_LOG_SHA256=f3525b6fea85526083224b38a7d48271ae6a356c3af4bf67908efa07c852495d

Wrapper HALTs before SSH when:
  approval is unset
  APPLY backup canon is unset / pending / historical / mismatched
  stdin payload SHA256 does not match the pinned digest
  stdin payload is empty or any other Python file

Linux pwsh Parser.ParseFile is not official PASS.
Windows PowerShell 5.1 Parser.ParseFile PARSE_ERROR_COUNT=0 is
Owner-confirm pending. Do not record ALL_PASS for this pack.

After unzip: sha256sum -c SHA256SUMS.txt
Re-run: python3 run_tests.py

PRODUCTION_022_APPLY_EXECUTION_ALLOWED=NO
OWNER_APPLY_APPROVED=NO
APPLY_EXECUTED=NO
FINAL_022_APPLY_PACK_EXECUTION_ALLOWED=NO
NEXT_STEP=INDEPENDENT_REVIEW_OF_FINAL_V2_022_APPLY_PACK
