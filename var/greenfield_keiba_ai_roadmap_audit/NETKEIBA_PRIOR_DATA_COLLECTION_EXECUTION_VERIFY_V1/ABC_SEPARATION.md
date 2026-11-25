# A / B / C Separation

Verified_at_JST: 2026-11-25T10:37:29+0900

Question under verification: Did **A** occur for the UNKNOWN=3117 prior-data campaign?

## A. New external network collection

| Check | Result |
|-------|--------|
| Network fetch ledger for campaign | ABSENT |
| HTTP status / URL / timestamp records | ABSENT |
| New saved files attributable to campaign fetch | ABSENT |
| Distinct from local reuse | N/A (nothing to distinguish) |

**A exists? NO**

## B. Local existing data reuse (first-time parse of already-on-disk HTML/AJAX/CSV)

| Check | Result |
|-------|--------|
| LOCAL_PRIOR_DATA_RECOVERY_V3 | ABSENT |
| Campaign parse of local cache resolving 3117 | ABSENT |
| Unrelated pipeline/debug CSVs | Present but not tied to UNKNOWN=3117 resolution |

**B for 3117 campaign? NO** (unrelated residual data ≠ campaign reuse)

## C. Recalculation only (F / C4 / B1 / CS / ALL4)

| Check | Result |
|-------|--------|
| Before/after metric packs for campaign | ABSENT |
| Recalc-only manifests | ABSENT |

**C for campaign? NO evidence**

## 3117 UNKNOWN partition

| Bucket | Count |
|--------|------:|
| Resolved by A (new external) | 0 |
| Resolved by B (local reuse) | 0 |
| Still UNKNOWN | 3117 |
| BEFORE_UNKNOWN | 3117 |
| AFTER_UNKNOWN | 3117 |
| NEWLY_RESOLVED_UNKNOWN | 0 |
| NEW_PRIOR_RECORDS | 0 |
