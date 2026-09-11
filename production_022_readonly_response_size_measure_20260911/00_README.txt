Production 022 GET-only response size measurement
=================================================

PACK=production_022_readonly_response_size_measure_20260911
Owner runs only 02_powershell/OWNER_MEASURE.ps1
This is not an APPLY pack. v4 is not re-run or overwritten.

v4 Owner log (imported facts, file bytes not present here):
  OUTPUT_SHA256=307fe722bbd75f650e4019a1d9eb600a0d39d3a15dd18245fd379536d14fa462
  HALT_REASON=HTTP_BODY_OVERSIZED
  stopped at PRE GET /v1/predictions
  APPLY_EXECUTED=NO

This pack measures internal GET sizes with bounded reads so v5 APPLY
limits can be chosen from evidence, not by bumping 262144.

Caps are measurement windows, not APPLY limits:
  INTERNAL_HEALTH=65536
  INTERNAL_LIST=8388608  (~12.6x smaller than inventory DB 105783296)
  INTERNAL_DETAIL=2097152
  PUBLIC_JSON=262144 (separated; not used for internal list)
  PUBLIC_HTML=524288

On oversized: HTTP_ENDPOINT_CLASS, HTTP_BYTES_READ_AT_LEAST, HTTP_LIMIT_BYTES.

After unzip: sha256sum -c SHA256SUMS.txt
Re-run: python3 run_tests.py
