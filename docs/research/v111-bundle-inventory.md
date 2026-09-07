# Version11.1 - Bundle Inventory

**Date:** 2026-07-27T08:06:29+00:00  
**Scope:** Research only / Prediction mutation FORBIDDEN  

## Totals

- Bundle candidate rows (sum across sources, may overlap): `381`
- Unique race_ids with Bundle (inventory scan): `337`
- Ingest unique races with Bundle: `337`
- Unique Tie races (|G|≥2): `15`
- Unique unrecoverable races: `0`

## Sources

| Source | Path | Rows | With Bundle | Unique races | Tie recoverable | Note |
|--------|------|-----:|------------:|-------------:|:---------------:|------|
| `db.predictions` | `var/expect_ai.db::predictions` | 56 | 56 | 53 | yes | Product table read-only; copied into research_historical_bundles |
| `db.prediction_history` | `var/expect_ai.db::prediction_history` | 0 | 0 | 0 | no | user view history; no Prediction Bundle payload |
| `db.research_prediction_snapshots` | `var/expect_ai.db::research_prediction_snapshots` | 57 | 0 | 0 | no | Evidence snapshots; usually features-only |
| `db.race_evaluations` | `var/expect_ai.db::race_evaluations` | 300 | 0 | 300 | no | hit metrics only; Bundle absent → unrecoverable for Tie |
| `real_285r_corpus` | `/home/ubuntu/KEIBA-Single-AI/research/v3_lab/baselines/offline_gate/real_285r_corpus.json` | 285 | 285 | 285 | yes | Offline gate corpus; horse_number often 0 → normalized by horse_id |
| `public.pi_json` | `/home/ubuntu/KEIBA-Single-AI/public/data/predictions` | 18 | 18 | 18 | yes | Rank/Confidence/HorseNumber → canonical Bundle |
| `miss_evidence` | `var/miss-evidence + var/improvement-evidence/miss` | 26 | 22 | 11 | yes | includes envelopes with payload.prediction_bundle |
| `baseline_285r_evaluations` | `/home/ubuntu/KEIBA-Single-AI/services/win5-ai/fixtures/stats/baseline-285r-evaluations.json` | 285 | 0 | 285 | no | evaluation-only; metadata / unrecoverable for Tie unless covered by real_285r |
| `tmp_api_captures` | `/home/ubuntu/KEIBA-Single-AI/tmp*pred*.json` | 0 | 0 | 0 | no | local API capture dumps; may duplicate live predictions |
| `s3_or_remote_backup` | `not found in checkout / EC2 var` | 0 | 0 | 0 | no | No S3 credentials or backup dumps discovered during inventory |

## By ingest source

| Source | Count |
|--------|------:|
| `db.predictions` | 56 |
| `real_285r_corpus` | 285 |
| `public.pi_json` | 9 |
| `miss_evidence` | 24 |
