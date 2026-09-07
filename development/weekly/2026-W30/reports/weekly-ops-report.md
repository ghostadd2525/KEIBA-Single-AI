# Weekly Ops Report — 2026-W30

**Operations Mode:** Version 8.5（正式運用）  
**Baseline Lock:** Version 8.5  
**Decision:** `no_improvement` （ok=true）  
**Incident:** 無  
**Generated:** 2026-07-26T12:59:35.691Z（JST 2026-07-26 Sun）

## Decision

- **value:** no_improvement
- **reason:** 改善案なし / 優位差なし。Version 維持は成功。
- **promote_to_production:** false
- **規則:** no_improvement / Version 維持は成功

## Baseline Health Check

| 項目 | 内容 |
|------|------|
| PE変更 | 無 |
| CE変更 | 無 |
| AI変更 | 無 |
| ResultAutomation正常 | OK |
| Miss Evidence正常 | OK |
| Knowledge更新 | OK |
| Governance更新 | NG |
| 285R比較実施 | NG |
| Feature Flag誤ON | 無 |
| Production Canary混入 | 無 |
| Baseline Lock | Version8.5 |
| Health OK | YES |

## Production Report

| 項目 | 値 |
|------|-----|
| ResultAutomation | ops_probe |
| race_results | — |
| race_evaluations | — |
| Miss件数 | 1 |
| Archive件数 | — |

## Research Report

| 項目 | 値 |
|------|-----|
| Miss件数 | 1 |
| Root Cause 主因 | miss_top1 |
| Proposal件数 | — |
| Validation Pass率 | — |
| Canary成功率 | — |
| Accept率 | — |
| Reject率 | — |
| no_improvement率 | — |

### Root Cause 分布

```json
{
  "miss_top1": 1
}
```

## Knowledge Report

| 項目 | 値 |
|------|-----|
| Active Pattern | — |
| Stale Pattern | — |
| Archived Pattern | — |
| Merge Candidate | — |
| Average Knowledge Score | — |

## Governance Report

| 項目 | 値 |
|------|-----|
| Active率 | — |
| Stale率 | — |
| Archive率 | — |
| Merge候補数 | — |
| Pattern寿命(平均週) | — |
| 平均 Knowledge Score | — |

## Analyzer Report

| 項目 | 値 |
|------|-----|
| Precision | — |
| Recall | — |
| Prediction Error | — |
| Confidence Calibration | {} |
| Validation Calibration | — |

## KPI Report（285R / 前週）

| 項目 | vs 285R | vs 前週 |
|------|---------|--------|
| Hit | — | — |
| Purchase | — | — |
| rank710 | — | — |
| other_miss | — | — |
| rank46 | — | — |

## Baseline（285R）

| 項目 | 値 |
|------|-----|
| baseline_id | formal-285r-offline-corpus |
| measured_delta_hit_at_1 | — |
| verdict | — |
| pe_mutated | false |

## Incident

- **無:** 異常トリガなし（Incident Report 未作成）

## Safety

- PE / CE / AI 変更なし: **true**
- Research → Production 非直結: **true**
- 新 Research 機能追加: **false**
- Baseline locked: **8.5**
- Operations Mode: **true**
