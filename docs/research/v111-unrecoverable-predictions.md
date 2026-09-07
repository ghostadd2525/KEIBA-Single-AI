# Version11.1 - Unrecoverable Predictions

**Date:** 2026-07-27T08:06:29+00:00  
- Unique unrecoverable race_ids (no Bundle from ANY source): `0`
- Total unrecoverable records: `0`

## Definition

A race is unrecoverable for Tie analysis when `evaluation.runners[].model_rank`
cannot be restored from any researched source.
Metadata-only rows are kept but **excluded from Tie analysis**.

## Native sources without Bundle (before cross-source recovery)

| Source | Native Bundle | Note |
|--------|:-------------:|------|
| `db.race_evaluations` | no | hit metrics only |
| `baseline_285r_evaluations` | no | evaluation-only JSON |
| `db.prediction_history` | no | empty (0 rows) |
| `db.research_prediction_snapshots` | rare | evidence features, not full Bundle |
| `s3_or_remote_backup` | not found | no dump discovered |

## Cross-source recovery result

- Evaluations without any Bundle after ingest: see inventory
- Remaining unique unrecoverable races: `0`

If baseline/evaluations race_ids are covered by `real_285r_corpus` or live
`predictions.bundle_json`, they are **recoverable** and not listed below.

## By source / reason

| Source | Reason | Records | Unique races |
|--------|--------|--------:|-------------:|

## Samples

| Source | Race | Reason |
|--------|------|--------|
