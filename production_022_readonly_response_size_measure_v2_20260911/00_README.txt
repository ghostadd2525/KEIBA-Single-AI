Production 022 GET-only response size measurement v2
====================================================

PACK=production_022_readonly_response_size_measure_v2_20260911
v1 independent review = CHANGES_REQUIRED.
This v2 pack is new. Do not overwrite the v1 measurement ZIP or v1-v4 APPLY ZIPs.
Owner must not run this pack until v2 independent review PASS.
This agent must not measure or APPLY on Production.

P0-1 verify_pre_schema() is an exact Owner-canon gate before any HTTP GET:
  schema_migrations == owner 22 names (count 22, missing 0, extra 0, duplicate 0)
  022_prediction_run_idempotency absent
  019_prediction_run_idempotency absent
  predictions columns == owner 8 columns exactly
  new 4 persist columns all absent
  uq_predictions_idempotency_key_not_null absent
  idx_predictions_race exists with columns race_id,created_at in that order
Mismatch HALTs before HTTP GET. missing-only / cols[:8] / index-exists-only are not used.

P0-2 write flags are not measured in this pack (option B):
  CACHE_WRITE=NOT_CHECKED
  FILE_WRITE=NOT_CHECKED
  CACHE_OR_FILE_WRITE_VERIFIED=NO
Do not emit CACHE_WRITE=NO or FILE_WRITE=NO without a measured inventory.

Detail GET emits INTERNAL_DETAIL_HTTP_STATUS, INTERNAL_DETAIL_OVERSIZED,
and INTERNAL_DETAIL_JSON_PARSE separately.
Detail oversized => OWNER_MEASURE_STATUS=PARTIAL.
HTTP status != 200 or JSON parse fail is not SUCCESS.
race_id values are not logged. POST is refused. Row delta must stay 0.
gzip wire/decoded stay separate. Body caps stay measurement windows, not APPLY limits.

Caps (measurement windows, not APPLY limits):
  INTERNAL_HEALTH=65536
  INTERNAL_LIST=8388608  (~12.6x smaller than inventory DB 105783296)
  INTERNAL_DETAIL=2097152
  PUBLIC_JSON=262144 (separated; not used for internal list)
  PUBLIC_HTML=524288

After unzip: sha256sum -c SHA256SUMS.txt
Re-run: python3 run_tests.py

PRODUCTION_022_APPLY_EXECUTION_ALLOWED=NO
OWNER_APPLY_APPROVED=NO
APPLY_EXECUTED=NO
NEXT_STEP=INDEPENDENT_REVIEW_OF_MEASUREMENT_V2
