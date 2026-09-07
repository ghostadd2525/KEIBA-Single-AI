# Version11 Research — Corpus Expansion Gap

**Date:** 2026-07-27  
**Scope:** Research only / Prediction 変更禁止 / Shadow only  

## Current Corpus (EC2)

| Metric | Current | Target | Gap |
|--------|--------:|-------:|----:|
| Prediction | 340 | 3000 | 2660 |
| Tie | 9 | 300 | 291 |
| Young Horse | 33 | 300 | 267 |

### Source

| Source | Count | Note |
|--------|------:|------|
| live_prediction | 56 | full Prediction Bundle |
| miss_evidence | 1 | net-new after dedupe |
| baseline_eval | 283 | evaluation-only (no Bundle / no Tie) |

### Coverage

- Prediction Bundle: 56
- RaceResult: 334
- Evidence Snapshot: 55
- Shadow Result: 9
- Governance: linked (status=`sample_insufficient`)

## Root Cause of Gap

1. **Prediction < 3000** — Research DB に存在するフル Bundle は ~56。baseline 285r は評価シードのみで Bundle なし。
2. **Tie < 300** — Tie は Bundle の `model_rank` 共有からしか作れない。現状 Tie=9（Shadow 評価済み分と一致）。
3. **Young Horse < 300** — `race_name` / `class_label` が取れる行が少ない。Bundle の `race_info.race_name` と races catalog 結合で 33 まで改善。

## Hard Constraints

- Prediction Logic / PE / CE / AI / Challenge / ResultAutomation — **変更禁止**
- Shadow / Research DB のみ書き込み
- 目標未達を偽データで埋めない

## Next Ingest Plan (Research)

1. **Historical Prediction Bundle backfill**  
   Cloudflare Pages / 過去 API / ローカル archive から Bundle JSON を Research DB へ取り込み（Product predictions テーブルを書き換えない）。
2. **RaceResults historical backfill**  
   対応する着順・winner を揃えて Tie 評価母数を増やす。
3. **Class / age meta enrichment**  
   `race_info.race_name`・番組表・既存 `races.class_label` を正規化し Young Horse 判定を安定化。
4. **再ビルド**  
   `python -m app.research.collector_runner --build-prediction-corpus`

## Decision

```
Action Type: Corpus Expansion (Research Ingest)
Implementation Required: Yes (ingest pipeline next)
Prediction Mutation: FORBIDDEN
Deployment Required: Research-only on EC2
Targets Met: No
```
