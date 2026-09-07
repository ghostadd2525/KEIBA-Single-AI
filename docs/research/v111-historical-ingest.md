# Version11.1 - Historical Bundle Ingest

**Date:** 2026-07-27T08:06:29+00:00  
**Run:** `c4880226-5aaa-45da-8288-b7eba73f9bad`  
**Shadow only / Research only / Prediction mutation FORBIDDEN**  

## Result

- Ingested bundle rows: `372`
- Recoverable (Bundle+Winner): `367`
- Bundle only (winner missing): `5`
- Unrecoverable records: `0`
- Unique races with Bundle: `337`
- Unique Tie races: `15`

## Validation chain

```
Prediction Bundle → model_rank runners → RaceResult/Winner
```

- `recoverable`: Bundle + model_rank + winner restored
- `bundle_only`: Bundle OK but winner missing (Tie structure OK, outcome eval limited)
- `unrecoverable`: no usable Bundle -> excluded from Tie analysis

## Decision

```
Action Type: Historical Bundle Ingest (Research)
Prediction Mutation: FORBIDDEN
Product tables: READ-ONLY
```
